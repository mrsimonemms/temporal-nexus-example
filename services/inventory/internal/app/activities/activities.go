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
package activities

import (
	"context"

	"github.com/mrsimonemms/temporal-nexus/example/services/inventory/internal/app/inventory"
	"go.temporal.io/sdk/activity"
)

// Activities own every read and write of the in-memory store, keeping the
// Workflows deterministic.
type Activities struct {
	store *inventory.Store
}

func (a *Activities) CheckStock(ctx context.Context, input inventory.CheckStockInput) (*inventory.CheckStockResult, error) {
	result := a.store.CheckStock(input.SKU)

	activity.GetLogger(ctx).Info("Inventory: stock checked",
		"sku", result.SKU, "available", result.Available, "status", result.Status)

	return &result, nil
}

func (a *Activities) AllocateStock(ctx context.Context, input inventory.AllocateStockInput) (*inventory.AllocateStockResult, error) {
	result := a.store.Allocate(input)

	activity.GetLogger(ctx).Info("Inventory: allocation requested",
		"orderId", input.OrderID, "sku", input.SKU, "quantity", input.Quantity, "status", result.Status)

	return &result, nil
}

func NewActivities(store *inventory.Store) (*Activities, error) {
	return &Activities{store: store}, nil
}
