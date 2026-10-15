# Product specification

## States

- Data admission: `READY`, `READY_WITH_WARNINGS`, `BLOCKED`.
- Resolution: `RESOLVED`, `PARTIAL`, `UNRESOLVED`.
- Route: `NO_ACTION`, `REVIEW`, `ESCALATE`, `HARD_BLOCK`.
- Human decision: `PENDING`, `APPROVED`, `REJECTED`, `RETURNED_FOR_WORK`.

## Required experience

The workflow validates a source package, creates deterministic exceptions, performs a bounded
evidence investigation, audits the claims, generates a controller-ready package, and records the
run. Live and replay modes must share the same contracts. Every user-facing surface must say that
the data is synthetic and must keep the system recommendation separate from human action.
