# Process design: from close data to a review decision

This page starts with the controller's questions, then reveals the system only as each question
needs an answer. Everything is synthetic. The diagrams are Mermaid blocks that render in GitHub
Markdown.

## Start with the finance question

> At month-end, we have variances, reconciliation breaks, and aging items. How do we know which
> are data issues, which we can resolve with evidence, and which need escalation before close?

Use one example to make that concrete: September software expense is USD 144,000 against a USD
12,000 monthly budget. Is it genuine overspending, an annual bill recorded in one month, or a
problem in the source data?

Then work through the questions the controller would ask:

1. What must pass before we let an agent investigate: file completeness, required columns,
   relationships, and reconciliations? What happens when a check fails?
2. If an older case suggests the answer, what would still count as proof for **this** September?
3. If the current evidence supports a correction, what can code calculate and prepare—and what
   must remain a controller's decision?
4. What if there is no supported answer, or a different control is getting worse before close?
5. How can we see what the agent used, how long it took, and whether the next version is better?

The example and first three follow-ups lead through the annual-software case. The fourth
introduces unmatched receipts: an early escalation, not a second AI-generated diagnosis. The
last connects both cases to run history, SME feedback, and eval-led improvement.

## The flow in one view

```mermaid
flowchart LR
    SIGNAL["Close signal"] --> TRUST{"Can we trust the inputs?"}
    TRUST -- "No" --> STOP["Stop and show failed checks"]
    TRUST -- "Yes" --> CASE{"What kind of decision?"}
    CASE -- "Annual software bill" --> PROOF["Find guidance, then current proof"]
    PROOF --> MATH["Calculate and prepare unposted draft"]
    MATH --> AUDIT["Check evidence, amount, and authority"]
    AUDIT --> REVIEW["Controller reviews"]
    CASE -- "Receipts getting older" --> RULE["Evaluate preventive thresholds"]
    RULE --> ESC["Escalate to AR owner before close"]
    REVIEW --> LEARN["Run history, SME feedback, evals"]
    ESC --> LEARN
```

Read this left to right as three decisions: **trust the data, establish the right evidence, then
choose a safe action**. The annual bill needs a bounded Codex investigation; receipt aging uses a
deterministic control rule, not an agent. Both leave the human decision open. A blocked annual
package creates a run record; blocked receipt admission currently raises an error without one.
The [build plan](ai-dlc/build-plan.md) calls out that gap.

## 1. Map the evidence

```mermaid
flowchart TB
    subgraph Current["Current-period synthetic records"]
        GL["GL actuals + budget + journal lines"]
        DOC["Vendor invoice + current contract"]
        AR["Bank receipts + unmatched view + close calendar"]
    end
    subgraph Context["Guidance and rules"]
        KB["Synthetic Confluence-style pages"]
        POLICY["Canonical controls/policy.yaml"]
    end
    GL --> ADMIT["Data admission"]
    DOC --> ADMIT
    AR --> ADMIT
    ADMIT --> EX["Exception or control result"]
    KB --> SEARCH["Local knowledge MCP search"]
    DOC --> EVIDENCE["Current evidence MCP lookup"]
    POLICY --> MATH["Deterministic calculations"]
    EX --> FINDING["Typed finding"]
    SEARCH --> FINDING
    EVIDENCE --> FINDING
    MATH --> FINDING
    FINDING --> GATES["Governance gates"]
    GATES --> REVIEW["Human review package"]
```

| Input | Actual location | What it can establish |
|---|---|---|
| Package identity and expected files | [`data/canonical/package_manifest.json`](../data/canonical/package_manifest.json) | Reporting period, row counts, and file hashes |
| Ledger, budget, journal, and account model | [`data/canonical/`](../data/canonical/) | The posted expense, comparison, account references, and journal balance |
| Current invoice and contract | [`vendor_invoices.csv`](../data/canonical/vendor_invoices.csv), [`contracts.csv`](../data/canonical/contracts.csv), [`evidence_manifest.json`](../data/evidence_manifest.json) | Current amount, linked contract, and service dates |
| Receipts, unmatched view, calendar, and owner | [`data/canonical/`](../data/canonical/) | Trend, age, time to close, and escalation owner |
| Prior procedures and cases | [`knowledge/confluence/`](../knowledge/confluence/) | What to investigate; never proof of this year's service period |
| Executable finance rules | [`controls/policy.yaml`](../controls/policy.yaml) | Thresholds, account mapping, and treatment convention |

No live ERP or Confluence account is connected. The local MCP server makes the synthetic knowledge
and evidence lookup visible through the same tool shape an external connector could later use.
Search is metadata-filtered lexical ranking; it is not a semantic or hybrid search service today.

## 2. Decide whether the data is usable

```mermaid
flowchart TB
    PKG["Synthetic package + manifest"] --> ID["File presence, hashes, row counts"]
    PKG --> SHAPE["Required CSV columns"]
    PKG --> LINKS["Account and invoice-contract links"]
    PKG --> RECON["Invoice totals, receipt view, journal balance"]
    PKG --> PERIOD["One reporting period"]
    ID --> RESULT{"Any blocking check failed?"}
    SHAPE --> RESULT
    LINKS --> RESULT
    RECON --> RESULT
    PERIOD --> RESULT
    RESULT -- "Yes" --> STOP["BLOCKED; annual model call skipped"]
    RESULT -- "No" --> GO["READY for exception logic"]
```

All check results are collected; this is not a step-by-step cleaning algorithm that quietly
modifies the records. `SCHEMA-*` currently means **required columns are present**, not that every
cell has passed type, null, uniqueness, or date validation. The relationship checks cover account
IDs and invoice-to-contract links; the reconciliations cover invoice/contract totals and currency,
the latest unmatched-receipt view against bank receipts, and journal debit/credit balance. The
synthetic package is deliberately narrow. [The build plan](ai-dlc/build-plan.md) includes deeper
row-level contracts as a next step, not a claim about today's validator.

## 3. Resolve the annual bill without posting

The problem is legible from the source records: September software expense is USD 144,000 against
a USD 12,000 budget. The USD 132,000 variance is calculated in code. The agent does not receive the
contract's service dates in its initial exception payload.

```mermaid
sequenceDiagram
    actor Reviewer
    participant Runner as Workflow runner
    participant QA as Data quality
    participant Engine as Finance code
    participant Codex as Codex investigator
    participant MCP as Local finance MCP
    participant Gates as Governance gates
    participant Ledger as Run ledger
    Reviewer->>Runner: Run annual-software-prepaid
    Runner->>QA: Validate synthetic package
    QA-->>Runner: READY
    Runner->>Engine: Calculate actual vs budget
    Engine-->>Runner: USD 132,000 material variance
    Runner->>Codex: Exception and invoice ID
    Codex->>MCP: Search close guidance
    MCP-->>Codex: Runbook and policy candidates
    Codex->>MCP: Fetch selected passage
    Codex->>MCP: Fetch current invoice and linked contract
    MCP-->>Codex: Current evidence and service dates
    Codex->>MCP: Calculate prepaid schedule
    MCP-->>Codex: USD 12,000 expense; USD 132,000 prepaid
    Codex->>MCP: Prepare unposted draft
    MCP-->>Codex: Debit 1450; credit 6250
    Codex-->>Runner: Typed finding; decision PENDING
    Runner->>Engine: Recompute schedule and draft
    Runner->>Gates: Audit evidence, claims, route, and draft
    Gates-->>Runner: Pass or fail closed
    Runner->>Ledger: Save run, events, and report
    Ledger-->>Reviewer: Review package
```

The historical page tells the agent to inspect the current contract. The invoice
`INV-SYN-1042` links to `CONTRACT-SYN-0077`, whose service dates are September 1, 2026 through
August 31, 2027. `POLICY-PREPAID-003` applies whole-month straight-line allocation. Code calculates
USD 12,000 for September and USD 132,000 for future service. The result is `RESOLVED` and routed
to `REVIEW`; the draft stays `UNPOSTED` and the human decision stays `PENDING`.

## 4. Escalate before close

The second case shows a different pattern: a control rule notices deterioration before the final
close, without asking a model to invent a cause.

```mermaid
flowchart LR
    W1["Sep 11<br/>USD 4,100 unmatched<br/>oldest 3 days"] --> W2["Sep 18<br/>USD 7,800 unmatched<br/>oldest 10 days"]
    W2 --> W3["Sep 25<br/>USD 12,400 unmatched<br/>oldest 17 days"]
    W3 --> RULE{"3 open checks<br/>balance at least USD 10,000<br/>age above 14 days<br/>close within 5 business days?"}
    RULE -- "Yes" --> ESC["ESCALATE to AR owner<br/>3 business days before close"]
    RULE -- "No" --> WATCH["Continue monitoring"]
```

The values come from `unmatched_customer_payments.csv`, the bank-receipt reconciliation, the close
calendar, and `POLICY-AR-007`. The rule is conjunctive: all four conditions must hold. The result
is `UNRESOLVED` with route `ESCALATE`, because the data shows a worsening control but does not prove
why individual receipts remain unmatched.

## 5. Show the limits, not just the successes

| Situation | System outcome | Reason |
|---|---|---|
| Required source data fails admission | Block the annual investigation before the model call; receipt case currently exits with an error | Garbage should not become a confident finding |
| Current contract is missing | `PARTIAL` and `ESCALATE` in the frozen eval case | Prior-year precedent cannot prove this year's service period |
| Current invoice, contract, calculation, and draft agree | `RESOLVED` and `REVIEW` | The controller still owns approval |
| Unmatched receipts cross the preventive thresholds | `UNRESOLVED` and `ESCALATE` | Intervention is needed before a root cause is established |

The missing-contract case is currently a replay fixture, not a full altered-package live run. That
is a specific next eval improvement in the [build plan](ai-dlc/build-plan.md).

## Technical reference: what runs at each stage

| Stage | Owner | Work performed | Artifact to inspect |
|---|---|---|---|
| 1. Load | Generator and repository | Read the September 2026 package and its manifests | `data/canonical/` and `data/evidence_manifest.json` |
| 2. Admit | `quality/validator.py` | Check files, columns, counts, hashes, account links, invoice/contract totals, receipt view, journal balance, and period | `financial-controller validate` output; `DATA-ADMISSION` gate in a run |
| 3. Detect | `engine/variance.py` or `engine/preventive.py` | Calculate the material software variance or evaluate four receipt thresholds | Variance in the agent case payload; control result in `events.jsonl` |
| 4. Investigate | `CodexProvider` and local finance MCP, for the annual case | Search guidance, fetch current evidence, call calculator and draft tool | MCP calls in `outputs/runs/<run-id>/events.jsonl` |
| 5. Check | `gates/audit.py` and workflow runner | Resolve cited IDs, inspect claims, require current proof, preserve human authority, verify draft | `gate_results` in `run.json` |
| 6. Review | Reporting and controller | Show finding, evidence map, route, and requested action; decision stays `PENDING` | `outputs/reports/<run-id>.md` or `.html` |
| 7. Improve | Run ledger, SME, and eval suite | Record time, tools, tokens, result, feedback, then freeze a failure as an eval | `outputs/run_ledger.sqlite3`, `evals/cases.yaml` |

The current HTML is a simple export. The [visualization plan](visualization-plan.md) defines the
next review board and the extra typed artifacts it needs.
