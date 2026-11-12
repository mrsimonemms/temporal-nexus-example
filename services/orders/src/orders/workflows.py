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
    from orders.models import OrderInput, OrderResult


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


def invalid_request(message: str) -> ApplicationError:
    # Non-retryable: an invalid request will never succeed on retry.
    return ApplicationError(message, type="InvalidRequest", non_retryable=True)


@workflow.defn(name="OrderWorkflow")
class OrderWorkflow:
    @workflow.run
    async def run(self, raw_request: Any) -> OrderResult:
        """Input: {"orderId", "customerRef", "sku", "quantity"}."""
        request = parse_request(raw_request)

        # PLACEHOLDER (inventory): check available stock for request.sku via
        # the Inventory Nexus Operation. Not implemented yet.

        # PLACEHOLDER (inventory): allocate request.quantity of request.sku to
        # request.customerRef via the Inventory Nexus Operation, keyed by
        # request.orderId. Not implemented yet.

        return await workflow.execute_activity_method(
            OrderActivities.record_order,
            request,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=5,
            ),
        )
