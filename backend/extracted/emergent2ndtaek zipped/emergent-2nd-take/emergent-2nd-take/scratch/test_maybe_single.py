import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Query a non-existent session
print("Querying non-existent session token 'does-not-exist'...")
try:
    res = supabase.table("sessions").select("user_id").eq("session_token", "does-not-exist").maybe_single().execute()
    print("Result type:", type(res))
    print("Result:", res)
    if res is not None:
        print("Result data:", res.data)
except Exception as e:
    print("Error:", e)
