import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

test_statuses = [
    "DRAFT", "PENDING_PAYMENT", "ACTIVE", "COMPLETED",
    "OPEN", "CLOSING_SOON", "UNDER_REVIEW",
    "draft", "pending_payment", "active", "completed"
]

# Get a campaign ID to test with
camps = supabase.table("campaigns").select("campaign_id,status").limit(1).execute()
if not camps.data:
    print("No campaigns found!")
    exit(1)

camp_id = camps.data[0]["campaign_id"]
original_status = camps.data[0]["status"]
print(f"Testing on campaign {camp_id} (original status: {original_status}):")

for s in test_statuses:
    try:
        supabase.table("campaigns").update({"status": s}).eq("campaign_id", camp_id).execute()
        print(f"  SUCCESS: {s}")
    except Exception as e:
        print(f"  FAILED: {s} - {str(e)[:150]}")

# Restore original status
supabase.table("campaigns").update({"status": original_status}).eq("campaign_id", camp_id).execute()

