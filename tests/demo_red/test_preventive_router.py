from __future__ import annotations

import pytest

from demo_starter.preventive_router import should_escalate


@pytest.mark.demo_red
def test_fourteen_day_boundary_does_not_escalate() -> None:
    assert (
        should_escalate(
            failed_checks=3,
            balance_cents=1_240_000,
            oldest_days=14,
            days_to_close=3,
        )
        is False
    )
