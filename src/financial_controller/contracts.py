from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataQualityStatus(StrEnum):
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    BLOCKED = "BLOCKED"


class ResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"
    UNRESOLVED = "UNRESOLVED"


class SystemRoute(StrEnum):
    NO_ACTION = "NO_ACTION"
    REVIEW = "REVIEW"
    ESCALATE = "ESCALATE"
    HARD_BLOCK = "HARD_BLOCK"


class HumanDecision(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RETURNED_FOR_WORK = "RETURNED_FOR_WORK"


class EvidenceTrust(StrEnum):
    SYSTEM_RECORD = "SYSTEM_RECORD"
    SUPPORTING_DOCUMENT = "SUPPORTING_DOCUMENT"
    HISTORICAL_GUIDANCE = "HISTORICAL_GUIDANCE"
    UNTRUSTED_TEXT = "UNTRUSTED_TEXT"


class CheckSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    BLOCKING = "BLOCKING"


class Money(StrictModel):
    amount_cents: int
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class DataQualityCheck(StrictModel):
    check_id: str
    passed: bool
    severity: CheckSeverity
    message: str
    source_ids: list[str] = Field(default_factory=list)


class DataQualityReport(StrictModel):
    package_id: str
    schema_version: str
    status: DataQualityStatus
    checks: list[DataQualityCheck]
    quarantined_records: int = 0
    generated_at: datetime


class VarianceResult(StrictModel):
    calculation_id: str
    case_id: str
    period: str
    entity_id: str
    account_id: str
    actual: Money
    comparison: Money
    variance: Money
    variance_basis_points: int | None
    material: bool
    materiality_rule_id: str | None
    source_ids: list[str]


class SearchHit(StrictModel):
    document_id: str
    passage_id: str
    title: str
    source_type: str
    version: str
    effective_date: date
    score: float
    retrieval_mode: str
    trust: EvidenceTrust
    excerpt: str


class KnowledgePassage(StrictModel):
    document_id: str
    passage_id: str
    title: str
    version: str
    trust: EvidenceTrust
    content_hash: str
    content: str


class EvidenceItem(StrictModel):
    evidence_id: str
    source_type: str
    source_record_id: str
    period: str
    entity_id: str
    trust: EvidenceTrust
    content_hash: str
    allowed_use: str
    fields: dict[str, Any]


class NumericClaim(StrictModel):
    name: str
    value: Money
    source_ids: list[str] = Field(min_length=1)


class PrepaidCalculation(StrictModel):
    calculation_id: str
    contract_id: str
    policy_id: str
    as_of_date: date
    service_start: date
    service_end: date
    term_months: int
    total: Money
    monthly_expense: Money
    expense_to_date: Money
    remaining_prepaid: Money
    source_ids: list[str]


class DraftLine(StrictModel):
    account_id: str
    debit: Money
    credit: Money
    description: str


class DraftAdjustment(StrictModel):
    draft_id: str
    status: str = "UNPOSTED"
    period: str
    calculation_id: str
    policy_id: str
    lines: list[DraftLine] = Field(min_length=2)
    evidence_ids: list[str]
    human_decision: HumanDecision = HumanDecision.PENDING


class Finding(StrictModel):
    case_id: str
    observation: str
    root_cause: str | None
    resolution_status: ResolutionStatus
    system_route: SystemRoute
    human_decision: HumanDecision = HumanDecision.PENDING
    guidance_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    calculation_ids: list[str] = Field(default_factory=list)
    numeric_claims: list[NumericClaim] = Field(default_factory=list)
    draft_adjustment_id: str | None = None
    unresolved_questions: list[str] = Field(default_factory=list)
    requested_human_action: str
    rationale: str


class PreventiveEscalationResult(StrictModel):
    case_id: str
    failed_checks: int
    current_unmatched: Money
    oldest_receipt_days: int
    business_days_to_close: int
    triggered: bool
    escalation_type: str | None
    rule_id: str
    route: SystemRoute


class GateResult(StrictModel):
    gate_id: str
    passed: bool
    message: str
    related_ids: list[str] = Field(default_factory=list)


class AgentRunRecord(StrictModel):
    run_id: str
    case_id: str
    mode: str
    provider: str
    authentication_mode: str
    requested_model: str | None
    returned_model: str | None
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    status: str
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_output_tokens: int | None = None
    billing_mode: str = "chatgpt_subscription"
    provider_cost_usd: float | None = None
    trace_id: str | None = None
    data_snapshot_id: str
    harness_version: str
    retrieval_ids: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)
    gate_results: list[GateResult] = Field(default_factory=list)
    finding: Finding | None = None
    artifact_paths: list[str] = Field(default_factory=list)
    error: str | None = None


class SMEFeedback(StrictModel):
    feedback_id: str
    run_id: str
    reviewer_role: str
    reviewed_at: datetime
    verdict: str
    route_correct: bool
    accounting_conclusion_correct: bool
    evidence_sufficient: bool
    missing_evidence_ids: list[str] = Field(default_factory=list)
    failure_categories: list[str] = Field(default_factory=list)
    reviewer_note: str
    nominate_as_eval: bool = False


class EvalResult(StrictModel):
    case_id: str
    passed: bool
    assertions: list[GateResult]
    mode: str
