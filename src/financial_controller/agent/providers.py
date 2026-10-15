from __future__ import annotations

import json
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from financial_controller.config import Settings
from financial_controller.contracts import Finding


def strict_output_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert a Pydantic schema to the all-fields-required Structured Outputs subset."""

    result = deepcopy(schema)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["required"] = list(properties)
                node["additionalProperties"] = False
            node.pop("default", None)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(result)
    return result


@dataclass
class ProviderResponse:
    finding: Finding
    provider: str
    requested_model: str | None
    returned_model: str | None
    trace_id: str | None
    duration_ms: int
    usage: dict[str, int | None] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    tool_names: list[str] = field(default_factory=list)


class InvestigatorProvider(ABC):
    @abstractmethod
    def investigate(self, case_payload: dict[str, Any]) -> ProviderResponse: ...


class ReplayProvider(InvestigatorProvider):
    def __init__(self, fixture_path: Path, case_id: str) -> None:
        self.fixture_path = fixture_path
        self.case_id = case_id

    def investigate(self, case_payload: dict[str, Any]) -> ProviderResponse:
        started = time.perf_counter()
        payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        finding = Finding.model_validate(payload[self.case_id])
        return ProviderResponse(
            finding=finding,
            provider="replay",
            requested_model=None,
            returned_model=None,
            trace_id=f"REPLAY-{self.case_id}",
            duration_ms=round((time.perf_counter() - started) * 1000),
            usage={
                "input_tokens": None,
                "cached_input_tokens": None,
                "output_tokens": None,
                "reasoning_output_tokens": None,
            },
            events=[],
            tool_names=[
                "search_close_knowledge",
                "get_knowledge_passages",
                "get_current_evidence",
                "calculate_prepaid_schedule",
                "prepare_draft_adjustment",
            ],
        )


class CodexProvider(InvestigatorProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _prompt(self, case_payload: dict[str, Any]) -> str:
        return f"""You are the bounded investigator for a synthetic financial-close demonstration.

Use only the read-only `finance_demo` MCP tools. Do not run shell commands, read repository files,
or use any other MCP server. Complete these stages in order with no more than six tool calls:

1. Search close knowledge for the account, renewal description, and prepaid treatment (top_k=3).
2. Fetch the most relevant runbook or policy passages by their returned IDs.
3. Retrieve the linked current invoice from `linked_current_evidence_ids` below.
4. Retrieve the current contract ID found on that invoice.
5. Call `calculate_prepaid_schedule` with the canonical policy and reporting date.
6. Call `prepare_draft_adjustment` with the same inputs.

The exception payload is:
{json.dumps(case_payload, indent=2)}

Historical guidance directs the procedure but is never current proof. Do not cite untrusted text as
guidance. Use POLICY-PREPAID-003 and tool results for every amount. Copy tool IDs exactly into the
finding.

Keep ID namespaces separate:
- evidence_ids must contain only IDs returned by get_current_evidence. For a resolved result, copy
  exactly the IDs in allowed_finding_evidence_ids; do not add any other IDs.
- GL, budget, variance, calculation, draft, policy, and knowledge IDs are not evidence_ids. The
  prohibited_finding_evidence_ids list gives concrete counterexamples for this case.
- Include monetary amounts stated in the narrative as numeric_claims. For each claim, use only the
  applicable lineage IDs from allowed_numeric_source_ids in numeric_claims.source_ids.
- Put the draft ID only in draft_adjustment_id, calculation IDs only in calculation_ids, the policy
  ID only in policy_ids, and retrieved knowledge document IDs only in guidance_ids.

Return only the schema-constrained finding. Human decision must remain PENDING; the route is REVIEW;
the draft remains UNPOSTED. All records are synthetic.
"""

    def investigate(self, case_payload: dict[str, Any]) -> ProviderResponse:
        with tempfile.TemporaryDirectory(prefix="financial-controller-codex-") as temp_dir:
            temp = Path(temp_dir)
            schema_path = temp / "finding.schema.json"
            output_path = temp / "finding.json"
            schema_path.write_text(
                json.dumps(strict_output_schema(Finding.model_json_schema()), indent=2),
                encoding="utf-8",
            )
            command = [
                "codex",
                "exec",
                "--ephemeral",
                "--json",
                "--sandbox",
                "read-only",
                "-C",
                str(self.settings.project_root),
                "-c",
                f'model_reasoning_effort="{self.settings.codex_reasoning}"',
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
            ]
            if self.settings.codex_model:
                command.extend(["--model", self.settings.codex_model])
            command.append("-")

            started = time.perf_counter()
            result = subprocess.run(
                command,
                input=self._prompt(case_payload),
                text=True,
                capture_output=True,
                timeout=self.settings.live_timeout_seconds,
                check=False,
            )
            duration_ms = round((time.perf_counter() - started) * 1000)
            if result.returncode:
                raise RuntimeError(
                    f"codex exec failed with exit {result.returncode}; "
                    f"events={result.stdout[-4000:]}; diagnostics={result.stderr[-2000:]}"
                )

            events = []
            for line in result.stdout.splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            finding = Finding.model_validate_json(output_path.read_text(encoding="utf-8"))
            completed = next(
                (event for event in reversed(events) if event.get("type") == "turn.completed"), {}
            )
            usage = completed.get("usage", {})
            thread = next((event for event in events if event.get("type") == "thread.started"), {})
            tool_names = sorted(
                {
                    event.get("item", {}).get("tool") or event.get("item", {}).get("name")
                    for event in events
                    if event.get("item", {}).get("type") == "mcp_tool_call"
                }
                - {None}
            )
            return ProviderResponse(
                finding=finding,
                provider="codex_exec",
                requested_model=self.settings.codex_model,
                returned_model=completed.get("model"),
                trace_id=thread.get("thread_id"),
                duration_ms=duration_ms,
                usage={
                    "input_tokens": usage.get("input_tokens"),
                    "cached_input_tokens": usage.get("cached_input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "reasoning_output_tokens": usage.get("reasoning_output_tokens"),
                },
                events=events,
                tool_names=tool_names,
            )
