import os
import sys
from dotenv import load_dotenv

WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

load_dotenv("backend/.env")

from backend.server import supabase

def fund_all_users():
    res = supabase.table("users").select("user_id, email, name, role").execute()
    users = res.data or []
    print(f"Found {len(users)} users. Funding each with INR 500000.0...")
    
    for u in users:
        supabase.table("users").update({
            "wallet_balance": 500000.0,
            "total_earnings": 500000.0
        }).eq("user_id", u["user_id"]).execute()
        print(f"Funded {u['role']} - {u['name']} ({u['email']})")

fund_all_users()
