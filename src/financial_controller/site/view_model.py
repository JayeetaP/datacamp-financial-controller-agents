from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

from financial_controller.config import Settings
from financial_controller.contracts import AgentRunRecord, DataQualityStatus
from financial_controller.engine.preventive import evaluate_unmatched_receipts
from financial_controller.engine.variance import calculate_variance
from financial_controller.money import dollars_to_cents
from financial_controller.quality.validator import validate_package
from financial_controller.repository import FinanceRepository
from financial_controller.services import FinanceServices

_RUN_ID = re.compile(r"^RUN-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_ID_KEYS = {
    "evidence_id",
    "contract_id",
    "document_id",
    "passage_id",
    "calculation_id",
    "draft_id",
    "policy_id",
    "rule_id",
    "source_id",
}
_ID_LIST_KEYS = {f"{key}s" for key in _ID_KEYS}


def _annual_preview(settings: Settings) -> dict[str, Any]:
    repository = FinanceRepository(settings)
    services = FinanceServices(settings)
    actual = repository.one("gl_actuals.csv", "source_id", "GL-SYN-6250-0908")
    budget = repository.one("budget.csv", "source_id", "BUD-SYN-6250-SEP")
    materiality = settings.load_policy()["materiality"]
    variance = calculate_variance(
        case_id="annual-software-prepaid",
        period=actual["period"],
        entity_id=actual["entity_id"],
        account_id=actual["account_id"],
        actual_cents=dollars_to_cents(actual["amount"]),
        comparison_cents=dollars_to_cents(budget["amount"]),
        currency=actual["currency"],
        source_ids=[actual["source_id"], budget["source_id"]],
        minimum_amount_cents=materiality["minimum_amount_cents"],
        minimum_percentage_basis_points=materiality["minimum_percentage_basis_points"],
        absolute_amount_cents=materiality["absolute_amount_cents"],
    )
    evidence = repository.get_evidence(["INV-SYN-1042", "CONTRACT-SYN-0077"])
    calculation = services.calculate_prepaid(
        "CONTRACT-SYN-0077", "POLICY-PREPAID-003", "2026-09-30"
    )
    draft = services.prepare_draft(calculation)
    guidance = services.search.search(
        "account 6250 Enterprise Platform Renewal prepaid treatment", top_k=3
    )
    return {
        "label": "DETERMINISTIC_SOURCE_PREVIEW",
        "variance": variance.model_dump(mode="json"),
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "guidance_candidates": [hit.model_dump(mode="json") for hit in guidance],
        "calculation": calculation.model_dump(mode="json"),
        "draft": draft.model_dump(mode="json"),
    }


def _receipts_preview(settings: Settings) -> dict[str, Any]:
    repository = FinanceRepository(settings)
    rows = sorted(
        repository.rows("unmatched_customer_payments.csv"), key=lambda row: row["check_date"]
    )
    latest = rows[-1]
    calendar = repository.one("close_calendar.csv", "period", "2026-09")
    policy = settings.load_policy()["unmatched_receipts"]
    result = evaluate_unmatched_receipts(
        case_id="unmatched-receipts",
        failed_checks=sum(row["status"] == "OPEN" for row in rows),
        current_unmatched_cents=dollars_to_cents(latest["unmatched_amount"]),
        oldest_receipt_days=int(latest["oldest_receipt_days"]),
        business_days_to_close=int(calendar["business_days_to_close"]),
        currency=latest["currency"],
        required_failed_checks=policy["consecutive_failed_checks"],
        minimum_balance_cents=policy["minimum_balance_cents"],
        minimum_oldest_age_days_exclusive=policy["minimum_oldest_age_days_exclusive"],
        close_within_business_days=policy["close_within_business_days"],
    )
    owner = repository.one("process_owners.csv", "process_id", "AR-CASH-MATCH")
    return {
        "label": "DETERMINISTIC_SOURCE_PREVIEW",
        "snapshots": [
            {
                "date": row["check_date"],
                "amount_cents": dollars_to_cents(row["unmatched_amount"]),
                "oldest_days": int(row["oldest_receipt_days"]),
                "status": row["status"],
            }
            for row in rows
        ],
        "control": result.model_dump(mode="json"),
        "thresholds": {
            "open_checks": policy["consecutive_failed_checks"],
            "balance_cents": policy["minimum_balance_cents"],
            "age_days_exclusive": policy["minimum_oldest_age_days_exclusive"],
            "close_business_days": policy["close_within_business_days"],
        },
        "owner": {
            "name": owner["owner_name"],
            "escalation_path": owner["escalation_path"],
        },
    }


def _load_runs(outputs_dir: Path) -> list[AgentRunRecord]:
    runs_dir = outputs_dir / "runs"
    if not runs_dir.exists():
        return []
    records: list[AgentRunRecord] = []
    for run_dir in runs_dir.iterdir():
        if run_dir.is_symlink() or not run_dir.is_dir() or not _RUN_ID.fullmatch(run_dir.name):
            continue
        path = run_dir / "run.json"
        if not path.is_file() or path.is_symlink():
            continue
        try:
            record = AgentRunRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.run_id == run_dir.name:
            records.append(record)
    return sorted(records, key=lambda record: record.completed_at, reverse=True)[:30]


def _collect_ids(value: Any) -> list[str]:
    ids: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                if key in _ID_KEYS and isinstance(item, str):
                    ids.append(item)
                elif key in _ID_LIST_KEYS and isinstance(item, list):
                    ids.extend(part for part in item if isinstance(part, str))
                else:
                    visit(item)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(value)
    return list(dict.fromkeys(ids))[:16]


def _tool_timeline(outputs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    path = outputs_dir / "runs" / run_id / "events.jsonl"
    if not path.is_file() or path.is_symlink():
        return []
    timeline: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index >= 2000:
                break
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "control.result":
                result = event.get("result", {})
                timeline.append(
                    {
                        "tool": "evaluate_unmatched_receipts",
                        "input_ids": [],
                        "result_ids": _collect_ids(result),
                        "hits": [],
                    }
                )
                continue
            item = event.get("item", {})
            if event.get("type") != "item.completed" or item.get("type") != "mcp_tool_call":
                continue
            result = item.get("result") or {}
            structured = result.get("structured_content", {})
            if isinstance(structured, dict):
                structured = structured.get("result", structured)
            hits = []
            if item.get("tool") == "search_close_knowledge" and isinstance(structured, list):
                hits = [
                    {
                        "passage_id": hit.get("passage_id"),
                        "title": hit.get("title"),
                        "trust": hit.get("trust"),
                    }
                    for hit in structured[:5]
                    if isinstance(hit, dict)
                ]
            timeline.append(
                {
                    "tool": str(item.get("tool") or "unknown_tool"),
                    "input_ids": _collect_ids(item.get("arguments") or {}),
                    "result_ids": _collect_ids(structured),
                    "hits": hits,
                }
            )
    return timeline


def _feedback(outputs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    database = outputs_dir / "run_ledger.sqlite3"
    if not database.is_file():
        return []
    uri = f"file:{quote(str(database), safe='/')}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            rows = connection.execute(
                "SELECT feedback_json FROM feedback WHERE run_id = ? ORDER BY reviewed_at DESC",
                (run_id,),
            ).fetchall()
    except sqlite3.Error:
        return []
    feedback = []
    for row in rows:
        try:
            item = json.loads(row[0])
        except json.JSONDecodeError:
            continue
        feedback.append(
            {
                "verdict": item.get("verdict"),
                "reviewed_at": item.get("reviewed_at"),
                "reviewer_note": item.get("reviewer_note"),
                "nominate_as_eval": item.get("nominate_as_eval", False),
            }
        )
    return feedback


def _run_summary(record: AgentRunRecord) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "case_id": record.case_id,
        "mode": record.mode,
        "provider": record.provider,
        "status": record.status,
        "completed_at": record.completed_at.isoformat(),
        "duration_ms": record.duration_ms,
        "data_snapshot_id": record.data_snapshot_id,
    }


def _run_detail(record: AgentRunRecord, outputs_dir: Path) -> dict[str, Any]:
    return {
        **_run_summary(record),
        "authentication_mode": record.authentication_mode,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "cached_input_tokens": record.cached_input_tokens,
        "provider_cost_usd": record.provider_cost_usd,
        "harness_version": record.harness_version,
        "finding": record.finding.model_dump(mode="json") if record.finding else None,
        "gates": [gate.model_dump(mode="json") for gate in record.gate_results],
        "timeline": _tool_timeline(outputs_dir, record.run_id),
        "feedback": _feedback(outputs_dir, record.run_id),
    }


def build_site_state(settings: Settings, selected_run_id: str | None = None) -> dict[str, Any]:
    """Return a curated, read-only viewer contract; never call a model or modify finance data."""

    if selected_run_id is not None and not _RUN_ID.fullmatch(selected_run_id):
        raise ValueError("Invalid run ID")
    quality = validate_package(settings.data_dir)
    runs = _load_runs(settings.outputs_dir)
    selected: AgentRunRecord | None = None
    if selected_run_id is not None:
        selected = next((record for record in runs if record.run_id == selected_run_id), None)
        if selected is None:
            raise LookupError(f"Unknown run ID: {selected_run_id}")
    elif runs:
        selected = next(
            (
                record
                for record in runs
                if record.case_id == "annual-software-prepaid"
                and record.mode == "live"
                and record.status == "SUCCEEDED"
            ),
            None,
        ) or next(
            (
                record
                for record in runs
                if record.case_id == "annual-software-prepaid" and record.status == "SUCCEEDED"
            ),
            runs[0],
        )

    ready = quality.status != DataQualityStatus.BLOCKED
    return {
        "synthetic": True,
        "quality": quality.model_dump(mode="json"),
        "annual": _annual_preview(settings) if ready else None,
        "receipts": _receipts_preview(settings) if ready else None,
        "runs": [_run_summary(record) for record in runs],
        "selected_run": _run_detail(selected, settings.outputs_dir) if selected else None,
    }
