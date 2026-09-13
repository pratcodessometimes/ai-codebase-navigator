import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Let's perform the status updates on campaigns
print("Running status updates on campaigns...")
res = supabase.table("campaigns").update({"status": "ACTIVE"}).in_("status", ["OPEN", "CLOSING_SOON"]).execute()
print(f"Updated {len(res.data or [])} campaigns to ACTIVE.")

# Also update status = 'PENDING_PAYMENT' WHERE status = 'UNDER_REVIEW'
res2 = supabase.table("campaigns").update({"status": "PENDING_PAYMENT"}).eq("status", "UNDER_REVIEW").execute()
print(f"Updated {len(res2.data or [])} campaigns to PENDING_PAYMENT.")

# Let's print all campaigns and their status values now
res_all = supabase.table("campaigns").select("campaign_id,title,status").execute()
print("\nCampaigns in DB now:")
for r in (res_all.data or []):
    print(f"  ID: {r['campaign_id']}, Title: {r['title']}, Status: {r['status']}")
