import os
import sys
from dotenv import load_dotenv
from pathlib import Path
from fastapi.testclient import TestClient

# Load env before importing backend
load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.server import app, supabase

client = TestClient(app, raise_server_exceptions=False)

# Fetch a session token and user ID
sess_resp = supabase.table("sessions").select("*").limit(1).execute()
if not sess_resp.data:
    print("NO SESSIONS IN DB - cannot run tests")
    sys.exit(1)

token = sess_resp.data[0]["session_token"]
user_id = sess_resp.data[0]["user_id"]
cookies = {"session_token": token}

print("=" * 60)
print(f"TESTING FLOWS for user_id: {user_id}")
print("=" * 60)

# 1. Test GET /api/dashboard
print("\n[Flow 1] GET /api/dashboard")
resp = client.get("/api/dashboard", cookies=cookies)
print(f"  Status: {resp.status_code}")
print(f"  Body (truncated): {resp.text[:300]}")

# 2. Test GET /api/campaigns?status=ACTIVE
print("\n[Flow 2] GET /api/campaigns?status=ACTIVE")
resp = client.get("/api/campaigns", params={"status": "ACTIVE"}, cookies=cookies)
print(f"  Status: {resp.status_code}")
campaigns = resp.json()
print(f"  Campaigns count: {len(campaigns)}")
if campaigns:
    print(f"  First Campaign ID: {campaigns[0].get('campaign_id')} (Title: {campaigns[0].get('title')})")
    camp_id = campaigns[0].get('campaign_id')
else:
    camp_id = None
    print("  WARNING: No active campaigns returned. Run database migrations first.")

# 3. Test GET /api/campaigns/{id} (Campaign Detail Page)
if camp_id:
    print(f"\n[Flow 3] GET /api/campaigns/{camp_id}")
    resp = client.get(f"/api/campaigns/{camp_id}", cookies=cookies)
    print(f"  Status: {resp.status_code}")
    print(f"  Body (truncated): {resp.text[:300]}")

    # 4. Test POST /api/campaigns/{id}/join (Join Campaign)
    print(f"\n[Flow 4] POST /api/campaigns/{camp_id}/join")
    join_payload = {"youtube_channel": "https://youtube.com/@testchannel"}
    resp = client.post(f"/api/campaigns/{camp_id}/join", json=join_payload, cookies=cookies)
    print(f"  Status: {resp.status_code}")
    print(f"  Body: {resp.text}")

    # 5. Test POST /api/clips (Submit Clip)
    print(f"\n[Flow 5] POST /api/clips")
    clip_payload = {
        "campaign_id": camp_id,
        "clip_url": "https://youtube.com/shorts/testclip123",
        "description": "Test submission description",
    }
    resp = client.post("/api/clips", json=clip_payload, cookies=cookies)
    print(f"  Status: {resp.status_code}")
    print(f"  Body: {resp.text}")
else:
    print("\n[Flow 3, 4, 5] Skipped because no active campaign was found.")
