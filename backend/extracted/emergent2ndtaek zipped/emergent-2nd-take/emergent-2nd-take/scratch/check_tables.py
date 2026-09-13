import os
import sys
from dotenv import load_dotenv

WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

load_dotenv("backend/.env")

from backend.server import supabase

def check_table(name):
    try:
        res = supabase.table(name).select("*").limit(1).execute()
        print(f"Table '{name}' exists. Columns: {list(res.data[0].keys()) if res.data else 'No data to inspect columns'}")
    except Exception as e:
        print(f"Table '{name}' check failed: {e}")

check_table("campaigns")
check_table("participations")
check_table("clips")
check_table("withdrawals")
check_table("settlement_logs")
