# Plan for a visual review experience

The [process design](process-design.md) is the GitHub-readable map. The next product view should
let someone inspect one real run without reading raw JSONL. It should render the validated outputs
already produced by the workflow, not calculate accounting results in the browser.

## The screen to build

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ SYNTHETIC DATA  •  period  •  case  •  mode  •  run status  •  elapsed time │
├──────────────────────┬───────────────────────────────┬──────────────────────┤
│ 1. PACKAGE HEALTH    │ 2. EXCEPTION AND EVIDENCE     │ 3. DECISION          │
│ schema / completeness│ variance or receipt trend     │ finding and route    │
│ reconciliation checks│ source → guidance → current   │ grounded claims      │
│ blocked items         │ evidence → calculation        │ unposted draft       │
├──────────────────────┴───────────────────────────────┴──────────────────────┤
│ 4. RUN TIMELINE: search → evidence → calculation → gates → report            │
│    tool calls, retrieved IDs, timing, token usage, feedback and eval links  │
└─────────────────────────────────────────────────────────────────────────────┘
```

The most useful interaction is clicking a claim such as “USD 132,000 prepaid” and seeing the
calculation, current contract, invoice, policy, and gate that support it. Historical guidance must
have a different visual treatment from current proof. A blocked package should show the failed
check before any investigation panel appears.

## Build it in three passes

| Pass | Deliverable | Input contract | Exit criterion |
|---|---|---|---|
| 0 — now | Mermaid maps in the README and process design | Versioned Markdown and source paths | A GitHub reader can follow both cases from data to decision |
| 1 — next | Persist a complete per-run artifact bundle | `quality.json`, `variance.json` or `control.json`, selected search hits, `calculation.json`, `draft.json`, `finding.json`, `gates.json`, plus existing `run.json` and `events.jsonl` | The same run can be reconstructed without parsing model prose |
| 2 — next | Read-only HTML review board that opens in Codex | The per-run bundle from pass 1 | Every amount and evidence edge is clickable; live and replay use the same layout |

The current code saves `run.json`, raw events, a SQLite record, and text-style Markdown/HTML. It
does **not** yet persist a standalone quality report, full search hits, or draft lines per run.
Those are the first output changes to make. They should have typed schemas and replay tests before
the visual board reads them.

## Design rules

1. Keep `SYNTHETIC DATA` visible in every view and export.
2. Show data admission before the agent timeline. A failed blocking check is the primary result.
3. Mark guidance, current evidence, canonical policy, and calculated values as distinct source
   types; never draw a prior-year page as the proof edge for a current-period claim.
4. Use source IDs and content hashes to open the exact record. Do not invent a friendly summary
   that loses lineage.
5. Show `PENDING` and `UNPOSTED` plainly. A draft is an item for review, not an executed entry.
6. Show token usage and elapsed time when returned. Display “cost not reported” for the Codex
   subscription runtime instead of estimating a dollar amount.
7. Keep the timeline concise: tool name, input IDs, output IDs, duration, and gate result. Do not
   expose private reasoning text.
8. Make the receipt trend and its four threshold checks visible together, so the preventive
   escalation can be understood without a model narrative.

## Acceptance check

Open one successful live annual run, one replay annual run, the receipt escalation, and a blocked
data-quality case. A reviewer should be able to answer: **What happened? Which current records
prove it? What did code calculate? Which gate allowed or stopped it? What must a human do next?**
No visual component should change the `Finding`, `DraftAdjustment`, or route.

After the local review board works, a presentation Site could read the same exported bundle. Site
work is a separate implementation step; this plan does not make the Site a dependency for running
the demo.
