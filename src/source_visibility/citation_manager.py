"""Citation tracking module"""

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Citation:
    id: str
    source_id: str
    text: str
    document_name: str
    page_number: Optional[int]
    confidence: float
    citation_type: str


class CitationManager:
    def __init__(self):
        self._citations: dict[str, Citation] = {}

    def create_citation(
        self,
        source_id: str,
        text: str,
        document_name: str,
        page: Optional[int] = None,
        confidence: float = 1.0,
        citation_type: str = "direct",
    ) -> Citation:
        citation = Citation(
            id=str(uuid.uuid4()),
            source_id=source_id,
            text=text,
            document_name=document_name,
            page_number=page,
            confidence=confidence,
            citation_type=citation_type,
        )
        self._citations[citation.id] = citation
        return citation

    def get_citation(self, citation_id: str) -> Optional[Citation]:
        return self._citations.get(citation_id)

    def find_citations_by_source(self, source_id: str) -> list[Citation]:
        return [c for c in self._citations.values() if c.source_id == source_id]

    def find_citations_by_text(self, query: str) -> list[Citation]:
        query_lower = query.lower()
        return [c for c in self._citations.values() if query_lower in c.text.lower()]

    def format_citation(self, citation: Citation, style: str = "apa") -> str:
        page = citation.page_number
        doc = citation.document_name
        if style == "apa":
            if page is not None:
                return f"({doc}, p. {page})"
            return f"({doc})"
        elif style == "mla":
            if page is not None:
                return f"({doc} {page})"
            return f"({doc})"
        elif style == "chicago":
            if page is not None:
                return f"{doc}, {page}."
            return f"{doc}."
        else:
            if page is not None:
                return f"{doc}, page {page}"
            return f"{doc}"

    def format_citations(self, citations: list[Citation], style: str = "apa") -> list[str]:
        return [self.format_citation(c, style) for c in citations]

    def get_citation_count(self) -> int:
        return len(self._citations)


_citation_manager_instance: Optional[CitationManager] = None


def get_citation_manager() -> CitationManager:
    global _citation_manager_instance
    if _citation_manager_instance is None:
        _citation_manager_instance = CitationManager()
    return _citation_manager_instance
