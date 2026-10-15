---
name: implementation-strategy
description: Plan a runtime, contract, or architecture change in this financial-controller repository before editing code that crosses system boundaries.
---

# Implementation strategy

Read the relevant specification and architecture decision before changing a public contract or
runtime boundary.

1. State the business behavior being changed and the source specification.
2. Identify the owning layer: data admission, deterministic engine, retrieval, investigator,
   governance, reporting, or observability.
3. Preserve the trust boundary: code calculates, current evidence proves, the model explains, and a
   human decides.
4. Identify the minimal contract and eval changes before implementation.
5. Avoid multi-agent or provider-specific complexity unless a frozen eval requires it.

Return a short implementation note naming affected contracts, tests, and compatibility risks.
