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
* [Nexus: inventory operations](#nexus-inventory-operations)
* [Contributing](#contributing)
  * [Open in a container](#open-in-a-container)
  * [Commit style](#commit-style)

<!-- Regenerate with "pre-commit run -a markdown-toc" -->

<!-- tocstop -->

## Inventory service

A Go worker on the `Inventory` Task Queue. It exposes stock checking and
allocation through Nexus (see
[Nexus: inventory operations](#nexus-inventory-operations)).

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
temporal workflow execute --namespace orders --task-queue Orders \
  --type OrderWorkflow --workflow-id order-1 \
  --input '{"orderId":"order-1","customerRef":"cust-1","sku":"WIDGET-1","quantity":2}'
# {"status":"recorded","order":{"orderId":"order-1",...,"inventoryChecked":true,
#   "inventoryAllocated":true,"allocationId":"ALLOC-order-1"},"message":""}
```

The Workflow runs check → allocate → record:

1. **Check** stock with Inventory's `check-stock` Nexus Operation. This is
   informational and reserves nothing. `unknown_product` or
   `insufficient_stock` stops here.
2. **Allocate** stock with `allocate-stock`. This is authoritative, because
   stock may have changed since the check. A rejection (`unknown_product`,
   `invalid_quantity`, `insufficient_stock` or `conflict`) stops here.
3. **Record** the order with both inventory flags `true` and the
   `allocationId`.

If the Workflow stops at steps 1 or 2, the order is **not** recorded. A Nexus
failure or timeout (2 minutes per Operation) fails the Workflow; it is never
treated as success. `recorded` means stock is allocated, not that the order
has shipped.

The order ID is the idempotency key in both services. Repeating an identical
order returns the existing allocation and record without consuming stock again.
Reusing the ID with different details returns `"status":"conflict"`. An
invalid request fails the Workflow with a non-retryable `InvalidRequest` error.

### Order storage limitations

Orders are held in the worker's memory. Run exactly **one** Orders worker.
Restarting it loses all order records.

## Nexus: inventory operations

Orders (`orders` Namespace) calls Inventory (`inventory` Namespace) through
Nexus:

| Concept | Name |
| --- | --- |
| Endpoint | `inventory` (targets Namespace `inventory`, Task Queue `Inventory`) |
| Service | `inventory` |
| Operation | `check-stock` (asynchronous, runs `CheckStockWorkflow`) |
| Operation | `allocate-stock` (asynchronous, runs `AllocateStockWorkflow`) |

`check-stock` request and response JSON:

```json
{"sku": "WIDGET-1"}
{"sku": "WIDGET-1", "available": 10, "status": "found"}
```

`allocate-stock` request and response JSON (`allocation` appears only when
`status` is `allocated`):

```json
{"orderId": "order-1", "customerRef": "cust-1", "sku": "WIDGET-1", "quantity": 2}
{"status": "allocated", "allocation": {"allocationId": "ALLOC-order-1",
  "orderId": "order-1", "customerRef": "cust-1", "sku": "WIDGET-1", "quantity": 2}}
{"status": "insufficient_stock", "message": "requested 99 of WIDGET-1 but only 8 available"}
```

The contract is defined in
[`service/nexus.go`](services/inventory/internal/app/service/nexus.go) and
[`types.go`](services/inventory/internal/app/inventory/types.go), and mirrored
in [`inventory_service.py`](services/orders/src/orders/inventory_service.py).
Compose creates the endpoint.

To demonstrate, check stock, run an order, then check stock again. Available
stock drops by the order quantity:

```sh
temporal workflow execute --namespace inventory --task-queue Inventory \
  --type CheckStockWorkflow --workflow-id stock-before \
  --input '{"sku":"WIDGET-1"}'
temporal workflow execute --namespace orders --task-queue Orders \
  --type OrderWorkflow --workflow-id demo-order-1 \
  --input '{"orderId":"demo-order-1","customerRef":"cust-1","sku":"WIDGET-1","quantity":2}'
temporal workflow show --namespace orders -w demo-order-1 | grep NexusOperation
temporal workflow execute --namespace inventory --task-queue Inventory \
  --type CheckStockWorkflow --workflow-id stock-after \
  --input '{"sku":"WIDGET-1"}'
```

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
