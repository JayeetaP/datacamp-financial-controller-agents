from __future__ import annotations

from financial_controller.contracts import Money, VarianceResult


def calculate_variance(
    *,
    case_id: str,
    period: str,
    entity_id: str,
    account_id: str,
    actual_cents: int,
    comparison_cents: int,
    currency: str,
    source_ids: list[str],
    minimum_amount_cents: int,
    minimum_percentage_basis_points: int,
    absolute_amount_cents: int,
) -> VarianceResult:
    variance_cents = actual_cents - comparison_cents
    percentage_basis_points = None
    if comparison_cents:
        percentage_basis_points = round(abs(variance_cents) / abs(comparison_cents) * 10_000)

    percentage_rule = (
        abs(variance_cents) >= minimum_amount_cents
        and percentage_basis_points is not None
        and percentage_basis_points >= minimum_percentage_basis_points
    )
    absolute_rule = abs(variance_cents) >= absolute_amount_cents
    material = percentage_rule or absolute_rule
    rule_id = None
    if absolute_rule:
        rule_id = "MATERIALITY-ABSOLUTE"
    elif percentage_rule:
        rule_id = "MATERIALITY-AMOUNT-AND-PERCENT"

    return VarianceResult(
        calculation_id=f"VAR-{case_id}-{period}-{account_id}",
        case_id=case_id,
        period=period,
        entity_id=entity_id,
        account_id=account_id,
        actual=Money(amount_cents=actual_cents, currency=currency),
        comparison=Money(amount_cents=comparison_cents, currency=currency),
        variance=Money(amount_cents=variance_cents, currency=currency),
        variance_basis_points=percentage_basis_points,
        material=material,
        materiality_rule_id=rule_id,
        source_ids=source_ids,
    )
