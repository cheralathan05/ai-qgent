"""Document Retriever for Phase 3."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .search_engine import get_search_engine, SearchResult, SearchResponse
from .indexer import get_index_manager, Chunk, IndexedDocument
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class RetrievedDocument:
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[Chunk] = field(default_factory=list)
    document: Optional[IndexedDocument] = None


class DocumentRetriever:
    def __init__(self):
        self.search_engine = get_search_engine()
        self.index_manager = get_index_manager()

    async def retrieve(self, query: str, top_k: int = 10, search_type: str = "hybrid",
                       filters: Optional[Dict] = None) -> List[RetrievedDocument]:
        response = await self.search_engine.search(
            query=query, search_type=search_type, top_k=top_k, filters=filters,
        )
        return self._convert_results(response.results)

    async def retrieve_with_scores(self, query: str, top_k: int = 10) -> List[RetrievedDocument]:
        response = await self.search_engine.hybrid_search(query, top_k=top_k)
        return self._convert_results(response.results)

    async def retrieve_by_source(self, query: str, source_type: str, top_k: int = 10) -> List[RetrievedDocument]:
        return await self.retrieve(query, top_k=top_k, filters={"source_type": source_type})

    async def retrieve_by_file(self, file_name: str) -> List[RetrievedDocument]:
        docs = self.index_manager.search_documents(file_name)
        results = []
        for doc in docs:
            chunks = [c for c in self.index_manager.get_all_chunks()
                     if c.metadata.get("document_id") == doc.id]
            results.append(RetrievedDocument(
                id=doc.id, text="", score=1.0,
                metadata=doc.metadata, chunks=chunks, document=doc,
            ))
        return results

    def _convert_results(self, results: List[SearchResult]) -> List[RetrievedDocument]:
        converted = []
        seen_docs = set()
        for r in results:
            doc_id = r.metadata.get("document_id", r.id)
            doc = self.index_manager.get_document(doc_id)
            chunk = None
            for c in self.index_manager.get_all_chunks():
                if c.id == r.id:
                    chunk = c
                    break
            ret = RetrievedDocument(
                id=r.id, text=r.text, score=r.score,
                metadata=r.metadata, document=doc,
            )
            if chunk:
                ret.chunks = [chunk]
            if doc_id not in seen_docs or r.score > 0.5:
                converted.append(ret)
                seen_docs.add(doc_id)
        return converted


_retriever: Optional[DocumentRetriever] = None


def get_document_retriever() -> DocumentRetriever:
    global _retriever
    if _retriever is None:
        _retriever = DocumentRetriever()
    return _retriever
