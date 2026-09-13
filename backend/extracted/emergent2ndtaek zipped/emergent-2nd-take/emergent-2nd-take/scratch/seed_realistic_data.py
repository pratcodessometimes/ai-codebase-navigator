import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

load_dotenv("backend/.env")

from backend.server import supabase, now_iso

def seed_data():
    print("--- START SEEDING REALISTIC TEST DATA ---")

    # 1. Fetch all existing users
    res_users = supabase.table("users").select("*").execute()
    users = res_users.data or []
    print(f"Found {len(users)} users in database.")

    creators = [u for u in users if u["role"] == "CREATOR"]
    editors = [u for u in users if u["role"] == "EDITOR"]
    admins = [u for u in users if u["role"] == "ADMIN"]

    print(f"Creators count: {len(creators)}")
    print(f"Editors count: {len(editors)}")
    print(f"Admins count: {len(admins)}")

    # Clean existing campaigns, clips, participations, withdrawals
    print("Cleaning database tables (except users)...")
    supabase.table("clips").delete().neq("clip_id", "keep_none").execute()
    supabase.table("participations").delete().neq("participation_id", "keep_none").execute()
    supabase.table("withdrawals").delete().neq("withdrawal_id", "keep_none").execute()
    supabase.table("campaigns").delete().neq("campaign_id", "keep_none").execute()
    print("Database cleared of old campaigns/clips/participations/withdrawals.")

    # 2. Update creator balances
    print("Funding creator accounts...")
    for c in creators:
        supabase.table("users").update({
            "wallet_balance": 200000.0,
            "total_earnings": 0.0,
            "total_withdrawn": 0.0
        }).eq("user_id", c["user_id"]).execute()

    # 3. Update editor balances with realistic test histories
    print("Funding editor accounts and updating histories...")
    # We will set specific histories for some editors, and zero out the rest
    editor_configs = {
        "editor@debug.test": {"total_earnings": 45000.0, "total_withdrawn": 35000.0, "wallet_balance": 10000.0},
        "editor_0c9564@example.com": {"total_earnings": 8000.0, "total_withdrawn": 5000.0, "wallet_balance": 3000.0},
        "editor_c38cc0@example.com": {"total_earnings": 45000.0, "total_withdrawn": 10000.0, "wallet_balance": 35000.0},
        "editor_cbba33@example.com": {"total_earnings": 2000.0, "total_withdrawn": 8000.0, "wallet_balance": 12000.0},
        "dhruv@outclipped.com": {"total_earnings": 25000.0, "total_withdrawn": 15000.0, "wallet_balance": 10000.0},
    }

    for e in editors:
        email = e.get("email")
        config = editor_configs.get(email, {"total_earnings": 0.0, "total_withdrawn": 0.0, "wallet_balance": 0.0})
        supabase.table("users").update({
            "wallet_balance": config["wallet_balance"],
            "total_earnings": config["total_earnings"],
            "total_withdrawn": config["total_withdrawn"]
        }).eq("user_id", e["user_id"]).execute()

    # Helper to find user ID by email
    def get_uid(email):
        for u in users:
            if u.get("email") == email:
                return u["user_id"]
        return None

    # Get some specific user IDs for links
    creator_debug = get_uid("creator@debug.test") or creators[0]["user_id"]
    creator_test1 = get_uid("creator_830c23@example.com") or creators[0]["user_id"]
    creator_test2 = get_uid("creator_31a8c0@example.com") or creators[0]["user_id"]
    creator_test3 = get_uid("user_3da2c3e8@test.com") or creators[0]["user_id"]
    creator_test4 = get_uid("user_d9737850@test.com") or creators[0]["user_id"]

    ed_debug = get_uid("editor@debug.test") or editors[0]["user_id"]
    ed_test1 = get_uid("editor_0c9564@example.com") or editors[0]["user_id"]
    ed_test2 = get_uid("editor_c38cc0@example.com") or editors[0]["user_id"]
    ed_test3 = get_uid("editor_cbba33@example.com") or editors[0]["user_id"]
    ed_test4 = get_uid("editor_a435ed@example.com") or editors[0]["user_id"]
    ed_dhruv = get_uid("dhruv@outclipped.com") or editors[0]["user_id"]

    # 4. Create campaigns
    now = datetime.now(timezone.utc)
    
    campaigns = [
        # Campaign 1: Small Active Campaign (Bounty: 2000)
        {
            "campaign_id": "camp_small_active",
            "title": "Small Active Shorts Challenge",
            "creator_id": creator_debug,
            "bounty_pool": 2000.0,
            "status": "ACTIVE",
            "escrow_funded": True,
            "escrow_order_id": None,
            "start_date": (now - timedelta(days=5)).date().isoformat(),
            "end_date": (now + timedelta(days=10)).date().isoformat(),
            "created_at": now_iso()
        },
        # Campaign 2: Small Completed Campaign (Bounty: 2000)
        {
            "campaign_id": "camp_small_completed",
            "title": "Small Retro Edit (Completed)",
            "creator_id": creator_test1,
            "bounty_pool": 2000.0,
            "status": "COMPLETED",
            "escrow_funded": True,
            "escrow_order_id": "TXN_SMALL_COMP",
            "start_date": (now - timedelta(days=30)).date().isoformat(),
            "end_date": (now - timedelta(days=10)).date().isoformat(),
            "created_at": now_iso(),
            "published_at": now_iso()
        },
        # Campaign 3: Medium Active Campaign (Bounty: 10000)
        {
            "campaign_id": "camp_medium_active",
            "title": "Medium Tech Unboxing Campaign",
            "creator_id": creator_test2,
            "bounty_pool": 10000.0,
            "status": "ACTIVE",
            "escrow_funded": True,
            "escrow_order_id": None,
            "start_date": (now - timedelta(days=2)).date().isoformat(),
            "end_date": (now + timedelta(days=15)).date().isoformat(),
            "created_at": now_iso()
        },
        # Campaign 4: Medium Pending Funding Campaign (Bounty: 10000)
        {
            "campaign_id": "camp_medium_pending_funding",
            "title": "Medium Vlog Edit (Pending Funding)",
            "creator_id": creator_test3,
            "bounty_pool": 10000.0,
            "status": "PENDING_PAYMENT",
            "escrow_funded": False,
            "escrow_order_id": "TXN_PENDING_10K_REF",
            "start_date": (now + timedelta(days=2)).date().isoformat(),
            "end_date": (now + timedelta(days=20)).date().isoformat(),
            "created_at": now_iso()
        },
        # Campaign 5: Medium Pending Settlement Campaign (Bounty: 10000)
        {
            "campaign_id": "camp_medium_pending_settle",
            "title": "Medium Gaming Clips (Pending Settlement)",
            "creator_id": creator_test4,
            "bounty_pool": 10000.0,
            "status": "ACTIVE",
            "escrow_funded": True,
            "escrow_order_id": "TXN_SETTLE_10K",
            "start_date": (now - timedelta(days=20)).date().isoformat(),
            "end_date": (now - timedelta(days=1)).date().isoformat(),
            "created_at": now_iso()
        },
        # Campaign 6: Large Active Campaign (Bounty: 50000)
        {
            "campaign_id": "camp_large_active",
            "title": "Mega Product Launch Campaign",
            "creator_id": creator_debug,
            "bounty_pool": 50000.0,
            "status": "ACTIVE",
            "escrow_funded": True,
            "escrow_order_id": None,
            "start_date": (now - timedelta(days=4)).date().isoformat(),
            "end_date": (now + timedelta(days=20)).date().isoformat(),
            "created_at": now_iso()
        },
        # Campaign 7: Large Completed Campaign (Bounty: 50000)
        {
            "campaign_id": "camp_large_completed",
            "title": "Large Fashion Show Compilation",
            "creator_id": creator_test1,
            "bounty_pool": 50000.0,
            "status": "COMPLETED",
            "escrow_funded": True,
            "escrow_order_id": "TXN_LARGE_COMP",
            "start_date": (now - timedelta(days=25)).date().isoformat(),
            "end_date": (now - timedelta(days=5)).date().isoformat(),
            "created_at": now_iso(),
            "published_at": now_iso()
        }
    ]

    for camp in campaigns:
        supabase.table("campaigns").insert(camp).execute()
    print(f"Created {len(campaigns)} campaigns.")

    # 5. Populate participations and clips
    print("Seeding participations, clips, and payouts...")

    # Campaign 1: Small Active
    parts_small_active = [
        {"participation_id": "part_sa_1", "campaign_id": "camp_small_active", "editor_id": ed_debug, "joined_at": now_iso(), "total_points": 270.0, "payout_status": "PENDING"},
        {"participation_id": "part_sa_2", "campaign_id": "camp_small_active", "editor_id": ed_test1, "joined_at": now_iso(), "total_points": 80.0, "payout_status": "PENDING"}
    ]
    for p in parts_small_active:
        supabase.table("participations").insert(p).execute()

    clips_small_active = [
        {"clip_id": "clip_sa_1", "campaign_id": "camp_small_active", "editor_id": ed_debug, "views": 1200, "ocv": 15.0, "points": 120.0, "clip_url": "https://youtube.com/shorts/sa_1", "submitted_at": now_iso()},
        {"clip_id": "clip_sa_2", "campaign_id": "camp_small_active", "editor_id": ed_debug, "views": 1500, "ocv": 18.0, "points": 150.0, "clip_url": "https://youtube.com/shorts/sa_2", "submitted_at": now_iso()},
        {"clip_id": "clip_sa_3", "campaign_id": "camp_small_active", "editor_id": ed_test1, "views": 800, "ocv": 10.0, "points": 80.0, "clip_url": "https://youtube.com/shorts/sa_3", "submitted_at": now_iso()}
    ]
    for c in clips_small_active:
        supabase.table("clips").insert(c).execute()

    # Campaign 2: Small Completed
    parts_small_completed = [
        {"participation_id": "part_sc_1", "campaign_id": "camp_small_completed", "editor_id": ed_debug, "joined_at": now_iso(), "total_points": 150.0, "rank": 1, "reward_share_pct": 60.0, "payout_amount": 1020.0, "payout_status": "COMPLETED", "payment_reference": "UTR_SETTLE_1", "paid_at": now_iso()},
        {"participation_id": "part_sc_2", "campaign_id": "camp_small_completed", "editor_id": ed_test1, "joined_at": now_iso(), "total_points": 100.0, "rank": 2, "reward_share_pct": 40.0, "payout_amount": 680.0, "payout_status": "COMPLETED", "payment_reference": "UTR_SETTLE_2", "paid_at": now_iso()}
    ]
    for p in parts_small_completed:
        supabase.table("participations").insert(p).execute()

    clips_small_completed = [
        {"clip_id": "clip_sc_1", "campaign_id": "camp_small_completed", "editor_id": ed_debug, "views": 1500, "ocv": 15.0, "points": 150.0, "clip_url": "https://youtube.com/shorts/sc_1", "submitted_at": now_iso()},
        {"clip_id": "clip_sc_2", "campaign_id": "camp_small_completed", "editor_id": ed_test1, "views": 1000, "ocv": 10.0, "points": 100.0, "clip_url": "https://youtube.com/shorts/sc_2", "submitted_at": now_iso()}
    ]
    for c in clips_small_completed:
        supabase.table("clips").insert(c).execute()

    # Campaign 3: Medium Active
    parts_med_active = [
        {"participation_id": "part_ma_1", "campaign_id": "camp_medium_active", "editor_id": ed_test2, "joined_at": now_iso(), "total_points": 450.0, "payout_status": "PENDING"},
        {"participation_id": "part_ma_2", "campaign_id": "camp_medium_active", "editor_id": ed_test3, "joined_at": now_iso(), "total_points": 300.0, "payout_status": "PENDING"}
    ]
    for p in parts_med_active:
        supabase.table("participations").insert(p).execute()

    clips_med_active = [
        {"clip_id": "clip_ma_1", "campaign_id": "camp_medium_active", "editor_id": ed_test2, "views": 4500, "ocv": 45.0, "points": 450.0, "clip_url": "https://youtube.com/shorts/ma_1", "submitted_at": now_iso()},
        {"clip_id": "clip_ma_2", "campaign_id": "camp_medium_active", "editor_id": ed_test3, "views": 3000, "ocv": 30.0, "points": 300.0, "clip_url": "https://youtube.com/shorts/ma_2", "submitted_at": now_iso()}
    ]
    for c in clips_med_active:
        supabase.table("clips").insert(c).execute()

    # Campaign 5: Medium Pending Settle
    parts_med_settle = [
        {"participation_id": "part_ms_1", "campaign_id": "camp_medium_pending_settle", "editor_id": ed_debug, "joined_at": now_iso(), "total_points": 200.0, "payout_amount": 0.0, "payout_status": "PENDING"},
        {"participation_id": "part_ms_2", "campaign_id": "camp_medium_pending_settle", "editor_id": ed_test1, "joined_at": now_iso(), "total_points": 100.0, "payout_amount": 0.0, "payout_status": "PENDING"}
    ]
    for p in parts_med_settle:
        supabase.table("participations").insert(p).execute()

    clips_med_settle = [
        {"clip_id": "clip_ms_1", "campaign_id": "camp_medium_pending_settle", "editor_id": ed_debug, "views": 2000, "ocv": 20.0, "points": 200.0, "clip_url": "https://youtube.com/shorts/ms_1", "submitted_at": now_iso()},
        {"clip_id": "clip_ms_2", "campaign_id": "camp_medium_pending_settle", "editor_id": ed_test1, "views": 1000, "ocv": 10.0, "points": 100.0, "clip_url": "https://youtube.com/shorts/ms_2", "submitted_at": now_iso()}
    ]
    for c in clips_med_settle:
        supabase.table("clips").insert(c).execute()

    # Campaign 6: Large Active
    parts_large_active = [
        {"participation_id": "part_la_1", "campaign_id": "camp_large_active", "editor_id": ed_debug, "joined_at": now_iso(), "total_points": 1200.0, "payout_status": "PENDING"},
        {"participation_id": "part_la_2", "campaign_id": "camp_large_active", "editor_id": ed_test2, "joined_at": now_iso(), "total_points": 800.0, "payout_status": "PENDING"},
        {"participation_id": "part_la_3", "campaign_id": "camp_large_active", "editor_id": ed_test4, "joined_at": now_iso(), "total_points": 400.0, "payout_status": "PENDING"}
    ]
    for p in parts_large_active:
        supabase.table("participations").insert(p).execute()

    clips_large_active = [
        {"clip_id": "clip_la_1", "campaign_id": "camp_large_active", "editor_id": ed_debug, "views": 12000, "ocv": 120.0, "points": 1200.0, "clip_url": "https://youtube.com/shorts/la_1", "submitted_at": now_iso()},
        {"clip_id": "clip_la_2", "campaign_id": "camp_large_active", "editor_id": ed_test2, "views": 8000, "ocv": 80.0, "points": 800.0, "clip_url": "https://youtube.com/shorts/la_2", "submitted_at": now_iso()},
        {"clip_id": "clip_la_3", "campaign_id": "camp_large_active", "editor_id": ed_test4, "views": 4000, "ocv": 40.0, "points": 400.0, "clip_url": "https://youtube.com/shorts/la_3", "submitted_at": now_iso()}
    ]
    for c in clips_large_active:
        supabase.table("clips").insert(c).execute()

    # Campaign 7: Large Completed
    parts_large_completed = [
        {"participation_id": "part_lc_1", "campaign_id": "camp_large_completed", "editor_id": ed_test2, "joined_at": now_iso(), "total_points": 900.0, "rank": 1, "reward_share_pct": 75.0, "payout_amount": 31875.0, "payout_status": "COMPLETED", "payment_reference": "UTR_LARGESETTLE_1", "paid_at": now_iso()},
        {"participation_id": "part_lc_2", "campaign_id": "camp_large_completed", "editor_id": ed_test3, "joined_at": now_iso(), "total_points": 300.0, "rank": 2, "reward_share_pct": 25.0, "payout_amount": 10625.0, "payout_status": "COMPLETED", "payment_reference": "UTR_LARGESETTLE_2", "paid_at": now_iso()}
    ]
    for p in parts_large_completed:
        supabase.table("participations").insert(p).execute()

    clips_large_completed = [
        {"clip_id": "clip_lc_1", "campaign_id": "camp_large_completed", "editor_id": ed_test2, "views": 9000, "ocv": 90.0, "points": 900.0, "clip_url": "https://youtube.com/shorts/lc_1", "submitted_at": now_iso()},
        {"clip_id": "clip_lc_2", "campaign_id": "camp_large_completed", "editor_id": ed_test3, "views": 3000, "ocv": 30.0, "points": 300.0, "clip_url": "https://youtube.com/shorts/lc_2", "submitted_at": now_iso()}
    ]
    for c in clips_large_completed:
        supabase.table("clips").insert(c).execute()

    # 6. Create withdrawals
    print("Creating withdrawals...")
    withdrawals = [
        # Editor 1
        {"withdrawal_id": "wd_ed1_1", "user_id": ed_debug, "amount": 20000.0, "status": "PAID", "razorpay_payout_id": "pout_ed1_1", "created_at": now_iso()},
        {"withdrawal_id": "wd_ed1_2", "user_id": ed_debug, "amount": 15000.0, "status": "PAID", "razorpay_payout_id": "pout_ed1_2", "created_at": now_iso()},
        {"withdrawal_id": "wd_ed1_3", "user_id": ed_debug, "amount": 5000.0, "status": "PENDING", "created_at": now_iso()},
        {"withdrawal_id": "wd_ed1_4", "user_id": ed_debug, "amount": 2000.0, "status": "REJECTED", "razorpay_payout_id": "REJECTED", "created_at": now_iso()},
        # Editor 2
        {"withdrawal_id": "wd_ed2_1", "user_id": ed_test1, "amount": 5000.0, "status": "PAID", "razorpay_payout_id": "pout_ed2_1", "created_at": now_iso()},
        {"withdrawal_id": "wd_ed2_2", "user_id": ed_test1, "amount": 3000.0, "status": "PENDING", "created_at": now_iso()},
        # Editor 3
        {"withdrawal_id": "wd_ed3_1", "user_id": ed_test2, "amount": 10000.0, "status": "PAID", "razorpay_payout_id": "pout_ed3_1", "created_at": now_iso()},
        # Editor 4
        {"withdrawal_id": "wd_ed4_1", "user_id": ed_test3, "amount": 8000.0, "status": "PAID", "razorpay_payout_id": "pout_ed4_1", "created_at": now_iso()},
        {"withdrawal_id": "wd_ed4_2", "user_id": ed_test3, "amount": 1000.0, "status": "REJECTED", "razorpay_payout_id": "REJECTED", "created_at": now_iso()},
        # Dhruv Bangera
        {"withdrawal_id": "wd_dhruv_1", "user_id": ed_dhruv, "amount": 15000.0, "status": "PAID", "razorpay_payout_id": "pout_dhruv_1", "created_at": now_iso()},
        {"withdrawal_id": "wd_dhruv_2", "user_id": ed_dhruv, "amount": 3000.0, "status": "PENDING", "created_at": now_iso()}
    ]

    for wd in withdrawals:
        supabase.table("withdrawals").insert(wd).execute()
    print(f"Created {len(withdrawals)} withdrawals.")

    print("--- SEEDING COMPLETED SUCCESSFULLY ---")

seed_data()
