"""Knowledge Analytics and Dashboard for Phase 3."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from knowledge.indexer import get_index_manager
from knowledge.source_connectors import get_all_connectors
from knowledge.vector_store import get_vector_store
from knowledge_graph.engine import get_knowledge_graph
from memory.engine import get_memory_engine

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeMetrics:
    indexed_documents: int = 0
    indexed_chunks: int = 0
    total_embeddings: int = 0
    knowledge_sources: int = 0
    memory_entries: int = 0
    graph_entities: int = 0
    graph_relationships: int = 0
    search_count: int = 0
    top_topics: List[str] = field(default_factory=list)
    sources_breakdown: Dict[str, int] = field(default_factory=dict)
    entity_types: Dict[str, int] = field(default_factory=dict)
    memory_types: Dict[str, int] = field(default_factory=dict)
    last_indexed: Optional[str] = None
    vector_store_size: int = 0


class KnowledgeAnalytics:
    def __init__(self):
        self._search_log: List[Dict] = []
        self._max_log = 1000

    def get_knowledge_metrics(self) -> KnowledgeMetrics:
        index = get_index_manager()
        kg = get_knowledge_graph()
        mem = get_memory_engine()
        store = get_vector_store()

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                vector_count = 0
            else:
                vector_count = loop.run_until_complete(store.count("documents"))
        except Exception:
            vector_count = index.get_chunk_count()

        metrics = KnowledgeMetrics(
            indexed_documents=index.get_document_count(),
            indexed_chunks=index.get_chunk_count(),
            total_embeddings=vector_count,
            knowledge_sources=index.to_dict().get("sources", []),
            memory_entries=mem.get_stats().get("total_sessions", 0),
            graph_entities=kg.get_entity_count(),
            graph_relationships=kg.get_relationship_count(),
            search_count=len(self._search_log),
            sources_breakdown=self._get_sources_breakdown(),
            entity_types=kg.get_entity_types(),
            memory_types=mem.get_stats(),
            vector_store_size=vector_count,
        )
        return metrics

    def get_search_analytics(self) -> Dict[str, Any]:
        if not self._search_log:
            return {"total_searches": 0, "avg_results": 0, "top_queries": []}

        queries = [s["query"] for s in self._search_log]
        query_counts: Dict[str, int] = {}
        for q in queries:
            query_counts[q] = query_counts.get(q, 0) + 1

        top_queries = sorted(query_counts.items(), key=lambda x: -x[1])[:10]

        now = datetime.utcnow()
        last_24h = sum(1 for s in self._search_log
                      if datetime.fromisoformat(s["timestamp"]) > now - timedelta(hours=24))

        avg_results = sum(s.get("total", 0) for s in self._search_log) / max(len(self._search_log), 1)

        return {
            "total_searches": len(self._search_log),
            "searches_24h": last_24h,
            "avg_results_per_search": round(avg_results, 1),
            "top_queries": [{"query": q, "count": c} for q, c in top_queries],
            "search_types": self._get_search_type_breakdown(),
        }

    def get_sources_analytics(self) -> Dict[str, Any]:
        connectors = get_all_connectors()
        index = get_index_manager()
        return {
            "total_sources": len(connectors),
            "connected_sources": sum(1 for c in connectors if c.is_connected),
            "sources": [
                {
                    "name": c.name,
                    "type": c.source_type,
                    "connected": c.is_connected,
                    "document_count": sum(
                        1 for d in index.get_all_documents()
                        if d.source_type == c.source_type
                    ),
                }
                for c in connectors
            ],
        }

    def get_memory_analytics(self) -> Dict[str, Any]:
        mem = get_memory_engine()
        stats = mem.get_stats()
        return {
            "memory_type_breakdown": stats,
            "total_entries": sum(stats.values()),
        }

    def log_search(self, query: str, search_type: str, total: int, time_ms: float):
        self._search_log.append({
            "query": query,
            "search_type": search_type,
            "total": total,
            "time_ms": time_ms,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(self._search_log) > self._max_log:
            self._search_log = self._search_log[-self._max_log:]

    def _get_sources_breakdown(self) -> Dict[str, int]:
        index = get_index_manager()
        sources: Dict[str, int] = {}
        for doc in index.get_all_documents():
            st = doc.source_type
            sources[st] = sources.get(st, 0) + 1
        return sources

    def _get_search_type_breakdown(self) -> Dict[str, int]:
        breakdown: Dict[str, int] = {}
        for s in self._search_log:
            st = s.get("search_type", "unknown")
            breakdown[st] = breakdown.get(st, 0) + 1
        return breakdown


_knowledge_analytics: Optional[KnowledgeAnalytics] = None


def get_knowledge_analytics() -> KnowledgeAnalytics:
    global _knowledge_analytics
    if _knowledge_analytics is None:
        _knowledge_analytics = KnowledgeAnalytics()
    return _knowledge_analytics
