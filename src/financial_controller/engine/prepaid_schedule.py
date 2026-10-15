from __future__ import annotations

import calendar
from datetime import date

from financial_controller.contracts import Money, PrepaidCalculation


def _month_index(value: date) -> int:
    return value.year * 12 + value.month


def calculate_prepaid_schedule(
    *,
    contract_id: str,
    policy_id: str,
    as_of_date: date,
    service_start: date,
    service_end: date,
    total_cents: int,
    currency: str,
    source_ids: list[str],
) -> PrepaidCalculation:
    if service_start.day != 1:
        raise ValueError("Whole-month policy requires service_start on the first day")
    expected_last_day = calendar.monthrange(service_end.year, service_end.month)[1]
    if service_end.day != expected_last_day:
        raise ValueError("Whole-month policy requires service_end on the last day")
    if service_end < service_start:
        raise ValueError("service_end must not precede service_start")
    if not service_start <= as_of_date <= service_end:
        raise ValueError("as_of_date must fall inside the service period")

    term_months = _month_index(service_end) - _month_index(service_start) + 1
    if total_cents % term_months:
        raise ValueError("Demo policy requires an evenly divisible whole-month amount")
    monthly_cents = total_cents // term_months
    elapsed_months = _month_index(as_of_date) - _month_index(service_start) + 1
    expense_to_date_cents = monthly_cents * elapsed_months
    remaining_cents = total_cents - expense_to_date_cents

    return PrepaidCalculation(
        calculation_id=f"CALC-PREPAID-{contract_id}-{as_of_date.isoformat()}",
        contract_id=contract_id,
        policy_id=policy_id,
        as_of_date=as_of_date,
        service_start=service_start,
        service_end=service_end,
        term_months=term_months,
        total=Money(amount_cents=total_cents, currency=currency),
        monthly_expense=Money(amount_cents=monthly_cents, currency=currency),
        expense_to_date=Money(amount_cents=expense_to_date_cents, currency=currency),
        remaining_prepaid=Money(amount_cents=remaining_cents, currency=currency),
        source_ids=source_ids,
    )
