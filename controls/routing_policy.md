# Routing policy

- `NO_ACTION`: supported explanation and no correction.
- `REVIEW`: supported correction or treatment requiring human approval.
- `ESCALATE`: material support is missing, conflict remains, or preventive policy requires action.
- `HARD_BLOCK`: source data fails an admission or reconciliation rule.

Resolution status and route are independent. A resolved exception can route to review; an
unresolved but time-sensitive control can route to escalation.
