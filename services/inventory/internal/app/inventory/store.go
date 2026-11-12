/*
 * Copyright 2026 Simon Emms <simon@simonemms.com>
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package inventory

import (
	"maps"
	"fmt"
	"sync"
)

// SeedStock is the stock loaded when the worker starts. All stock and
// allocation records are held in memory and reset when the worker restarts.
var SeedStock = map[string]int{
	"WIDGET-1": 10,
	"GADGET-1": 3,
	"GIZMO-1":  0,
}

// Store is a process-local, in-memory inventory. It is only correct when a
// single Inventory worker process is running.
type Store struct {
	mu          sync.Mutex
	stock       map[string]int
	allocations map[string]Allocation // keyed by order ID
}

func NewStore(seed map[string]int) *Store {
	stock := make(map[string]int, len(seed))
	maps.Copy(stock, seed)

	return &Store{
		stock:       stock,
		allocations: map[string]Allocation{},
	}
}

// CheckStock reads the available quantity for a SKU without changing it.
func (s *Store) CheckStock(sku string) CheckStockResult {
	s.mu.Lock()
	defer s.mu.Unlock()

	qty, ok := s.stock[sku]
	if !ok {
		return CheckStockResult{SKU: sku, Status: StockStatusUnknownProduct}
	}

	return CheckStockResult{SKU: sku, Available: qty, Status: StockStatusFound}
}

// Allocate checks availability and reserves stock in one locked operation.
// The order ID is the idempotency key.
func (s *Store) Allocate(req AllocateStockInput) AllocateStockResult {
	s.mu.Lock()
	defer s.mu.Unlock()

	if existing, ok := s.allocations[req.OrderID]; ok {
		if existing.CustomerRef == req.CustomerRef && existing.SKU == req.SKU && existing.Quantity == req.Quantity {
			// Identical repeat: return the original allocation, consume nothing.
			return AllocateStockResult{Status: AllocationStatusAllocated, Allocation: &existing}
		}

		return AllocateStockResult{
			Status:  AllocationStatusConflict,
			Message: fmt.Sprintf("order %s already has a different allocation (%s)", req.OrderID, existing.AllocationID),
		}
	}

	if req.Quantity <= 0 {
		return AllocateStockResult{
			Status:  AllocationStatusInvalidQuantity,
			Message: "quantity must be a positive integer",
		}
	}

	available, ok := s.stock[req.SKU]
	if !ok {
		return AllocateStockResult{
			Status:  AllocationStatusUnknownProduct,
			Message: fmt.Sprintf("unknown product %s", req.SKU),
		}
	}

	if available < req.Quantity {
		return AllocateStockResult{
			Status:    AllocationStatusInsufficientStock,
			Message:   fmt.Sprintf("requested %d of %s but only %d available", req.Quantity, req.SKU, available),
			Available: &available,
		}
	}

	s.stock[req.SKU] = available - req.Quantity

	allocation := Allocation{
		AllocationID: "ALLOC-" + req.OrderID,
		OrderID:      req.OrderID,
		CustomerRef:  req.CustomerRef,
		SKU:          req.SKU,
		Quantity:     req.Quantity,
	}
	s.allocations[req.OrderID] = allocation

	return AllocateStockResult{Status: AllocationStatusAllocated, Allocation: &allocation}
}
