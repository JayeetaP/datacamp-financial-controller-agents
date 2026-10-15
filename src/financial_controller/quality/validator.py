from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from financial_controller.contracts import (
    CheckSeverity,
    DataQualityCheck,
    DataQualityReport,
    DataQualityStatus,
)
from financial_controller.money import dollars_to_cents

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "chart_of_accounts.csv": {"account_id", "account_name", "account_type", "currency"},
    "gl_actuals.csv": {"source_id", "period", "entity_id", "account_id", "amount", "currency"},
    "journal_lines.csv": {
        "line_id",
        "journal_id",
        "period",
        "entity_id",
        "account_id",
        "debit",
        "credit",
        "currency",
    },
    "budget.csv": {"source_id", "period", "entity_id", "account_id", "amount", "currency"},
    "vendor_invoices.csv": {
        "evidence_id",
        "invoice_id",
        "vendor_name",
        "contract_id",
        "amount",
        "currency",
        "invoice_date",
    },
    "contracts.csv": {
        "evidence_id",
        "contract_id",
        "vendor_name",
        "service_start",
        "service_end",
        "total_amount",
        "currency",
    },
    "bank_receipts.csv": {"receipt_id", "bank_date", "amount", "currency", "customer_reference"},
    "ar_open_invoices.csv": {"invoice_id", "customer_id", "open_amount", "currency", "due_date"},
    "unmatched_customer_payments.csv": {
        "check_date",
        "unmatched_amount",
        "oldest_receipt_days",
        "status",
        "currency",
    },
    "process_owners.csv": {"process_id", "entity_id", "owner_name", "escalation_path"},
    "close_calendar.csv": {"period", "close_date", "as_of_date", "business_days_to_close"},
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_package(data_dir: Path) -> DataQualityReport:
    manifest_path = data_dir / "package_manifest.json"
    checks: list[DataQualityCheck] = []
    if not manifest_path.exists():
        return DataQualityReport(
            package_id="unknown",
            schema_version="unknown",
            status=DataQualityStatus.BLOCKED,
            checks=[
                DataQualityCheck(
                    check_id="PACKAGE-MANIFEST",
                    passed=False,
                    severity=CheckSeverity.BLOCKING,
                    message="package_manifest.json is missing",
                )
            ],
            generated_at=datetime.now(UTC),
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    package_id = manifest["package_id"]
    schema_version = manifest["schema_version"]
    file_entries = {entry["name"]: entry for entry in manifest["files"]}

    for file_name, required in REQUIRED_COLUMNS.items():
        path = data_dir / file_name
        present = path.exists()
        checks.append(
            DataQualityCheck(
                check_id=f"FILE-{file_name}",
                passed=present,
                severity=CheckSeverity.BLOCKING,
                message="required file present"
                if present
                else f"missing required file {file_name}",
                source_ids=[file_name],
            )
        )
        if not present:
            continue
        entry = file_entries.get(file_name)
        hash_matches = entry is not None and entry.get("sha256") == _sha256(path)
        checks.append(
            DataQualityCheck(
                check_id=f"HASH-{file_name}",
                passed=hash_matches,
                severity=CheckSeverity.BLOCKING,
                message="file hash matches manifest" if hash_matches else "file hash mismatch",
                source_ids=[file_name],
            )
        )
        rows = _read_rows(path)
        expected_rows = entry.get("row_count") if entry else None
        count_matches = expected_rows == len(rows)
        checks.append(
            DataQualityCheck(
                check_id=f"COMPLETENESS-{file_name}",
                passed=count_matches and bool(rows),
                severity=CheckSeverity.BLOCKING,
                message=(
                    f"row count matches manifest ({len(rows)})"
                    if count_matches and rows
                    else (
                        "row count mismatch or empty file: "
                        f"expected {expected_rows}, got {len(rows)}"
                    )
                ),
                source_ids=[file_name],
            )
        )
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
        missing = sorted(required - columns)
        checks.append(
            DataQualityCheck(
                check_id=f"SCHEMA-{file_name}",
                passed=not missing,
                severity=CheckSeverity.BLOCKING,
                message="required columns present"
                if not missing
                else f"missing columns: {missing}",
                source_ids=[file_name],
            )
        )

    accounts_path = data_dir / "chart_of_accounts.csv"
    account_ids = (
        {row["account_id"] for row in _read_rows(accounts_path)}
        if accounts_path.exists()
        else set()
    )
    unknown_accounts: set[str] = set()
    for file_name in ("gl_actuals.csv", "journal_lines.csv", "budget.csv"):
        path = data_dir / file_name
        if path.exists():
            unknown_accounts.update(
                row["account_id"]
                for row in _read_rows(path)
                if row.get("account_id") not in account_ids
            )
    checks.append(
        DataQualityCheck(
            check_id="RELATIONSHIP-ACCOUNTS",
            passed=not unknown_accounts,
            severity=CheckSeverity.BLOCKING,
            message=(
                "all account references resolve"
                if not unknown_accounts
                else f"unknown accounts: {sorted(unknown_accounts)}"
            ),
            source_ids=sorted(unknown_accounts),
        )
    )

    invoice_path = data_dir / "vendor_invoices.csv"
    contract_path = data_dir / "contracts.csv"
    unmatched_contracts: list[str] = []
    amount_mismatches: list[str] = []
    if invoice_path.exists() and contract_path.exists():
        contracts = {row["contract_id"]: row for row in _read_rows(contract_path)}
        for invoice in _read_rows(invoice_path):
            contract = contracts.get(invoice["contract_id"])
            if contract is None:
                unmatched_contracts.append(invoice["contract_id"])
            elif (
                dollars_to_cents(invoice["amount"]) != dollars_to_cents(contract["total_amount"])
                or invoice["currency"] != contract["currency"]
            ):
                amount_mismatches.append(invoice["evidence_id"])
    checks.append(
        DataQualityCheck(
            check_id="RELATIONSHIP-INVOICE-CONTRACT",
            passed=not unmatched_contracts,
            severity=CheckSeverity.BLOCKING,
            message=(
                "all invoice contract references resolve"
                if not unmatched_contracts
                else f"missing contracts: {sorted(unmatched_contracts)}"
            ),
            source_ids=sorted(unmatched_contracts),
        )
    )
    checks.append(
        DataQualityCheck(
            check_id="RECONCILIATION-INVOICE-CONTRACT",
            passed=not amount_mismatches,
            severity=CheckSeverity.BLOCKING,
            message=(
                "invoice and contract totals and currencies reconcile"
                if not amount_mismatches
                else f"invoice/contract mismatches: {sorted(amount_mismatches)}"
            ),
            source_ids=sorted(amount_mismatches),
        )
    )

    unmatched_path = data_dir / "unmatched_customer_payments.csv"
    receipts_path = data_dir / "bank_receipts.csv"
    receipt_view_ok = False
    if unmatched_path.exists() and receipts_path.exists():
        unmatched_rows = sorted(_read_rows(unmatched_path), key=lambda row: row["check_date"])
        latest_unmatched = dollars_to_cents(unmatched_rows[-1]["unmatched_amount"])
        receipt_total = sum(dollars_to_cents(row["amount"]) for row in _read_rows(receipts_path))
        receipt_view_ok = latest_unmatched == receipt_total
    checks.append(
        DataQualityCheck(
            check_id="RECONCILIATION-UNMATCHED-VIEW",
            passed=receipt_view_ok,
            severity=CheckSeverity.BLOCKING,
            message=(
                "latest unmatched view reconciles to synthetic bank receipts"
                if receipt_view_ok
                else "latest unmatched view does not reconcile to synthetic bank receipts"
            ),
            source_ids=["unmatched_customer_payments.csv", "bank_receipts.csv"],
        )
    )

    journal_path = data_dir / "journal_lines.csv"
    imbalances: dict[str, int] = {}
    if journal_path.exists():
        totals: defaultdict[str, int] = defaultdict(int)
        for row in _read_rows(journal_path):
            totals[row["journal_id"]] += dollars_to_cents(row["debit"]) - dollars_to_cents(
                row["credit"]
            )
        imbalances = {journal_id: amount for journal_id, amount in totals.items() if amount}
    checks.append(
        DataQualityCheck(
            check_id="ACCOUNTING-JOURNAL-BALANCE",
            passed=not imbalances,
            severity=CheckSeverity.BLOCKING,
            message=(
                "all journals balance"
                if not imbalances
                else f"unbalanced journals: {sorted(imbalances)}"
            ),
            source_ids=sorted(imbalances),
        )
    )

    periods: set[str] = set()
    for file_name in ("gl_actuals.csv", "journal_lines.csv", "budget.csv"):
        path = data_dir / file_name
        if path.exists():
            periods.update(row["period"] for row in _read_rows(path))
    expected_period = manifest["reporting_period"]
    period_ok = periods == {expected_period}
    checks.append(
        DataQualityCheck(
            check_id="COMPLETENESS-PERIOD",
            passed=period_ok,
            severity=CheckSeverity.BLOCKING,
            message=(
                f"all finance records use {expected_period}"
                if period_ok
                else f"unexpected periods: {sorted(periods)}"
            ),
        )
    )

    blocked = any(not check.passed and check.severity == CheckSeverity.BLOCKING for check in checks)
    warned = any(not check.passed and check.severity == CheckSeverity.WARNING for check in checks)
    status = (
        DataQualityStatus.BLOCKED
        if blocked
        else DataQualityStatus.READY_WITH_WARNINGS
        if warned
        else DataQualityStatus.READY
    )
    return DataQualityReport(
        package_id=package_id,
        schema_version=schema_version,
        status=status,
        checks=checks,
        generated_at=datetime.now(UTC),
    )
