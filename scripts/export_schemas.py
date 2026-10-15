from __future__ import annotations

import json
from pathlib import Path

from financial_controller.contracts import AgentRunRecord, DataQualityReport, Finding, SMEFeedback

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"


def main() -> int:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    models = {
        "agent-run-record": AgentRunRecord,
        "data-quality-report": DataQualityReport,
        "finding": Finding,
        "sme-feedback": SMEFeedback,
    }
    for name, model in models.items():
        (SCHEMA_DIR / f"{name}.schema.json").write_text(
            json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8"
        )
    print(f"Exported {len(models)} JSON schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
