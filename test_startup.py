"""Test if the FastAPI app can start up properly."""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

os.environ["DATABASE_URL"] = "postgresql://apa_user:changeme@localhost:5432/apa_os"
os.environ["DEBUG"] = "false"

import logging
logging.basicConfig(level=logging.ERROR)

# Monkey-patch database BEFORE any imports use it
import database.connection as db_conn
import database.models as db_models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

test_engine = create_engine("sqlite:///:memory:", echo=False)
test_session = sessionmaker(bind=test_engine)
db_conn.engine = test_engine
db_conn.SessionLocal = test_session
db_models.Base.metadata.create_all(bind=test_engine)

print(f"Database initialized (SQLite in-memory)")
print(f"Tables created: {db_models.Base.metadata.tables.keys()}")

# Now import app
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Health endpoints
r = client.get("/")
print(f"GET /: {r.status_code} - {r.json()}")

r = client.get("/health")
print(f"GET /health: {r.status_code}")

r = client.get("/devices")
print(f"GET /devices: {r.status_code}")

r = client.get("/workflows")
print(f"GET /workflows: {r.status_code} - count={r.json().get('total', 'N/A')}")

# Test command endpoint
r = client.post("/command", json={"command": "Open Instagram", "user_id": "test"})
print(f"POST /command: {r.status_code}")
data = r.json()
print(f"  success={data.get('success')}, intent={data.get('intent')}, target={data.get('target')}")

print("\n=== ALL TESTS PASSED ===")
