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

import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from orders.activities import OrderActivities
from orders.constants import TASK_QUEUE
from orders.store import OrderStore
from orders.workflows import OrderWorkflow

logger = logging.getLogger("orders")


async def run() -> None:
    # Load connection settings from TEMPORAL_* environment variables only.
    # File loading is disabled so no temporal.toml is read.
    connect_config = ClientConfig.load_client_connect_config(disable_file=True)

    client = await Client.connect(**connect_config)

    # In-memory store shared by the Activities in this process.
    activities = OrderActivities(OrderStore())

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[OrderWorkflow],
        activities=[activities.record_order],
    )

    logger.info(
        "Orders: worker started address=%s namespace=%s taskQueue=%s",
        connect_config["target_host"],
        client.namespace,
        TASK_QUEUE,
    )
    await worker.run()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(run())


if __name__ == "__main__":
    main()
