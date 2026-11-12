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

from temporalio import activity

from orders.models import OrderInput, OrderResult
from orders.store import OrderStore


class OrderActivities:
    """Activities own all access to the in-memory store."""

    def __init__(self, store: OrderStore) -> None:
        self._store = store

    @activity.defn
    async def record_order(self, request: OrderInput) -> OrderResult:
        result = self._store.record(request)
        activity.logger.info(
            "Orders: record order orderId=%s status=%s",
            request.orderId,
            result.status,
        )
        return result
