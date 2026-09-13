import os
import sys
from dotenv import load_dotenv

WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

load_dotenv("backend/.env")

from backend.server import supabase, calculate_ocv, recompute_campaign

async def migrate_all_ocv():
    print("Fetching all clips from the database...")
    res = supabase.table("clips").select("clip_id, campaign_id, views, retention_pct, engagement_pct, ocv").execute()
    clips = res.data or []
    print(f"Found {len(clips)} total clips to process.")

    campaign_ids = set()
    updated_count = 0

    for clip in clips:
        clip_id = clip["clip_id"]
        campaign_id = clip["campaign_id"]
        views = clip.get("views", 0)
        retention = clip.get("retention_pct", 0.0)
        engagement = clip.get("engagement_pct", 0.0)
        old_ocv = clip.get("ocv")

        new_ocv = calculate_ocv(views, retention, engagement)
        campaign_ids.add(campaign_id)

        # Update the database regardless of whether it matches (to ensure we overwrite old formula results)
        supabase.table("clips").update({
            "ocv": new_ocv
        }).eq("clip_id", clip_id).execute()

        updated_count += 1
        print(f"Updated clip {clip_id}: Views={views}, Ret={retention}%, Eng={engagement}%, Old OCV={old_ocv}, New OCV={new_ocv}")

    for campaign_id in campaign_ids:
        # recompute_campaign is an async function in backend/server.py
        await recompute_campaign(campaign_id)
        print(f"Recalculated stats for campaign {campaign_id}")

    print(f"Migration completed. Recalculated {updated_count} clips across {len(campaign_ids)} campaigns.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate_all_ocv())
