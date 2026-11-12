# Copyright 2026 Simon Emms <simon@simonemms.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Public Nexus contract for the Inventory service.

This mirrors the Go Inventory service's Nexus names and JSON field names. The
Orders service depends only on this contract, not on Inventory's code or
internal Workflow names.
"""

from dataclasses import dataclass

import nexusrpc

# Endpoint: the named routing destination, created on the Temporal server.
INVENTORY_ENDPOINT = "inventory"

# Values of CheckStockResult.status.
STOCK_FOUND = "found"
STOCK_UNKNOWN_PRODUCT = "unknown_product"

# Values of AllocateStockResult.status. Anything other than "allocated" is a
# business rejection: no stock was consumed.
ALLOCATION_ALLOCATED = "allocated"
ALLOCATION_REJECTIONS = (
    "unknown_product",
    "invalid_quantity",
    "insufficient_stock",
    "conflict",
)


@dataclass
class CheckStockInput:
    sku: str


@dataclass
class CheckStockResult:
    sku: str
    available: int
    status: str


@dataclass
class AllocateStockInput:
    orderId: str  # Inventory's idempotency key
    customerRef: str
    sku: str
    quantity: int


@dataclass
class Allocation:
    allocationId: str
    orderId: str
    customerRef: str
    sku: str
    quantity: int


@dataclass
class AllocateStockResult:
    status: str
    # Present only when status is "allocated".
    allocation: Allocation | None = None
    message: str = ""


# Service: the named collection of Operations.
@nexusrpc.service(name="inventory")
class InventoryService:
    # Operation: the callable contract. Looks up stock; does not reserve it.
    check_stock: nexusrpc.Operation[CheckStockInput, CheckStockResult] = (
        nexusrpc.Operation(name="check-stock")
    )
    # Operation: atomically checks and reserves stock for an order.
    allocate_stock: nexusrpc.Operation[AllocateStockInput, AllocateStockResult] = (
        nexusrpc.Operation(name="allocate-stock")
    )
