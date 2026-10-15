from __future__ import annotations

import re
from decimal import Decimal

from financial_controller.contracts import (
    DraftAdjustment,
    EvidenceItem,
    EvidenceTrust,
    Finding,
    GateResult,
    HumanDecision,
    PrepaidCalculation,
    ResolutionStatus,
    SystemRoute,
)


def audit_finding(
    *,
    finding: Finding,
    evidence: list[EvidenceItem],
    calculations: list[PrepaidCalculation],
    draft: DraftAdjustment | None,
    additional_source_ids: list[str] | None = None,
) -> list[GateResult]:
    evidence_by_id = {item.evidence_id: item for item in evidence}
    calculation_ids = {item.calculation_id for item in calculations}
    allowed_numeric_sources = (
        set(evidence_by_id) | calculation_ids | set(additional_source_ids or [])
    )

    missing_evidence = sorted(set(finding.evidence_ids) - set(evidence_by_id))
    gates = [
        GateResult(
            gate_id="EVIDENCE-RESOLUTION",
            passed=not missing_evidence,
            message=(
                "all evidence IDs resolve"
                if not missing_evidence
                else f"missing evidence IDs: {missing_evidence}"
            ),
            related_ids=missing_evidence,
        )
    ]

    unsupported_claims = [
        claim.name
        for claim in finding.numeric_claims
        if not set(claim.source_ids).issubset(allowed_numeric_sources)
    ]
    gates.append(
        GateResult(
            gate_id="NUMERIC-GROUNDING",
            passed=not unsupported_claims,
            message=(
                "all numeric claims resolve"
                if not unsupported_claims
                else f"unsupported numeric claims: {unsupported_claims}"
            ),
            related_ids=unsupported_claims,
        )
    )

    narrative = " ".join(
        filter(
            None,
            [
                finding.observation,
                finding.root_cause,
                finding.rationale,
                finding.requested_human_action,
            ],
        )
    )
    mentioned_cents = {
        int(Decimal(match.replace(",", "")) * 100)
        for match in re.findall(r"(?:USD|\$)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", narrative)
    }
    claimed_cents = {claim.value.amount_cents for claim in finding.numeric_claims}
    unsupported_amounts = sorted(mentioned_cents - claimed_cents)
    gates.append(
        GateResult(
            gate_id="OUTPUT-CLAIM-AUDIT",
            passed=not unsupported_amounts,
            message=(
                "all monetary statements appear in the grounded claim map"
                if not unsupported_amounts
                else f"unmapped monetary statements in narrative: {unsupported_amounts}"
            ),
            related_ids=[str(amount) for amount in unsupported_amounts],
        )
    )

    current_proof = [
        item
        for item in evidence
        if item.trust in {EvidenceTrust.SYSTEM_RECORD, EvidenceTrust.SUPPORTING_DOCUMENT}
        and item.allowed_use == "current_period_proof"
    ]
    causal_ok = finding.resolution_status != ResolutionStatus.RESOLVED or (
        finding.root_cause is not None and len(current_proof) >= 2
    )
    gates.append(
        GateResult(
            gate_id="CAUSAL-GROUNDING",
            passed=causal_ok,
            message=(
                "resolved cause has qualifying current evidence"
                if causal_ok
                else "resolved cause lacks qualifying current evidence"
            ),
            related_ids=[item.evidence_id for item in current_proof],
        )
    )

    authority_ok = finding.human_decision == HumanDecision.PENDING and finding.system_route in {
        SystemRoute.REVIEW,
        SystemRoute.ESCALATE,
        SystemRoute.HARD_BLOCK,
        SystemRoute.NO_ACTION,
    }
    gates.append(
        GateResult(
            gate_id="HUMAN-AUTHORITY",
            passed=authority_ok,
            message=(
                "human decision remains pending"
                if authority_ok
                else "system output attempted to set a human decision"
            ),
        )
    )

    if draft is not None:
        debits = sum(line.debit.amount_cents for line in draft.lines)
        credits = sum(line.credit.amount_cents for line in draft.lines)
        draft_ok = (
            draft.status == "UNPOSTED"
            and draft.human_decision == HumanDecision.PENDING
            and debits == credits
            and draft.calculation_id in calculation_ids
            and finding.draft_adjustment_id == draft.draft_id
        )
        gates.append(
            GateResult(
                gate_id="DRAFT-INTEGRITY",
                passed=draft_ok,
                message="draft is balanced and unposted" if draft_ok else "draft integrity failed",
                related_ids=[draft.draft_id, draft.calculation_id],
            )
        )

    return gates


def require_all_gates(gates: list[GateResult]) -> None:
    failures = [gate for gate in gates if not gate.passed]
    if failures:
        summary = "; ".join(f"{gate.gate_id}: {gate.message}" for gate in failures)
        raise ValueError(f"Governance gate failure: {summary}")
