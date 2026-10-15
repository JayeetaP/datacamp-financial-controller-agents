from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data" / "canonical"
    evidence_manifest: Path = PROJECT_ROOT / "data" / "evidence_manifest.json"
    knowledge_manifest: Path = PROJECT_ROOT / "knowledge" / "retrieval_manifest.json"
    policy_path: Path = PROJECT_ROOT / "controls" / "policy.yaml"
    outputs_dir: Path = PROJECT_ROOT / "outputs"
    codex_model: str | None = os.getenv("FIN_CONTROLLER_CODEX_MODEL") or None
    codex_reasoning: str = os.getenv("FIN_CONTROLLER_CODEX_REASONING", "low")
    live_timeout_seconds: int = int(os.getenv("FIN_CONTROLLER_LIVE_TIMEOUT_SECONDS", "180"))

    def load_policy(self) -> dict[str, Any]:
        with self.policy_path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)


SETTINGS = Settings()
