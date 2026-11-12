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

"""Process-local, in-memory order store.

Records reset when the worker restarts. Only correct with a single Orders
worker process.
"""

import threading

from orders.models import Order, OrderInput, OrderResult


class OrderStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._orders: dict[str, Order] = {}

    def record(self, request: OrderInput) -> OrderResult:
        """Record an order, using the order ID as the idempotency key."""
        with self._lock:
            existing = self._orders.get(request.orderId)
            if existing is not None:
                if (
                    existing.customerRef == request.customerRef
                    and existing.sku == request.sku
                    and existing.quantity == request.quantity
                ):
                    # Identical repeat: return the original record.
                    return OrderResult(status="recorded", order=existing)

                return OrderResult(
                    status="conflict",
                    message=(
                        f"order {request.orderId} already exists "
                        "with different details"
                    ),
                )

            order = Order(
                orderId=request.orderId,
                customerRef=request.customerRef,
                sku=request.sku,
                quantity=request.quantity,
            )
            self._orders[order.orderId] = order

            return OrderResult(status="recorded", order=order)
