# Financial Controller Agent

An eval-led, auditable monthly-close demonstration built for a DataCamp session. Every company,
person, vendor, customer, document, and amount is synthetic.

> Code owns the math. Evidence owns the facts. The model connects and explains. A human owns the
> decision.

## What the demo shows

1. Deterministic data-quality admission before any model call.
2. A material annual-software expense investigated through synthetic Confluence-style knowledge.
3. Current invoice and contract evidence used to calculate a USD 132,000 prepaid reclassification.
4. An unposted draft adjustment routed to a controller for review.
5. A second control that escalates recurring unmatched receipts before month-end.
6. Traces, evals, SME feedback, timing, token usage, and versioned run records.

## Quick start

Requirements: Python 3.11+, `uv`, Git, and the Codex CLI signed in with ChatGPT for live mode.

```bash
make setup
make verify
make demo-1
```

No API key is required for the default live path. `make demo-1` invokes `codex exec`, which reuses
the local Codex ChatGPT sign-in. Confirm it with:

```bash
codex login status
```

All tests and replay evals are network-free after setup:

```bash
make test
make eval-replay
```

`uv.lock` is included. Use `uv sync --extra dev --frozen` when you want the exact tested
environment after cloning.

## Demo stories

### 1. Annual software renewal

September software expense is USD 144,000 against a USD 12,000 budget. The investigator retrieves
the prepaid policy and prior procedure, then uses the current contract to prove a twelve-month
service period. Deterministic code calculates USD 12,000 current expense and USD 132,000 prepaid,
and prepares an unposted draft adjustment for controller review.

### 2. Preventive escalation

Unmatched customer receipts grow across three weekly checks to USD 12,400; the oldest item reaches
17 days and close is three business days away. A deterministic rule escalates before the control
becomes a final-close failure without inventing a root cause.

## Repository map

- `specs/`: business, product, technical, and eval contracts.
- `controls/`: executable policy inputs and evidence rules.
- `data/canonical/`: generated synthetic finance records.
- `knowledge/`: synthetic runbooks and prior investigations.
- `domain_skills/`: runtime finance playbooks.
- `src/financial_controller/`: validation, finance engine, retrieval, agent, gates, reporting.
- `evals/`: frozen behavioral cases and replay fixtures.
- `.agents/skills/`: repo-local Codex development workflows.

See [FINAL_BUILD_PLAN.md](FINAL_BUILD_PLAN.md) for the complete implementation contract.
The executable flow and presenter commands are in [docs/architecture.md](docs/architecture.md) and
[docs/demo-runbook.md](docs/demo-runbook.md).

## Safety boundary

This project is educational and not production accounting software. It does not connect to a real
ERP or bank, post entries, approve a close, or use real financial data.
