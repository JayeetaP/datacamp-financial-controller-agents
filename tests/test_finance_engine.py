from __future__ import annotations

from datetime import date

from financial_controller.contracts import SystemRoute
from financial_controller.engine.prepaid_schedule import calculate_prepaid_schedule
from financial_controller.engine.preventive import evaluate_unmatched_receipts
from financial_controller.engine.variance import calculate_variance


def test_annual_prepaid_schedule() -> None:
    calculation = calculate_prepaid_schedule(
        contract_id="CONTRACT-SYN-0077",
        policy_id="POLICY-PREPAID-003",
        as_of_date=date(2026, 9, 30),
        service_start=date(2026, 9, 1),
        service_end=date(2027, 8, 31),
        total_cents=14_400_000,
        currency="USD",
        source_ids=["CONTRACT-SYN-0077"],
    )

    assert calculation.term_months == 12
    assert calculation.monthly_expense.amount_cents == 1_200_000
    assert calculation.remaining_prepaid.amount_cents == 13_200_000


def test_variance_is_material() -> None:
    variance = calculate_variance(
        case_id="annual-software-prepaid",
        period="2026-09",
        entity_id="CPS-US",
        account_id="6250",
        actual_cents=14_400_000,
        comparison_cents=1_200_000,
        currency="USD",
        source_ids=["GL-SYN-6250-0908", "BUD-SYN-6250-SEP"],
        minimum_amount_cents=1_000_000,
        minimum_percentage_basis_points=1_000,
        absolute_amount_cents=2_500_000,
    )

    assert variance.variance.amount_cents == 13_200_000
    assert variance.material is True
    assert variance.materiality_rule_id == "MATERIALITY-ABSOLUTE"


def test_preventive_rule_requires_age_strictly_above_fourteen_days() -> None:
    boundary = evaluate_unmatched_receipts(
        case_id="unmatched-receipts",
        failed_checks=3,
        current_unmatched_cents=1_240_000,
        oldest_receipt_days=14,
        business_days_to_close=3,
        currency="USD",
        required_failed_checks=3,
        minimum_balance_cents=1_000_000,
        minimum_oldest_age_days_exclusive=14,
        close_within_business_days=5,
    )
    triggered = boundary.model_copy(update={"oldest_receipt_days": 17})
    actual = evaluate_unmatched_receipts(
        case_id="unmatched-receipts",
        failed_checks=3,
        current_unmatched_cents=1_240_000,
        oldest_receipt_days=17,
        business_days_to_close=3,
        currency="USD",
        required_failed_checks=3,
        minimum_balance_cents=1_000_000,
        minimum_oldest_age_days_exclusive=14,
        close_within_business_days=5,
    )

    assert boundary.triggered is False
    assert actual.triggered is True
    assert actual.route == SystemRoute.ESCALATE
    assert triggered.oldest_receipt_days == actual.oldest_receipt_days
