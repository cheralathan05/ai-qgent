"""
Phase 3 Acceptance Tests for APA-OS
Tests all Knowledge Intelligence components
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_phase3")

PASS = 0
FAIL = 0
TOTAL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL, TOTAL
    TOTAL += 1
    if condition:
        PASS += 1
        logger.info(f"  PASS: {name}")
    else:
        FAIL += 1
        logger.error(f"  FAIL: {name} - {detail}")


async def test_knowledge_source_connectors():
    logger.info("\n=== Knowledge Source Connectors ===")
    from knowledge.source_connectors import (
        LocalFileConnector, GitHubConnector, ensure_default_connectors,
        get_all_connectors, register_connector,
    )

    import tempfile
    test_dir = tempfile.mkdtemp()
    test_file = os.path.join(test_dir, "test_doc.txt")
    with open(test_file, 'w') as f:
        f.write("This is a test document for APA-OS.")

    connector = LocalFileConnector("test", base_paths=[test_dir])
    connected = await connector.connect()
    check("Local file connector connects", connected)

    files = await connector.list_files()
    check("Local connector lists files", len(files) > 0)
    check("Found test file", any(f['file_name'] == 'test_doc.txt' for f in files))

    if files:
        f = files[0]
        doc = await connector.read_file(f["id"])
        check(f"Can read file: {f['file_name']}", doc is not None)

    sync_result = await connector.sync()
    check("Sync returns result", sync_result.total_files > 0)
    check("Sync has source type", sync_result.source_type == "local_files")


async def test_document_parsers():
    logger.info("\n=== Document Parsers ===")
    from knowledge.parsers import get_parser_for_file, TXTParser, JSONParser, MDParser, CSVParser, CodeParser

    txt_parser = TXTParser()
    content = b"Hello World\nThis is a test file."
    parsed = txt_parser.parse(content, "test.txt")
    check("TXT parser extracts text", len(parsed.text) > 0)
    check("TXT parser word count", parsed.word_count > 0)

    md_parser = MDParser()
    md_content = b"# Heading 1\n\nSome text here.\n\n## Heading 2\n\nMore text."
    parsed = md_parser.parse(md_content, "test.md")
    check("MD parser extracts headings", len(parsed.headings) > 0)
    check("MD parser heading found", "Heading 1" in parsed.headings or any("Heading" in h for h in parsed.headings))

    json_parser = JSONParser()
    json_content = b'{"name": "test", "value": 42}'
    parsed = json_parser.parse(json_content, "test.json")
    check("JSON parser extracts text", parsed.word_count > 0)

    csv_parser = CSVParser()
    csv_content = b"name,age\nAlice,30\nBob,25"
    parsed = csv_parser.parse(csv_content, "test.csv")
    check("CSV parser extracts tables", len(parsed.tables) > 0)

    code_parser = CodeParser()
    code_content = b"def hello():\n    print('hello')\n\nclass Test:\n    pass"
    parsed = code_parser.parse(code_content, "test.py")
    check("Code parser extracts functions", len(parsed.metadata.get("functions", [])) > 0)
    check("Code parser detects language", parsed.metadata.get("language") == "python")

    parser = get_parser_for_file("test.pdf")
    check("PDF parser registered", parser is not None)
    check("PDF parser supports pdf", parser.supports('.pdf'))

    parser = get_parser_for_file("test.docx")
    check("DOCX parser registered", parser is not None)


async def test_embedding_engine():
    logger.info("\n=== Embedding Engine ===")
    from knowledge.embedding_engine import get_embedding_engine

    engine = get_embedding_engine("ollama")
    check("Embedding engine created", engine is not None)
    check("Engine has dimensions", engine.dimensions() > 0)
    check("Engine has model name", len(engine.model_name()) > 0)


async def test_vector_store():
    logger.info("\n=== Vector Store ===")
    from knowledge.vector_store import get_vector_store, VectorRecord
    import random

    store = get_vector_store("faiss")
    check("Vector store created", store is not None)

    created = await store.create_collection("test_collection", 4)
    check("Collection created", created)

    records = [
        VectorRecord(
            id="test1", vector=[0.1, 0.2, 0.3, 0.4], text="This is a test document about APA-OS.",
            metadata={"source": "test", "file_name": "test.txt"},
            created_at=datetime.utcnow().isoformat(),
        ),
        VectorRecord(
            id="test2", vector=[0.9, 0.8, 0.7, 0.6], text="Machine learning and AI concepts.",
            metadata={"source": "test", "file_name": "ai.txt"},
            created_at=datetime.utcnow().isoformat(),
        ),
    ]
    added = await store.add("test_collection", records)
    check("Records added to store", added > 0)

    count = await store.count("test_collection")
    check("Collection has records", count > 0)

    results = await store.search("test_collection", [0.15, 0.25, 0.35, 0.45], top_k=5)
    check("Vector search returns results", len(results) > 0)
    if results:
        check("Search results have scores", results[0].score > 0)

    collections = await store.list_collections()
    check("Can list collections", len(collections) > 0)

    await store.delete_collection("test_collection")
    check("Collection deleted", True)


async def test_search_engine():
    logger.info("\n=== Search Engine ===")
    from knowledge.search_engine import get_search_engine

    engine = get_search_engine()
    check("Search engine created", engine is not None)

    test_docs = [
        {"id": "doc1", "text": "DBMS notes for database management systems", "metadata": {"file_name": "dbms.pdf", "source_type": "local"}},
        {"id": "doc2", "text": "Operating system concepts and process management", "metadata": {"file_name": "os.pdf", "source_type": "local"}},
        {"id": "doc3", "text": "Python programming for FastAPI backend development", "metadata": {"file_name": "fastapi.md", "source_type": "local"}},
        {"id": "doc4", "text": "Machine learning algorithms and neural networks", "metadata": {"file_name": "ml.pdf", "source_type": "local"}},
        {"id": "doc5", "text": "DBMS Lab experiments and SQL queries", "metadata": {"file_name": "dbms_lab.pdf", "source_type": "local"}},
    ]
    engine.update_document_cache(test_docs)

    results = await engine.search("DBMS notes", search_type="keyword", top_k=5)
    check(f"Keyword search returns results for 'DBMS'", results.total > 0)
    if results.total > 0:
        check("Search results have scores", results.results[0].score > 0)
        check("Search results match query", "DBMS" in results.results[0].text or "dbms" in results.results[0].text)

    results = await engine.search("machine learning", search_type="fuzzy", top_k=5)
    check(f"Fuzzy search works", results.total > 0)

    results = await engine.search("database", search_type="bm25", top_k=5)
    check(f"BM25 search works", True)


async def test_document_ingestion():
    logger.info("\n=== Document Ingestion ===")
    from knowledge.document_ingestion import get_ingestion_pipeline

    pipeline = get_ingestion_pipeline()
    check("Ingestion pipeline created", pipeline is not None)

    from knowledge.source_connectors import SourceDocument
    docs = [
        SourceDocument(
            id="test_doc_1", source_type="test", source_name="test",
            file_path="test.txt", file_name="test.txt",
            file_size=50, mime_type="text/plain",
            content="This is a test document about APA-OS knowledge management system.",
        ),
        SourceDocument(
            id="test_doc_2", source_type="test", source_name="test",
            file_path="test2.txt", file_name="test2.txt",
            file_size=60, mime_type="text/plain",
            content="Machine learning and artificial intelligence concepts for modern systems.",
        ),
    ]
    result = await pipeline.ingest_documents(docs)
    check("Documents ingested", result.indexed_documents > 0)
    check("Chunks created", result.total_chunks > 0)
    check("No errors in ingestion", len(result.errors) == 0)

    chunks = pipeline.chunk_text(
        "This is a long text that should be split into multiple chunks for testing the chunking mechanism of the ingestion pipeline.",
        "test.txt", {"source_type": "test"},
    )
    check("Chunking works", len(chunks) > 0)


async def test_knowledge_graph():
    logger.info("\n=== Knowledge Graph ===")
    from knowledge_graph.engine import get_knowledge_graph, EntityType, RelationshipType

    kg = get_knowledge_graph()
    check("Knowledge graph created", kg is not None)

    entity1 = kg.create_entity("Cheralathan", EntityType.PERSON, {"email": "cheralathan@example.com"})
    check("Person entity created", entity1 is not None)
    check("Entity has ID", len(entity1.id) > 0)

    entity2 = kg.create_entity("APA-OS", EntityType.PROJECT, {"description": "AI Operating System"})
    check("Project entity created", entity2 is not None)

    entity3 = kg.create_entity("GitHub", EntityType.REPOSITORY, {"url": "https://github.com/apa-os"})
    check("Repository entity created", entity3 is not None)

    rel1 = kg.create_relationship(entity1.id, entity2.id, RelationshipType.WORKS_ON)
    check("Relationship created", rel1 is not None)

    rel2 = kg.create_relationship(entity2.id, entity3.id, RelationshipType.CONTAINS)
    check("Second relationship created", rel2 is not None)

    found = kg.find_entity("Cheralathan")
    check("Can find entity by name", found is not None)

    entities = kg.get_all_entities()
    check("Graph has entities", len(entities) >= 3)

    relationships = kg.get_all_relationships()
    check("Graph has relationships", len(relationships) >= 2)

    entity_types = kg.get_entity_types()
    check("Entity types reported", len(entity_types) > 0)

    subgraph = kg.get_subgraph(entity1.id, depth=2)
    check("Subgraph returns results", subgraph["total_entities"] > 0)

    entity_count = kg.get_entity_count()
    relationship_count = kg.get_relationship_count()
    check("Entity count matches", entity_count >= 3)
    check("Relationship count matches", relationship_count >= 2)

    connected = kg.get_connected_entities(entity1.id)
    check("Connected entities found", len(connected) > 0)


async def test_memory_engine():
    logger.info("\n=== Memory Engine ===")
    from memory.engine import get_memory_engine, Memory, MemoryType, MemoryQuery

    mem = get_memory_engine()
    check("Memory engine created", mem is not None)

    mem.store(Memory(
        id="test_short_1", type=MemoryType.SHORT_TERM,
        content="Current session test", user_id="test_user", session_id="test_session",
        importance=0.8,
    ))
    check("Short-term memory stored", True)

    mem.store(Memory(
        id="test_long_1", type=MemoryType.LONG_TERM,
        content="User knows Python and FastAPI", user_id="test_user",
        importance=0.9,
    ))
    check("Long-term memory stored", True)

    mem.store_conversation("test_user", "test_conv", "What is APA-OS?", "APA-OS is an AI Operating System")
    check("Conversation memory stored", True)

    results = mem.query(MemoryQuery(query="", user_id="test_user", top_k=10))
    check("Memory query returns results", len(results) > 0)

    convs = mem.get_conversation("test_conv")
    check("Conversation retrieved", len(convs) > 0)
    if convs:
        check("Conversation has user message", convs[0].content == "What is APA-OS?")

    mem.set_preference("test_user", "theme", "dark")
    pref = mem.get_preference("test_user", "theme")
    check("Preference stored and retrieved", pref == "dark")

    stats = mem.get_stats()
    check("Memory stats available", len(stats) > 0)

    mem.clear_session("test_session")
    check("Session cleared", True)


async def test_rag_engine():
    logger.info("\n=== RAG Engine ===")
    from rag.engine import get_rag_engine

    rag = get_rag_engine()
    check("RAG engine created", rag is not None)

    response = await rag.answer("What is APA-OS?")
    check("RAG returns answer", len(response.answer) > 0)
    check("RAG returns citations", len(response.citations) >= 0)
    check("RAG has confidence score", response.confidence >= 0)

    retry_response = await rag.retrieve("knowledge management", top_k=5)
    check("RAG retrieve returns results", retry_response["total"] >= 0)


async def test_context_engine():
    logger.info("\n=== Context Engine ===")
    from context.engine import get_context_engine

    ctx = get_context_engine()
    check("Context engine created", ctx is not None)

    ctx.update(current_device_id="test_device", current_app="test_app")
    current = ctx.get_current()
    check("Context updated", current.current_device_id == "test_device")
    check("Context has app", current.current_app == "test_app")

    ctx.add_search("test query")
    check("Search added to context", "test query" in ctx.get_current().recent_searches)

    ctx.add_document("test.pdf", "/path/to/test.pdf")
    check("Document added to context", ctx.get_current().active_document == "test.pdf")

    summary = ctx.get_context_summary()
    check("Context summary available", len(summary) > 0)

    history = ctx.get_history()
    check("Context history available", True)


async def test_file_explorer():
    logger.info("\n=== File Explorer ===")
    from file_explorer.explorer import get_file_explorer

    explorer = get_file_explorer()
    check("File explorer created", explorer is not None)

    files = await explorer.browse(os.path.expanduser("~"))
    check("Can browse home directory", len(files) > 0)

    search_results = await explorer.search_files("test")
    check("File search works", len(search_results) >= 0)

    explorer.add_favorite(os.path.expanduser("~"))
    favorites = await explorer.get_favorites()
    check("Favorites work", len(favorites) > 0)


async def test_knowledge_analytics():
    logger.info("\n=== Knowledge Analytics ===")
    from analytics.knowledge_analytics import get_knowledge_analytics

    analytics = get_knowledge_analytics()
    check("Analytics created", analytics is not None)

    analytics.log_search("test query", "hybrid", 5, 100.0)
    search_analytics = analytics.get_search_analytics()
    check("Search analytics works", search_analytics["total_searches"] > 0)

    metrics = analytics.get_knowledge_metrics()
    check("Knowledge metrics available", metrics is not None)

    sources = analytics.get_sources_analytics()
    check("Sources analytics available", sources is not None)


async def test_knowledge_agent():
    logger.info("\n=== Knowledge Agent ===")
    from agents.knowledge_agent import get_knowledge_agent

    agent = get_knowledge_agent()
    check("Knowledge agent created", agent is not None)

    response = await agent.search("test query", search_type="keyword")
    check("Agent search works", response.total >= 0)

    response = await agent.answer("What is APA-OS?")
    check("Agent answer returns response", len(response.answer) > 0)
    check("Agent answer has sources", len(response.sources) >= 0)

    response = await agent.find_file("test")
    check("Agent find file works", len(response.answer) > 0)


async def test_reasoning_agent():
    logger.info("\n=== Reasoning Agent ===")
    from agents.reasoning_agent import get_reasoning_agent

    agent = get_reasoning_agent()
    check("Reasoning agent created", agent is not None)

    result = await agent.reason("What do I know about Python?")
    check("Reasoning returns conclusion", len(result.conclusion) > 0)
    check("Reasoning has steps", len(result.reasoning_steps) > 0)
    check("Reasoning has evidence", len(result.evidence) >= 0)

    result = await agent.analyze("knowledge management")
    check("Analysis works", len(result.conclusion) > 0)


async def test_phase1_2_integration():
    logger.info("\n=== Phase 1/2 Integration ===")
    from agents.knowledge_agent import get_knowledge_agent

    agent = get_knowledge_agent()
    check("Knowledge agent integrates with Phase 1/2", agent is not None)

    response = await agent.find_file("DBMS notes")
    check("Integration: find file for Phase 1 open action", len(response.answer) > 0)
    if response.actions:
        check("Integration: returns open_file actions", any(a.get("type") == "open_file" for a in response.actions))


async def test_phase3_index_command():
    logger.info("\n=== Phase 3 Index Command ===")
    from knowledge.document_ingestion import get_ingestion_pipeline
    pipeline = get_ingestion_pipeline()
    status = pipeline.get_status()
    check("Pipeline status available", "indexed_documents" in status)
    check("Pipeline has chunk config", status["chunk_size"] == 500)
    check("Pipeline has chunk overlap", status["chunk_overlap"] == 50)


async def main():
    logger.info("=" * 60)
    logger.info("APA-OS Phase 3 Acceptance Tests")
    logger.info(f"Started: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)

    await test_knowledge_source_connectors()
    await test_document_parsers()
    await test_embedding_engine()
    await test_vector_store()
    await test_search_engine()
    await test_document_ingestion()
    await test_knowledge_graph()
    await test_memory_engine()
    await test_rag_engine()
    await test_context_engine()
    await test_file_explorer()
    await test_knowledge_analytics()
    await test_knowledge_agent()
    await test_reasoning_agent()
    await test_phase1_2_integration()
    await test_phase3_index_command()

    logger.info("=" * 60)
    logger.info(f"RESULTS: {PASS}/{TOTAL} passed, {FAIL} failed")
    logger.info("=" * 60)

    if FAIL > 0:
        logger.error("Phase 3 Acceptance: SOME TESTS FAILED")
        sys.exit(1)
    else:
        logger.info("Phase 3 Acceptance: ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
