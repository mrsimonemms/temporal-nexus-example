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
// Package service exposes Inventory Workflows to other services through Nexus.
// Callers depend only on these names and the JSON contract in the inventory
// package, never on the internal Workflow names.
package service

import (
	"context"

	"github.com/mrsimonemms/temporal-nexus/example/services/inventory/internal/app/inventory"
	"github.com/mrsimonemms/temporal-nexus/example/services/inventory/internal/app/workflows"
	"github.com/nexus-rpc/sdk-go/nexus"
	"go.temporal.io/sdk/client"
	"go.temporal.io/sdk/temporalnexus"
)

const (
	// ServiceName is the Nexus Service: the named collection of Operations.
	ServiceName = "inventory"

	// Nexus Operations callers invoke.
	CheckStockOperationName    = "check-stock"
	AllocateStockOperationName = "allocate-stock"
)

// CheckStockOperation is an asynchronous, Workflow-backed Operation that runs
// CheckStockWorkflow and returns its result to the caller.
var CheckStockOperation = temporalnexus.NewWorkflowRunOperation(
	CheckStockOperationName,
	workflows.CheckStockWorkflow,
	func(ctx context.Context, input inventory.CheckStockInput, options nexus.StartOperationOptions) (client.StartWorkflowOptions, error) {
		return client.StartWorkflowOptions{
			// RequestID is stable across retries of the same Operation start, so
			// a retried request does not start a second Workflow.
			ID: "check-stock-" + options.RequestID,
		}, nil
	},
)

// AllocateStockOperation is an asynchronous, Workflow-backed Operation that
// runs AllocateStockWorkflow. Idempotency comes from the order ID inside the
// Inventory store, so repeating an order does not consume stock twice.
var AllocateStockOperation = temporalnexus.NewWorkflowRunOperation(
	AllocateStockOperationName,
	workflows.AllocateStockWorkflow,
	func(ctx context.Context, input inventory.AllocateStockInput, options nexus.StartOperationOptions) (client.StartWorkflowOptions, error) {
		return client.StartWorkflowOptions{
			// RequestID is stable across retries of the same Operation start, so
			// a retried request does not start a second Workflow.
			ID: "allocate-stock-" + options.RequestID,
		}, nil
	},
)

// New builds the Inventory Nexus Service.
func New() (*nexus.Service, error) {
	svc := nexus.NewService(ServiceName)
	if err := svc.Register(CheckStockOperation, AllocateStockOperation); err != nil {
		return nil, err
	}

	return svc, nil
}
