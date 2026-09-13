import os
import sys
from dotenv import load_dotenv

WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

load_dotenv("backend/.env")

from backend.server import supabase

res = supabase.table("users").select("user_id, email, name, role, wallet_balance, total_earnings, total_withdrawn").execute()
users = res.data or []
print(f"Total users found: {len(users)}")
for u in users:
    print(f"User: {u['name']} ({u['email']}) | Role: {u['role']} | Wallet: {u['wallet_balance']} | Total Earnings: {u['total_earnings']}")
