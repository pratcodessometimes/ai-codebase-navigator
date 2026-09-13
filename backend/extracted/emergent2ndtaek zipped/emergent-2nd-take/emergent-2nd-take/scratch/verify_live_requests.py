import requests
from supabase import create_client, Client
import os

from dotenv import load_dotenv
import os
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Get a real session
sess_resp = supabase.table("sessions").select("*").limit(1).execute()
if not sess_resp.data:
    print("NO SESSIONS IN DB")
    exit(1)

token = sess_resp.data[0]["session_token"]
user_id = sess_resp.data[0]["user_id"]

print(f"Using session token: {token[:10]}... for user: {user_id}\n")

# 1. GET /api/auth/me with cookie
url1 = "http://localhost:8000/api/auth/me"
resp1 = requests.get(url1, cookies={"session_token": token})
print(f"URL: {url1}")
print(f"Status code: {resp1.status_code}")
print(f"Response body: {resp1.text}")
print("-" * 50)

# 2. GET /api/campaigns?status=ACTIVE with cookie
url2 = "http://localhost:8000/api/campaigns"
resp2 = requests.get(url2, params={"status": "ACTIVE"}, cookies={"session_token": token})
print(f"URL: {url2}?status=ACTIVE")
print(f"Status code: {resp2.status_code}")
print(f"Response body: {resp2.text}")
print("-" * 50)

# 3. GET /api/campaigns?status=ACTIVE without cookie
url3 = "http://localhost:8000/api/campaigns"
resp3 = requests.get(url3, params={"status": "ACTIVE"})
print(f"URL: {url3}?status=ACTIVE")
print(f"Status code: {resp3.status_code}")
print(f"Response body: {resp3.text}")
print("-" * 50)

# 4. GET /api/auth/me without cookie
url4 = "http://localhost:8000/api/auth/me"
resp4 = requests.get(url4)
print(f"URL: {url4}")
print(f"Status code: {resp4.status_code}")
print(f"Response body: {resp4.text}")
print("-" * 50)
