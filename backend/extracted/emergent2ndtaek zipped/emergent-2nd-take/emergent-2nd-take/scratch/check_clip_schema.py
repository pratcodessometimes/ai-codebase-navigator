import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent / 'backend' / '.env')
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Get one clip
res = supabase.table("clips").select("*").limit(1).execute()
if res.data:
    print("Clip keys and values:")
    for k, v in res.data[0].items():
        print(f"  {k}: {v} (type: {type(v).__name__})")
else:
    print("No clips found in DB!")
