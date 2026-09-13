import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from backend/.env
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")

supabase = create_client(url, key)

from server import get_retention_multiplier, get_engagement_multiplier, calculate_ocv

def main():
    print("Fetching clips with missing OCV...")
    # Fetch clips where ocv is null
    res = supabase.table("clips").select("clip_id, views, retention_pct, engagement_pct").is_("ocv", "null").execute()
    clips = res.data or []
    print(f"Found {len(clips)} clips to backfill.")

    updated_count = 0
    for clip in clips:
        clip_id = clip["clip_id"]
        views = clip.get("views", 0)
        retention = clip.get("retention_pct", 0.0)
        engagement = clip.get("engagement_pct", 0.0)
        
        ocv_val = calculate_ocv(views, retention, engagement)
        
        # Update the database
        supabase.table("clips").update({
            "ocv": ocv_val,
            "ocv_formula_version": 1
        }).eq("clip_id", clip_id).execute()
        
        updated_count += 1
        print(f"Updated clip {clip_id}: Views={views}, Ret={retention}%, Eng={engagement}%, OCV={ocv_val}")
        
    print(f"Backfill completed successfully. Updated {updated_count} clips.")

if __name__ == "__main__":
    main()
