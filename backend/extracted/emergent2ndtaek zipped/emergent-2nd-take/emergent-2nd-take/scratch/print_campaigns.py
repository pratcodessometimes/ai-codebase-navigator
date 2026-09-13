import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Get distinct status values
res = supabase.table("campaigns").select("campaign_id,title,status").execute()
print("Campaigns in DB:")
for r in (res.data or []):
    print(f"  ID: {r['campaign_id']}, Title: {r['title']}, Status: {r['status']}")
