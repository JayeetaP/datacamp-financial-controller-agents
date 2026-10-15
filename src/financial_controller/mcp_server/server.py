from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from financial_controller.config import SETTINGS
from financial_controller.services import FinanceServices

mcp = FastMCP("Synthetic Financial Close Evidence")


def _services() -> FinanceServices:
    return FinanceServices(SETTINGS)


@mcp.tool()
def search_close_knowledge(
    query: str, filters: dict[str, str] | None = None, top_k: int = 5
) -> list[dict[str, Any]]:
    """Search synthetic historical close guidance; results are not current-period proof."""
    return [
        hit.model_dump(mode="json")
        for hit in _services().search.search(query, filters=filters, top_k=top_k)
    ]


@mcp.tool()
def get_knowledge_passages(document_id: str, passage_ids: list[str]) -> list[dict[str, Any]]:
    """Fetch selected synthetic guidance passages by stable IDs."""
    return [
        passage.model_dump(mode="json")
        for passage in _services().search.get_passages(document_id, passage_ids)
    ]


@mcp.tool()
def get_current_evidence(evidence_ids: list[str]) -> list[dict[str, Any]]:
    """Fetch current-period synthetic evidence by immutable evidence ID."""
    return [
        item.model_dump(mode="json") for item in _services().repository.get_evidence(evidence_ids)
    ]


@mcp.tool()
def calculate_prepaid_schedule(contract_id: str, policy_id: str, as_of_date: str) -> dict[str, Any]:
    """Apply the canonical deterministic prepaid policy to a current synthetic contract."""
    return _services().calculate_prepaid(contract_id, policy_id, as_of_date).model_dump(mode="json")


@mcp.tool()
def prepare_draft_adjustment(contract_id: str, policy_id: str, as_of_date: str) -> dict[str, Any]:
    """Create a balanced UNPOSTED draft from a verified deterministic calculation."""
    services = _services()
    calculation = services.calculate_prepaid(contract_id, policy_id, as_of_date)
    return services.prepare_draft(calculation).model_dump(mode="json")


@mcp.tool()
def get_process_owner(process_id: str, entity_id: str) -> dict[str, str]:
    """Return the synthetic owner and escalation path for a finance process."""
    rows = _services().repository.rows("process_owners.csv")
    matches = [
        row for row in rows if row["process_id"] == process_id and row["entity_id"] == entity_id
    ]
    if len(matches) != 1:
        raise LookupError(f"No unique owner for {process_id}/{entity_id}")
    return matches[0]


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
