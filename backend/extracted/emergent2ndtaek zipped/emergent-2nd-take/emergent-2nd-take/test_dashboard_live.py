"""Test dashboard endpoint with live traceback"""
import sys, traceback
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from backend.server import api, supabase

client = TestClient(api, raise_server_exceptions=True)

# Grab a session token from Supabase
sess_resp = supabase.table("sessions").select("session_token").limit(1).execute()
if not sess_resp.data:
    print("No sessions found in DB")
    sys.exit(1)

token = sess_resp.data[0]["session_token"]
print("Using token:", token[:20], "...")

try:
    resp = client.get("/api/dashboard", cookies={"session_token": token})
    print("Response status:", resp.status_code)
    print("Response body:\n", resp.text[:500])
except Exception as e:
    print("--- Exception captured ---")
    traceback.print_exc()
    # Show exception details
    print("Exception type:", type(e).__name__)
    print("Exception message:", e)
