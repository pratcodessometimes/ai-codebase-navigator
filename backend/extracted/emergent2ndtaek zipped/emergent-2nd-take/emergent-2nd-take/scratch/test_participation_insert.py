import os
import sys
from dotenv import load_dotenv

WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

load_dotenv("backend/.env")

from backend.server import supabase

def test_status(status_val):
    test_id = f"test_part_{status_val.lower()}"
    p_data = {
        "participation_id": test_id,
        "campaign_id": "camp_small_completed",
        "editor_id": "e2e_debug_editor",
        "payout_status": status_val,
        "payout_amount": 100.0
    }
    try:
        supabase.table("participations").insert(p_data).execute()
        print(f"Status '{status_val}' is VALID (Inserted successfully!)")
        supabase.table("participations").delete().eq("participation_id", test_id).execute()
    except Exception as e:
        print(f"Status '{status_val}' is INVALID: {e}")

# Let's test common status values
for val in ["NONE", "PENDING", "PAID", "COMPLETED", "AWAITING_PAYMENT", "EARNED", "NONE", "none", "pending", "paid", "completed"]:
    test_status(val)
