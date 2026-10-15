from __future__ import annotations

import html
from pathlib import Path

from financial_controller.contracts import AgentRunRecord
from financial_controller.money import format_money


def _finding_markdown(record: AgentRunRecord) -> list[str]:
    finding = record.finding
    if finding is None:
        return ["## Result", "", f"Run failed before a finding was produced: {record.error}"]

    lines = [
        "## Decision",
        "",
        f"- Resolution: `{finding.resolution_status}`",
        f"- System route: `{finding.system_route}`",
        f"- Human decision: `{finding.human_decision}`",
        f"- Requested action: {finding.requested_human_action}",
        "",
        "## Finding",
        "",
        finding.observation,
        "",
        f"**Root cause:** {finding.root_cause or 'Not established'}",
        "",
        f"**Rationale:** {finding.rationale}",
        "",
        "## Grounded numeric claims",
        "",
        "| Claim | Value | Sources |",
        "|---|---:|---|",
    ]
    for claim in finding.numeric_claims:
        lines.append(
            f"| {claim.name} | {format_money(claim.value.amount_cents, claim.value.currency)} "
            f"| {', '.join(claim.source_ids)} |"
        )
    lines.extend(
        [
            "",
            "## Evidence map",
            "",
            f"- Current evidence: {', '.join(finding.evidence_ids) or 'None'}",
            f"- Guidance: {', '.join(finding.guidance_ids) or 'None'}",
            f"- Policies: {', '.join(finding.policy_ids) or 'None'}",
            f"- Calculations: {', '.join(finding.calculation_ids) or 'None'}",
            f"- Draft adjustment: {finding.draft_adjustment_id or 'None'}",
        ]
    )
    return lines


def render_run_report(record: AgentRunRecord, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / f"{record.run_id}.md"
    html_path = output_dir / f"{record.run_id}.html"
    input_tokens = record.input_tokens if record.input_tokens is not None else "not reported"
    output_tokens = record.output_tokens if record.output_tokens is not None else "not reported"
    provider_cost = (
        "not reported by subscription runtime"
        if record.provider_cost_usd is None
        else f"USD {record.provider_cost_usd:.4f}"
    )
    markdown = "\n".join(
        [
            "# Synthetic Financial Close Review",
            "",
            "> **SYNTHETIC DATA — EDUCATIONAL DEMONSTRATION ONLY**",
            "",
            f"Run `{record.run_id}` · case `{record.case_id}` · mode `{record.mode}`",
            "",
            *_finding_markdown(record),
            "",
            "## Governance gates",
            "",
            "| Gate | Result | Detail |",
            "|---|---|---|",
            *[
                f"| {gate.gate_id} | {'PASS' if gate.passed else 'FAIL'} | {gate.message} |"
                for gate in record.gate_results
            ],
            "",
            "## Run telemetry",
            "",
            f"- Provider: `{record.provider}`",
            f"- Authentication: `{record.authentication_mode}`",
            f"- Duration: {record.duration_ms} ms",
            f"- Input tokens: {input_tokens}",
            f"- Output tokens: {output_tokens}",
            f"- Provider cost: {provider_cost}",
            f"- Tools: {', '.join(record.tool_names) or 'None'}",
            "",
        ]
    )
    markdown_path.write_text(markdown, encoding="utf-8")

    escaped = html.escape(markdown)
    html_document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Synthetic close review — {html.escape(record.run_id)}</title>
<style>
body {{ font: 16px/1.55 system-ui, sans-serif; max-width: 980px; margin: 40px auto;
padding: 0 24px; color: #17202a; }}
pre {{ white-space: pre-wrap; background: #f6f8fa; border: 1px solid #d8dee4;
padding: 24px; border-radius: 12px; }}
</style></head><body><pre>{escaped}</pre></body></html>"""
    html_path.write_text(html_document, encoding="utf-8")
    return markdown_path, html_path
