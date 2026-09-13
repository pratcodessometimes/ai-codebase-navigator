import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Get distinct status values
res = supabase.table("campaigns").select("status").execute()
statuses = [r["status"] for r in (res.data or [])]
distinct_statuses = set(statuses)
print(f"Distinct statuses in DB: {distinct_statuses}")
print("All statuses count:")
for ds in distinct_statuses:
    print(f"  {ds}: {statuses.count(ds)}")
