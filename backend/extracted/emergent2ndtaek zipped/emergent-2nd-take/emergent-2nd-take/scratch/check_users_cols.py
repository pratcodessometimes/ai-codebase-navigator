import os
import sys
from dotenv import load_dotenv

WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

load_dotenv("backend/.env")

from backend.server import supabase

res = supabase.table("users").select("*").limit(1).execute()
if res.data:
    print("Columns in users table:")
    for k in res.data[0].keys():
        print(f" - {k}")
else:
    print("No users found to inspect columns.")
