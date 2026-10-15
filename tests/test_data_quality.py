from __future__ import annotations

import shutil
from pathlib import Path

from financial_controller.config import SETTINGS
from financial_controller.contracts import DataQualityStatus
from financial_controller.quality.validator import validate_package


def test_generated_package_is_ready() -> None:
    report = validate_package(SETTINGS.data_dir)

    assert report.status == DataQualityStatus.READY
    assert all(check.passed for check in report.checks)
    assert {check.check_id for check in report.checks} >= {
        "ACCOUNTING-JOURNAL-BALANCE",
        "RELATIONSHIP-INVOICE-CONTRACT",
        "RECONCILIATION-INVOICE-CONTRACT",
        "RECONCILIATION-UNMATCHED-VIEW",
    }


def test_tampered_package_is_blocked(tmp_path: Path) -> None:
    copied = tmp_path / "canonical"
    shutil.copytree(SETTINGS.data_dir, copied)
    journal = copied / "journal_lines.csv"
    journal.write_text(
        journal.read_text(encoding="utf-8").replace("0.00,144000.00", "0.00,143000.00"),
        encoding="utf-8",
    )

    report = validate_package(copied)

    assert report.status == DataQualityStatus.BLOCKED
    failures = {check.check_id for check in report.checks if not check.passed}
    assert "HASH-journal_lines.csv" in failures
    assert "ACCOUNTING-JOURNAL-BALANCE" in failures
