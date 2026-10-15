from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime

from financial_controller.config import SETTINGS
from financial_controller.contracts import SMEFeedback
from financial_controller.evaluation.runner import run_evaluations
from financial_controller.observability.store import RunStore
from financial_controller.quality.validator import validate_package
from financial_controller.reporting.render import render_run_report
from financial_controller.site.server import run_site
from financial_controller.workflows.runner import WorkflowRunner, record_as_json


def _store() -> RunStore:
    return RunStore(SETTINGS.outputs_dir / "run_ledger.sqlite3", SETTINGS.outputs_dir / "runs")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="financial-controller",
        description="Synthetic, governed financial-close agent demonstration",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="Run data-quality admission checks")

    run_parser = subparsers.add_parser("run", help="Run one demonstration case")
    run_parser.add_argument(
        "--case",
        required=True,
        choices=["annual-software-prepaid", "unmatched-receipts"],
    )
    run_parser.add_argument("--mode", choices=["replay", "live"], default="replay")

    eval_parser = subparsers.add_parser("eval", help="Run the five-case release gate")
    eval_parser.add_argument("--mode", choices=["replay", "live"], default="replay")

    report_parser = subparsers.add_parser("report", help="Regenerate a run report")
    report_target = report_parser.add_mutually_exclusive_group(required=True)
    report_target.add_argument("--latest", action="store_true")
    report_target.add_argument("--run-id")

    runs_parser = subparsers.add_parser("runs", help="List normalized run history")
    runs_parser.add_argument("--limit", type=int, default=10)

    site_parser = subparsers.add_parser("site", help="Serve the local read-only review site")
    site_parser.add_argument("--port", type=int, default=4173)

    feedback_parser = subparsers.add_parser("feedback", help="Attach structured SME feedback")
    feedback_parser.add_argument("--run-id", required=True)
    feedback_parser.add_argument("--verdict", choices=["ACCEPT", "REJECT"], required=True)
    feedback_parser.add_argument("--note", required=True)
    feedback_parser.add_argument("--nominate-as-eval", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.command == "validate":
        report = validate_package(SETTINGS.data_dir)
        print(report.model_dump_json(indent=2))
        return 0 if report.status != "BLOCKED" else 2

    if args.command == "run":
        record = WorkflowRunner(SETTINGS).run(args.case, args.mode)
        print(record_as_json(record))
        return 0 if record.status == "SUCCEEDED" else 1

    if args.command == "eval":
        results = run_evaluations(SETTINGS, args.mode)
        print(json.dumps([result.model_dump(mode="json") for result in results], indent=2))
        return 0 if all(result.passed for result in results) else 1

    if args.command == "report":
        store = _store()
        record = store.latest_run() if args.latest else store.get_run(args.run_id)
        paths = render_run_report(record, SETTINGS.outputs_dir / "reports")
        print("\n".join(str(path) for path in paths))
        return 0

    if args.command == "runs":
        rows = [
            {
                "run_id": record.run_id,
                "case_id": record.case_id,
                "mode": record.mode,
                "status": record.status,
                "duration_ms": record.duration_ms,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "provider_cost_usd": record.provider_cost_usd,
            }
            for record in _store().list_runs(args.limit)
        ]
        print(json.dumps(rows, indent=2))
        return 0

    if args.command == "site":
        run_site(SETTINGS, port=args.port)
        return 0

    if args.command == "feedback":
        feedback = SMEFeedback(
            feedback_id=f"FEEDBACK-{uuid.uuid4().hex[:10]}",
            run_id=args.run_id,
            reviewer_role="finance_sme",
            reviewed_at=datetime.now(UTC),
            verdict=args.verdict,
            route_correct=args.verdict == "ACCEPT",
            accounting_conclusion_correct=args.verdict == "ACCEPT",
            evidence_sufficient=args.verdict == "ACCEPT",
            reviewer_note=args.note,
            nominate_as_eval=args.nominate_as_eval,
        )
        store = _store()
        store.get_run(args.run_id)
        store.save_feedback(feedback)
        print(feedback.model_dump_json(indent=2))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
