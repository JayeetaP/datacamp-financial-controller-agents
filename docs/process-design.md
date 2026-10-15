# Process design: from close data to a review decision

This page shows what happens in the running demo, where each input comes from, and what a
controller can inspect at each stage. Everything is synthetic. The diagrams are Mermaid blocks
and render directly in GitHub Markdown.

## One-screen view

```mermaid
flowchart LR
    P["1. Synthetic close package"] --> Q{"2. Data quality ready?"}
    Q -- "No" --> B["Blocked quality result"]
    Q -- "Yes" --> D["3. Deterministic exception"]
    D --> C{"Which case?"}
    C -- "Annual software bill" --> A["4. Codex investigates"]
    C -- "Unmatched receipts" --> R["4. Preventive control"]
    A --> G["5. Evidence and authority gates"]
    R --> G
    G --> O["6. Review output and run record"]
    O --> F["7. SME feedback and evals"]
    F --> D
```

The two cases share admission, policy, run storage for successful runs, and human authority. They
differ at stage 4: the annual bill needs a bounded investigation; the receipt threshold is
calculated directly. A blocked annual package creates a run record; blocked receipt admission
currently raises an error without one. The [build plan](ai-dlc/build-plan.md) calls out that gap.

## Where the information comes from

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

## Data admission, up close

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

## What happens at each stage

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

## Case 1: solve the annual software bill

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

## Case 2: intervene before close

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

## Where the workflow stops

| Situation | System outcome | Reason |
|---|---|---|
| Required source data fails admission | Block the annual investigation before the model call; receipt case currently exits with an error | Garbage should not become a confident finding |
| Current contract is missing | `PARTIAL` and `ESCALATE` in the frozen eval case | Prior-year precedent cannot prove this year's service period |
| Current invoice, contract, calculation, and draft agree | `RESOLVED` and `REVIEW` | The controller still owns approval |
| Unmatched receipts cross the preventive thresholds | `UNRESOLVED` and `ESCALATE` | Intervention is needed before a root cause is established |

The missing-contract case is currently a replay fixture, not a full altered-package live run. That
is a specific next eval improvement in the [build plan](ai-dlc/build-plan.md).
