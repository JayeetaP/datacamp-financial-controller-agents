# Presenter runbook

## Before the session

```bash
make setup
make verify
codex login status
make demo-1
```

Run `make demo-1` once from the same Codex desktop environment that will be used on stage. Replay
remains the fallback if the live runtime is unavailable.

## Suggested live sequence

1. Show `data/canonical/` and the synthetic-data banner in the report.
2. Run `uv run financial-controller validate` and point out schema, row-count, hash, relationship,
   journal-balance, and derived-view reconciliation checks.
3. Run `make demo-1`. In the event stream, highlight directed knowledge search, current evidence,
   deterministic calculation, draft construction, and governance gates.
4. Run `uv run financial-controller runs` to show timing, model, tokens, cost availability, and
   status. Open the latest HTML report from `outputs/reports/` inside Codex.
5. Run `make demo-2` to contrast an agent investigation with a deterministic preventive control.
6. For the coding segment, run `make demo-red`, ask Codex to diagnose and fix only
   `demo_starter/preventive_router.py`, rerun the focused eval, then run `make verify`.

## Recovery

- If live Codex fails, run the annual case with `--mode replay`; all gates and artifacts remain real.
- If the knowledge manifest is missing, run `uv run python scripts/build_knowledge_index.py`.
- Never improvise a production connection or paste a credential. This repo is synthetic and local.
