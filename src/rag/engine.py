"""RAG Engine with Full Citation Support for Phase 3."""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from knowledge.retriever import get_document_retriever, RetrievedDocument
from knowledge.embedding_engine import get_embedding_engine
from knowledge.search_engine import get_search_engine

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    document_id: str
    document_name: str
    source_type: str
    text: str
    score: float
    page_number: Optional[int] = None
    chunk_index: int = 0
    file_path: str = ""


@dataclass
class RAGResponse:
    answer: str
    citations: List[Citation] = field(default_factory=list)
    query: str = ""
    time_ms: float = 0.0
    model: str = ""
    confidence: float = 0.0


class ContextBuilder:
    def build(self, query: str, documents: List[RetrievedDocument], max_context: int = 4000) -> str:
        context_parts = []
        total_chars = 0

        for i, doc in enumerate(documents):
            text = doc.text[:2000] if doc.text else ""
            source = doc.metadata.get("file_name", doc.metadata.get("source_name", "unknown"))
            header = f"[Source {i+1}: {source} (score: {doc.score:.3f})]"
            entry = f"{header}\n{text}\n"
            if total_chars + len(entry) > max_context:
                remaining = max_context - total_chars
                if remaining > 200:
                    entry = f"{header}\n{text[:remaining]}\n"
                else:
                    break
            context_parts.append(entry)
            total_chars += len(entry)

        return "\n---\n".join(context_parts)

    def build_citations(self, documents: List[RetrievedDocument]) -> List[Citation]:
        citations = []
        for doc in documents:
            meta = doc.metadata
            citations.append(Citation(
                document_id=meta.get("document_id", doc.id),
                document_name=meta.get("file_name", meta.get("source_name", "Unknown")),
                source_type=meta.get("source_type", "unknown"),
                text=doc.text[:500] if doc.text else "",
                score=doc.score,
                page_number=meta.get("page_number"),
                chunk_index=meta.get("chunk_index", 0),
                file_path=meta.get("file_path", ""),
            ))
        return citations


class PromptBuilder:
    def build_qa_prompt(self, query: str, context: str) -> str:
        return f"""You are APA, an AI assistant with knowledge about the user's digital life.
Answer the question based on the provided context. If the context doesn't contain the answer, say so.
Always cite your sources by referencing the [Source N] markers.

Context:
{context}

Question: {query}

Provide a clear, concise answer with references to the sources used."""

    def build_chat_prompt(self, query: str, context: str, conversation_history: str = "") -> str:
        return f"""You are APA, an AI assistant with knowledge about the user's digital life.
Use the context and conversation history to answer naturally.

Conversation History:
{conversation_history}

Context:
{context}

User: {query}

Respond helpfully, citing sources where applicable."""


class Reranker:
    def rerank(self, query: str, documents: List[RetrievedDocument], top_k: int = 5) -> List[RetrievedDocument]:
        query_terms = set(query.lower().split())
        for doc in documents:
            text_lower = doc.text.lower() if doc.text else ""
            term_overlap = sum(1 for t in query_terms if t in text_lower)
            doc.score = doc.score * 0.7 + (term_overlap / max(len(query_terms), 1)) * 0.3

        documents.sort(key=lambda d: -d.score)
        return documents[:top_k]


class ResponseGenerator:
    async def generate(self, prompt: str, max_tokens: int = 500) -> str:
        try:
            from config import Config
            import httpx
            config = Config.get_ollama_config()
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"http://{config.host}:{config.port}/api/generate",
                    json={
                        "model": config.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": max_tokens},
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama generate failed: {e}")

        try:
            from services.qwen_service import get_qwen_service
            service = get_qwen_service()
            if service:
                result = await service.generate(prompt, max_tokens=max_tokens)
                if result:
                    return result
        except Exception as e:
            logger.warning(f"Qwen generate failed: {e}")

        return self._fallback_generate(prompt)

    def _fallback_generate(self, prompt: str) -> str:
        lines = prompt.split("\n")
        question = ""
        for line in lines:
            if line.startswith("Question:") or line.startswith("User:"):
                question = line.split(":", 1)[1].strip()
                break
        if not question:
            question = lines[-1].strip() if lines else ""

        sources = []
        for line in lines:
            if line.startswith("[Source"):
                src_name = line.split(":")[1].split("]")[0].strip() if ":" in line else ""
                if src_name:
                    sources.append(src_name)

        context_parts = []
        in_context = False
        for line in lines:
            if line.startswith("Context:"):
                in_context = True
                continue
            if line.startswith("Question:") or line.startswith("User:"):
                in_context = False
            if in_context and line.strip():
                context_parts.append(line.strip())

        context_summary = context_parts[:3] if context_parts else []

        if sources:
            answer = f"Based on the information I found"
            if len(sources) == 1:
                answer += f" in {sources[0]}"
            elif len(sources) <= 3:
                answer += f" from {', '.join(sources)}"
            if context_summary:
                answer += f", {context_summary[0][:200]}"
            answer += "."
        elif context_summary:
            answer = f"I found relevant information. {context_summary[0][:300]}"
        else:
            answer = "I couldn't find specific information about that in your knowledge base."

        return answer


class RAGEngine:
    def __init__(self):
        self.retriever = get_document_retriever()
        self.context_builder = ContextBuilder()
        self.prompt_builder = PromptBuilder()
        self.reranker = Reranker()
        self.generator = ResponseGenerator()
        self.search_engine = get_search_engine()

    async def answer(self, query: str, top_k: int = 10, max_context: int = 4000) -> RAGResponse:
        start = time.time()

        retrieved = await self.retriever.retrieve(query, top_k=top_k)
        reranked = self.reranker.rerank(query, retrieved, top_k=5)

        context = self.context_builder.build(query, reranked, max_context)
        citations = self.context_builder.build_citations(reranked)

        prompt = self.prompt_builder.build_qa_prompt(query, context)
        answer = await self.generator.generate(prompt)

        time_ms = (time.time() - start) * 1000
        confidence = min(1.0, sum(c.score for c in citations) / max(len(citations), 1)) if citations else 0.0

        return RAGResponse(
            answer=answer,
            citations=citations,
            query=query,
            time_ms=time_ms,
            model="ollama/qwen3",
            confidence=confidence,
        )

    async def chat(self, query: str, conversation_history: str = "", top_k: int = 10) -> RAGResponse:
        start = time.time()

        retrieved = await self.retriever.retrieve(query, top_k=top_k)
        reranked = self.reranker.rerank(query, retrieved, top_k=5)

        context = self.context_builder.build(query, reranked)
        citations = self.context_builder.build_citations(reranked)

        prompt = self.prompt_builder.build_chat_prompt(query, context, conversation_history)
        answer = await self.generator.generate(prompt)

        time_ms = (time.time() - start) * 1000
        confidence = min(1.0, sum(c.score for c in citations) / max(len(citations), 1)) if citations else 0.0

        return RAGResponse(
            answer=answer,
            citations=citations,
            query=query,
            time_ms=time_ms,
            model="ollama/qwen3",
            confidence=confidence,
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
                        "id": d.document.id if d.document else "",
                        "file_name": d.document.file_name if d.document else "",
                        "source_type": d.document.source_type if d.document else "",
                    } if d.document else None,
                }
                for d in retrieved
            ],
            "total": len(retrieved),
        }


_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
