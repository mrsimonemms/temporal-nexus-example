# temporal-nexus-example

A Temporal Nexus reference architecture

<!-- toc -->

* [Inventory service](#inventory-service)
  * [Start the worker](#start-the-worker)
  * [Workflows](#workflows)
  * [Seeded stock](#seeded-stock)
  * [Limitations](#limitations)
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
