import sys
import os
from fastapi.testclient import TestClient

# Add workspace directory to path
WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

# Load env variables from backend/.env
with open(os.path.join(WORKSPACE_DIR, "backend", ".env")) as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            os.environ[k.strip()] = v.strip()

from backend.server import app, supabase

client = TestClient(app, raise_server_exceptions=True)

try:
    camps = supabase.table("campaigns").select("*").eq("status", "ACTIVE").limit(1).execute().data
    if not camps:
        print("No active campaigns found in Supabase.")
        sys.exit(1)
    else:
        campaign_id = camps[0]["campaign_id"]
        print(f"Using campaign: {campaign_id}")

    editor_token = "token_e2e_editor_1"

    print("\n--- Step 1: Editor joins campaign ---")
    join_payload = {"youtube_channel": "dhruv_bangera"}
    resp = client.post(f"/api/campaigns/{campaign_id}/join", json=join_payload, cookies={"session_token": editor_token})
    print(f"Join status: {resp.status_code}")

    print("\n--- Step 2: Get campaign details ---")
    resp_get = client.get(f"/api/campaigns/{campaign_id}", cookies={"session_token": editor_token})
    print(f"Get campaign status: {resp_get.status_code}")

    print("\n--- Step 3: Get clips ---")
    resp_clips = client.get(f"/api/clips?campaign_id={campaign_id}", cookies={"session_token": editor_token})
    print(f"Get clips status: {resp_clips.status_code}")
    print(f"Get clips content len: {len(resp_clips.text)}")

    print("\n--- Step 4: Get leaderboard ---")
    resp_lb = client.get(f"/api/leaderboard/campaign/{campaign_id}", cookies={"session_token": editor_token})
    print(f"Get leaderboard status: {resp_lb.status_code}")
    print(f"Get leaderboard content len: {len(resp_lb.text)}")

except Exception as e:
    import traceback
    print("\nException raised during test:")
    traceback.print_exc()
