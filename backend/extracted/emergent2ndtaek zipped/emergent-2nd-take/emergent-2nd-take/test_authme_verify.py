"""Verify: does /api/auth/me with no cookie return 401 or 500?"""
import sys
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from backend.server import app

# Test with raise_server_exceptions=False (like a real browser would see)
client = TestClient(app, raise_server_exceptions=False)
resp = client.get("/api/auth/me")
print(f"/api/auth/me (no cookie): status={resp.status_code} body={resp.text[:200]}")

# Also test /api/auth/me with a BOGUS cookie
resp2 = client.get("/api/auth/me", cookies={"session_token": "bogus-fake-token"})
print(f"/api/auth/me (bogus cookie): status={resp2.status_code} body={resp2.text[:200]}")
