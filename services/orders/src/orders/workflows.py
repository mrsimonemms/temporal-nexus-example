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

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from orders.activities import OrderActivities
    from orders.inventory_service import (
        ALLOCATION_ALLOCATED,
        ALLOCATION_INSUFFICIENT_STOCK,
        ALLOCATION_REJECTIONS,
        INVENTORY_ENDPOINT,
        STOCK_FOUND,
        STOCK_UNKNOWN_PRODUCT,
        AllocateStockInput,
        CheckStockInput,
        InventoryService,
    )
    from orders.models import Order, OrderInput, OrderResult

# Long enough for a presenter to stop and restart the Inventory worker while
# an order waits on the stock check. On timeout the Workflow fails; it never
# assumes stock is available.
CHECK_STOCK_TIMEOUT = timedelta(minutes=2)

# Same convention as the stock check. On timeout the Workflow fails; it never
# assumes stock was allocated.
ALLOCATE_STOCK_TIMEOUT = timedelta(minutes=2)


def parse_request(raw: Any) -> OrderInput:
    """Validate the raw JSON request and convert it to an OrderInput.

    The Workflow accepts raw JSON rather than OrderInput so that wrongly typed
    fields fail the Workflow here, instead of failing payload decoding (which
    would retry the Workflow Task indefinitely).
    """
    if not isinstance(raw, dict):
        raise invalid_request("request must be a JSON object")

    problems = []
    for field in ("orderId", "customerRef", "sku"):
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{field} is required")

    quantity = raw.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        problems.append("quantity must be a positive integer")

    if problems:
        raise invalid_request("; ".join(problems))

    return OrderInput(
        orderId=raw["orderId"],
        customerRef=raw["customerRef"],
        sku=raw["sku"],
        quantity=raw["quantity"],
    )


def insufficient_stock(sku: str, requested: int, available: int) -> ApplicationError:
    """Structured, non-retryable failure. Type, message and details are visible
    in Temporal UI and CLI."""
    return ApplicationError(
        f"Insufficient stock for {sku}: requested {requested}, available {available}",
        {
            "sku": sku,
            "requestedQuantity": requested,
            "availableQuantity": available,
        },
        type="INSUFFICIENT_STOCK",
        non_retryable=True,
    )


def invalid_request(message: str) -> ApplicationError:
    # Non-retryable: an invalid request will never succeed on retry.
    return ApplicationError(message, type="InvalidRequest", non_retryable=True)


@workflow.defn(name="OrderWorkflow")
class OrderWorkflow:
    @workflow.run
    async def run(self, raw_request: Any) -> OrderResult:
        """Input: {"orderId", "customerRef", "sku", "quantity"}."""
        request = parse_request(raw_request)

        # Check stock through the Inventory Nexus Operation. Infrastructure
        # failures and timeouts raise and fail this Workflow.
        inventory = workflow.create_nexus_client(
            service=InventoryService, endpoint=INVENTORY_ENDPOINT
        )
        stock = await inventory.execute_operation(
            InventoryService.check_stock,
            CheckStockInput(sku=request.sku),
            schedule_to_close_timeout=CHECK_STOCK_TIMEOUT,
        )

        if stock.status == STOCK_UNKNOWN_PRODUCT:
            return OrderResult(
                status="unknown_product",
                message=f"unknown product {request.sku}; order not recorded",
            )
        if stock.status != STOCK_FOUND:
            raise ApplicationError(
                f"unexpected stock status {stock.status!r}",
                type="UnexpectedInventoryResponse",
                non_retryable=True,
            )
        if stock.available < request.quantity:
            raise insufficient_stock(request.sku, request.quantity, stock.available)

        # Allocate stock through the Inventory Nexus Operation. Allocation is
        # authoritative: stock may have changed since the check above.
        # Inventory uses the order ID as the idempotency key, so retrying an
        # order does not consume stock twice.
        allocation_result = await inventory.execute_operation(
            InventoryService.allocate_stock,
            AllocateStockInput(
                orderId=request.orderId,
                customerRef=request.customerRef,
                sku=request.sku,
                quantity=request.quantity,
            ),
            schedule_to_close_timeout=ALLOCATE_STOCK_TIMEOUT,
        )

        if allocation_result.status == ALLOCATION_INSUFFICIENT_STOCK:
            # Use the quantity from the atomic allocation check, not the
            # earlier (possibly stale) stock check.
            if allocation_result.available is None:
                raise ApplicationError(
                    "insufficient_stock response is missing available",
                    type="UnexpectedInventoryResponse",
                    non_retryable=True,
                )
            raise insufficient_stock(
                request.sku, request.quantity, allocation_result.available
            )
        if allocation_result.status in ALLOCATION_REJECTIONS:
            return OrderResult(
                status=allocation_result.status,
                message=(
                    f"allocation rejected: {allocation_result.message}; "
                    "order not recorded"
                ),
            )
        if (
            allocation_result.status != ALLOCATION_ALLOCATED
            or allocation_result.allocation is None
        ):
            raise ApplicationError(
                f"unexpected allocation status {allocation_result.status!r}",
                type="UnexpectedInventoryResponse",
                non_retryable=True,
            )

        order = Order(
            orderId=request.orderId,
            customerRef=request.customerRef,
            sku=request.sku,
            quantity=request.quantity,
            inventoryChecked=True,
            inventoryAllocated=True,
            allocationId=allocation_result.allocation.allocationId,
        )

        return await workflow.execute_activity_method(
            OrderActivities.record_order,
            order,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=5,
            ),
        )
