import os
import sys
from dotenv import load_dotenv

WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

load_dotenv("backend/.env")

from backend.server import supabase

sql = "SELECT 1 as val;"
try:
    result = supabase.rpc("run_sql", {"sql": sql}).execute()
    print("SUCCESS! run_sql RPC works. Result data:", result.data)
except Exception as e:
    print("FAILED! run_sql RPC did not work:", e)
