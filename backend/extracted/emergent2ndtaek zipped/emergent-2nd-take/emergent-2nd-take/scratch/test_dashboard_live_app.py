import sys
import os
import traceback
from dotenv import load_dotenv
from pathlib import Path
from fastapi.testclient import TestClient

# Load env before importing backend
load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.server import app, supabase

client = TestClient(app, raise_server_exceptions=True)

# Fetch a session token and user ID
sess_resp = supabase.table("sessions").select("*").limit(1).execute()
if not sess_resp.data:
    print("NO SESSIONS IN DB - cannot run tests")
    sys.exit(1)

token = sess_resp.data[0]["session_token"]
user_id = sess_resp.data[0]["user_id"]
cookies = {"session_token": token}

print(f"Using token: {token[:10]}... for user: {user_id}")

try:
    resp = client.get("/api/dashboard", cookies=cookies)
    print(f"Status Code: {resp.status_code}")
    print(f"Response Body (truncated): {resp.text[:500]}")
except Exception as e:
    print("\n--- Exception Captured ---")
    traceback.print_exc()
    print("Exception Type:", type(e).__name__)
    print("Exception Message:", e)
