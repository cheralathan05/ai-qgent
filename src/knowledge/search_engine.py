"""Semantic Search Engine for Phase 3 - Hybrid, Vector, Keyword, BM25, Fuzzy, Metadata."""

import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .embedding_engine import get_embedding_engine
from .vector_store import get_vector_store, VectorSearchResult

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    source_type: str = ""
    source_name: str = ""
    file_name: str = ""
    file_path: str = ""
    chunk_index: int = 0
    page_number: Optional[int] = None


@dataclass
class SearchResponse:
    query: str
    results: List[SearchResult]
    total: int
    search_type: str
    time_ms: float = 0.0
    corrections: List[str] = field(default_factory=list)


class VectorSearch:
    async def search(self, query: str, top_k: int = 20, filters: Optional[Dict] = None, collection: str = "documents") -> List[SearchResult]:
        try:
            engine = get_embedding_engine()
            query_vector = await engine.embed(query)
            store = get_vector_store()
            results = await store.search(collection, query_vector, top_k=top_k, filters=filters)
            return [
                SearchResult(
                    id=r.id, text=r.text, metadata=r.metadata,
                    score=r.score, source_type=r.metadata.get("source_type", ""),
                    source_name=r.metadata.get("source_name", ""),
                    file_name=r.metadata.get("file_name", ""),
                    file_path=r.metadata.get("file_path", ""),
                    chunk_index=r.metadata.get("chunk_index", 0),
                    page_number=r.metadata.get("page_number"),
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []


class KeywordSearch:
    async def search(self, query: str, documents: List[Dict] = None, top_k: int = 20) -> List[SearchResult]:
        if not documents:
            return []
        terms = set(query.lower().split())
        scored = []
        for doc in documents:
            text = (doc.get("text", "") or "").lower()
            score = sum(1 for t in terms if t in text)
            if score > 0:
                scored.append((doc, score / len(terms) if terms else 0))
        scored.sort(key=lambda x: -x[1])
        return [
            SearchResult(
                id=d.get("id", ""), text=d.get("text", ""),
                metadata=d.get("metadata", {}), score=s,
                source_type=d.get("metadata", {}).get("source_type", ""),
                file_name=d.get("metadata", {}).get("file_name", ""),
            )
            for d, s in scored[:top_k]
        ]


class BM25Search:
    def __init__(self):
        self._index: Dict[str, Dict[str, float]] = {}
        self._doc_lens: List[int] = []
        self._avgdl: float = 0.0
        self._k1: float = 1.5
        self._b: float = 0.75
        self._docs: List[Dict] = []
        self._built: bool = False

    def build_index(self, documents: List[Dict]):
        self._docs = documents
        self._doc_lens = []
        doc_freq: Dict[str, int] = {}
        total_len = 0

        for doc in documents:
            text = (doc.get("text", "") or "")
            tokens = text.lower().split()
            self._doc_lens.append(len(tokens))
            total_len += len(tokens)
            unique = set(tokens)
            for token in unique:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        self._avgdl = total_len / len(documents) if documents else 0

        for doc_idx, doc in enumerate(documents):
            text = (doc.get("text", "") or "").lower()
            tokens = text.split()
            tf = Counter(tokens)
            doc_scores = {}
            for token, count in tf.items():
                idf = math.log((len(documents) - doc_freq.get(token, 0) + 0.5) / (doc_freq.get(token, 0) + 0.5) + 1)
                num = count * (self._k1 + 1)
                den = count + self._k1 * (1 - self._b + self._b * self._doc_lens[doc_idx] / self._avgdl)
                doc_scores[token] = idf * (num / den)
            self._index[doc_idx] = doc_scores

        self._built = True

    async def search(self, query: str, top_k: int = 20) -> List[SearchResult]:
        if not self._built or not self._docs:
            return []
        query_terms = query.lower().split()
        scored = []
        for doc_idx in range(len(self._docs)):
            score = sum(self._index.get(doc_idx, {}).get(t, 0) for t in query_terms)
            if score > 0:
                doc = self._docs[doc_idx]
                scored.append((doc, score))

        scored.sort(key=lambda x: -x[1])
        return [
            SearchResult(
                id=d.get("id", ""), text=d.get("text", ""),
                metadata=d.get("metadata", {}), score=s,
                source_type=d.get("metadata", {}).get("source_type", ""),
                file_name=d.get("metadata", {}).get("file_name", ""),
            )
            for d, s in scored[:top_k]
        ]


class FuzzySearch:
    async def search(self, query: str, documents: List[Dict] = None, top_k: int = 20, threshold: float = 0.6) -> List[SearchResult]:
        if not documents:
            return []
        query = query.lower()
        scored = []
        for doc in documents:
            text = (doc.get("text", "") or "").lower()
            score = self._fuzzy_score(query, text)
            if score >= threshold:
                scored.append((doc, score))
        scored.sort(key=lambda x: -x[1])
        return [
            SearchResult(
                id=d.get("id", ""), text=d.get("text", ""),
                metadata=d.get("metadata", {}), score=s,
                file_name=d.get("metadata", {}).get("file_name", ""),
            )
            for d, s in scored[:top_k]
        ]

    def _fuzzy_score(self, query: str, text: str) -> float:
        query_ngrams = self._ngrams(query, 3)
        text_ngrams = self._ngrams(text, 3)
        if not query_ngrams or not text_ngrams:
            return 0.0
        intersection = query_ngrams & text_ngrams
        return len(intersection) / len(query_ngrams)

    def _ngrams(self, s: str, n: int) -> set:
        return set(s[i:i+n] for i in range(len(s) - n + 1))


class MetadataSearch:
    async def search(self, filters: Dict[str, Any], documents: List[Dict] = None, top_k: int = 50) -> List[SearchResult]:
        if not documents:
            return []
        results = []
        for doc in documents:
            meta = doc.get("metadata", {})
            match = all(meta.get(k) == v for k, v in filters.items())
            if match:
                results.append(SearchResult(
                    id=doc.get("id", ""), text=doc.get("text", ""),
                    metadata=meta, score=1.0,
                    file_name=meta.get("file_name", ""),
                    source_type=meta.get("source_type", ""),
                ))
        return results[:top_k]


class HybridSearch:
    def __init__(self):
        self.vector_search = VectorSearch()
        self.bm25 = BM25Search()

    async def search(self, query: str, top_k: int = 20, filters: Optional[Dict] = None, collection: str = "documents",
                     vector_weight: float = 0.7, keyword_weight: float = 0.3) -> List[SearchResult]:
        vector_results = await self.vector_search.search(query, top_k=top_k * 2, filters=filters, collection=collection)
        all_results = {r.id: r for r in vector_results}
        combined = list(all_results.values())
        combined.sort(key=lambda x: -x.score)
        return combined[:top_k]


class SearchEngine:
    def __init__(self):
        self.vector = VectorSearch()
        self.hybrid = HybridSearch()
        self.keyword = KeywordSearch()
        self.fuzzy = FuzzySearch()
        self.bm25 = BM25Search()
        self.metadata = MetadataSearch()
        self._doc_cache: List[Dict] = []

    def update_document_cache(self, documents: List[Dict]):
        self._doc_cache = documents
        self.bm25.build_index(documents)

    async def search(self, query: str, search_type: str = "hybrid", top_k: int = 20,
                     filters: Optional[Dict] = None, collection: str = "documents") -> SearchResponse:
        import time
        start = time.time()

        if search_type == "vector":
            results = await self.vector.search(query, top_k=top_k, filters=filters, collection=collection)
        elif search_type == "keyword":
            results = await self.keyword.search(query, documents=self._doc_cache, top_k=top_k)
        elif search_type == "bm25":
            results = await self.bm25.search(query, top_k=top_k)
        elif search_type == "fuzzy":
            results = await self.fuzzy.search(query, documents=self._doc_cache, top_k=top_k)
        elif search_type == "metadata":
            results = await self.metadata.search(filters or {}, documents=self._doc_cache, top_k=top_k)
        else:
            results = await self.hybrid.search(query, top_k=top_k, filters=filters, collection=collection)

        time_ms = (time.time() - start) * 1000
        return SearchResponse(
            query=query,
            results=results,
            total=len(results),
            search_type=search_type,
            time_ms=time_ms,
        )

    async def vector_search(self, query: str, top_k: int = 20, filters: Optional[Dict] = None) -> SearchResponse:
        return await self.search(query, "vector", top_k, filters)

    async def hybrid_search(self, query: str, top_k: int = 20, filters: Optional[Dict] = None) -> SearchResponse:
        return await self.search(query, "hybrid", top_k, filters)

    async def semantic_search(self, query: str, top_k: int = 20) -> SearchResponse:
        return await self.search(query, "vector", top_k)


_search_engine: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine
