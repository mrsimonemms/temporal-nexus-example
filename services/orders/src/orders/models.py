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

"""Request and result types for the Orders service.

Field names are camelCase so the JSON payloads match the other services'
contracts.
"""

from dataclasses import dataclass


@dataclass
class OrderInput:
    orderId: str
    customerRef: str
    sku: str
    quantity: int


@dataclass
class Order:
    orderId: str
    customerRef: str
    sku: str
    quantity: int
    # True once Inventory has confirmed enough stock. Checking does not
    # reserve stock.
    inventoryChecked: bool = False
    # True once Inventory has allocated (reserved) the stock.
    inventoryAllocated: bool = False
    # Inventory's allocation reference, using Inventory's field name.
    allocationId: str | None = None


@dataclass
class OrderResult:
    # "recorded", "conflict", "unknown_product", "invalid_quantity" or
    # "insufficient_stock". "recorded" means stock was allocated and the order
    # saved; it is not shipped. Other statuses mean the order was not recorded.
    status: str
    order: Order | None = None
    message: str = ""
