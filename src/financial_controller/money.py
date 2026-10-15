from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def dollars_to_cents(value: str | int | Decimal) -> int:
    decimal_value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(decimal_value * 100)


def cents_to_dollars(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    absolute = abs(cents)
    return f"{sign}{absolute // 100:,}.{absolute % 100:02d}"


def format_money(cents: int, currency: str = "USD") -> str:
    return f"{currency} {cents_to_dollars(cents)}"
