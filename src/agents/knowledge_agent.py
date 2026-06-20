"""Knowledge Agent for Phase 3 - Search, Retrieve, Summarize, Answer, Recommend."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from knowledge.search_engine import get_search_engine, SearchResponse, SearchResult
from knowledge.retriever import get_document_retriever, RetrievedDocument
from knowledge.vector_store import get_vector_store
from knowledge.source_connectors import get_all_connectors
from rag.engine import get_rag_engine, RAGResponse
from memory.engine import get_memory_engine, Memory, MemoryType
from knowledge_graph.engine import get_knowledge_graph, KnowledgeEntity, EntityType, RelationshipType

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeAgentResponse:
    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    type: str = "answer"
    suggestions: List[str] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)


class KnowledgeAgent:
    def __init__(self):
        self.search_engine = get_search_engine()
        self.rag = get_rag_engine()
        self.retriever = get_document_retriever()
        self.memory = get_memory_engine()
        self.graph = get_knowledge_graph()

    async def search(self, query: str, search_type: str = "hybrid", top_k: int = 20) -> SearchResponse:
        self.memory.store(Memory(
            id=f"search_{query}_{hash(query)}",
            type=MemoryType.KNOWLEDGE,
            content=f"Searched for: {query}",
            metadata={"search_type": search_type, "query": query},
            importance=0.6,
        ))
        return await self.search_engine.search(query, search_type=search_type, top_k=top_k)

    async def answer(self, query: str) -> KnowledgeAgentResponse:
        rag_response = await self.rag.answer(query)

        sources = [
            {
                "document": c.document_name,
                "source_type": c.source_type,
                "score": c.score,
                "text_preview": c.text[:300],
                "page": c.page_number,
                "chunk": c.chunk_index,
                "file_path": c.file_path,
            }
            for c in rag_response.citations
        ]

        self.memory.store(Memory(
            id=f"qa_{query}_{hash(query)}",
            type=MemoryType.KNOWLEDGE,
            content=f"Q: {query}\nA: {rag_response.answer[:200]}",
            metadata={"sources": len(sources), "confidence": rag_response.confidence},
            importance=0.8,
        ))

        suggestions = await self._generate_suggestions(query)

        return KnowledgeAgentResponse(
            answer=rag_response.answer,
            sources=sources,
            confidence=rag_response.confidence,
            type="answer",
            suggestions=suggestions,
        )

    async def chat(self, query: str, conversation_id: str = "") -> KnowledgeAgentResponse:
        history = ""
        if conversation_id:
            convs = self.memory.get_conversation(conversation_id, limit=10)
            history = "\n".join(
                f"{'User' if m.metadata.get('role') == 'user' else 'Assistant'}: {m.content}"
                for m in convs[-6:]
            )

        rag_response = await self.rag.chat(query, conversation_history=history)

        sources = [
            {
                "document": c.document_name,
                "source_type": c.source_type,
                "score": c.score,
                "text_preview": c.text[:300],
            }
            for c in rag_response.citations
        ]

        self.memory.store_conversation(
            user_id="default",
            session_id=conversation_id or "default",
            user_message=query,
            assistant_message=rag_response.answer,
            metadata={"sources": len(sources)},
        )

        return KnowledgeAgentResponse(
            answer=rag_response.answer,
            sources=sources,
            confidence=rag_response.confidence,
            type="chat",
        )

    async def retrieve(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        retrieved = await self.retriever.retrieve(query, top_k=top_k)
        return {
            "query": query,
            "results": [
                {
                    "id": d.id,
                    "text": d.text[:500],
                    "score": d.score,
                    "metadata": d.metadata,
                    "document": {
                        "file_name": d.document.file_name if d.document else "",
                        "source_type": d.document.source_type if d.document else "",
                        "file_path": d.document.file_path if d.document else "",
                    } if d.document else {},
                }
                for d in retrieved
            ],
            "total": len(retrieved),
        }

    async def summarize(self, query: str) -> KnowledgeAgentResponse:
        rag_response = await self.rag.answer(f"Summarize information about: {query}")
        return KnowledgeAgentResponse(
            answer=rag_response.answer,
            sources=[{"document": c.document_name, "score": c.score} for c in rag_response.citations],
            confidence=rag_response.confidence,
            type="summary",
        )

    async def recommend(self, query: str) -> KnowledgeAgentResponse:
        rag_response = await self.rag.answer(f"Based on my knowledge, what do you recommend regarding: {query}")
        return KnowledgeAgentResponse(
            answer=rag_response.answer,
            sources=[{"document": c.document_name, "score": c.score} for c in rag_response.citations],
            confidence=rag_response.confidence,
            type="recommendation",
        )

    async def compare(self, item_a: str, item_b: str) -> KnowledgeAgentResponse:
        rag_response = await self.rag.answer(f"Compare and contrast {item_a} vs {item_b}")
        return KnowledgeAgentResponse(
            answer=rag_response.answer,
            sources=[{"document": c.document_name, "score": c.score} for c in rag_response.citations],
            confidence=rag_response.confidence,
            type="comparison",
        )

    async def find_file(self, query: str) -> KnowledgeAgentResponse:
        search = await self.search_engine.search(query, search_type="hybrid")
        results = search.results

        if not results:
            return KnowledgeAgentResponse(
                answer=f"I couldn't find any files matching '{query}'.",
                type="file_search",
            )

        file_list = "\n".join(
            f"{i+1}. {r.file_name or 'Unknown'} (in {r.source_name or 'local files'})"
            for i, r in enumerate(results[:10])
        )

        answer = f"I found {len(results[:10])} files matching '{query}':\n\n{file_list}\n\nWould you like me to open one?"
        actions = [
            {"type": "open_file", "file_path": r.file_path, "file_name": r.file_name}
            for r in results[:5] if r.file_path
        ]

        return KnowledgeAgentResponse(
            answer=answer,
            sources=[{"document": r.file_name, "score": r.score, "file_path": r.file_path} for r in results[:10]],
            type="file_search",
            actions=actions,
        )

    async def _generate_suggestions(self, query: str) -> List[str]:
        suggestions = [
            f"Find more about this topic",
            f"Search related documents",
            f"Summarize the key points",
        ]
        try:
            graph_results = self.graph.search_entities(query)
            if graph_results:
                suggestions.append(f"Explore related: {graph_results[0].name}")
        except Exception:
            pass
        return suggestions

    def get_status(self) -> Dict[str, Any]:
        return {
            "type": "knowledge_agent",
            "search_engine": True,
            "rag_engine": True,
            "memory": True,
            "knowledge_graph": True,
            "indexed_documents": len(self.retriever.index_manager.get_all_documents()),
            "graph_entities": self.graph.get_entity_count(),
        }


_knowledge_agent: Optional[KnowledgeAgent] = None


def get_knowledge_agent() -> KnowledgeAgent:
    global _knowledge_agent
    if _knowledge_agent is None:
        _knowledge_agent = KnowledgeAgent()
    return _knowledge_agent
