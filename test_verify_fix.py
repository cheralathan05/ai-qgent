"""Verify device status fix is working - no hardcoded values."""
import os, sys
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
os.environ["DATABASE_URL"] = "postgresql://apa_user:changeme@localhost:5432/apa_os"
os.environ["DEBUG"] = "false"
import logging; logging.basicConfig(level=logging.ERROR)

import database.connection as db_conn
import database.models as db_models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
test_engine = create_engine("sqlite:///:memory:", echo=False)
db_conn.engine = test_engine
db_conn.SessionLocal = sessionmaker(bind=test_engine)
db_models.Base.metadata.create_all(bind=test_engine)

from api.main import app
from fastapi.testclient import TestClient
client = TestClient(app)

tests = [
    ("GET", "/device/status", None),
    ("GET", "/api/debug/adb", None),
    ("GET", "/devices", None),
    ("GET", "/health", None),
]

for method, path, body in tests:
    if method == "GET":
        r = client.get(path)
    else:
        r = client.post(path, json=body)
    data = r.json()
    print(f"\n{method} {path} [{r.status_code}]")
    for k, v in data.items():
        print(f"  {k}: {v}")

# Critical assertions for /device/status
r = client.get("/device/status")
s = r.json()
assert s["connected"] == False, f"Expected connected=false, got {s}"
assert s.get("battery_level") is None or s.get("battery") is None, f"No battery should be reported when disconnected: {s}"
assert "No Android devices" in str(r.text), f"Should explain why disconnected"
print("\n\n=== ALL ASSERTIONS PASSED ===")
