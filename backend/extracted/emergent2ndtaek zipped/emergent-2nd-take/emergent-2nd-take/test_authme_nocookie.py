"""Reproduce the 500 from /api/auth/me with no cookie."""
import sys, traceback
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from backend.server import api

client = TestClient(api, raise_server_exceptions=True)

try:
    resp = client.get("/api/auth/me")
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:500]}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")
    traceback.print_exc()
