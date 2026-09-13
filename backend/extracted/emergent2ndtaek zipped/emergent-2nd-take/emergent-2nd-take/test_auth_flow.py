"""Simulate the exact browser flow: login → dashboard → browse campaigns.
Capture every request/response to find what causes the guest-state flip."""
import sys
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from backend.server import api, supabase

client = TestClient(api, raise_server_exceptions=False)

# Step 0: Get a real session token from Supabase
sess_resp = supabase.table("sessions").select("*").limit(5).execute()
print("=" * 70)
print("STEP 0: Sessions in DB")
print("=" * 70)
for s in (sess_resp.data or []):
    print(f"  token={s['session_token'][:20]}...  user_id={s['user_id']}")

if not sess_resp.data:
    print("NO SESSIONS - cannot test")
    sys.exit(1)

token = sess_resp.data[0]["session_token"]
user_id = sess_resp.data[0]["user_id"]

# Check if this user actually exists in users table
print(f"\n{'=' * 70}")
print(f"STEP 0b: Does user_id={user_id} exist in users table?")
print("=" * 70)
user_check = supabase.table("users").select("user_id,role,display_name").eq("user_id", user_id).execute()
print(f"  Result: {user_check.data}")

# Step 1: GET /api/auth/me (what AuthContext.refresh() calls on every mount)
print(f"\n{'=' * 70}")
print("STEP 1: GET /api/auth/me (with session cookie)")
print("=" * 70)
resp = client.get("/api/auth/me", cookies={"session_token": token})
print(f"  Status: {resp.status_code}")
print(f"  Body:   {resp.text[:500]}")

# Step 2: GET /api/dashboard (what dashboard page fetches)
print(f"\n{'=' * 70}")
print("STEP 2: GET /api/dashboard (with session cookie)")
print("=" * 70)
resp = client.get("/api/dashboard", cookies={"session_token": token})
print(f"  Status: {resp.status_code}")
print(f"  Body:   {resp.text[:500]}")

# Step 3: Navigate to campaigns - this triggers AuthProvider remount
# which calls GET /api/auth/me AGAIN
print(f"\n{'=' * 70}")
print("STEP 3: GET /api/auth/me AGAIN (simulates AuthProvider remount on navigation)")
print("=" * 70)
resp = client.get("/api/auth/me", cookies={"session_token": token})
print(f"  Status: {resp.status_code}")
print(f"  Body:   {resp.text[:500]}")

# Step 4: GET /api/campaigns (what Campaigns.jsx fetches)
print(f"\n{'=' * 70}")
print("STEP 4: GET /api/campaigns?status=ACTIVE (with session cookie)")
print("=" * 70)
resp = client.get("/api/campaigns", params={"status": "ACTIVE"}, cookies={"session_token": token})
print(f"  Status: {resp.status_code}")
print(f"  Body:   {resp.text[:500]}")

# Step 5: GET /api/campaigns without cookie (guest mode)
print(f"\n{'=' * 70}")
print("STEP 5: GET /api/campaigns?status=ACTIVE (NO cookie - guest)")
print("=" * 70)
resp = client.get("/api/campaigns", params={"status": "ACTIVE"})
print(f"  Status: {resp.status_code}")
print(f"  Body:   {resp.text[:500]}")

# Step 6: GET /api/auth/me without cookie (what happens if cookie is lost)
print(f"\n{'=' * 70}")
print("STEP 6: GET /api/auth/me (NO cookie)")
print("=" * 70)
resp = client.get("/api/auth/me")
print(f"  Status: {resp.status_code}")
print(f"  Body:   {resp.text[:500]}")

# Step 7: Test ALL session tokens
print(f"\n{'=' * 70}")
print("STEP 7: Test ALL session tokens against /api/auth/me")
print("=" * 70)
for s in (sess_resp.data or []):
    t = s["session_token"]
    r = client.get("/api/auth/me", cookies={"session_token": t})
    print(f"  token={t[:20]}...  user_id={s['user_id']}  →  status={r.status_code}  body={r.text[:200]}")
