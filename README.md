# temporal-nexus-example

A Temporal Nexus reference architecture

<!-- toc -->

* [Inventory service](#inventory-service)
  * [Start the worker](#start-the-worker)
  * [Workflows](#workflows)
  * [Seeded stock](#seeded-stock)
  * [Limitations](#limitations)
* [Orders service](#orders-service)
  * [Install](#install)
  * [Configure and start the worker](#configure-and-start-the-worker)
  * [Run OrderWorkflow](#run-orderworkflow)
  * [Order storage limitations](#order-storage-limitations)
* [Contributing](#contributing)
  * [Open in a container](#open-in-a-container)
  * [Commit style](#commit-style)

<!-- Regenerate with "pre-commit run -a markdown-toc" -->

<!-- tocstop -->

## Inventory service

A Go worker on the `Inventory` Task Queue. It does not have Nexus operations yet.

### Start the worker

Start a local Temporal server (for example, `temporal server start-dev`), then:

```sh
cd services/inventory
go run ./cmd/worker
```

The worker connects using the `TEMPORAL_ADDRESS` and `TEMPORAL_NAMESPACE`
environment variables. The defaults are `localhost:7233` and `default`.

### Workflows

`CheckStockWorkflow` reports available stock. It does not change stock.

```sh
temporal workflow execute --task-queue Inventory --type CheckStockWorkflow \
  --workflow-id check-widget --input '{"sku":"WIDGET-1"}'
# {"sku":"WIDGET-1","available":10,"status":"found"}
```

`AllocateStockWorkflow` checks stock and allocates it in one locked step:

```sh
temporal workflow execute --task-queue Inventory --type AllocateStockWorkflow \
  --workflow-id allocate-order-1 \
  --input '{"orderId":"order-1","customerRef":"cust-1","sku":"WIDGET-1","quantity":4}'
# {"status":"allocated","allocation":{"allocationId":"ALLOC-order-1",...}}
```

Business outcomes appear in `status`. The Workflow still completes:

* `CheckStockWorkflow`: `found` or `unknown_product`.
* `AllocateStockWorkflow`: `allocated`, `unknown_product`, `invalid_quantity`,
  `insufficient_stock` or `conflict`.

The order ID is the idempotency key. Repeating an identical request returns the
existing allocation without using more stock. Reusing the same order ID with
different details returns `conflict`.

### Seeded stock

| SKU | Quantity |
| --- | --- |
| `WIDGET-1` | 10 |
| `GADGET-1` | 3 |
| `GIZMO-1` | 0 |

### Limitations

Stock and allocation records are stored in the worker's memory.

* Run exactly **one** Inventory worker process. Multiple workers would each have
  separate stock.
* Restarting the worker resets stock to the seeded values and loses all
  allocation records, including idempotency records.

## Orders service

A Python worker on the `Orders` Task Queue. Requires Python 3.10+.

### Install

```sh
cd services/orders
python3 -m venv .venv
.venv/bin/pip install -e .
```

### Configure and start the worker

Connection settings come from environment variables only. File-based
configuration (`temporal.toml`) is disabled.

| Variable | Default |
| --- | --- |
| `TEMPORAL_ADDRESS` | `localhost:7233` |
| `TEMPORAL_NAMESPACE` | `default` |
| `TEMPORAL_API_KEY` | unset (only needed for Temporal Cloud) |

Other `TEMPORAL_*` variables are listed in the
[environment configuration docs](https://docs.temporal.io/develop/environment-configuration).

```sh
.venv/bin/orders-worker
```

### Run OrderWorkflow

```sh
temporal workflow execute --task-queue Orders --type OrderWorkflow \
  --workflow-id order-1 \
  --input '{"orderId":"order-1","customerRef":"cust-1","sku":"WIDGET-1","quantity":2}'
# {"status":"recorded","order":{"orderId":"order-1",...,
#   "inventoryChecked":false,"inventoryAllocated":false},"message":""}
```

`recorded` only means the order was saved. Stock is **not** checked or allocated
yet. The Workflow has marked placeholders where the Inventory calls will go.

The order ID is the idempotency key. Repeating an identical request returns the
existing order. Reusing the ID with different details returns
`"status":"conflict"`. An invalid request fails the Workflow with a
non-retryable `InvalidRequest` error.

### Order storage limitations

Orders are held in the worker's memory. Run exactly **one** Orders worker.
Restarting it loses all order records.

## Contributing

### Open in a container

* [Open in a container](https://code.visualstudio.com/docs/devcontainers/containers)

### Commit style

All commits must be done in the [Conventional Commit](https://www.conventionalcommits.org)
format.

```git
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```
