"""Reasoning Agent for Phase 3 - Analyze, Compare, Generate Insights."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from knowledge.search_engine import get_search_engine
from knowledge.retriever import get_document_retriever
from rag.engine import get_rag_engine
from knowledge_graph.engine import get_knowledge_graph, EntityType
from memory.engine import get_memory_engine

logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    conclusion: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    reasoning_steps: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ReasoningAgent:
    def __init__(self):
        self.rag = get_rag_engine()
        self.search = get_search_engine()
        self.retriever = get_document_retriever()
        self.graph = get_knowledge_graph()
        self.memory = get_memory_engine()

    async def reason(self, query: str) -> ReasoningResult:
        rag_response = await self.rag.answer(query)

        reasoning_steps = [
            "Parsed the query and identified key concepts",
            f"Searched knowledge base for relevant information",
            f"Retrieved and analyzed {len(rag_response.citations)} relevant sources",
            "Cross-referenced information across sources",
            "Generated answer with citations",
        ]

        evidence = [
            {
                "source": c.document_name,
                "type": c.source_type,
                "relevance": c.score,
                "text": c.text[:200],
            }
            for c in rag_response.citations[:5]
        ]

        suggestions = await self._generate_insights(query)

        return ReasoningResult(
            conclusion=rag_response.answer,
            evidence=evidence,
            confidence=rag_response.confidence,
            reasoning_steps=reasoning_steps,
            suggestions=suggestions,
        )

    async def analyze(self, topic: str) -> ReasoningResult:
        rag_response = await self.rag.answer(f"Provide a detailed analysis of: {topic}")

        graph_entities = self.graph.search_entities(topic)
        graph_context = ""
        if graph_entities:
            related = self.graph.get_connected_entities(graph_entities[0].id, depth=2)
            if related:
                graph_context = f"Related entities: {', '.join(e.name for e in related[:5])}"

        reasoning_steps = [
            f"Analyzing topic: {topic}",
            "Retrieving knowledge base documents",
            "Cross-referencing with knowledge graph",
            "Synthesizing information",
        ]

        if graph_context:
            reasoning_steps.append(f"Found {graph_context}")

        suggestions = [f"Explore relationships of {topic} in knowledge graph"]
        if graph_entities:
            suggestions.append(f"Deep dive into related entities")

        return ReasoningResult(
            conclusion=rag_response.answer,
            evidence=[{"source": c.document_name, "type": c.source_type, "relevance": c.score} for c in rag_response.citations[:5]],
            confidence=rag_response.confidence,
            reasoning_steps=reasoning_steps,
            suggestions=suggestions,
        )

    async def compare(self, items: List[str]) -> ReasoningResult:
        query = f"Compare and contrast: {' vs '.join(items)}"
        rag_response = await self.rag.answer(query)

        return ReasoningResult(
            conclusion=rag_response.answer,
            evidence=[{"source": c.document_name, "type": c.source_type, "relevance": c.score} for c in rag_response.citations[:8]],
            confidence=rag_response.confidence,
            reasoning_steps=[f"Comparing {len(items)} items: {', '.join(items)}", "Retrieving relevant information for each item", "Identifying similarities and differences", "Generating comparative analysis"],
            suggestions=[f"Deep dive into {items[0]}", f"Explore related topics"],
        )

    async def _generate_insights(self, query: str) -> List[str]:
        return [
            "Would you like me to search for more details?",
            "I can also analyze related topics if you're interested.",
            "Let me know if you want me to summarize key findings.",
        ]


_reasoning_agent: Optional[ReasoningAgent] = None


def get_reasoning_agent() -> ReasoningAgent:
    global _reasoning_agent
    if _reasoning_agent is None:
        _reasoning_agent = ReasoningAgent()
    return _reasoning_agent
