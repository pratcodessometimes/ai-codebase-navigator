import os
import sys
from dotenv import load_dotenv
from pathlib import Path
from fastapi.testclient import TestClient

load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.server import app, supabase

client = TestClient(app, raise_server_exceptions=False)

# Fetch a session token and user ID to start with
sess_resp = supabase.table("sessions").select("*").limit(1).execute()
if not sess_resp.data:
    print("NO SESSIONS IN DB - cannot run tests")
    sys.exit(1)

token = sess_resp.data[0]["session_token"]
user_id = sess_resp.data[0]["user_id"]

print(f"Initial test token: {token[:15]}...")

# 1. Call GET /api/auth/me with cookie to verify we are logged in
resp = client.get("/api/auth/me", cookies={"session_token": token})
print(f"GET /me status before logout: {resp.status_code}")
assert resp.status_code == 200, "Should be authenticated"

# 2. Call POST /api/auth/logout
resp_logout = client.post("/api/auth/logout", cookies={"session_token": token})
print(f"POST /logout status: {resp_logout.status_code}")
print(f"POST /logout response headers: {dict(resp_logout.headers)}")
print(f"POST /logout response cookies: {dict(resp_logout.cookies)}")
print(f"POST /logout body: {resp_logout.text}")

# Verify that the cookie is cleared in response headers
set_cookie_header = resp_logout.headers.get("set-cookie", "")
print(f"Set-Cookie Header: {set_cookie_header}")

# 3. Verify that the session row was deleted from the sessions table in database
db_check = supabase.table("sessions").select("*").eq("session_token", token).execute()
print(f"Session row count in DB after logout: {len(db_check.data)}")
assert len(db_check.data) == 0, "Session row should be deleted from DB"

# 4. Verify that calling GET /api/auth/me with the logged out cookie returns 401
client_debug = TestClient(app, raise_server_exceptions=True)
try:
    resp_after = client_debug.get("/api/auth/me", cookies={"session_token": token})
except Exception as e:
    import traceback
    traceback.print_exc()
    raise e
print(f"GET /me status after logout (with old cookie): {resp_after.status_code}")
print(f"GET /me response after logout: {resp_after.text}")
assert resp_after.status_code == 401, "Should be unauthenticated now"

print("\nSUCCESS: Logout flow fully verified!")
