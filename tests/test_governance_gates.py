from __future__ import annotations

import json

from financial_controller.agent.providers import strict_output_schema
from financial_controller.config import SETTINGS
from financial_controller.contracts import Finding
from financial_controller.gates.audit import audit_finding
from financial_controller.services import FinanceServices


def _replay_finding() -> Finding:
    payload = json.loads(
        (SETTINGS.project_root / "evals/fixtures/provider_findings.json").read_text(
            encoding="utf-8"
        )
    )
    return Finding.model_validate(payload["annual-software-prepaid"])


def test_supported_finding_passes_all_gates() -> None:
    services = FinanceServices(SETTINGS)
    finding = _replay_finding()
    calculation = services.calculate_prepaid(
        "CONTRACT-SYN-0077", "POLICY-PREPAID-003", "2026-09-30"
    )
    draft = services.prepare_draft(calculation)

    gates = audit_finding(
        finding=finding,
        evidence=services.repository.get_evidence(finding.evidence_ids),
        calculations=[calculation],
        draft=draft,
        additional_source_ids=[
            "GL-SYN-6250-0908",
            "BUD-SYN-6250-SEP",
            "VAR-annual-software-prepaid-2026-09-6250",
        ],
    )

    assert all(gate.passed for gate in gates)


def test_unmapped_money_in_narrative_fails_claim_audit() -> None:
    services = FinanceServices(SETTINGS)
    finding = _replay_finding().model_copy(
        update={"rationale": "The unexplained amount is USD 999,999."}
    )
    calculation = services.calculate_prepaid(
        "CONTRACT-SYN-0077", "POLICY-PREPAID-003", "2026-09-30"
    )

    gates = audit_finding(
        finding=finding,
        evidence=services.repository.get_evidence(finding.evidence_ids),
        calculations=[calculation],
        draft=services.prepare_draft(calculation),
        additional_source_ids=[
            "GL-SYN-6250-0908",
            "BUD-SYN-6250-SEP",
            "VAR-annual-software-prepaid-2026-09-6250",
        ],
    )

    claim_gate = next(gate for gate in gates if gate.gate_id == "OUTPUT-CLAIM-AUDIT")
    assert claim_gate.passed is False


def test_codex_output_schema_requires_every_property() -> None:
    schema = strict_output_schema(Finding.model_json_schema())

    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False
    for definition in schema["$defs"].values():
        if "properties" in definition:
            assert set(definition["required"]) == set(definition["properties"])
            assert definition["additionalProperties"] is False
