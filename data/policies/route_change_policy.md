# Route Change Policy

## Planned Tours

Shipments assigned to a planned tour may be moved to another tour only
after route feasibility has been checked.

The feasibility check must verify:

- vehicle capacity
- shipment time windows
- operational route constraints

A feasible simulation does not execute the route change.

The operator must explicitly confirm the change before it can be applied.

## Started Tours

Shipments on a tour that has already started must not be automatically
reassigned.

Changes to started tours require dispatcher escalation.

## Audit Requirements

Every executed route modification must record:

- shipment identifier
- source tour
- target tour
- operator
- timestamp
- previous tour versions
- resulting tour versions

## Safety

The assistant must never claim that a route change was executed unless
the operational system explicitly confirms execution.