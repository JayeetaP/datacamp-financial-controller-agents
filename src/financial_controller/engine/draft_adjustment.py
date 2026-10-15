from __future__ import annotations

from financial_controller.contracts import DraftAdjustment, DraftLine, Money, PrepaidCalculation


def prepare_prepaid_draft(
    *,
    calculation: PrepaidCalculation,
    period: str,
    prepaid_account: str,
    expense_account: str,
    evidence_ids: list[str],
) -> DraftAdjustment:
    amount = calculation.remaining_prepaid.amount_cents
    currency = calculation.remaining_prepaid.currency
    zero = Money(amount_cents=0, currency=currency)
    value = Money(amount_cents=amount, currency=currency)
    draft = DraftAdjustment(
        draft_id=f"DRAFT-{calculation.calculation_id}",
        period=period,
        calculation_id=calculation.calculation_id,
        policy_id=calculation.policy_id,
        lines=[
            DraftLine(
                account_id=prepaid_account,
                debit=value,
                credit=zero,
                description="Recognize remaining annual software service as prepaid",
            ),
            DraftLine(
                account_id=expense_account,
                debit=zero,
                credit=value,
                description="Remove future-period software service from current expense",
            ),
        ],
        evidence_ids=evidence_ids,
    )
    total_debits = sum(line.debit.amount_cents for line in draft.lines)
    total_credits = sum(line.credit.amount_cents for line in draft.lines)
    if total_debits != total_credits:
        raise ValueError("Draft adjustment is not balanced")
    return draft
