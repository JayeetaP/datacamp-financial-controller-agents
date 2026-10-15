"""Intentionally flawed starter for the eval-led live coding segment."""


def should_escalate(
    *, failed_checks: int, balance_cents: int, oldest_days: int, days_to_close: int
) -> bool:
    # Intentional bug: policy says the oldest age must be strictly greater than 14 days.
    return (
        failed_checks >= 3
        and balance_cents >= 1_000_000
        and oldest_days >= 14
        and days_to_close <= 5
    )
