"""Frozen viewer cases for the synthetic close review site.

These preserve the business boundary: data admission first, current evidence for a
resolved case, deterministic math, and a pending human decision.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import replace

import pytest

from financial_controller.config import SETTINGS
from financial_controller.site.server import route_get
from financial_controller.site.view_model import build_site_state
from financial_controller.workflows.runner import WorkflowRunner


def test_ready_package_has_two_distinct_finance_paths(tmp_path):
    settings = replace(SETTINGS, outputs_dir=tmp_path / "outputs")

    state = build_site_state(settings)

    assert state["synthetic"] is True
    assert state["quality"]["status"] == "READY"
    assert state["annual"]["variance"]["variance"]["amount_cents"] == 13_200_000
    assert state["annual"]["calculation"]["remaining_prepaid"]["amount_cents"] == 13_200_000
    assert state["annual"]["draft"]["status"] == "UNPOSTED"
    assert state["annual"]["draft"]["human_decision"] == "PENDING"
    assert state["receipts"]["control"]["triggered"] is True
    assert state["receipts"]["control"]["route"] == "ESCALATE"
    assert state["selected_run"] is None  # Scenario facts are not presented as an agent run.


def test_blocked_package_hides_finance_outputs_before_any_agent_run(tmp_path):
    data_dir = tmp_path / "data"
    shutil.copytree(SETTINGS.data_dir, data_dir)
    actuals = data_dir / "gl_actuals.csv"
    actuals.write_text(actuals.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    settings = replace(SETTINGS, data_dir=data_dir, outputs_dir=tmp_path / "outputs")

    state = build_site_state(settings)

    assert state["quality"]["status"] == "BLOCKED"
    assert state["annual"] is None
    assert state["receipts"] is None
    assert state["selected_run"] is None
    assert any(not check["passed"] for check in state["quality"]["checks"])


def test_recorded_run_shows_audited_result_but_not_private_event_text(tmp_path):
    settings = replace(SETTINGS, outputs_dir=tmp_path / "outputs")
    record = WorkflowRunner(settings).run("annual-software-prepaid", "replay")
    assert record.status == "SUCCEEDED"
    events = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": "PRIVATE_TEXT"}},
        {
            "type": "item.completed",
            "item": {
                "type": "mcp_tool_call",
                "tool": "search_close_knowledge",
                "arguments": {"query": "annual renewal"},
                "result": {
                    "structured_content": {
                        "result": [
                            {
                                "document_id": "KB-CLOSE-014",
                                "passage_id": "KB-CLOSE-014-P1",
                                "title": "Annual renewal guidance",
                                "trust": "HISTORICAL_GUIDANCE",
                            }
                        ]
                    }
                },
            },
        },
    ]
    path = settings.outputs_dir / "runs" / record.run_id / "events.jsonl"
    path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")

    state = build_site_state(settings, selected_run_id=record.run_id)
    selected = state["selected_run"]

    assert selected["finding"]["resolution_status"] == "RESOLVED"
    assert selected["finding"]["human_decision"] == "PENDING"
    assert all(gate["passed"] for gate in selected["gates"])
    assert selected["timeline"][0]["tool"] == "search_close_knowledge"
    assert selected["timeline"][0]["result_ids"] == ["KB-CLOSE-014", "KB-CLOSE-014-P1"]
    assert "PRIVATE_TEXT" not in json.dumps(selected)


def test_run_selection_rejects_path_traversal(tmp_path):
    settings = replace(SETTINGS, outputs_dir=tmp_path / "outputs")

    with pytest.raises(ValueError, match="run ID"):
        build_site_state(settings, selected_run_id="../secrets")


def test_site_serves_only_curated_state_and_static_assets(tmp_path):
    settings = replace(SETTINGS, outputs_dir=tmp_path / "outputs")

    status, content_type, body = route_get(settings, "/api/state", "")

    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    assert json.loads(body)["synthetic"] is True
    assert route_get(settings, "/README.md", "")[0] == 404
    assert route_get(settings, "/api/state", "run=../secrets")[0] == 400


def test_direct_html_open_explains_how_to_start_the_local_site(tmp_path):
    settings = replace(SETTINGS, outputs_dir=tmp_path / "outputs")

    status, _, body = route_get(settings, "/", "")
    html = body.decode("utf-8")
    script = route_get(settings, "/app.js", "")[2].decode("utf-8")

    assert status == 200
    assert 'href="./styles.css"' in html
    assert 'src="./app.js"' in html
    assert 'id="annualRunLink"' in html
    assert 'window.location.protocol === "file:"' in script
    assert "make site" in script


def test_site_uses_a_restrained_finance_workspace_shell(tmp_path):
    settings = replace(SETTINGS, outputs_dir=tmp_path / "outputs")
    html = route_get(settings, "/", "")[2].decode("utf-8")
    css = route_get(settings, "/styles.css", "")[2].decode("utf-8")

    assert "September close review" in html
    assert "Annual software expense" in html
    assert "Run history" in html
    assert "--paper: #ffffff" in css
    assert "Georgia" not in css
