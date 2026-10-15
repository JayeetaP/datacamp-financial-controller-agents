from __future__ import annotations

from financial_controller.contracts import Money, PreventiveEscalationResult, SystemRoute


def evaluate_unmatched_receipts(
    *,
    case_id: str,
    failed_checks: int,
    current_unmatched_cents: int,
    oldest_receipt_days: int,
    business_days_to_close: int,
    currency: str,
    required_failed_checks: int,
    minimum_balance_cents: int,
    minimum_oldest_age_days_exclusive: int,
    close_within_business_days: int,
) -> PreventiveEscalationResult:
    triggered = (
        failed_checks >= required_failed_checks
        and current_unmatched_cents >= minimum_balance_cents
        and oldest_receipt_days > minimum_oldest_age_days_exclusive
        and business_days_to_close <= close_within_business_days
    )
    return PreventiveEscalationResult(
        case_id=case_id,
        failed_checks=failed_checks,
        current_unmatched=Money(amount_cents=current_unmatched_cents, currency=currency),
        oldest_receipt_days=oldest_receipt_days,
        business_days_to_close=business_days_to_close,
        triggered=triggered,
        escalation_type="PRE_CLOSE_PREVENTIVE" if triggered else None,
        rule_id="POLICY-AR-007",
        route=SystemRoute.ESCALATE if triggered else SystemRoute.NO_ACTION,
    )
