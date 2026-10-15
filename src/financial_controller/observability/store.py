from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from financial_controller.contracts import AgentRunRecord, SMEFeedback


class RunStore:
    """Persist normalized runs while keeping raw provider events inspectable."""

    def __init__(self, database_path: Path, artifacts_dir: Path) -> None:
        self.database_path = database_path
        self.artifacts_dir = artifacts_dir
        database_path.parent.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS runs_case_time
                    ON runs(case_id, completed_at DESC);
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    feedback_json TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                """
            )

    def save_run(self, record: AgentRunRecord, events: list[dict[str, Any]] | None = None) -> Path:
        payload = record.model_dump_json(indent=2)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, case_id, mode, provider, status, started_at,
                    completed_at, duration_ms, record_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.run_id,
                    record.case_id,
                    record.mode,
                    record.provider,
                    record.status,
                    record.started_at.isoformat(),
                    record.completed_at.isoformat(),
                    record.duration_ms,
                    payload,
                ),
            )

        run_dir = self.artifacts_dir / record.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        record_path = run_dir / "run.json"
        record_path.write_text(payload + "\n", encoding="utf-8")
        events_path = run_dir / "events.jsonl"
        with events_path.open("w", encoding="utf-8") as handle:
            for event in events or []:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
        return record_path

    def save_feedback(self, feedback: SMEFeedback) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO feedback (
                    feedback_id, run_id, reviewed_at, feedback_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    feedback.feedback_id,
                    feedback.run_id,
                    feedback.reviewed_at.isoformat(),
                    feedback.model_dump_json(),
                ),
            )

    def get_run(self, run_id: str) -> AgentRunRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record_json FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise LookupError(f"Unknown run ID: {run_id}")
        return AgentRunRecord.model_validate_json(row["record_json"])

    def latest_run(self, case_id: str | None = None) -> AgentRunRecord:
        query = "SELECT record_json FROM runs"
        parameters: tuple[str, ...] = ()
        if case_id:
            query += " WHERE case_id = ?"
            parameters = (case_id,)
        query += " ORDER BY completed_at DESC LIMIT 1"
        with self._connect() as connection:
            row = connection.execute(query, parameters).fetchone()
        if row is None:
            raise LookupError("No recorded runs")
        return AgentRunRecord.model_validate_json(row["record_json"])

    def list_runs(self, limit: int = 20) -> list[AgentRunRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record_json FROM runs ORDER BY completed_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [AgentRunRecord.model_validate_json(row["record_json"]) for row in rows]
