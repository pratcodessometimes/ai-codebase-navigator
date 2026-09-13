import sys
import os
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

# Workspace root for imports
WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

# Load env vars
with open(os.path.join(WORKSPACE_DIR, "backend", ".env")) as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            os.environ[k.strip()] = v.strip()

from backend.server import app, supabase, now_iso

client = TestClient(app, raise_server_exceptions=True)

# IDs & tokens
CREATOR_ID = "e2e_test_creator"
EDITOR_1_ID = "e2e_test_editor_1"
EDITOR_2_ID = "e2e_test_editor_2"
ADMIN_ID = "e2e_test_admin"
TOKEN_CREATOR = "token_e2e_creator"
TOKEN_EDITOR_1 = "token_e2e_editor_1"
TOKEN_EDITOR_2 = "token_e2e_editor_2"
TOKEN_ADMIN = "token_e2e_admin"

class MockResponse:
    def __init__(self, data):
        self.data = data

def get_user_data(user_id: str) -> MockResponse:
    # wallet_balance, total_earnings, total_withdrawn
    u = supabase.table("users").select("wallet_balance,total_earnings").eq("user_id", user_id).single().execute().data
    wd = (
        supabase.table("withdrawals")
        .select("amount,status")
        .eq("user_id", user_id)
        .eq("status", "PAID")
        .execute()
    )
    total_w = sum(float(w["amount"] or 0) for w in (wd.data or []))
    u["total_withdrawn"] = total_w
    return MockResponse(u)

def clean_database():
    supabase.table("sessions").delete().in_("user_id", [CREATOR_ID, EDITOR_1_ID, EDITOR_2_ID, ADMIN_ID]).execute()
    camps = supabase.table("campaigns").select("campaign_id").eq("creator_id", CREATOR_ID).execute().data or []
    camp_ids = [c["campaign_id"] for c in camps]
    if camp_ids:
        supabase.table("clips").delete().in_("campaign_id", camp_ids).execute()
        supabase.table("participations").delete().in_("campaign_id", camp_ids).execute()
        supabase.table("campaigns").delete().in_("campaign_id", camp_ids).execute()
    # Delete clips & participations by editor_id just in case they were registered elsewhere
    supabase.table("clips").delete().in_("editor_id", [EDITOR_1_ID, EDITOR_2_ID]).execute()
    supabase.table("participations").delete().in_("editor_id", [EDITOR_1_ID, EDITOR_2_ID]).execute()
    supabase.table("withdrawals").delete().in_("user_id", [EDITOR_1_ID, EDITOR_2_ID]).execute()
    supabase.table("users").delete().in_("user_id", [CREATOR_ID, EDITOR_1_ID, EDITOR_2_ID, ADMIN_ID]).execute()

def setup_users():
    verified_channels = [{"channel_id": "UCcmV1rN_n79xld1cPti4QUA", "handle": "dhruv_bangera", "title": "Dhruv Bangera"}]
    users = [
        {"user_id": CREATOR_ID, "email": "creator@e2e.test", "name": "E2E Creator", "username": "e2e_creator", "role": "CREATOR", "wallet_balance": 20000.0, "total_earnings": 0.0, "created_at": now_iso()},
        {"user_id": EDITOR_1_ID, "email": "editor1@e2e.test", "name": "E2E Editor 1", "username": "e2e_editor_1", "role": "EDITOR", "wallet_balance": 0.0, "total_earnings": 0.0, "created_at": now_iso(), "verified_yt_channels": verified_channels},
        {"user_id": EDITOR_2_ID, "email": "editor2@e2e.test", "name": "E2E Editor 2", "username": "e2e_editor_2", "role": "EDITOR", "wallet_balance": 0.0, "total_earnings": 0.0, "created_at": now_iso(), "verified_yt_channels": verified_channels},
        {"user_id": ADMIN_ID, "email": "admin@e2e.test", "name": "E2E Admin", "username": "e2e_admin", "role": "ADMIN", "wallet_balance": 0.0, "total_earnings": 0.0, "created_at": now_iso()},
    ]
    for u in users:
        supabase.table("users").insert(u).execute()
    expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    sessions = [
        {"session_token": TOKEN_CREATOR, "user_id": CREATOR_ID, "expires_at": expires, "created_at": now_iso()},
        {"session_token": TOKEN_EDITOR_1, "user_id": EDITOR_1_ID, "expires_at": expires, "created_at": now_iso()},
        {"session_token": TOKEN_EDITOR_2, "user_id": EDITOR_2_ID, "expires_at": expires, "created_at": now_iso()},
        {"session_token": TOKEN_ADMIN, "user_id": ADMIN_ID, "expires_at": expires, "created_at": now_iso()},
    ]
    for s in sessions:
        supabase.table("sessions").insert(s).execute()

def test_e2e_flow():
    clean_database()
    try:
        setup_users()
        # 1. Create campaign
        payload = {
            "title": "E2E Money Flow Campaign",
            "content_type": "YOUTUBE_SHORTS",
            "description": "Testing new payout architecture",
            "bounty_pool": 10000.0,
            "max_clips_per_editor": 10,
            "start_date": "2026-06-22",
            "end_date": "2026-06-30",
        }
        resp = client.post("/api/campaigns", json=payload, cookies={"session_token": TOKEN_CREATOR})
        assert resp.status_code == 200, resp.text
        campaign_id = resp.json()["campaign_id"]

        # 2. Publish
        resp = client.post(f"/api/campaigns/{campaign_id}/publish", json={"payment_reference": "UTR_E2E_PUB"}, cookies={"session_token": TOKEN_CREATOR})
        assert resp.status_code == 200
        camp = supabase.table("campaigns").select("status,escrow_order_id").eq("campaign_id", campaign_id).single().execute()
        assert camp.data["status"] == "PENDING_PAYMENT"
        assert camp.data["escrow_order_id"] == "UTR_E2E_PUB"

        # 3. Admin approve funding
        resp = client.post(f"/api/admin/campaigns/{campaign_id}/funding-decision", json={"decision": "APPROVE"}, cookies={"session_token": TOKEN_ADMIN})
        assert resp.status_code == 200
        # Verify creator wallet balance decreased
        creator_post = supabase.table("users").select("wallet_balance").eq("user_id", CREATOR_ID).single().execute().data
        assert float(creator_post["wallet_balance"]) == 10000.0
        
        # Verify duplicate approval attempts are rejected
        resp_dup = client.post(f"/api/admin/campaigns/{campaign_id}/funding-decision", json={"decision": "APPROVE"}, cookies={"session_token": TOKEN_ADMIN})
        assert resp_dup.status_code == 400
        
        assert supabase.table("campaigns").select("escrow_funded").eq("campaign_id", campaign_id).single().execute().data["escrow_funded"] is True

        # 4. Activate
        resp = client.post(f"/api/admin/campaigns/{campaign_id}/status", json={"status": "ACTIVE"}, cookies={"session_token": TOKEN_ADMIN})
        assert resp.status_code == 200
        assert supabase.table("campaigns").select("status").eq("campaign_id", campaign_id).single().execute().data["status"] == "ACTIVE"

        # 5. Editors join
        resp = client.post(f"/api/campaigns/{campaign_id}/join", json={"youtube_channel": "@dhruv_bangera"}, cookies={"session_token": TOKEN_EDITOR_1})
        assert resp.status_code == 200
        part1 = resp.json()["participation_id"]
        resp = client.post(f"/api/campaigns/{campaign_id}/join", json={"youtube_channel": "@dhruv_bangera"}, cookies={"session_token": TOKEN_EDITOR_2})
        assert resp.status_code == 200
        part2 = resp.json()["participation_id"]

        # 6. Submit clips
        resp = client.post("/api/clips", json={"campaign_id": campaign_id, "platform": "YOUTUBE_SHORTS", "clip_url": "https://youtube.com/shorts/vid11111111"}, cookies={"session_token": TOKEN_EDITOR_1})
        assert resp.status_code == 200
        resp = client.post("/api/clips", json={"campaign_id": campaign_id, "platform": "YOUTUBE_SHORTS", "clip_url": "https://youtube.com/shorts/vid22222222"}, cookies={"session_token": TOKEN_EDITOR_2})
        assert resp.status_code == 200

        # 7. Settlement (credits wallets)
        resp = client.post(f"/api/admin/campaigns/{campaign_id}/start-settlement", cookies={"session_token": TOKEN_ADMIN})
        assert resp.status_code == 200
        p1 = supabase.table("participations").select("payout_amount,payout_status").eq("participation_id", part1).single().execute().data
        p2 = supabase.table("participations").select("payout_amount,payout_status").eq("participation_id", part2).single().execute().data
        assert float(p1["payout_amount"]) == 4250.0
        assert float(p2["payout_amount"]) == 4250.0
        assert p1["payout_status"] == "PENDING"
        assert p2["payout_status"] == "PENDING"
        # Wallets should already be credited
        ed1 = supabase.table("users").select("wallet_balance,total_earnings").eq("user_id", EDITOR_1_ID).single().execute().data
        ed2 = supabase.table("users").select("wallet_balance,total_earnings").eq("user_id", EDITOR_2_ID).single().execute().data
        assert float(ed1["wallet_balance"]) == 4250.0
        assert float(ed1["total_earnings"]) == 4250.0
        assert float(ed2["wallet_balance"]) == 4250.0
        assert float(ed2["total_earnings"]) == 4250.0

     # 8. Campaign should already be completed after settlement
        camp = (
            supabase.table("campaigns")
            .select("status")
            .eq("campaign_id", campaign_id)
            .single()
            .execute()
            .data
        )
        assert camp["status"] == "COMPLETED"

        # 9. Editor 1 requests withdrawal
        resp = client.post(
            "/api/wallet/cashout",
            json={"amount": 1000.0},
            cookies={"session_token": TOKEN_EDITOR_1},
        )
        assert resp.status_code == 200
        request_id = resp.json()["withdrawal"]["withdrawal_id"]
        
        # 10. Admin approves withdrawal
        resp = client.post(f"/api/admin/withdrawal-requests/{request_id}/status", json={"status": "PAID", "payment_reference": "UTR_WD1"}, cookies={"session_token": TOKEN_ADMIN})
        assert resp.status_code == 200
        # wallet decreased, total_withdrawn increased
        ed1_post = get_user_data(EDITOR_1_ID)
        assert float(ed1_post.data["wallet_balance"]) == 3250.0
        assert float(ed1_post.data["total_withdrawn"]) == 1000.0
        # withdrawal row updated
        wd_row = supabase.table("withdrawals").select("status,payment_reference").eq("withdrawal_id", request_id).single().execute().data
        assert wd_row["status"] == "PAID"
        assert wd_row["payment_reference"] == "UTR_WD1"
        # payment_reference mirrored onto participation
        part1_after_wd = supabase.table("participations").select("payment_reference").eq("participation_id", part1).single().execute().data
        assert part1_after_wd["payment_reference"] == "UTR_WD1"
        # duplicate approval rejected
        resp = client.post(f"/api/admin/withdrawal-requests/{request_id}/status", json={"status": "PAID", "payment_reference": "UTR_WD1"}, cookies={"session_token": TOKEN_ADMIN})
        assert resp.status_code == 400

        # 11. Editor 2 requests withdrawal and gets rejected
        resp = client.post("/api/wallet/cashout", json={"amount": 2000.0}, cookies={"session_token": TOKEN_EDITOR_2})
        
        assert resp.status_code == 200
        wd2 = resp.json()["withdrawal"]
        request_id2 = wd2["withdrawal_id"]
        # admin rejects
        resp = client.post(f"/api/admin/withdrawal-requests/{request_id2}/status", json={"status": "REJECTED"}, cookies={"session_token": TOKEN_ADMIN})
        assert resp.status_code == 200
        # wallet unchanged, total_withdrawn unchanged, participation payment_reference not set
        ed2_post = get_user_data(EDITOR_2_ID)
        assert float(ed2_post.data["wallet_balance"]) == 4250.0
        assert float(ed2_post.data["total_withdrawn"]) == 0.0
        part2_row = supabase.table("participations").select("payment_reference").eq("participation_id", part2).single().execute().data
        assert part2_row["payment_reference"] is None
    finally:
        clean_database()
