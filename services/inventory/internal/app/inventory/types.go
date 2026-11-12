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

// Business outcomes are returned as a status rather than as errors, so the
// Workflow completes successfully and the caller decides what to do next.

type StockStatus string

const (
	StockStatusFound          StockStatus = "found"
	StockStatusUnknownProduct StockStatus = "unknown_product"
)

type AllocationStatus string

const (
	AllocationStatusAllocated         AllocationStatus = "allocated"
	AllocationStatusUnknownProduct    AllocationStatus = "unknown_product"
	AllocationStatusInvalidQuantity   AllocationStatus = "invalid_quantity"
	AllocationStatusInsufficientStock AllocationStatus = "insufficient_stock"
	AllocationStatusConflict          AllocationStatus = "conflict"
)

type CheckStockInput struct {
	SKU string `json:"sku"`
}

type CheckStockResult struct {
	SKU       string      `json:"sku"`
	Available int         `json:"available"`
	Status    StockStatus `json:"status"`
}

type AllocateStockInput struct {
	OrderID     string `json:"orderId"`
	CustomerRef string `json:"customerRef"`
	SKU         string `json:"sku"`
	Quantity    int    `json:"quantity"`
}

type Allocation struct {
	AllocationID string `json:"allocationId"`
	OrderID      string `json:"orderId"`
	CustomerRef  string `json:"customerRef"`
	SKU          string `json:"sku"`
	Quantity     int    `json:"quantity"`
}

type AllocateStockResult struct {
	Status     AllocationStatus `json:"status"`
	Allocation *Allocation      `json:"allocation,omitempty"`
	Message    string           `json:"message,omitempty"`
}
