import sys
import os
import traceback
from dotenv import load_dotenv
from pathlib import Path
from fastapi.testclient import TestClient

load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.server import app, supabase

client = TestClient(app, raise_server_exceptions=True)

# Fetch all sessions (up to 20)
sess_resp = supabase.table("sessions").select("*").limit(20).execute()
sessions = sess_resp.data or []
print(f"Found {len(sessions)} sessions in database.")

for idx, sess in enumerate(sessions):
    token = sess["session_token"]
    user_id = sess["user_id"]
    
    # Check user role
    user_resp = supabase.table("users").select("role").eq("user_id", user_id).execute()
    role = user_resp.data[0].get("role") if user_resp.data else "UNKNOWN"
    
    print("-" * 60)
    print(f"Session {idx+1}: User ID: {user_id}, Role: {role}, Token: {token[:10]}...")
    
    try:
        resp = client.get("/api/dashboard", cookies={"session_token": token})
        print(f"  Result: {resp.status_code}")
        print(f"  Body (truncated): {resp.text[:300]}")
    except Exception as e:
        print("\n--- Exception Captured ---")
        traceback.print_exc()
        print("Exception Type:", type(e).__name__)
        print("Exception Message:", e)
        # Stop on first error
        break
