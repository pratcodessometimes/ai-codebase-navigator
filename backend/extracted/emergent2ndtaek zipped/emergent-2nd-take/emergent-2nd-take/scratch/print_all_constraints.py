import os
import sys
from dotenv import load_dotenv

WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

load_dotenv("backend/.env")

from backend.server import supabase

def print_constraints(table_name):
    print(f"\nConstraints for table '{table_name}':")
    # Fetch from information_schema
    # Note: check constraints are in information_schema.check_constraints and table_constraints
    sql = f"""
    SELECT 
        tc.constraint_name, 
        cc.check_clause
    FROM 
        information_schema.table_constraints tc
        JOIN information_schema.check_constraints cc ON tc.constraint_name = cc.constraint_name
    WHERE 
        tc.table_name = '{table_name}';
    """
    try:
        res = supabase.rpc("run_sql", {"sql": sql}).execute()
        print("Result:", res.data)
    except Exception as e:
        # Since run_sql RPC is not available, we can try running query on pg_constraint via REST if possible, 
        # or info_schema views. Let's try querying information_schema views directly via REST API!
        # Note: information_schema tables might not be exposed by PostgREST REST API by default.
        # Let's try standard query.
        try:
            res = supabase.table("pg_catalog.pg_constraint").select("*").execute()
            print("pg_constraint:", res.data)
        except Exception as e2:
            print("REST check constraints failed:", e2)

print_constraints("campaigns")
print_constraints("withdrawals")
