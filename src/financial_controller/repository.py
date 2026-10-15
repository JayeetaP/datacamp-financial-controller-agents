from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from financial_controller.config import Settings
from financial_controller.contracts import EvidenceItem, EvidenceTrust


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class FinanceRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def rows(self, file_name: str) -> list[dict[str, str]]:
        return read_csv_rows(self.settings.data_dir / file_name)

    def one(self, file_name: str, key: str, value: str) -> dict[str, str]:
        matches = [row for row in self.rows(file_name) if row.get(key) == value]
        if len(matches) != 1:
            raise LookupError(f"Expected one {file_name} row for {key}={value}; got {len(matches)}")
        return matches[0]

    def evidence_manifest(self) -> dict[str, Any]:
        return json.loads(self.settings.evidence_manifest.read_text(encoding="utf-8"))

    def get_evidence(self, evidence_ids: list[str]) -> list[EvidenceItem]:
        records = {row["evidence_id"]: row for row in self.evidence_manifest()["records"]}
        results: list[EvidenceItem] = []
        for evidence_id in evidence_ids:
            manifest_record = records.get(evidence_id)
            if manifest_record is None:
                raise LookupError(f"Unknown evidence ID: {evidence_id}")
            file_name = Path(manifest_record["file"]).name
            row = self.one(file_name, "evidence_id", evidence_id)
            results.append(
                EvidenceItem(
                    evidence_id=evidence_id,
                    source_type=manifest_record["source_type"],
                    source_record_id=manifest_record["source_record_id"],
                    period=manifest_record["period"],
                    entity_id=manifest_record["entity_id"],
                    trust=EvidenceTrust(manifest_record["trust"]),
                    content_hash=manifest_record["content_hash"],
                    allowed_use=manifest_record["allowed_use"],
                    fields=row,
                )
            )
        return results
