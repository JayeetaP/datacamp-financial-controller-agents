from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from financial_controller.config import SETTINGS, Settings


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Settings:
    return replace(SETTINGS, outputs_dir=tmp_path / "outputs")
