from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from financial_controller.contracts import EvidenceTrust, KnowledgePassage, SearchHit


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9-]+", value)]


class KnowledgeSearch:
    def __init__(self, root: Path, manifest_path: Path) -> None:
        self.root = root
        self.manifest_path = manifest_path
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.documents: list[dict[str, Any]] = payload["documents"]
        self._contents: dict[str, str] = {}
        for document in self.documents:
            text = (root / document["path"]).read_text(encoding="utf-8")
            content = text.split("---", 2)[-1].strip()
            self._contents[document["document_id"]] = content

    def search(
        self,
        query: str,
        *,
        filters: dict[str, str] | None = None,
        top_k: int = 5,
    ) -> list[SearchHit]:
        filters = filters or {}
        candidates = [
            document
            for document in self.documents
            if all(str(document.get(key)) == value for key, value in filters.items())
        ]
        query_terms = _tokens(query)
        document_terms = {
            item["document_id"]: _tokens(
                " ".join(
                    [
                        item["title"],
                        self._contents[item["document_id"]],
                        " ".join(item.get("semantic_terms", [])),
                    ]
                )
            )
            for item in candidates
        }
        document_frequency = Counter(
            term for terms in document_terms.values() for term in set(terms)
        )
        total_documents = max(len(candidates), 1)
        scored: list[tuple[float, dict[str, Any]]] = []
        for document in candidates:
            terms = document_terms[document["document_id"]]
            counts = Counter(terms)
            lexical_score = 0.0
            for term in query_terms:
                if counts[term]:
                    inverse_frequency = math.log(
                        1
                        + (total_documents - document_frequency[term] + 0.5)
                        / (document_frequency[term] + 0.5)
                    )
                    lexical_score += counts[term] * inverse_frequency
            title_boost = sum(1.25 for term in query_terms if term in _tokens(document["title"]))
            scored.append((lexical_score + title_boost, document))

        hits: list[SearchHit] = []
        for score, document in sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]:
            content = self._contents[document["document_id"]]
            hits.append(
                SearchHit(
                    document_id=document["document_id"],
                    passage_id=document["passage_id"],
                    title=document["title"],
                    source_type=Path(document["path"]).parent.name,
                    version=str(document["version"]),
                    effective_date=date.fromisoformat(document["effective_date"]),
                    score=round(score, 6),
                    retrieval_mode="metadata+bm25",
                    trust=EvidenceTrust(document["trust"]),
                    excerpt=" ".join(content.split())[:280],
                )
            )
        return hits

    def get_passages(self, document_id: str, passage_ids: list[str]) -> list[KnowledgePassage]:
        document = next(
            (item for item in self.documents if item["document_id"] == document_id), None
        )
        if document is None:
            raise LookupError(f"Unknown knowledge document: {document_id}")
        if document["passage_id"] not in passage_ids:
            raise LookupError(f"Passage does not belong to {document_id}")
        return [
            KnowledgePassage(
                document_id=document_id,
                passage_id=document["passage_id"],
                title=document["title"],
                version=str(document["version"]),
                trust=EvidenceTrust(document["trust"]),
                content_hash=document["content_hash"],
                content=self._contents[document_id],
            )
        ]
