# AGENTS.md

## Project purpose

Build a small, command-line order management demo for a live workshop about
Temporal Nexus.

The audience should understand:

- How independent services communicate through Nexus.
- How service contracts work across programming languages.
- How Temporal preserves progress when workers stop and restart.
- How to inspect executions in Temporal UI.

Prioritize a reliable demonstration, clear explanations, and minimal setup. This
is a teaching project, not a production order management system.

## Authorization and scope

Treat questions, exploration, plans, preferences, and links as discussion, not
permission to implement.

Only create or modify files, change settings, install software, or take actions
in external systems when explicitly requested. Read-only research is permitted.

Keep each implementation task within its requested scope. Do not build future
stages merely because they appear in this document.

## Existing scaffold

Inspect the existing scaffold before making changes. Follow its directory
structure, tooling, naming conventions, and dependency management.

Do not regenerate the application or replace working infrastructure
unnecessarily.

The architecture below supersedes earlier plans involving a payment service or
an orders service written in Go. Remove or migrate legacy code only when
requested.

## Architecture

Use three independently runnable services:

| Service | Language | Responsibility |
| --- | --- | --- |
| Orders | Python | Coordinate customer orders |
| Inventory | Go | Report stock availability and allocate stock to customers |
| Shipping | TypeScript | Simulate arranging shipment |

There is no payment service.

Use Temporal Nexus for calls between services.

The CLI starts an order Workflow through the Temporal client. The order Workflow
calls inventory and shipping through their public Nexus Operations.

Each receiving service owns its operation handlers and internal Workflows and
Activities.

Give each service its own Task Queue. Use the existing local Temporal
development server and a single Namespace unless explicitly asked otherwise.

Do not implement service-to-service communication through direct HTTP requests,
shared database tables, cross-service Activities, or cross-service Child
Workflows.

Services may use Activities internally.

## Minimal business flow

1. Accept an order ID, customer reference, product SKU, and positive integer
   quantity.
2. Query available stock through an inventory Nexus Operation.
3. Request allocation to the customer through an inventory Nexus Operation.
4. If allocation succeeds, request shipment through a shipping Nexus Operation.
5. Complete the order with allocation and shipment references.
6. If stock is insufficient, return a clear business outcome without requesting
   shipment.

Use fake customers, seeded stock, and simulated shipments. Do not integrate real
providers.

Keep the first implementation to one SKU per order. Add baskets, partial
fulfillment, replenishment, or allocation release only when requested.

## Inventory behavior

Inventory owns stock and allocation state. Other services must access that state
through its public contract.

Expose separate operations for checking availability and allocating stock.

An availability check is informational: stock may change before allocation.
Allocation must atomically check availability and reserve the requested
quantity.

Never rely on a preceding stock check to prevent overselling.

Use the order ID as an allocation idempotency key. Repeating an identical
allocation request must return the existing allocation without consuming stock
again. Reject reuse of that key with different request details.

Treat insufficient stock as an expected business outcome, not a transient
failure that should retry indefinitely.

Keep storage minimal. Follow any existing persistence approach in the scaffold.
If storage is absent, explain the tradeoff before introducing persistence or
adopting process-local state.

Do not claim that in-memory stock or deduplication survives a worker restart.

## Nexus contracts

Use simple JSON-compatible requests and responses with consistent field names
across languages.

Keep endpoint names, service names, operation names, and payload contracts
visible and easy to explain.

Use synchronous Nexus Operations only for reliably short operations that
complete within the handler deadline. Use asynchronous Operations backed by
Workflows for shipment and other potentially long-running work.

A stock availability operation is a candidate for a synchronous handler. Decide
based on its actual implementation and current SDK guidance.

Nexus handlers may use Temporal client APIs to access service-owned Workflows.
Keep allocation atomicity and idempotency in the inventory implementation.

Callers must depend on public contracts, not receiving services' implementation
languages or internal Workflow names.

## Teaching priorities

Make these concepts identifiable in code and documentation:

- Endpoint: the named routing destination used by a caller.
- Service: the named collection of exposed Operations.
- Operation: the callable contract.
- Workflow: durable orchestration.
- Activity: execution of side effects.

Explain the distinction between a business operation that checks stock and a
Temporal Workflow Query. A read-only Workflow Query must not mutate inventory.

Describe Nexus as durable communication across service boundaries. Avoid
claiming that Temporal replaces every REST API or guarantees exactly-once
external side effects.

## Demonstration scenarios

### Happy path

Start all workers, submit an order, and show stock checking, allocation,
shipping, and completion.

### Insufficient stock

Submit an order exceeding available stock. Show the clear business outcome and
confirm that shipment was not requested.

### Unavailable service

Stop the shipping worker and submit an order. Show that inventory is allocated
and shipment is pending.

Restart shipping and show the same order completing without another allocation.

Choose explicit timeouts long enough for the presenter to perform this
demonstration.

### Order worker recovery

Stop and restart the order worker while an order is waiting for shipping. Show
that processing resumes without submitting another order.

Use stable order IDs so the presenter can find executions easily.

Do not present inventory restart durability as demonstrated unless its storage
and recovery behavior have been implemented and verified.

## Implementation principles

- Prefer small, readable functions and conventional SDK patterns.
- Keep orchestration deterministic.
- Put side effects inside Activities or appropriate Nexus handlers.
- Use Temporal timers for Workflow delays.
- Make retries and timeouts explicit where they affect the demonstration.
- Distinguish expected business outcomes from infrastructure failures.
- Preserve idempotency for allocations and simulated shipments.
- Avoid frameworks and abstractions that obscure Nexus.
- Do not add a frontend, authentication, Kubernetes, or real infrastructure
  unless requested.
- Add compensation, cancellation, and advanced failure scenarios only when
  requested.

## Dependencies and documentation

Before choosing versions or implementing Nexus APIs, check current official
Temporal documentation and official SDK examples for Python, Go, and TypeScript.

Confirm that the chosen server, CLI, SDKs, and Nexus packages work together. Pin
dependencies and commit applicable lockfiles.

Never invent SDK methods, package names, feature flags, or CLI commands.

If a language presents a compatibility problem, explain it before changing the
agreed language allocation.

## MCP tools

Use the MCP tools exposed by the current agent session. Configuration files for
other clients do not establish tool availability in this session.

Select tools by their advertised capabilities and descriptions. Prefer
documentation tools when checking current Temporal Nexus APIs, SDK
compatibility, and examples.

If a required capability is unavailable, report it and use official
documentation directly where possible. Do not change or synchronize MCP
configurations unless explicitly requested.

Tool availability does not expand authorization: actions that modify external
systems still require an explicit user request.

## Developer experience

Provide a README with:

- Prerequisites and verified versions.
- Exact server, endpoint, worker, and submission commands.
- A simple architecture diagram.
- Inventory seeding and stock inspection instructions.
- Expected CLI output.
- Where to inspect executions in Temporal UI.
- A short presenter walkthrough for each demonstration.
- Clear restart and reset instructions.
- Any limits on inventory persistence and recovery.

Keep individual service startup commands visible even if a convenience command
starts everything.

Print concise logs containing the service name and order ID. Keep business
results distinguishable from diagnostic output.

## Verification

Verify the real three-language path against the local Temporal server.

Check:

- Successful stock checking, allocation, and shipment.
- Insufficient stock without shipment.
- Repeated allocation requests without double consumption.
- Conflicting reuse of an allocation idempotency key.
- Concurrent allocations without overselling.
- Order and shipping worker stop/restart scenarios.
- Correct request and result serialization across languages.

Keep tests focused on contracts, inventory correctness, and demonstrated
recovery behavior.

Run the configured pre-commit hooks against all files after changes. Fix
failures without disabling hooks, weakening rules, adding bypasses, or making
unrelated changes.

Report what was actually run, what passed, and any remaining limitations. Never
describe an unexecuted check as verified.

## Working style

Implement in small, reviewable stages.

After each requested stage, explain what changed, how to run it, and how it was
verified.

Do not commit or push unless explicitly requested.

Favor a dependable workshop demonstration over additional features.
