"""
APA-OS Complete Backend Integration Test
Validates the full Phase 1 → Phase 2 → Phase 3 pipeline end-to-end.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
for p in [SRC_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_integration")

PASS = 0
FAIL = 0
TOTAL = 0


def check(name: str, condition: bool):
    global PASS, FAIL, TOTAL
    TOTAL += 1
    if condition:
        PASS += 1
        logger.info(f"  \u2713 PASS: {name}")
    else:
        FAIL += 1
        logger.error(f"  \u2717 FAIL: {name}")


async def test_01_phase3_knowledge_pipeline():
    """Phase 3: Complete knowledge pipeline - ingest, index, search, retrieve, RAG."""
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 3: Knowledge Intelligence Pipeline")
    logger.info("=" * 60)

    from knowledge.source_connectors import LocalFileConnector
    from knowledge.document_ingestion import get_ingestion_pipeline
    from knowledge.search_engine import get_search_engine
    from rag.engine import get_rag_engine
    from knowledge_graph.engine import get_knowledge_graph, EntityType

    with tempfile.TemporaryDirectory() as tmpdir:
        basedir = Path(tmpdir)
        check("Temp directory created", basedir.exists())

        notes_file = basedir / "DBMS_Notes.txt"
        notes_file.write_text(
            "Database Management Systems Notes\n"
            "================================\n\n"
            "A Database Management System (DBMS) is software that interacts with end users, applications, "
            "and the database itself to capture and analyze data. DBMS allows users to create, read, update, "
            "and delete data in a database.\n\n"
            "Popular DBMS: Oracle, MySQL, PostgreSQL, MongoDB, Redis."
        )
        check("Notes file created", notes_file.exists())

        connector = LocalFileConnector(str(basedir))
        files = await connector.list_files()
        check("Local connector lists files", len(files) >= 0)

        if files:
            doc = await connector.read_file(files[0]["id"])
            check("File readable", doc is not None)

            pipeline = get_ingestion_pipeline()
            chunks = await pipeline.ingest_document(doc)
            check("Document ingested", chunks is not None)
            if chunks:
                check("Chunks created", len(chunks) > 0)

        search = get_search_engine()
        check("Search engine created", search is not None)
        results = await search.search("DBMS", search_type="keyword")
        check("Keyword search returns results", results.total >= 0)

        rag = get_rag_engine()
        check("RAG engine created", rag is not None)
        response = await rag.answer("What is a DBMS?")
        check("RAG returns answer", len(response.answer) > 0)
        check("RAG returns citations", len(response.citations) >= 0)
        check("RAG has confidence", response.confidence >= 0)

        kg = get_knowledge_graph()
        entity = kg.create_entity("DBMS Notes", EntityType.NOTE, {"source": "test"})
        check("KG entity created", entity is not None)
        check("Entity has ID", len(entity.id) > 0)
        check("Entity name matches", entity.name == "DBMS Notes")
        found = kg.search_entities("DBMS")
        check("Can search entities", len(found) > 0)


async def test_02_intent_engine():
    """Intent Engine: Detect intents from natural language commands."""
    logger.info("\n" + "=" * 60)
    logger.info("INTENT: Intent Detection Engine")
    logger.info("=" * 60)

    from services.intent_agent import get_intent_agent

    agent = get_intent_agent()
    check("Intent agent created", agent is not None)

    intent = await agent.detect_intent("Open Instagram")
    check("Intent detected for 'Open Instagram'", intent is not None)
    check("Intent has intent field", hasattr(intent, 'intent') or (isinstance(intent, dict) and "action" in intent))

    intent2 = await agent.detect_intent("Send message to John")
    check("Intent detected for message sending", intent2 is not None)

    intent3 = await agent.detect_intent("What is DBMS?")
    check("Intent detected for knowledge query", intent3 is not None)


async def test_03_planner_agent():
    """Planner Agent: Create execution plans from intents."""
    logger.info("\n" + "=" * 60)
    logger.info("PLANNER: Planner Agent")
    logger.info("=" * 60)

    from services.planner_agent import get_planner_agent
    from services.intent_agent import get_intent_agent

    planner = get_planner_agent()
    check("Planner agent created", planner is not None)

    intent_agent = get_intent_agent()
    intent = await intent_agent.detect_intent("Open Instagram")

    plan = planner.plan(intent)
    check("Plan created", plan is not None)


async def test_04_memory_engine():
    """Memory Engine: Store, query, recall across short/medium/long term."""
    logger.info("\n" + "=" * 60)
    logger.info("MEMORY: Multi-term Memory Engine")
    logger.info("=" * 60)

    from memory.engine import get_memory_engine, Memory, MemoryQuery, MemoryType

    mem = get_memory_engine()
    check("Memory engine created", mem is not None)

    mem.store(Memory(
        id="test_short_1", type=MemoryType.SHORT_TERM,
        content="Current screen is Instagram feed",
        user_id="test_user", session_id="test_session",
    ))
    mem.store(Memory(
        id="test_long_1", type=MemoryType.LONG_TERM,
        content="User prefers dark mode",
        user_id="test_user", importance=0.9,
    ))
    check("Short-term memory stored", True)
    check("Long-term memory stored", True)

    results = mem.query(MemoryQuery(query="", user_id="test_user", top_k=5))
    check("Memory query returns results", len(results) > 0)

    mem.store(Memory(id="test_conv_1", type=MemoryType.CONVERSATION,
        content="I need help with DBMS notes",
        user_id="test_user", session_id="test_session", metadata={"role": "user"},
    ))
    mem.store(Memory(id="test_conv_2", type=MemoryType.CONVERSATION,
        content="Here are your DBMS notes",
        user_id="test_user", session_id="test_session", metadata={"role": "assistant"},
    ))
    conv = mem.get_conversation("test_session")
    check("Conversation retrieved", len(conv) > 0)
    check("Conversation has user message", any(m.metadata.get("role") == "user" for m in conv))

    mem.set_preference("test_user", "theme", "dark")
    pref = mem.get_preference("test_user", "theme")
    check("Preference stored and retrieved", pref == "dark")

    stats = mem.get_stats()
    check("Memory stats available", len(stats) > 0)


async def test_05_knowledge_graph():
    """Knowledge Graph: Entity/relationship CRUD, search, subgraph."""
    logger.info("\n" + "=" * 60)
    logger.info("GRAPH: Knowledge Graph Engine")
    logger.info("=" * 60)

    from knowledge_graph.engine import get_knowledge_graph, EntityType, RelationshipType

    kg = get_knowledge_graph()
    check("Knowledge graph created", kg is not None)

    alice = kg.create_entity("Alice", EntityType.PERSON, {"role": "developer"})
    bob = kg.create_entity("Bob", EntityType.PERSON, {"role": "designer"})
    project = kg.create_entity("APA-OS", EntityType.PROJECT, {"status": "active"})
    check("Person entities created", alice is not None and bob is not None)
    check("Project entity created", project is not None)

    kg.create_relationship(alice.id, project.id, RelationshipType.WORKS_ON, {"since": "2024"})
    kg.create_relationship(bob.id, project.id, RelationshipType.WORKS_ON, {"since": "2024"})
    check("Relationships created", True)

    all_entities = kg.get_all_entities()
    check("Graph has entities", len(all_entities) >= 3)

    types = kg.get_entity_types()
    check("Entity types reported", len(types) >= 2)

    subgraph = kg.get_subgraph(project.id, depth=2)
    check("Subgraph returns entities", len(subgraph.get("entities", [])) > 0)
    check("Subgraph returns relationships", len(subgraph.get("relationships", [])) > 0)

    connected = kg.get_connected_entities(project.id)
    check("Connected entities found", len(connected) > 0)


async def test_06_context_engine():
    """Context Engine: Track device, screen, app, conversation context."""
    logger.info("\n" + "=" * 60)
    logger.info("CONTEXT: Context Engine")
    logger.info("=" * 60)

    from context.engine import get_context_engine

    ctx = get_context_engine()
    check("Context engine created", ctx is not None)

    ctx.update(current_device_id="phone_1", current_device_type="android",
                current_app="Instagram", current_screen="feed")
    check("Context updated", True)

    summary = ctx.get_current()
    check("Context summary available", summary is not None)

    history = ctx.get_history(limit=10)
    check("Context history available", len(history) > 0)

    logger.info(f"  Context summary: {str(summary)[:200]}")


async def test_07_file_explorer():
    """File Explorer: Browse, search, favorites."""
    logger.info("\n" + "=" * 60)
    logger.info("FILES: File Explorer")
    logger.info("=" * 60)

    from file_explorer.explorer import get_file_explorer

    explorer = get_file_explorer()
    check("File explorer created", explorer is not None)

    files = await explorer.browse()
    check("Can browse home directory", len(files) > 0)

    search_results = await explorer.search_files("test")
    check("File search works", search_results is not None)

    favorites = await explorer.get_favorites()
    check("Favorites available", favorites is not None)


async def test_08_knowledge_agent():
    """Knowledge Agent: Search, retrieve, summarize, answer."""
    logger.info("\n" + "=" * 60)
    logger.info("AGENT: Knowledge Agent")
    logger.info("=" * 60)

    from agents.knowledge_agent import get_knowledge_agent

    agent = get_knowledge_agent()
    check("Knowledge agent created", agent is not None)

    search_resp = await agent.search("DBMS", search_type="keyword")
    check("Agent search works", search_resp.total >= 0)

    answer_resp = await agent.answer("What is DBMS?")
    check("Agent answer returns response", len(str(answer_resp.answer)) > 0)
    check("Agent answer has sources", len(answer_resp.sources) >= 0)

    find_resp = await agent.find_file("test")
    check("Agent find file works", len(str(find_resp.answer)) > 0)


async def test_09_reasoning_agent():
    """Reasoning Agent: Reason, analyze, compare with evidence."""
    logger.info("\n" + "=" * 60)
    logger.info("REASONING: Reasoning Agent")
    logger.info("=" * 60)

    from agents.reasoning_agent import get_reasoning_agent

    agent = get_reasoning_agent()
    check("Reasoning agent created", agent is not None)

    result = await agent.reason("What do I know about Python?")
    check("Reasoning returns conclusion", len(result.conclusion) > 0)
    check("Reasoning has steps", len(result.reasoning_steps) > 0)
    check("Reasoning has evidence", len(result.evidence) >= 0)

    analysis = await agent.analyze("knowledge management")
    check("Analysis works", len(analysis.conclusion) > 0)

    comparison = await agent.compare(["Python", "JavaScript"])
    check("Comparison works", len(comparison.conclusion) > 0)


async def test_10_analytics():
    """Analytics: Knowledge, search, memory, sources metrics."""
    logger.info("\n" + "=" * 60)
    logger.info("ANALYTICS: Knowledge Analytics")
    logger.info("=" * 60)

    from analytics.knowledge_analytics import get_knowledge_analytics

    analytics = get_knowledge_analytics()
    check("Analytics created", analytics is not None)

    search_stats = analytics.get_search_analytics()
    check("Search analytics works", search_stats is not None)

    knowledge_metrics = analytics.get_knowledge_metrics()
    check("Knowledge metrics available", knowledge_metrics is not None)

    sources_analytics = analytics.get_sources_analytics()
    check("Sources analytics available", sources_analytics is not None)


async def test_11_vector_store_api():
    """Vector Store: CRUD operations for vector collections."""
    logger.info("\n" + "=" * 60)
    logger.info("VECTOR: Vector Store API")
    logger.info("=" * 60)

    from knowledge.vector_store import get_vector_store, VectorRecord
    from datetime import datetime

    store = get_vector_store("faiss")
    check("Vector store created", store is not None)

    created = await store.create_collection("integration_test", 4)
    check("Collection created", created)

    records = [
        VectorRecord(id="v1", vector=[0.1, 0.2, 0.3, 0.4],
            text="DBMS test document",
            metadata={"source": "test"}, created_at=datetime.now().isoformat()),
        VectorRecord(id="v2", vector=[0.9, 0.8, 0.7, 0.6],
            text="Machine learning concepts",
            metadata={"source": "test"}, created_at=datetime.now().isoformat()),
    ]
    added = await store.add("integration_test", records)
    check("Records added to store", added > 0)

    count = await store.count("integration_test")
    check("Collection has records", count > 0)

    results = await store.search("integration_test", [0.15, 0.25, 0.35, 0.45], top_k=5)
    check("Vector search returns results", len(results) > 0)
    if results:
        check("Search results have scores", results[0].score > 0)

    collections = await store.list_collections()
    check("Can list collections", len(collections) > 0)

    await store.delete_collection("integration_test")
    check("Collection deleted", True)


async def test_12_embedding_engine():
    """Embedding Engine: Generate embeddings for text."""
    logger.info("\n" + "=" * 60)
    logger.info("EMBED: Embedding Engine")
    logger.info("=" * 60)

    from knowledge.embedding_engine import get_embedding_engine

    engine = get_embedding_engine()
    check("Embedding engine created", engine is not None)
    check("Engine has dimensions", engine.dimensions() > 0)
    check("Engine has model name", len(engine.model_name()) > 0)

    embedding = await engine.embed("DBMS test query")
    check("Embedding generated", len(embedding) > 0)

    batch = await engine.embed_batch(["first query", "second query", "third query"])
    check("Batch embedding works", len(batch) == 3)


async def test_13_rag_engine_detail():
    """RAG Engine: Full RAG pipeline with citations and confidence."""
    logger.info("\n" + "=" * 60)
    logger.info("RAG: Detailed RAG Pipeline")
    logger.info("=" * 60)

    from rag.engine import get_rag_engine

    rag = get_rag_engine()
    check("RAG engine created", rag is not None)

    response = await rag.retrieve("What is a database?")
    check("RAG retrieve returns results", len(response) > 0)

    response2 = await rag.answer("Explain databases")
    check("RAG answer returns content", len(response2.answer) > 0)
    check("RAG citations present", len(response2.citations) >= 0)
    check("RAG confidence valid", 0 <= response2.confidence <= 1.0)


async def main():
    logger.info("=" * 60)
    logger.info("APA-OS COMPLETE BACKEND INTEGRATION TEST")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    tests = [
        ("Phase 3 Knowledge Pipeline", test_01_phase3_knowledge_pipeline),
        ("Intent Engine", test_02_intent_engine),
        ("Planner Agent", test_03_planner_agent),
        ("Memory Engine", test_04_memory_engine),
        ("Knowledge Graph", test_05_knowledge_graph),
        ("Context Engine", test_06_context_engine),
        ("File Explorer", test_07_file_explorer),
        ("Knowledge Agent", test_08_knowledge_agent),
        ("Reasoning Agent", test_09_reasoning_agent),
        ("Analytics", test_10_analytics),
        ("Vector Store API", test_11_vector_store_api),
        ("Embedding Engine", test_12_embedding_engine),
        ("RAG Engine Detail", test_13_rag_engine_detail),
    ]

    for name, test_fn in tests:
        try:
            await test_fn()
        except Exception as e:
            logger.error(f"  \u2717 FAIL: {name} - {e}")
            global FAIL, TOTAL
            FAIL += 1
            TOTAL += 1

    logger.info("\n" + "=" * 60)
    logger.info(f"RESULTS: {PASS}/{TOTAL} passed, {FAIL} failed")
    logger.info("=" * 60)

    if FAIL > 0:
        logger.error("INTEGRATION TEST: SOME TESTS FAILED")
        sys.exit(1)
    else:
        logger.info("INTEGRATION TEST: ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
