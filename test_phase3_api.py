"""
Phase 3 API Integration Tests for APA-OS
Tests all Phase 3 API endpoints via FastAPI TestClient using a standalone test app
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_phase3_api")

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.phase3 import router as phase3_router

    app = FastAPI()
    app.include_router(phase3_router)
    client = TestClient(app)
    FASTAPI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"FastAPI TestClient not available: {e}")
    FASTAPI_AVAILABLE = False

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


def test_root_api():
    logger.info("\n=== Test: GET /api/phase3/ ===")
    response = client.get("/api/phase3/")
    check("Root endpoint returns 200", response.status_code == 200)
    data = response.json()
    check("Root response has name", "name" in data)
    check("Root response has version", "version" in data)


def test_search_api():
    logger.info("\n=== Test: POST /api/phase3/search ===")
    response = client.post("/api/phase3/search", json={
        "query": "test document",
        "search_type": "keyword",
        "top_k": 10,
    })
    check("Search endpoint returns 200", response.status_code == 200)
    data = response.json()
    check("Search response has query", "query" in data)
    check("Search response has results", "results" in data)
    check("Search response has total", "total" in data)


def test_documents_api():
    logger.info("\n=== Test: GET /api/phase3/documents ===")
    response = client.get("/api/phase3/documents")
    check("Documents list returns 200", response.status_code == 200)
    data = response.json()
    check("Documents list has total", "total" in data)
    check("Documents list has documents", "documents" in data)


def test_sources_api():
    logger.info("\n=== Test: GET /api/phase3/sources ===")
    response = client.get("/api/phase3/sources")
    check("Sources list returns 200", response.status_code == 200)
    data = response.json()
    check("Sources list has sources", "sources" in data)
    check("Sources list has total", "total" in data)


def test_ask_api():
    logger.info("\n=== Test: POST /api/phase3/ask ===")
    response = client.post("/api/phase3/ask", json={
        "query": "What is APA-OS?",
        "top_k": 3,
    })
    check("Ask endpoint returns 200", response.status_code == 200)
    data = response.json()
    check("Ask response has answer", "answer" in data)
    check("Ask response has sources", "sources" in data)
    check("Ask response has confidence", "confidence" in data)


def test_retrieve_api():
    logger.info("\n=== Test: POST /api/phase3/retrieve ===")
    response = client.post("/api/phase3/retrieve", json={
        "query": "test",
        "top_k": 5,
    })
    check("Retrieve endpoint returns 200", response.status_code == 200)
    data = response.json()
    check("Retrieve response has results", "results" in data)


def test_memory_api():
    logger.info("\n=== Test: GET /api/phase3/memory/current ===")
    response = client.get("/api/phase3/memory/current?session_id=test_session")
    check("Memory current returns 200", response.status_code == 200)
    data = response.json()
    check("Memory response has session", "session" in data)

    logger.info("\n=== Test: GET /api/phase3/memory/history ===")
    response = client.get("/api/phase3/memory/history?user_id=test_user")
    check("Memory history returns 200", response.status_code == 200)
    data = response.json()
    check("Memory history has memories", "memories" in data)


def test_knowledge_graph_api():
    logger.info("\n=== Test: GET /api/phase3/graph/entities ===")
    response = client.get("/api/phase3/graph/entities")
    check("Graph entities returns 200", response.status_code == 200)
    data = response.json()
    check("Graph entities has entities", "entities" in data)
    check("Graph entities has total", "total" in data)

    logger.info("\n=== Test: POST /api/phase3/graph/entity ===")
    response = client.post("/api/phase3/graph/entity", json={
        "name": "API Test Entity",
        "entity_type": "concept",
    })
    check("Create entity returns 200", response.status_code == 200)
    data = response.json()

    logger.info("\n=== Test: GET /api/phase3/graph/relationships ===")
    response = client.get("/api/phase3/graph/relationships")
    check("Graph relationships returns 200", response.status_code == 200)


def test_file_explorer_api():
    logger.info("\n=== Test: GET /api/phase3/files ===")
    response = client.get("/api/phase3/files")
    check("File explorer returns 200", response.status_code == 200)
    data = response.json()
    check("File explorer has files", "files" in data)

    logger.info("\n=== Test: GET /api/phase3/files/recent ===")
    response = client.get("/api/phase3/files/recent?limit=5")
    check("Recent files returns 200", response.status_code == 200)

    logger.info("\n=== Test: GET /api/phase3/files/search ===")
    response = client.get("/api/phase3/files/search?query=test")
    check("File search returns 200", response.status_code == 200)


def test_analytics_api():
    logger.info("\n=== Test: GET /api/phase3/analytics/knowledge ===")
    response = client.get("/api/phase3/analytics/knowledge")
    check("Knowledge analytics returns 200", response.status_code == 200)

    logger.info("\n=== Test: GET /api/phase3/analytics/search ===")
    response = client.get("/api/phase3/analytics/search")
    check("Search analytics returns 200", response.status_code == 200)

    logger.info("\n=== Test: GET /api/phase3/analytics/memory ===")
    response = client.get("/api/phase3/analytics/memory")
    check("Memory analytics returns 200", response.status_code == 200)

    logger.info("\n=== Test: GET /api/phase3/analytics/sources ===")
    response = client.get("/api/phase3/analytics/sources")
    check("Sources analytics returns 200", response.status_code == 200)


def test_agents_api():
    logger.info("\n=== Test: GET /api/phase3/agents ===")
    response = client.get("/api/phase3/agents")
    check("Agents list returns 200", response.status_code == 200)
    data = response.json()
    check("Agents list has agents", "agents" in data)


def test_context_api():
    logger.info("\n=== Test: GET /api/phase3/context/current ===")
    response = client.get("/api/phase3/context/current")
    check("Context returns 200", response.status_code == 200)
    data = response.json()
    check("Context has data", len(data) > 0)


def test_conversation_api():
    logger.info("\n=== Test: GET /api/phase3/conversations ===")
    response = client.get("/api/phase3/conversations")
    check("Conversations list returns 200", response.status_code == 200)


def run_all_api_tests():
    if not FASTAPI_AVAILABLE:
        logger.warning("Skipping API tests - FastAPI TestClient not available")
        return

    tests = [
        test_root_api,
        test_search_api,
        test_documents_api,
        test_sources_api,
        test_ask_api,
        test_retrieve_api,
        test_memory_api,
        test_knowledge_graph_api,
        test_file_explorer_api,
        test_analytics_api,
        test_agents_api,
        test_context_api,
        test_conversation_api,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            logger.error(f"  FAIL: {test.__name__} - {e}")
            global FAIL, TOTAL
            FAIL += 1
            TOTAL += 1


def main():
    logger.info("=" * 60)
    logger.info("APA-OS Phase 3 API Tests")
    logger.info("=" * 60)

    run_all_api_tests()

    logger.info("=" * 60)
    logger.info(f"RESULTS: {PASS}/{TOTAL} passed, {FAIL} failed")
    logger.info("=" * 60)

    return FAIL == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
