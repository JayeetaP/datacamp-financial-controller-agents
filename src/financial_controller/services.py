from __future__ import annotations

from datetime import date

from financial_controller.config import SETTINGS, Settings
from financial_controller.contracts import DraftAdjustment, PrepaidCalculation
from financial_controller.engine.draft_adjustment import prepare_prepaid_draft
from financial_controller.engine.prepaid_schedule import calculate_prepaid_schedule
from financial_controller.money import dollars_to_cents
from financial_controller.repository import FinanceRepository
from financial_controller.retrieval.search import KnowledgeSearch


class FinanceServices:
    def __init__(self, settings: Settings = SETTINGS) -> None:
        self.settings = settings
        self.repository = FinanceRepository(settings)
        self.search = KnowledgeSearch(settings.project_root, settings.knowledge_manifest)

    def calculate_prepaid(
        self, contract_id: str, policy_id: str, as_of_date: str
    ) -> PrepaidCalculation:
        contract = self.repository.one("contracts.csv", "contract_id", contract_id)
        policy = self.settings.load_policy()["prepaid_software"]
        if policy_id != policy["policy_id"]:
            raise ValueError(f"Policy {policy_id} is not the canonical prepaid policy")
        total_cents = dollars_to_cents(contract["total_amount"])
        if total_cents < policy["minimum_invoice_cents"]:
            raise ValueError("Contract does not meet the prepaid threshold")
        calculation = calculate_prepaid_schedule(
            contract_id=contract_id,
            policy_id=policy_id,
            as_of_date=date.fromisoformat(as_of_date),
            service_start=date.fromisoformat(contract["service_start"]),
            service_end=date.fromisoformat(contract["service_end"]),
            total_cents=total_cents,
            currency=contract["currency"],
            source_ids=[contract["evidence_id"]],
        )
        if calculation.term_months < policy["minimum_term_months"]:
            raise ValueError("Contract does not meet the prepaid term threshold")
        return calculation

    def prepare_draft(self, calculation: PrepaidCalculation) -> DraftAdjustment:
        policy = self.settings.load_policy()["prepaid_software"]
        return prepare_prepaid_draft(
            calculation=calculation,
            period=self.settings.load_policy()["reporting"]["period"],
            prepaid_account=policy["prepaid_account"],
            expense_account=policy["expense_account"],
            evidence_ids=["INV-SYN-1042", calculation.contract_id],
        )
