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
package workflows

import (
	"time"

	"github.com/mrsimonemms/temporal-nexus/example/services/inventory/internal/app/activities"
	"github.com/mrsimonemms/temporal-nexus/example/services/inventory/internal/app/inventory"
	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/workflow"
)

// Activities only touch process memory, so they should finish almost
// instantly. Business outcomes are returned as values, so retries only cover
// infrastructure failures (eg, the worker stopping mid-Activity).
var activityOptions = workflow.ActivityOptions{
	StartToCloseTimeout: 10 * time.Second,
	RetryPolicy: &temporal.RetryPolicy{
		InitialInterval:    time.Second,
		BackoffCoefficient: 2,
		MaximumInterval:    10 * time.Second,
		MaximumAttempts:    5,
	},
}

var a *activities.Activities

// CheckStockWorkflow reports the available stock for a SKU. It does not
// change stock.
func CheckStockWorkflow(ctx workflow.Context, input inventory.CheckStockInput) (*inventory.CheckStockResult, error) {
	ctx = workflow.WithActivityOptions(ctx, activityOptions)

	var result inventory.CheckStockResult
	if err := workflow.ExecuteActivity(ctx, a.CheckStock, input).Get(ctx, &result); err != nil {
		return nil, err
	}

	return &result, nil
}

// AllocateStockWorkflow atomically checks availability and allocates stock to
// a customer. The order ID is the idempotency key.
func AllocateStockWorkflow(ctx workflow.Context, input inventory.AllocateStockInput) (*inventory.AllocateStockResult, error) {
	if input.OrderID == "" || input.CustomerRef == "" {
		return nil, temporal.NewNonRetryableApplicationError("orderId and customerRef are required", "InvalidRequest", nil)
	}

	ctx = workflow.WithActivityOptions(ctx, activityOptions)

	var result inventory.AllocateStockResult
	if err := workflow.ExecuteActivity(ctx, a.AllocateStock, input).Get(ctx, &result); err != nil {
		return nil, err
	}

	return &result, nil
}
