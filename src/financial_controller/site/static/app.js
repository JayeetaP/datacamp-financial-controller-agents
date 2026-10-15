"use strict";

const ui = {
  data: null,
  view: "overview",
  evidenceStep: "signal",
  selectedRunId: null,
  fingerprint: null,
};

const byId = (id) => document.getElementById(id);
const money = (cents, currency = "USD") => new Intl.NumberFormat("en-US", {
  style: "currency", currency, maximumFractionDigits: 0,
}).format((Number(cents) || 0) / 100);
const duration = (ms) => ms == null ? "not reported" : `${(ms / 1000).toFixed(1)}s`;
const text = (id, value) => { byId(id).textContent = value; };
const clear = (target) => { target.replaceChildren(); };

function node(tag, className = "", value = "") {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (value !== "") result.textContent = String(value);
  return result;
}

function fact(label, value) {
  const wrap = node("span", "fact-pill");
  wrap.append(node("small", "", label), node("strong", "", value));
  return wrap;
}

function stateFingerprint(data) {
  const quality = { ...data.quality };
  delete quality.generated_at;
  return JSON.stringify({
    quality,
    annual: data.annual,
    receipts: data.receipts,
    runs: data.runs,
    selected_run: data.selected_run,
  });
}

function setView(view, scrollToSection = false) {
  ui.view = view;
  for (const button of document.querySelectorAll(".view-tab")) {
    const active = button.dataset.view === view;
    button.classList.toggle("is-active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  }
  for (const panel of document.querySelectorAll(".view-panel")) {
    panel.hidden = panel.id !== `view-${view}`;
  }
  if (window.location.hash !== `#${view}`) history.replaceState(null, "", `#${view}`);
  if (scrollToSection) document.querySelector(".view-nav").scrollIntoView({ block: "start" });
}

function renderHero(data) {
  const quality = data.quality;
  text("heroQuality", quality.status.replaceAll("_", " "));
  const failed = quality.checks.filter((check) => !check.passed).length;
  text("heroQualitySub", failed
    ? `${failed} check${failed === 1 ? "" : "s"} failed · investigate admission first`
    : `${quality.checks.length} checks passed · ${quality.package_id}`);
  const run = data.selected_run;
  if (run) {
    text("heroRun", `${run.mode === "live" ? "Live" : "Replay"} run · ${run.status.toLowerCase()}`);
    text("heroRunSub", `${run.case_id.replaceAll("-", " ")} · ${duration(run.duration_ms)}`);
  } else {
    text("heroRun", "Source preview");
    text("heroRunSub", "No recorded agent finding is implied by the preview");
  }
}

function qualityGroup(name, checks) {
  const failed = checks.some((check) => !check.passed);
  const item = node("div", `quality-group${failed ? " failed" : ""}`);
  item.append(node("span", "quality-group-mark", failed ? "!" : "✓"), node("span", "", name));
  return item;
}

function renderQuality(data) {
  const quality = data.quality;
  const passed = quality.checks.filter((check) => check.passed).length;
  text("qualityCount", `${passed}/${quality.checks.length}`);
  text("qualityCountLabel", "admission checks passed");
  const badge = byId("qualityBadge");
  badge.className = "status-badge";
  if (quality.status === "BLOCKED") badge.classList.add("blocked");
  if (quality.status === "READY_WITH_WARNINGS") badge.classList.add("warn");
  badge.textContent = quality.status.replaceAll("_", " ");
  text("qualityExplanation", quality.status === "BLOCKED"
    ? "A blocking check failed. The annual investigation must stop before a model call."
    : "Package identity, structure, links, and selected reconciliations are visible below.");

  const groups = [
    ["Files + counts + hashes", (id) => id === "PACKAGE-MANIFEST" || id.startsWith("FILE-") || id.startsWith("HASH-") || (id.startsWith("COMPLETENESS-") && id !== "COMPLETENESS-PERIOD")],
    ["Required columns", (id) => id.startsWith("SCHEMA-")],
    ["Record relationships", (id) => id.startsWith("RELATIONSHIP-")],
    ["Reconciliations", (id) => id.startsWith("RECONCILIATION-") || id.startsWith("ACCOUNTING-")],
    ["Reporting period", (id) => id === "COMPLETENESS-PERIOD"],
  ];
  const groupTarget = byId("qualityGroups");
  clear(groupTarget);
  for (const [name, filter] of groups) {
    groupTarget.append(qualityGroup(name, quality.checks.filter((check) => filter(check.check_id))));
  }
  const checksTarget = byId("allQualityChecks");
  clear(checksTarget);
  for (const check of quality.checks) {
    const row = node("div", "check-row");
    row.append(
      node("span", check.passed ? "check-pass" : "check-fail", check.passed ? "✓" : "!"),
      node("strong", "", check.check_id),
      node("span", "", check.message),
    );
    checksTarget.append(row);
  }
  text("overviewVariance", data.annual
    ? `${money(data.annual.variance.variance.amount_cents)} variance`
    : "Blocked by data quality");
  text("overviewReceipts", data.receipts
    ? `${money(data.receipts.control.current_unmatched.amount_cents)} unmatched`
    : "Blocked by data quality");
}

function detailHeader(target, kind, eyebrow, title, description) {
  clear(target);
  const topline = node("div", `detail-topline ${kind}`);
  topline.append(node("span", "", eyebrow), node("span", "", "SYNTHETIC SOURCE"));
  target.append(topline, node("h3", "", title), node("p", "", description));
  const facts = node("div", "detail-facts");
  target.append(facts);
  return facts;
}

function renderEvidenceDetail(data) {
  const annual = data.annual;
  if (!annual) return;
  const target = byId("evidenceDetail");
  const variance = annual.variance;
  const invoice = annual.evidence.find((item) => item.evidence_id === "INV-SYN-1042");
  const contract = annual.evidence.find((item) => item.evidence_id === "CONTRACT-SYN-0077");
  const calculation = annual.calculation;
  const draft = annual.draft;
  const annualRun = data.selected_run?.case_id === "annual-software-prepaid" ? data.selected_run : null;
  const step = ui.evidenceStep;

  if (step === "signal") {
    const facts = detailHeader(target, "", "01 / THE EXCEPTION", "A material variance needs a reason.",
      "Code compares the September ledger with the monthly budget. This detects an exception; it does not establish the accounting treatment.");
    facts.append(
      fact("Actual source", variance.source_ids[0]),
      fact("Budget source", variance.source_ids[1]),
      fact("Variance", money(variance.variance.amount_cents)),
      fact("Materiality", variance.material ? "Material" : "Below threshold"),
    );
  } else if (step === "guidance") {
    const liveSearch = annualRun?.timeline.find((item) => item.tool === "search_close_knowledge");
    const hits = liveSearch?.hits.length ? liveSearch.hits : annual.guidance_candidates;
    const facts = detailHeader(target, "guidance", "02 / HISTORICAL GUIDANCE", "A lead, never current proof.",
      liveSearch?.hits.length
        ? "These are the candidates returned in the selected run. The agent may use a prior procedure to choose the next lookup, but not to prove this period's dates."
        : "These are source-package search candidates, not evidence of an agent search. A prior case suggests where to look; it cannot prove this year's contract.");
    facts.append(fact("Trust class", "HISTORICAL_GUIDANCE"), fact("Retrieval", "Local lexical ranking"));
    for (const hit of hits) {
      const row = node("div", "guidance-hit");
      row.append(node("strong", "", hit.title || hit.passage_id),
        node("span", "", `${hit.passage_id} · ${hit.trust}`));
      target.append(row);
    }
  } else if (step === "evidence") {
    const facts = detailHeader(target, "", "03 / CURRENT-PERIOD PROOF", "The invoice leads to the contract.",
      "The invoice and linked contract are separate current records. Together they establish the amount and the September 2026–August 2027 service term.");
    facts.append(
      fact("Invoice", invoice?.evidence_id || "missing"),
      fact("Invoice amount", money(calculation.total.amount_cents)),
      fact("Linked contract", contract?.evidence_id || "missing"),
      fact("Service starts", contract?.fields.service_start || "missing"),
      fact("Service ends", contract?.fields.service_end || "missing"),
      fact("Trust class", "CURRENT SUPPORT"),
    );
  } else if (step === "calculation") {
    const facts = detailHeader(target, "policy", "04 / POLICY + DETERMINISTIC CODE", "The amount is not model arithmetic.",
      "POLICY-PREPAID-003 applies straight-line monthly allocation. The Python calculator produces the period expense and remaining prepaid.");
    facts.append(
      fact("Policy", calculation.policy_id),
      fact("Service months", calculation.term_months),
      fact("September expense", money(calculation.monthly_expense.amount_cents)),
      fact("Remaining prepaid", money(calculation.remaining_prepaid.amount_cents)),
      fact("Calculation ID", calculation.calculation_id),
    );
  } else {
    const finding = annualRun?.status === "SUCCEEDED" ? annualRun.finding : null;
    const facts = detailHeader(target, "", "05 / HUMAN HANDOFF", finding ? "Resolved for review, not posted." : "A draft preview, not a decision.",
      finding
        ? "The selected run passed its governance gates. Its unposted adjustment is routed for a controller's independent decision."
        : "This is a deterministic preview from synthetic source data. Run the annual case to produce an audited agent finding.");
    facts.append(
      fact("Draft", draft.draft_id),
      fact("Status", draft.status),
      fact("Human decision", finding?.human_decision || "PENDING"),
      fact("Debit", `${draft.lines[0].account_id} · ${money(draft.lines[0].debit.amount_cents)}`),
      fact("Credit", `${draft.lines[1].account_id} · ${money(draft.lines[1].credit.amount_cents)}`),
    );
    const handoff = node("div", "handoff-grid");
    const cards = finding
      ? [
        ["SYSTEM PREPARED", "Balanced draft + evidence gates", "The workflow stopped at a reviewable, unposted proposal."],
        ["CONTROLLER DECIDES", "Approve, reject, or return", "Review the current invoice, contract, policy calculation, and draft."],
        ["NOT YET DONE", "No approval or posting", "The human decision is pending; no ledger entry was posted."],
      ]
      : [
        ["SOURCE PREVIEW", "Draft calculation only", "This panel is not evidence that an agent investigation ran."],
        ["NEXT STEP", "Run and inspect the case", "Use make demo-1, then review the recorded evidence and gates."],
        ["NOT YET DONE", "No approval or posting", "The human decision is pending; no ledger entry was posted."],
      ];
    for (const [eyebrow, title, description] of cards) {
      const card = node("div", "handoff-card");
      card.append(node("small", "", eyebrow), node("strong", "", title), node("span", "", description));
      handoff.append(card);
    }
    target.append(handoff);
  }
}

function decisionBand(targetId, label, title, description, badges) {
  const target = byId(targetId);
  clear(target);
  const copy = node("div");
  copy.append(node("span", "decision-label", label), node("h3", "", title), node("p", "", description));
  const meta = node("div", "decision-meta");
  for (const badge of badges) meta.append(node("span", "", badge));
  target.append(copy, meta);
}

function renderAnnual(data) {
  const blocked = data.quality.status === "BLOCKED" || !data.annual;
  byId("annualBlocked").hidden = !blocked;
  byId("annualBody").hidden = blocked;
  if (blocked) {
    text("annualBlocked", "Data admission is blocked. The annual investigation and derived finance outputs are hidden until the source package passes its checks.");
    byId("annualRunLink").hidden = true;
    return;
  }
  const annual = data.annual;
  const variance = annual.variance;
  text("annualActual", money(variance.actual.amount_cents));
  text("annualBudget", money(variance.comparison.amount_cents));
  text("annualVariance", money(variance.variance.amount_cents));
  text("actualBarLabel", money(variance.actual.amount_cents));
  text("budgetBarLabel", money(variance.comparison.amount_cents));
  byId("actualBar").style.width = "100%";
  byId("budgetBar").style.width = `${Math.max(3, Math.min(100, variance.comparison.amount_cents / variance.actual.amount_cents * 100))}%`;
  renderEvidenceDetail(data);
  const run = data.selected_run?.case_id === "annual-software-prepaid" ? data.selected_run : null;
  byId("annualRunLink").hidden = !run;
  const finding = run?.status === "SUCCEEDED" ? run.finding : null;
  decisionBand("annualDecision", finding ? "RECORDED RUN · GOVERNED OUTCOME" : "SOURCE-DERIVED PREVIEW",
    finding ? "Resolved for controller review." : "The accounting preview is not an agent finding.",
    finding ? finding.requested_human_action : "Run make demo-1 in the Codex terminal to record the investigation, evidence calls, gates, and finding.",
    finding ? [finding.resolution_status, finding.system_route, finding.human_decision, "UNPOSTED"] : ["NO RUN SELECTED", "UNPOSTED", "PENDING"]);
}

function renderReceipts(data) {
  const blocked = data.quality.status === "BLOCKED" || !data.receipts;
  byId("receiptsBlocked").hidden = !blocked;
  byId("receiptsBody").hidden = blocked;
  if (blocked) {
    text("receiptsBlocked", "Data admission is blocked. The receipt trend and escalation rule are hidden until the synthetic source package passes its checks.");
    return;
  }
  const receipts = data.receipts;
  const chart = byId("receiptChart");
  clear(chart);
  const maximum = Math.max(...receipts.snapshots.map((snapshot) => snapshot.amount_cents), 1);
  const summary = receipts.snapshots.map((item) => `${item.date}: ${money(item.amount_cents)} unmatched, oldest ${item.oldest_days} days`).join("; ");
  chart.setAttribute("aria-label", `Unmatched receipts trend: ${summary}`);
  for (const snapshot of receipts.snapshots) {
    const column = node("div", "chart-column");
    const bar = node("span", "chart-bar");
    bar.style.height = `${Math.max(8, Math.round(snapshot.amount_cents / maximum * 165))}px`;
    column.append(node("span", "chart-value", money(snapshot.amount_cents)), bar,
      node("span", "chart-date", snapshot.date.slice(5)));
    chart.append(column);
  }
  const table = byId("receiptTrendTable");
  clear(table);
  for (const snapshot of receipts.snapshots) {
    const row = node("div", "trend-row");
    row.append(node("span", "", `${snapshot.date} · oldest item ${snapshot.oldest_days} days`),
      node("strong", "", money(snapshot.amount_cents)));
    table.append(row);
  }
  const control = receipts.control;
  const thresholds = receipts.thresholds;
  const checks = [
    ["Repeated open checks", `${control.failed_checks} open · need ${thresholds.open_checks}`, control.failed_checks >= thresholds.open_checks],
    ["Material balance", `${money(control.current_unmatched.amount_cents)} · need ${money(thresholds.balance_cents)}`, control.current_unmatched.amount_cents >= thresholds.balance_cents],
    ["Aging beyond tolerance", `${control.oldest_receipt_days} days · must exceed ${thresholds.age_days_exclusive}`, control.oldest_receipt_days > thresholds.age_days_exclusive],
    ["Close is near", `${control.business_days_to_close} business days · within ${thresholds.close_business_days}`, control.business_days_to_close <= thresholds.close_business_days],
  ];
  const list = byId("thresholdList");
  clear(list);
  for (const [title, detail, passed] of checks) {
    const row = node("div", "threshold-item");
    const mark = node("span", `threshold-mark${passed ? "" : " failed"}`, passed ? "✓" : "!");
    const copy = node("div");
    copy.append(node("strong", "", title), node("small", "", detail));
    row.append(mark, copy);
    list.append(row);
  }
  decisionBand("receiptDecision", "DETERMINISTIC PRE-CLOSE CONTROL",
    control.triggered ? "Escalate before the close." : "Keep monitoring.",
    control.triggered
      ? `${receipts.owner.name} owns the ${receipts.owner.escalation_path} path. The root cause remains unproven; no journal entry is proposed.`
      : "The rule has not met all four conditions. No cause or accounting correction is inferred.",
    [control.route, "ROOT CAUSE NOT ESTABLISHED", "HUMAN DECISION PENDING"]);
}

function surface(topline, title, description = "") {
  const wrap = node("article", "surface");
  wrap.append(node("div", "surface-topline", topline), node("h3", "", title));
  if (description) wrap.append(node("p", "", description));
  return wrap;
}

function renderRunDetail(data) {
  const target = byId("runDetail");
  clear(target);
  const run = data.selected_run;
  if (!run) {
    const empty = node("div", "surface empty-state");
    empty.append(node("strong", "", "No saved run yet."),
      node("span", "", "Use the Codex terminal to run make demo-1 or the replay command; then refresh this view."));
    target.append(empty);
    return;
  }
  const finding = run.finding;
  const overview = surface("RECORDED OUTCOME", finding ? finding.resolution_status.replaceAll("_", " ") : run.status,
    finding?.observation || "The run ended before a governed finding was recorded. Raw provider diagnostics are not displayed here.");
  const facts = node("div", "run-facts");
  const values = [
    run.case_id.replaceAll("-", " "), run.mode.toUpperCase(), run.status,
    finding?.system_route || "NO ROUTE", finding?.human_decision || "NO DECISION",
  ];
  for (const value of values) facts.append(node("span", "run-fact", value));
  overview.append(facts);
  if (finding?.requested_human_action) overview.append(node("p", "", finding.requested_human_action));
  target.append(overview);

  const telemetry = surface("TIME, MODEL USE, AND COST", "Run telemetry");
  const telemetryFacts = node("div", "detail-facts");
  telemetryFacts.append(
    fact("Elapsed", duration(run.duration_ms)),
    fact("Provider", run.provider),
    fact("Input tokens", run.input_tokens == null ? "not reported" : run.input_tokens.toLocaleString()),
    fact("Output tokens", run.output_tokens == null ? "not reported" : run.output_tokens.toLocaleString()),
    fact("Provider cost", run.provider_cost_usd == null ? "not reported" : money(Math.round(run.provider_cost_usd * 100))),
    fact("Harness", run.harness_version),
  );
  telemetry.append(telemetryFacts);
  target.append(telemetry);

  const gates = surface("GOVERNANCE", "Checks before handoff");
  for (const gate of run.gates) {
    const row = node("div", "gate-row");
    row.append(node("span", `gate-icon${gate.passed ? "" : " failed"}`, gate.passed ? "✓" : "!"),
      node("strong", "", gate.gate_id), node("span", "", gate.message));
    gates.append(row);
  }
  target.append(gates);

  const timeline = surface("TOOL TRACE · NO PRIVATE REASONING", "What the workflow called");
  if (!run.timeline.length) timeline.append(node("p", "", "No live tool calls were recorded for this run. Replay cases use a frozen finding; only governed outputs are shown."));
  for (const [index, item] of run.timeline.entries()) {
    const row = node("div", "timeline-item");
    const body = node("div");
    body.append(node("strong", "", item.tool));
    if (item.input_ids.length) body.append(node("small", "", `Input IDs: ${item.input_ids.join(", ")}`));
    if (item.result_ids.length) body.append(node("small", "", `Returned IDs: ${item.result_ids.join(", ")}`));
    if (item.hits?.length) {
      const list = node("ul", "hit-list");
      for (const hit of item.hits) list.append(node("li", "", `${hit.title} · ${hit.passage_id} · ${hit.trust}`));
      body.append(list);
    }
    row.append(node("span", "timeline-index", index + 1), body);
    timeline.append(row);
  }
  target.append(timeline);

  const feedback = surface("SME REVIEW", "Feedback becomes a future eval");
  if (!run.feedback.length) feedback.append(node("p", "", "No SME verdict is attached to this run yet. The feedback command records a reviewer verdict and can nominate a failure for a frozen eval."));
  for (const item of run.feedback) {
    const row = node("div", "timeline-item");
    const body = node("div");
    body.append(node("strong", "", `${item.verdict} · ${item.reviewed_at}`), node("small", "", item.reviewer_note || "No note"));
    if (item.nominate_as_eval) body.append(node("small", "", "Nominated as eval"));
    row.append(node("span", "timeline-index", "✓"), body);
    feedback.append(row);
  }
  target.append(feedback);
}

function renderRuns(data) {
  text("runCount", String(data.runs.length));
  const list = byId("runList");
  clear(list);
  if (!data.runs.length) list.append(node("div", "empty-state", "No recorded runs yet."));
  for (const run of data.runs) {
    const selected = data.selected_run?.run_id === run.run_id;
    const item = node("button", `run-item${selected ? " is-selected" : ""}`);
    item.type = "button";
    item.setAttribute("aria-pressed", String(selected));
    item.append(node("strong", "", run.case_id.replaceAll("-", " ")),
      node("span", "", `${run.mode.toUpperCase()} · ${run.status} · ${duration(run.duration_ms)}`),
      node("span", "", run.run_id));
    item.addEventListener("click", () => { ui.selectedRunId = run.run_id; refreshData(true); });
    list.append(item);
  }
  renderRunDetail(data);
}

function render(data) {
  renderHero(data);
  renderQuality(data);
  renderAnnual(data);
  renderReceipts(data);
  renderRuns(data);
}

async function refreshData(force = false) {
  const params = ui.selectedRunId ? `?run=${encodeURIComponent(ui.selectedRunId)}` : "";
  try {
    const response = await fetch(`/api/state${params}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`The local site returned ${response.status}.`);
    const data = await response.json();
    const fingerprint = stateFingerprint(data);
    ui.data = data;
    if (force || fingerprint !== ui.fingerprint) {
      ui.fingerprint = fingerprint;
      render(data);
    }
    byId("loadError").hidden = true;
    text("refreshState", `Updated ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`);
  } catch (error) {
    const box = byId("loadError");
    box.textContent = `Could not load the local review data. ${error.message}`;
    box.hidden = false;
    text("refreshState", "Connection unavailable");
  }
}

for (const button of document.querySelectorAll(".view-tab")) {
  button.addEventListener("click", () => setView(button.dataset.view));
}
for (const button of document.querySelectorAll("[data-go]")) {
  button.addEventListener("click", () => setView(button.dataset.go, true));
}
byId("annualRunLink").addEventListener("click", () => setView("runs", true));
for (const button of document.querySelectorAll(".flow-step")) {
  button.addEventListener("click", () => {
    ui.evidenceStep = button.dataset.step;
    for (const step of document.querySelectorAll(".flow-step")) {
      const selected = step === button;
      step.classList.toggle("is-selected", selected);
      step.setAttribute("aria-pressed", String(selected));
    }
    if (ui.data) renderEvidenceDetail(ui.data);
  });
}
byId("refreshButton").addEventListener("click", () => refreshData(true));
const initialView = window.location.hash.replace("#", "");
setView(["overview", "annual", "receipts", "runs"].includes(initialView) ? initialView : "overview");
if (window.location.protocol === "file:") {
  byId("fileNotice").hidden = false;
  text("heroQuality", "Needs local server");
  text("heroQualitySub", "Run make site in the repository terminal");
  text("heroRun", "No data loaded");
  text("heroRunSub", "Open http://127.0.0.1:4173/ instead of this HTML file");
  text("refreshState", "Start the local server");
} else {
  refreshData(true);
  setInterval(() => refreshData(), 5000);
}
