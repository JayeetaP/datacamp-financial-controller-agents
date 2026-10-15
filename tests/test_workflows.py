from __future__ import annotations

from pathlib import Path

from financial_controller.config import Settings
from financial_controller.contracts import HumanDecision, SystemRoute
from financial_controller.observability.store import RunStore
from financial_controller.workflows.runner import WorkflowRunner


def test_replay_workflow_records_governed_result(isolated_settings: Settings) -> None:
    record = WorkflowRunner(isolated_settings).run("annual-software-prepaid", "replay")

    assert record.status == "SUCCEEDED"
    assert record.finding is not None
    assert record.finding.system_route == SystemRoute.REVIEW
    assert record.finding.human_decision == HumanDecision.PENDING
    assert all(gate.passed for gate in record.gate_results)
    assert all(Path(path).exists() for path in record.artifact_paths)

    stored = RunStore(
        isolated_settings.outputs_dir / "run_ledger.sqlite3",
        isolated_settings.outputs_dir / "runs",
    ).get_run(record.run_id)
    assert stored == record


def test_preventive_workflow_escalates_without_model(isolated_settings: Settings) -> None:
    record = WorkflowRunner(isolated_settings).run("unmatched-receipts", "replay")

    assert record.status == "SUCCEEDED"
    assert record.provider == "deterministic_control"
    assert record.finding is not None
    assert record.finding.system_route == SystemRoute.ESCALATE
    assert record.finding.root_cause is None
