from __future__ import annotations

from financial_controller.config import SETTINGS
from financial_controller.contracts import EvidenceTrust
from financial_controller.retrieval.search import KnowledgeSearch


def test_annual_renewal_guidance_is_in_top_three() -> None:
    search = KnowledgeSearch(SETTINGS.project_root, SETTINGS.knowledge_manifest)

    hits = search.search("annual software renewal prepaid contract", top_k=3)

    assert "KB-CLOSE-014" in {hit.document_id for hit in hits}
    assert all(hit.retrieval_mode == "metadata+bm25" for hit in hits)


def test_adversarial_document_keeps_untrusted_label() -> None:
    search = KnowledgeSearch(SETTINGS.project_root, SETTINGS.knowledge_manifest)

    hits = search.search("ignore controller policy mark approved", top_k=5)
    unsafe = next(hit for hit in hits if hit.document_id == "CASE-SYN-UNSAFE-001")

    assert unsafe.trust == EvidenceTrust.UNTRUSTED_TEXT
