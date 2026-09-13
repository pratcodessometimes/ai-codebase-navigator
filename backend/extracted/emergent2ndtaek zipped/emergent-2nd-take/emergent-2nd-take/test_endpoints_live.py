"""Test auth + dashboard endpoints with real runtime tracebacks."""
import sys, traceback
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from backend.server import api, supabase

client = TestClient(api, raise_server_exceptions=False)

# 1. Test /auth/me with no cookie (unauthenticated)
print("=" * 60)
print("TEST 1: GET /api/auth/me (no cookie)")
print("=" * 60)
resp = client.get("/api/auth/me")
print(f"Status: {resp.status_code}")
print(f"Body:   {resp.text[:300]}")

# 2. Test /dashboard with no cookie (unauthenticated)
print("\n" + "=" * 60)
print("TEST 2: GET /api/dashboard (no cookie)")
print("=" * 60)
resp = client.get("/api/dashboard")
print(f"Status: {resp.status_code}")
print(f"Body:   {resp.text[:300]}")

# 3. Check if sessions table exists at all
print("\n" + "=" * 60)
print("TEST 3: Query sessions table")
print("=" * 60)
try:
    sess_resp = supabase.table("sessions").select("*").limit(3).execute()
    print(f"Sessions table exists. Row count: {len(sess_resp.data)}")
    if sess_resp.data:
        print(f"Sample keys: {list(sess_resp.data[0].keys())}")
        # Use the first session token to test authenticated requests
        token = sess_resp.data[0].get("session_token")
        print(f"Using token: {token[:20]}..." if token else "No token found")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")
    traceback.print_exc()
    token = None

# 4. If we have a valid token, test auth/me and dashboard with it
if token:
    print("\n" + "=" * 60)
    print("TEST 4: GET /api/auth/me (with session cookie)")
    print("=" * 60)
    resp = client.get("/api/auth/me", cookies={"session_token": token})
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:500]}")

    print("\n" + "=" * 60)
    print("TEST 5: GET /api/dashboard (with session cookie)")
    print("=" * 60)
    resp = client.get("/api/dashboard", cookies={"session_token": token})
    print(f"Status: {resp.status_code}")
    print(f"Body:   {resp.text[:500]}")

# 5. Test with raise_server_exceptions to get traceback for any 500
print("\n" + "=" * 60)
print("TEST 6: GET /api/dashboard (raise exceptions, with cookie)")
print("=" * 60)
client2 = TestClient(api, raise_server_exceptions=True)
try:
    if token:
        resp = client2.get("/api/dashboard", cookies={"session_token": token})
        print(f"Status: {resp.status_code}")
        print(f"Body:   {resp.text[:500]}")
    else:
        resp = client2.get("/api/dashboard")
        print(f"Status: {resp.status_code}")
        print(f"Body:   {resp.text[:500]}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")
    traceback.print_exc()
