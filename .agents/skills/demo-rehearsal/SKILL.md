---
name: demo-rehearsal
description: Rehearse the two DataCamp financial-controller stories, validate fallbacks, and prepare a concise evidence-backed demo status.
---

# Demo rehearsal

1. Confirm `codex login status` uses ChatGPT authentication.
2. Run `make verify` from the repository root.
3. Run Demo 1 once live and once in replay mode; compare the typed outcome and draft.
4. Exercise the intentional Demo 2 before/after path and review the diff.
5. Confirm run records show provider, timing, usage, retrievals, gates, and versions.
6. Confirm every visible record says `SYNTHETIC DATA` and no credentials appear.
7. Preserve a replay result and report as the first fallback.

Stop if the live and replay outputs disagree on calculation, evidence, route, or human-decision
state. Latency or wording differences are acceptable when the structured decision is unchanged.
