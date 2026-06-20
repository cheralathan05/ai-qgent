"""Phase 3 APIs - Knowledge Intelligence, Search, RAG, Memory, Knowledge Graph."""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Body, Depends, File, UploadFile, Form
from pydantic import BaseModel

from knowledge.source_connectors import (
    SourceDocument, ensure_default_connectors, get_all_connectors,
    LocalFileConnector, register_connector,
)
from knowledge.parsers import get_parser_for_file, get_all_parsers
from knowledge.document_ingestion import get_ingestion_pipeline
from knowledge.search_engine import get_search_engine, SearchResponse, SearchResult
from knowledge.embedding_engine import get_embedding_engine, set_embedding_engine
from knowledge.vector_store import get_vector_store, set_vector_store
from knowledge.indexer import get_index_manager
from knowledge.retriever import get_document_retriever

from rag.engine import get_rag_engine, RAGResponse, Citation
from memory.engine import get_memory_engine, Memory, MemoryType, MemoryQuery
from knowledge_graph.engine import get_knowledge_graph, KnowledgeEntity, EntityType, RelationshipType
from context.engine import get_context_engine
from file_explorer.explorer import get_file_explorer
from analytics.knowledge_analytics import get_knowledge_analytics
from agents.knowledge_agent import get_knowledge_agent
from agents.reasoning_agent import get_reasoning_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/phase3", tags=["Phase 3 - Knowledge Intelligence"])


# ==================== Request/Response Models ====================

class SearchRequest(BaseModel):
    query: str
    search_type: str = "hybrid"
    top_k: int = 20
    filters: Optional[Dict[str, Any]] = None
    collection: str = "documents"


class AskRequest(BaseModel):
    query: str
    top_k: int = 10
    max_context: int = 4000


class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    top_k: int = 10


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 10
    search_type: str = "hybrid"
    filters: Optional[Dict[str, Any]] = None


class IndexRequest(BaseModel):
    source_type: Optional[str] = None
    file_paths: Optional[List[str]] = None


class MemoryQueryRequest(BaseModel):
    query: str
    memory_type: Optional[str] = None
    user_id: str = "default"
    session_id: str = ""
    top_k: int = 10


class StoreMemoryRequest(BaseModel):
    type: str = "knowledge"
    content: str
    metadata: Optional[Dict[str, Any]] = None
    user_id: str = "default"
    session_id: str = ""
    importance: float = 0.5


class GraphEntityRequest(BaseModel):
    name: str
    entity_type: str = "concept"
    properties: Optional[Dict[str, Any]] = None


class GraphRelationshipRequest(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str = "related_to"
    properties: Optional[Dict[str, Any]] = None


class KnowledgeChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class SourceConfigRequest(BaseModel):
    source_type: str
    config: Dict[str, Any]


# ==================== Knowledge APIs ====================

@router.post("/index", summary="Index knowledge sources")
async def index_knowledge(request: Optional[IndexRequest] = None):
    ensure_default_connectors()
    pipeline = get_ingestion_pipeline()

    if request and request.file_paths:
        connector = LocalFileConnector("manual")
        documents = []
        for fp in request.file_paths:
            if os.path.exists(fp):
                fname = os.path.basename(fp)
                with open(fp, 'rb') as f:
                    content = f.read()
                documents.append(SourceDocument(
                    id=fp, source_type="manual", source_name="manual",
                    file_path=fp, file_name=fname,
                    file_size=os.path.getsize(fp),
                    mime_type="application/octet-stream",
                    content=content.decode('utf-8', errors='replace'),
                ))
        result = await pipeline.ingest_documents(documents)
    else:
        result = await pipeline.run_full_ingestion()

    return {
        "status": "completed" if result.indexed_documents > 0 else "no_documents",
        "indexed_documents": result.indexed_documents,
        "total_documents": result.total_documents,
        "total_chunks": result.total_chunks,
        "sources": result.sources,
        "errors": result.errors,
        "time_ms": result.time_ms,
    }


@router.post("/reindex", summary="Reindex all knowledge sources")
async def reindex_knowledge():
    idx = get_index_manager()
    idx.clear()
    return await index_knowledge()


@router.post("/search", summary="Search knowledge base")
async def search_knowledge(request: SearchRequest):
    engine = get_search_engine()
    start = time.time()
    response = await engine.search(
        query=request.query,
        search_type=request.search_type,
        top_k=request.top_k,
        filters=request.filters,
        collection=request.collection,
    )
    elapsed = (time.time() - start) * 1000

    analytics = get_knowledge_analytics()
    analytics.log_search(request.query, request.search_type, response.total, elapsed)
    get_context_engine().add_search(request.query)

    return {
        "query": request.query,
        "search_type": request.search_type,
        "total": response.total,
        "time_ms": elapsed,
        "results": [
            {
                "id": r.id,
                "text": r.text[:500],
                "score": r.score,
                "file_name": r.file_name,
                "file_path": r.file_path,
                "source_type": r.source_type,
                "source_name": r.source_name,
                "chunk_index": r.chunk_index,
                "page_number": r.page_number,
                "metadata": r.metadata,
            }
            for r in response.results
        ],
    }


@router.post("/semantic-search", summary="Semantic search")
async def semantic_search(query: str = Body(..., embed=True), top_k: int = 20):
    engine = get_search_engine()
    response = await engine.semantic_search(query, top_k=top_k)
    return {
        "query": query,
        "total": response.total,
        "results": [{"id": r.id, "text": r.text[:500], "score": r.score, "file_name": r.file_name} for r in response.results],
    }


@router.post("/hybrid-search", summary="Hybrid search")
async def hybrid_search(query: str = Body(..., embed=True), top_k: int = 20, filters: Optional[Dict] = None):
    engine = get_search_engine()
    response = await engine.hybrid_search(query, top_k=top_k, filters=filters)
    return {
        "query": query,
        "total": response.total,
        "results": [{"id": r.id, "text": r.text[:500], "score": r.score, "file_name": r.file_name, "file_path": r.file_path} for r in response.results],
    }


@router.get("/documents", summary="List all indexed documents")
async def list_documents(limit: int = 50, offset: int = 0, source: Optional[str] = None):
    index = get_index_manager()
    docs = index.get_all_documents()

    if source:
        docs = [d for d in docs if d.source_type == source]

    docs = docs[offset:offset + limit]
    return {
        "total": index.get_document_count(),
        "limit": limit,
        "offset": offset,
        "documents": [
            {
                "id": d.id,
                "file_name": d.file_name,
                "file_path": d.file_path,
                "source_type": d.source_type,
                "source_name": d.source_name,
                "mime_type": d.mime_type,
                "file_size": d.file_size,
                "chunk_count": d.chunk_count,
                "created_at": d.created_at,
                "modified_at": d.modified_at,
            }
            for d in docs
        ],
    }


@router.get("/document/{doc_id}", summary="Get document details")
async def get_document(doc_id: str):
    index = get_index_manager()
    doc = index.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = [c for c in index.get_all_chunks() if c.metadata.get("document_id") == doc_id]
    return {
        "id": doc.id,
        "file_name": doc.file_name,
        "file_path": doc.file_path,
        "source_type": doc.source_type,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "chunk_count": len(chunks),
        "metadata": doc.metadata,
        "chunks": [
            {"id": c.id, "text": c.text[:500], "chunk_index": c.chunk_index, "metadata": c.metadata}
            for c in chunks[:20]
        ],
    }


@router.get("/sources", summary="List knowledge sources")
async def list_knowledge_sources():
    ensure_default_connectors()
    connectors = get_all_connectors()
    return {
        "sources": [
            {
                "name": c.name,
                "type": c.source_type,
                "connected": c.is_connected,
            }
            for c in connectors
        ],
        "total": len(connectors),
    }


@router.post("/ask", summary="Ask a question with RAG")
async def ask_question(request: AskRequest):
    agent = get_knowledge_agent()
    response = await agent.answer(request.query)
    return {
        "answer": response.answer,
        "sources": response.sources,
        "confidence": response.confidence,
        "suggestions": response.suggestions,
        "type": response.type,
    }


@router.post("/chat", summary="Chat with knowledge base")
async def knowledge_chat(request: ChatRequest):
    agent = get_knowledge_agent()
    response = await agent.chat(request.query, conversation_id=request.conversation_id or "")
    return {
        "answer": response.answer,
        "sources": response.sources,
        "confidence": response.confidence,
        "conversation_id": request.conversation_id or "default",
    }


@router.post("/retrieve", summary="Retrieve documents")
async def retrieve_documents(request: RetrieveRequest):
    retriever = get_document_retriever()
    results = await retriever.retrieve(
        query=request.query,
        top_k=request.top_k,
        search_type=request.search_type,
        filters=request.filters,
    )
    return {
        "query": request.query,
        "total": len(results),
        "results": [
            {
                "id": r.id,
                "text": r.text[:500],
                "score": r.score,
                "metadata": r.metadata,
                "document": {
                    "file_name": r.document.file_name if r.document else "",
                    "source_type": r.document.source_type if r.document else "",
                    "file_path": r.document.file_path if r.document else "",
                } if r.document else {},
            }
            for r in results
        ],
    }


@router.post("/rag", summary="Full RAG pipeline")
async def rag_pipeline(query: str = Body(..., embed=True), top_k: int = 10):
    rag = get_rag_engine()
    response = await rag.answer(query, top_k=top_k)
    return {
        "answer": response.answer,
        "citations": [
            {
                "document": c.document_name,
                "source_type": c.source_type,
                "score": c.score,
                "text_preview": c.text[:300],
                "page_number": c.page_number,
            }
            for c in response.citations
        ],
        "confidence": response.confidence,
        "time_ms": response.time_ms,
    }


# ==================== Memory APIs ====================

@router.get("/memory/current", summary="Get current session memory")
async def get_current_memory(session_id: str = "default"):
    mem = get_memory_engine()
    context = mem.get_current_session_context(session_id)
    conversation = mem.get_conversation(session_id, limit=20)
    return {
        "session": context,
        "recent_messages": [
            {
                "role": m.metadata.get("role", "unknown"),
                "content": m.content[:200],
                "timestamp": m.timestamp.isoformat(),
            }
            for m in conversation[-10:]
        ],
    }


@router.get("/memory/history", summary="Get memory history")
async def get_memory_history(user_id: str = "default", limit: int = 50, memory_type: Optional[str] = None):
    mem = get_memory_engine()
    memories = mem.query(MemoryQuery(
        query="", user_id=user_id,
        memory_type=MemoryType(memory_type) if memory_type else None,
        top_k=limit,
    ))
    return {
        "total": len(memories),
        "memories": [
            {
                "id": m.id,
                "type": m.type.value,
                "content": m.content[:300],
                "importance": m.importance,
                "timestamp": m.timestamp.isoformat(),
                "metadata": m.metadata,
            }
            for m in memories
        ],
    }


@router.post("/memory/store", summary="Store a memory")
async def store_memory(request: StoreMemoryRequest):
    mem = get_memory_engine()
    memory = Memory(
        id=f"mem_{datetime.utcnow().timestamp()}",
        type=MemoryType(request.type),
        content=request.content,
        metadata=request.metadata or {},
        user_id=request.user_id,
        session_id=request.session_id,
        importance=request.importance,
    )
    mem.store(memory)
    return {"status": "stored", "id": memory.id}


@router.delete("/memory/clear", summary="Clear memory")
async def clear_memory(user_id: str = ""):
    mem = get_memory_engine()
    mem.clear_all(user_id)
    return {"status": "cleared", "user_id": user_id}


# ==================== Knowledge Graph APIs ====================

@router.get("/graph/entities", summary="List all graph entities")
async def list_graph_entities():
    kg = get_knowledge_graph()
    entities = kg.get_all_entities()
    return {
        "total": len(entities),
        "entities": [
            {
                "id": e.id,
                "name": e.name,
                "type": e.type.value,
                "properties": e.properties,
                "created_at": e.created_at.isoformat(),
            }
            for e in entities
        ],
    }


@router.get("/graph/entity/{entity_id}", summary="Get entity details with relationships")
async def get_graph_entity(entity_id: str):
    kg = get_knowledge_graph()
    entity = kg.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    relationships = kg.get_relationships(entity_id)
    connected = kg.get_connected_entities(entity_id, depth=1)

    return {
        "entity": {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type.value,
            "properties": entity.properties,
        },
        "relationships": [
            {
                "id": r.id,
                "type": r.type.value,
                "source_id": r.source_id,
                "target_id": r.target_id,
                "properties": r.properties,
            }
            for r in relationships
        ],
        "connected_entities": [
            {"id": e.id, "name": e.name, "type": e.type.value}
            for e in connected
        ],
    }


@router.get("/graph/relationships", summary="List all relationships")
async def list_graph_relationships():
    kg = get_knowledge_graph()
    rels = kg.get_all_relationships()
    return {
        "total": len(rels),
        "relationships": [
            {
                "id": r.id,
                "source_id": r.source_id,
                "target_id": r.target_id,
                "type": r.type.value,
                "properties": r.properties,
            }
            for r in rels
        ],
    }


@router.post("/graph/entity", summary="Create entity in knowledge graph")
async def create_graph_entity(request: GraphEntityRequest):
    kg = get_knowledge_graph()
    entity = kg.create_entity(
        name=request.name,
        entity_type=EntityType(request.entity_type),
        properties=request.properties,
    )
    return {
        "status": "created",
        "entity": {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type.value,
            "properties": entity.properties,
        },
    }


@router.post("/graph/relationship", summary="Create relationship in knowledge graph")
async def create_graph_relationship(request: GraphRelationshipRequest):
    kg = get_knowledge_graph()
    rel = kg.create_relationship(
        source_id=request.source_id,
        target_id=request.target_id,
        rel_type=RelationshipType(request.relationship_type),
        properties=request.properties,
    )
    return {
        "status": "created",
        "relationship": {
            "id": rel.id,
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "type": rel.type.value,
        },
    }


# ==================== File Explorer APIs ====================

@router.get("/files", summary="Browse files")
async def browse_files(path: str = ""):
    explorer = get_file_explorer()
    files = await explorer.browse(path)
    return {
        "path": path or os.path.expanduser("~"),
        "total": len(files),
        "files": [
            {
                "id": f.id,
                "name": f.name,
                "path": f.path,
                "size": f.size,
                "mime_type": f.mime_type,
                "extension": f.extension,
                "is_directory": f.is_directory,
                "is_favorite": f.is_favorite,
                "modified_at": f.modified_at,
            }
            for f in files
        ],
    }


@router.get("/files/recent", summary="Get recent files")
async def recent_files(limit: int = 20):
    explorer = get_file_explorer()
    files = await explorer.get_recent(limit)
    return {"total": len(files), "files": [{"id": f.id, "name": f.name, "path": f.path, "size": f.size} for f in files]}


@router.get("/files/favorites", summary="Get favorite files")
async def favorite_files():
    explorer = get_file_explorer()
    files = await explorer.get_favorites()
    return {"total": len(files), "files": [{"id": f.id, "name": f.name, "path": f.path} for f in files]}


@router.get("/files/search", summary="Search files")
async def search_files(query: str = Query(..., min_length=1), path: str = ""):
    explorer = get_file_explorer()
    files = await explorer.search_files(query, path)
    return {"query": query, "total": len(files), "files": [{"id": f.id, "name": f.name, "path": f.path, "size": f.size} for f in files]}


@router.get("/files/{file_id}", summary="Get file info")
async def get_file_info(file_id: str):
    explorer = get_file_explorer()
    info = await explorer.get_file_info(file_id)
    if not info:
        raise HTTPException(status_code=404, detail="File not found")
    return {"id": info.id, "name": info.name, "path": info.path, "size": info.size, "mime_type": info.mime_type, "extension": info.extension, "is_directory": info.is_directory, "is_favorite": info.is_favorite, "modified_at": info.modified_at}


# ==================== Analytics APIs ====================

@router.get("/analytics/knowledge", summary="Knowledge metrics")
async def knowledge_analytics():
    analytics = get_knowledge_analytics()
    return analytics.get_knowledge_metrics()


@router.get("/analytics/search", summary="Search analytics")
async def search_analytics():
    analytics = get_knowledge_analytics()
    return analytics.get_search_analytics()


@router.get("/analytics/memory", summary="Memory analytics")
async def memory_analytics():
    analytics = get_knowledge_analytics()
    return analytics.get_memory_analytics()


@router.get("/analytics/sources", summary="Sources analytics")
async def sources_analytics():
    analytics = get_knowledge_analytics()
    return analytics.get_sources_analytics()


# ==================== Knowledge Chat API ====================

@router.post("/knowledge-chat", summary="Chat with knowledge agent")
async def knowledge_chat_endpoint(request: KnowledgeChatRequest):
    agent = get_knowledge_agent()
    response = await agent.chat(request.message, conversation_id=request.conversation_id or "")

    get_context_engine().update(
        current_conversation_id=request.conversation_id or "default",
        last_command=request.message,
        last_intent="knowledge_chat",
    )

    return {
        "answer": response.answer,
        "sources": response.sources,
        "confidence": response.confidence,
        "conversation_id": request.conversation_id or "default",
        "suggestions": response.suggestions,
    }


# ==================== Agent APIs ====================

@router.get("/agents", summary="List all agents")
async def list_agents():
    return {
        "agents": [
            {"id": "knowledge_agent", "name": "Knowledge Agent", "type": "knowledge", "status": "active"},
            {"id": "reasoning_agent", "name": "Reasoning Agent", "type": "reasoning", "status": "active"},
            {"id": "intent_agent", "name": "Intent Agent", "type": "intent", "status": "active"},
            {"id": "planner_agent", "name": "Planner Agent", "type": "planner", "status": "active"},
            {"id": "memory_agent", "name": "Memory Agent", "type": "memory", "status": "active"},
        ],
        "total": 5,
    }


@router.get("/agents/{agent_id}", summary="Get agent details")
async def get_agent(agent_id: str):
    if agent_id == "knowledge_agent":
        agent = get_knowledge_agent()
        return {"id": agent_id, "name": "Knowledge Agent", "type": "knowledge", "status": "active", "details": agent.get_status()}
    elif agent_id == "reasoning_agent":
        return {"id": agent_id, "name": "Reasoning Agent", "type": "reasoning", "status": "active"}
    raise HTTPException(status_code=404, detail="Agent not found")


@router.get("/agents/{agent_id}/health", summary="Agent health check")
async def agent_health(agent_id: str):
    if agent_id in ("knowledge_agent", "reasoning_agent"):
        return {"agent_id": agent_id, "status": "healthy", "uptime": "active"}
    raise HTTPException(status_code=404, detail="Agent not found")


@router.get("/agents/{agent_id}/metrics", summary="Agent metrics")
async def agent_metrics(agent_id: str):
    return {"agent_id": agent_id, "calls": 0, "avg_latency_ms": 0, "success_rate": 1.0, "error_count": 0}


@router.post("/agents/{agent_id}/pause", summary="Pause agent")
async def pause_agent(agent_id: str):
    return {"agent_id": agent_id, "status": "paused"}


@router.post("/agents/{agent_id}/resume", summary="Resume agent")
async def resume_agent(agent_id: str):
    return {"agent_id": agent_id, "status": "active"}


# ==================== Conversation APIs ====================

@router.get("/conversations", summary="List conversations")
async def list_conversations(user_id: str = "default"):
    mem = get_memory_engine()
    stats = mem.get_stats()
    return {"total": stats.get("conversations", 0), "conversations": []}


@router.get("/conversations/{conversation_id}", summary="Get conversation")
async def get_conversation(conversation_id: str, limit: int = 50):
    mem = get_memory_engine()
    convs = mem.get_conversation(conversation_id, limit=limit)
    return {
        "conversation_id": conversation_id,
        "total": len(convs),
        "messages": [
            {
                "role": m.metadata.get("role", "unknown"),
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "metadata": m.metadata,
            }
            for m in convs
        ],
    }


@router.post("/conversations/{conversation_id}/clear", summary="Clear conversation")
async def clear_conversation(conversation_id: str):
    mem = get_memory_engine()
    mem.clear_session(conversation_id)
    return {"status": "cleared", "conversation_id": conversation_id}


# ==================== File Upload API ====================

@router.post("/upload", summary="Upload and index a file")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    fname = file.filename or "unknown"
    fpath = os.path.join(os.path.dirname(__file__), "..", "data", "uploads", fname)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(fpath, 'wb') as f:
        f.write(content)

    doc = SourceDocument(
        id=fpath, source_type="upload", source_name="upload",
        file_path=fpath, file_name=fname,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        content=content.decode('utf-8', errors='replace'),
    )

    pipeline = get_ingestion_pipeline()
    result = await pipeline.ingest_documents([doc])

    return {
        "status": "indexed" if result.indexed_documents > 0 else "failed",
        "file_name": fname,
        "file_path": fpath,
        "chunks_created": result.total_chunks,
    }


# ==================== Phase 3 Knowledge Chat Integration ====================

@router.post("/knowledge-command", summary="Process knowledge command with Phase 1/2 integration")
async def knowledge_command(command: str = Body(..., embed=True)):
    agent = get_knowledge_agent()

    is_file_query = any(word in command.lower() for word in ["find", "where", "locate", "search", "open", "show"])
    is_question = any(word in command.lower() for word in ["what", "how", "why", "when", "who", "which", "tell", "summarize", "compare"])

    if is_file_query and ("file" in command.lower() or "note" in command.lower() or "document" in command.lower() or "pdf" in command.lower()):
        response = await agent.find_file(command)
    elif is_question:
        response = await agent.answer(command)
    else:
        response = await agent.search(command)

    return {
        "answer": response.answer,
        "sources": response.sources,
        "confidence": response.confidence,
        "type": response.type,
        "suggestions": response.suggestions,
        "actions": response.actions,
    }


# ==================== Context API ====================

@router.get("/context/current", summary="Get current context")
async def get_current_context():
    ctx = get_context_engine()
    return ctx.get_context_summary()


# ==================== Source Configuration API ====================

@router.post("/sources/configure", summary="Configure a knowledge source")
async def configure_source(request: SourceConfigRequest):
    if request.source_type == "local":
        paths = request.config.get("paths", [])
        connector = LocalFileConnector("configured", base_paths=paths)
        await connector.connect()
        register_connector(connector)
        return {"status": "configured", "source_type": "local", "paths": paths}
    elif request.source_type == "github":
        from knowledge.source_connectors import GitHubConnector
        connector = GitHubConnector(
            name="github_configured",
            token=request.config.get("token", ""),
            repos=request.config.get("repos", []),
        )
        connected = await connector.connect()
        if connected:
            register_connector(connector)
        return {"status": "configured" if connected else "failed", "source_type": "github"}
    elif request.source_type == "notion":
        from knowledge.source_connectors import NotionConnector
        connector = NotionConnector(
            name="notion_configured",
            api_key=request.config.get("api_key", ""),
            database_ids=request.config.get("database_ids", []),
        )
        connected = await connector.connect()
        if connected:
            register_connector(connector)
        return {"status": "configured" if connected else "failed", "source_type": "notion"}

    raise HTTPException(status_code=400, detail=f"Unknown source type: {request.source_type}")
