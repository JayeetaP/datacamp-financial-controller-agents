---
name: eval-case-authoring
description: Turn a requested behavior, reviewed run failure, or finance-policy change into a frozen regression case before implementation.
---

# Eval-case authoring

Create the smallest case that distinguishes correct from incorrect behavior.

- Link the case to a business requirement and data snapshot.
- Specify available and deliberately missing evidence.
- Separate deterministic assertions from rubric-based quality checks.
- Include required claims, prohibited claims, route, resolution status, and human action.
- Add a counterexample that should not trigger the same route.
- Use stable synthetic IDs and amounts; never introduce real data.
- Freeze the case before changing the implementation.

If the requested behavior contradicts a current policy or architecture decision, stop and surface
the conflict instead of encoding both expectations.
