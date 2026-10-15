# How to run the demo

All records and names are synthetic. The primary live path uses the Codex CLI's saved ChatGPT
login; the replay path runs without a model call.

## Set up and check the project

From the repository root:

```bash
make setup
make verify
codex login status
```

`make verify` checks `uv.lock`, generated data and knowledge, lint, twelve normal tests, and five
replay eval cases. `codex login status` should report a ChatGPT login before a live run. No
`OPENAI_API_KEY` is needed for the Codex path.

## Run the two cases

```bash
uv run financial-controller validate
make demo-1
make demo-2
```

`validate` shows why the data package is admitted. `demo-1` starts a bounded Codex investigation
of the annual software bill, finds current support through local MCP tools, calculates the prepaid
amount, and returns an unposted draft for review. `demo-2` evaluates the unmatched-receipt trend
using a deterministic control rule.

For the primary case without a live model call:

```bash
uv run financial-controller run --case annual-software-prepaid --mode replay
```

## Inspect what happened

```bash
uv run financial-controller runs --limit 5
uv run financial-controller report --latest
```

Each run writes `outputs/runs/<run-id>/run.json` and `events.jsonl`, plus Markdown and HTML in
`outputs/reports/`. The SQLite ledger is `outputs/run_ledger.sqlite3`. Open the HTML report in
Codex for the review output; open `events.jsonl` to show the live search, evidence, calculation,
and draft tool calls. The [process design](process-design.md) explains each stage before you run it.

## Show the eval-led repair loop

```bash
make demo-red
```

This isolated test intentionally fails at the exact 14-day threshold. Fix only
`demo_starter/preventive_router.py`, rerun `make demo-red`, and then run `make verify`. Normal
verification excludes this starter test until you perform that repair. The production preventive
control already has the correct strict boundary.
