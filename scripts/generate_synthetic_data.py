from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "canonical"
EVIDENCE_MANIFEST = ROOT / "data" / "evidence_manifest.json"


TABLES: dict[str, list[dict[str, str]]] = {
    "chart_of_accounts.csv": [
        {"account_id": "1000", "account_name": "Cash", "account_type": "ASSET", "currency": "USD"},
        {
            "account_id": "1100",
            "account_name": "Accounts receivable",
            "account_type": "ASSET",
            "currency": "USD",
        },
        {
            "account_id": "1450",
            "account_name": "Prepaid software",
            "account_type": "ASSET",
            "currency": "USD",
        },
        {
            "account_id": "2000",
            "account_name": "Accounts payable",
            "account_type": "LIABILITY",
            "currency": "USD",
        },
        {
            "account_id": "3000",
            "account_name": "Synthetic equity",
            "account_type": "EQUITY",
            "currency": "USD",
        },
        {
            "account_id": "6250",
            "account_name": "Software subscriptions",
            "account_type": "EXPENSE",
            "currency": "USD",
        },
    ],
    "gl_actuals.csv": [
        {
            "source_id": "GL-SYN-6250-0908",
            "period": "2026-09",
            "entity_id": "CPS-US",
            "account_id": "6250",
            "amount": "144000.00",
            "currency": "USD",
            "journal_id": "JE-SYN-0908-014",
        },
        {
            "source_id": "GL-SYN-1100-0925",
            "period": "2026-09",
            "entity_id": "CPS-US",
            "account_id": "1100",
            "amount": "512400.00",
            "currency": "USD",
            "journal_id": "SYSTEM-AR-SEP",
        },
    ],
    "journal_lines.csv": [
        {
            "line_id": "JL-SYN-0908-014-1",
            "journal_id": "JE-SYN-0908-014",
            "period": "2026-09",
            "entity_id": "CPS-US",
            "account_id": "6250",
            "debit": "144000.00",
            "credit": "0.00",
            "currency": "USD",
            "memo": "Enterprise Platform Renewal — synthetic record",
            "source_id": "INV-SYN-1042",
        },
        {
            "line_id": "JL-SYN-0908-014-2",
            "journal_id": "JE-SYN-0908-014",
            "period": "2026-09",
            "entity_id": "CPS-US",
            "account_id": "2000",
            "debit": "0.00",
            "credit": "144000.00",
            "currency": "USD",
            "memo": "Enterprise Platform Renewal — synthetic record",
            "source_id": "INV-SYN-1042",
        },
    ],
    "budget.csv": [
        {
            "source_id": "BUD-SYN-6250-SEP",
            "period": "2026-09",
            "entity_id": "CPS-US",
            "account_id": "6250",
            "amount": "12000.00",
            "currency": "USD",
        }
    ],
    "vendor_invoices.csv": [
        {
            "evidence_id": "INV-SYN-1042",
            "invoice_id": "NGS-2026-1042",
            "vendor_name": "NimbusGrid Systems (Synthetic)",
            "contract_id": "CONTRACT-SYN-0077",
            "amount": "144000.00",
            "currency": "USD",
            "invoice_date": "2026-09-05",
            "description": "Enterprise Platform Renewal",
            "entity_id": "CPS-US",
            "period": "2026-09",
        }
    ],
    "contracts.csv": [
        {
            "evidence_id": "CONTRACT-SYN-0077",
            "contract_id": "CONTRACT-SYN-0077",
            "vendor_name": "NimbusGrid Systems (Synthetic)",
            "service_start": "2026-09-01",
            "service_end": "2027-08-31",
            "total_amount": "144000.00",
            "currency": "USD",
            "entity_id": "CPS-US",
            "period": "2026-09",
            "description": "Twelve-month enterprise platform subscription",
        }
    ],
    "bank_receipts.csv": [
        {
            "receipt_id": "REC-SYN-001",
            "bank_date": "2026-09-08",
            "amount": "4100.00",
            "currency": "USD",
            "customer_reference": "CUST-SYN-A",
        },
        {
            "receipt_id": "REC-SYN-002",
            "bank_date": "2026-09-13",
            "amount": "3700.00",
            "currency": "USD",
            "customer_reference": "CUST-SYN-B",
        },
        {
            "receipt_id": "REC-SYN-003",
            "bank_date": "2026-09-20",
            "amount": "4600.00",
            "currency": "USD",
            "customer_reference": "CUST-SYN-C",
        },
    ],
    "ar_open_invoices.csv": [
        {
            "invoice_id": "AR-SYN-5001",
            "customer_id": "CUST-SYN-A",
            "open_amount": "4100.00",
            "currency": "USD",
            "due_date": "2026-09-10",
        },
        {
            "invoice_id": "AR-SYN-5002",
            "customer_id": "CUST-SYN-B",
            "open_amount": "3700.00",
            "currency": "USD",
            "due_date": "2026-09-15",
        },
        {
            "invoice_id": "AR-SYN-5003",
            "customer_id": "CUST-SYN-C",
            "open_amount": "4600.00",
            "currency": "USD",
            "due_date": "2026-09-22",
        },
    ],
    "unmatched_customer_payments.csv": [
        {
            "check_date": "2026-09-11",
            "unmatched_amount": "4100.00",
            "oldest_receipt_days": "3",
            "status": "OPEN",
            "currency": "USD",
        },
        {
            "check_date": "2026-09-18",
            "unmatched_amount": "7800.00",
            "oldest_receipt_days": "10",
            "status": "OPEN",
            "currency": "USD",
        },
        {
            "check_date": "2026-09-25",
            "unmatched_amount": "12400.00",
            "oldest_receipt_days": "17",
            "status": "OPEN",
            "currency": "USD",
        },
    ],
    "process_owners.csv": [
        {
            "process_id": "AR-CASH-MATCH",
            "entity_id": "CPS-US",
            "owner_name": "Morgan Lee (Synthetic)",
            "escalation_path": "Controller > AR Operations Lead",
        }
    ],
    "close_calendar.csv": [
        {
            "period": "2026-09",
            "close_date": "2026-09-30",
            "as_of_date": "2026-09-25",
            "business_days_to_close": "3",
        }
    ],
}


def _csv_text(rows: list[dict[str, str]]) -> str:
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _row_hash(row: dict[str, str]) -> str:
    payload = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    return _sha256_bytes(payload)


def build_outputs() -> dict[Path, str]:
    outputs: dict[Path, str] = {}
    file_entries: list[dict[str, Any]] = []
    for name, rows in TABLES.items():
        text = _csv_text(rows)
        outputs[DATA_DIR / name] = text
        file_entries.append(
            {
                "name": name,
                "sha256": _sha256_bytes(text.encode()),
                "row_count": len(rows),
            }
        )

    evidence_records = []
    for file_name in ("vendor_invoices.csv", "contracts.csv"):
        for row in TABLES[file_name]:
            evidence_records.append(
                {
                    "evidence_id": row["evidence_id"],
                    "source_type": "vendor_invoice"
                    if file_name.startswith("vendor")
                    else "contract",
                    "file": f"data/canonical/{file_name}",
                    "source_record_id": row.get("invoice_id") or row["contract_id"],
                    "period": row["period"],
                    "entity_id": row["entity_id"],
                    "trust": "SUPPORTING_DOCUMENT",
                    "content_hash": _row_hash(row),
                    "allowed_use": "current_period_proof",
                }
            )
    evidence_text = (
        json.dumps({"version": "1.0", "synthetic": True, "records": evidence_records}, indent=2)
        + "\n"
    )
    outputs[EVIDENCE_MANIFEST] = evidence_text

    manifest = {
        "package_id": "PKG-CPS-2026-09-V1",
        "schema_version": "1.0",
        "reporting_period": "2026-09",
        "entity_id": "CPS-US",
        "synthetic": True,
        "extracted_at": "2026-09-25T18:00:00Z",
        "files": file_entries,
    }
    outputs[DATA_DIR / "package_manifest.json"] = json.dumps(manifest, indent=2) + "\n"
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if generated files differ")
    args = parser.parse_args()
    outputs = build_outputs()
    differences: list[str] = []
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_bytes() != content.encode("utf-8"):
                differences.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if differences:
        print("Synthetic data is out of date:")
        for difference in differences:
            print(f"- {difference}")
        return 1
    action = "Verified" if args.check else "Generated"
    print(f"{action} {len(outputs)} deterministic synthetic files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
