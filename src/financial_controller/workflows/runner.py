from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from financial_controller.agent.providers import CodexProvider, InvestigatorProvider, ReplayProvider
from financial_controller.config import Settings
from financial_controller.contracts import (
    AgentRunRecord,
    DataQualityStatus,
    Finding,
    GateResult,
    HumanDecision,
    Money,
    NumericClaim,
    ResolutionStatus,
)
from financial_controller.engine.preventive import evaluate_unmatched_receipts
from financial_controller.engine.variance import calculate_variance
from financial_controller.gates.audit import audit_finding, require_all_gates
from financial_controller.money import dollars_to_cents, format_money
from financial_controller.observability.store import RunStore
from financial_controller.quality.validator import validate_package
from financial_controller.reporting.render import render_run_report
from financial_controller.repository import FinanceRepository
from financial_controller.services import FinanceServices

HARNESS_VERSION = "2026.10-demo.1"
ANNUAL_CASE_ID = "annual-software-prepaid"
RECEIPTS_CASE_ID = "unmatched-receipts"


class WorkflowRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.repository = FinanceRepository(settings)
        self.services = FinanceServices(settings)
        self.store = RunStore(
            settings.outputs_dir / "run_ledger.sqlite3", settings.outputs_dir / "runs"
        )

    def _provider(self, mode: str) -> InvestigatorProvider:
        if mode == "live":
            return CodexProvider(self.settings)
        if mode == "replay":
            return ReplayProvider(
                self.settings.project_root / "evals/fixtures/provider_findings.json",
                ANNUAL_CASE_ID,
            )
        raise ValueError(f"Unsupported mode: {mode}")

    def _save(self, record: AgentRunRecord, events: list[dict[str, Any]]) -> AgentRunRecord:
        run_dir = self.settings.outputs_dir / "runs" / record.run_id
        report_paths = render_run_report(record, self.settings.outputs_dir / "reports")
        record.artifact_paths.extend(
            [str(run_dir / "run.json"), str(run_dir / "events.jsonl")]
            + [str(path) for path in report_paths]
        )
        self.store.save_run(record, events)
        return record

    def run(self, case_id: str, mode: str) -> AgentRunRecord:
        if case_id == ANNUAL_CASE_ID:
            return self._run_annual(mode)
        if case_id == RECEIPTS_CASE_ID:
            return self._run_receipts(mode)
        raise ValueError(f"Unknown case: {case_id}")

    def _run_annual(self, mode: str) -> AgentRunRecord:
        started_at = datetime.now(UTC)
        wall_started = time.perf_counter()
        run_id = f"RUN-{started_at.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        quality = validate_package(self.settings.data_dir)
        if quality.status == DataQualityStatus.BLOCKED:
            completed_at = datetime.now(UTC)
            return self._save(
                AgentRunRecord(
                    run_id=run_id,
                    case_id=ANNUAL_CASE_ID,
                    mode=mode,
                    provider="not_invoked",
                    authentication_mode="none",
                    requested_model=None,
                    returned_model=None,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=round((time.perf_counter() - wall_started) * 1000),
                    status="BLOCKED_DATA_QUALITY",
                    data_snapshot_id=quality.package_id,
                    harness_version=HARNESS_VERSION,
                    gate_results=[
                        GateResult(
                            gate_id="DATA-ADMISSION",
                            passed=False,
                            message="source package failed blocking quality checks",
                        )
                    ],
                    error="Data-quality admission failed; provider was not invoked",
                ),
                [],
            )

        actual = self.repository.one("gl_actuals.csv", "source_id", "GL-SYN-6250-0908")
        budget = self.repository.one("budget.csv", "source_id", "BUD-SYN-6250-SEP")
        policy = self.settings.load_policy()
        materiality = policy["materiality"]
        variance = calculate_variance(
            case_id=ANNUAL_CASE_ID,
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
        case_payload = {
            "case_id": ANNUAL_CASE_ID,
            "data_quality_status": quality.status,
            "variance": variance.model_dump(mode="json"),
            "journal_description": "Enterprise Platform Renewal — synthetic record",
            "linked_current_evidence_ids": ["INV-SYN-1042"],
            "allowed_finding_evidence_ids": ["INV-SYN-1042", "CONTRACT-SYN-0077"],
            "allowed_numeric_source_ids": [
                *variance.source_ids,
                variance.calculation_id,
                "INV-SYN-1042",
                "CONTRACT-SYN-0077",
                "CALC-PREPAID-CONTRACT-SYN-0077-2026-09-30",
            ],
            "prohibited_finding_evidence_ids": [
                *variance.source_ids,
                variance.calculation_id,
                "CALC-PREPAID-CONTRACT-SYN-0077-2026-09-30",
                "DRAFT-CALC-PREPAID-CONTRACT-SYN-0077-2026-09-30",
            ],
            "canonical_policy_id": "POLICY-PREPAID-003",
            "reporting_date": "2026-09-30",
            "required_output": "supported finding and unposted draft for human review",
        }

        provider = self._provider(mode)
        events: list[dict[str, Any]] = []
        try:
            response = provider.investigate(case_payload)
            events = response.events
            evidence = self.repository.get_evidence(response.finding.evidence_ids)
            calculation = self.services.calculate_prepaid(
                "CONTRACT-SYN-0077", "POLICY-PREPAID-003", "2026-09-30"
            )
            draft = self.services.prepare_draft(calculation)
            gates = [
                GateResult(
                    gate_id="DATA-ADMISSION",
                    passed=True,
                    message=f"source package admitted as {quality.status}",
                )
            ]
            gates.extend(
                audit_finding(
                    finding=response.finding,
                    evidence=evidence,
                    calculations=[calculation],
                    draft=draft,
                    additional_source_ids=[*variance.source_ids, variance.calculation_id],
                )
            )
            unsafe_guidance = sorted(
                guidance_id
                for guidance_id in response.finding.guidance_ids
                if guidance_id.startswith("CASE-SYN-UNSAFE-001")
            )
            gates.append(
                GateResult(
                    gate_id="RETRIEVAL-AUTHORITY",
                    passed=not unsafe_guidance,
                    message=(
                        "retrieved text did not override canonical authority"
                        if not unsafe_guidance
                        else f"untrusted guidance was cited as authority: {unsafe_guidance}"
                    ),
                    related_ids=unsafe_guidance,
                )
            )
            require_all_gates(gates)
            completed_at = datetime.now(UTC)
            record = AgentRunRecord(
                run_id=run_id,
                case_id=ANNUAL_CASE_ID,
                mode=mode,
                provider=response.provider,
                authentication_mode=(
                    "chatgpt_saved_login" if response.provider == "codex_exec" else "fixture"
                ),
                requested_model=response.requested_model,
                returned_model=response.returned_model,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=round((time.perf_counter() - wall_started) * 1000),
                status="SUCCEEDED",
                input_tokens=response.usage.get("input_tokens"),
                cached_input_tokens=response.usage.get("cached_input_tokens"),
                output_tokens=response.usage.get("output_tokens"),
                reasoning_output_tokens=response.usage.get("reasoning_output_tokens"),
                trace_id=response.trace_id,
                data_snapshot_id=quality.package_id,
                harness_version=HARNESS_VERSION,
                retrieval_ids=response.finding.guidance_ids,
                tool_names=response.tool_names,
                gate_results=gates,
                finding=response.finding,
            )
        except Exception as error:
            completed_at = datetime.now(UTC)
            record = AgentRunRecord(
                run_id=run_id,
                case_id=ANNUAL_CASE_ID,
                mode=mode,
                provider="codex_exec" if mode == "live" else "replay",
                authentication_mode="chatgpt_saved_login" if mode == "live" else "fixture",
                requested_model=self.settings.codex_model,
                returned_model=None,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=round((time.perf_counter() - wall_started) * 1000),
                status="FAILED",
                data_snapshot_id=quality.package_id,
                harness_version=HARNESS_VERSION,
                error=str(error),
            )
        return self._save(record, events)

    def _run_receipts(self, mode: str) -> AgentRunRecord:
        started_at = datetime.now(UTC)
        wall_started = time.perf_counter()
        run_id = f"RUN-{started_at.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        quality = validate_package(self.settings.data_dir)
        if quality.status == DataQualityStatus.BLOCKED:
            raise ValueError("Data package is blocked; preventive workflow did not execute")

        rows = sorted(
            self.repository.rows("unmatched_customer_payments.csv"), key=lambda r: r["check_date"]
        )
        latest = rows[-1]
        calendar = self.repository.one("close_calendar.csv", "period", "2026-09")
        policy = self.settings.load_policy()["unmatched_receipts"]
        result = evaluate_unmatched_receipts(
            case_id=RECEIPTS_CASE_ID,
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
        owner = self.repository.one("process_owners.csv", "process_id", "AR-CASH-MATCH")
        finding = Finding(
            case_id=RECEIPTS_CASE_ID,
            observation=(
                "Unmatched customer receipts reached "
                f"{format_money(result.current_unmatched.amount_cents)} "
                f"after {result.failed_checks} consecutive open checks; the oldest item is "
                f"{result.oldest_receipt_days} days old with {result.business_days_to_close} "
                "business days to close."
            ),
            root_cause=None,
            resolution_status=ResolutionStatus.UNRESOLVED,
            system_route=result.route,
            human_decision=HumanDecision.PENDING,
            policy_ids=[result.rule_id],
            calculation_ids=[f"CONTROL-{RECEIPTS_CASE_ID}-2026-09-25"],
            numeric_claims=[
                NumericClaim(
                    name="current unmatched receipts",
                    value=Money(
                        amount_cents=result.current_unmatched.amount_cents,
                        currency=result.current_unmatched.currency,
                    ),
                    source_ids=["UNMATCHED-SNAPSHOT-2026-09-25"],
                )
            ],
            unresolved_questions=[
                "Which customer remittances or references are missing for the open receipts?"
            ],
            requested_human_action=(
                f"{owner['owner_name']} should coordinate the {owner['escalation_path']} path "
                "before close; no accounting root cause is inferred."
            ),
            rationale=(
                "The deterministic threshold requires three failed checks, at least USD 10,000, "
                "an oldest age above 14 days, and close within five business days. "
                "All conditions hold."
            ),
        )
        gates = [
            GateResult(
                gate_id="DATA-ADMISSION",
                passed=True,
                message=f"source package admitted as {quality.status}",
            ),
            GateResult(
                gate_id="PREVENTIVE-THRESHOLD",
                passed=result.triggered,
                message="all preventive escalation conditions hold",
                related_ids=[result.rule_id],
            ),
            GateResult(
                gate_id="NO-INVENTED-CAUSE",
                passed=finding.root_cause is None,
                message="workflow escalates without inventing a root cause",
            ),
            GateResult(
                gate_id="HUMAN-AUTHORITY",
                passed=finding.human_decision == HumanDecision.PENDING,
                message="human decision remains pending",
            ),
        ]
        require_all_gates(gates)
        completed_at = datetime.now(UTC)
        record = AgentRunRecord(
            run_id=run_id,
            case_id=RECEIPTS_CASE_ID,
            mode=mode,
            provider="deterministic_control",
            authentication_mode="none",
            requested_model=None,
            returned_model=None,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=round((time.perf_counter() - wall_started) * 1000),
            status="SUCCEEDED",
            billing_mode="not_applicable",
            data_snapshot_id=quality.package_id,
            harness_version=HARNESS_VERSION,
            tool_names=["evaluate_unmatched_receipts", "get_process_owner"],
            gate_results=gates,
            finding=finding,
        )
        return self._save(
            record, [{"type": "control.result", "result": result.model_dump(mode="json")}]
        )


def record_as_json(record: AgentRunRecord) -> str:
    return json.dumps(record.model_dump(mode="json"), indent=2)
