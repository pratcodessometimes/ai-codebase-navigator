import os
import sys
from dotenv import load_dotenv
from fastapi.testclient import TestClient

WORKSPACE_DIR = r"c:\\Users\\bange\\OneDrive\\Desktop\\coding\\outclipped\\emergent-2nd-take"
sys.path.insert(0, WORKSPACE_DIR)

load_dotenv("backend/.env")

from backend.server import app, supabase

client = TestClient(app, raise_server_exceptions=False)

# Mock tokens for E2E testing
TOKEN_CREATOR = "token_e2e_creator"
TOKEN_ADMIN = "token_e2e_admin"
TOKEN_EDITOR = "token_e2e_editor_1"

CREATOR_ID = "e2e_test_creator"
EDITOR_ID = "e2e_test_editor_1"
ADMIN_ID = "e2e_test_admin"

def clean_database():
    supabase.table("sessions").delete().in_("user_id", [CREATOR_ID, EDITOR_ID, ADMIN_ID]).execute()
    camps = supabase.table("campaigns").select("campaign_id").eq("creator_id", CREATOR_ID).execute().data or []
    camp_ids = [c["campaign_id"] for c in camps]
    if camp_ids:
        supabase.table("clips").delete().in_("campaign_id", camp_ids).execute()
        supabase.table("participations").delete().in_("campaign_id", camp_ids).execute()
        supabase.table("campaigns").delete().in_("campaign_id", camp_ids).execute()
    supabase.table("withdrawals").delete().in_("user_id", [EDITOR_ID]).execute()
    supabase.table("users").delete().in_("user_id", [CREATOR_ID, EDITOR_ID, ADMIN_ID]).execute()

def setup_users(creator_bal=20000.0, editor_bal=0.0):
    users = [
        {"user_id": CREATOR_ID, "email": "creator@e2e.test", "name": "E2E Creator", "username": "e2e_creator", "role": "CREATOR", "wallet_balance": creator_bal, "total_earnings": 0.0},
        {"user_id": EDITOR_ID, "email": "editor1@e2e.test", "name": "E2E Editor 1", "username": "e2e_editor_1", "role": "EDITOR", "wallet_balance": editor_bal, "total_earnings": editor_bal},
        {"user_id": ADMIN_ID, "email": "admin@e2e.test", "name": "E2E Admin", "username": "e2e_admin", "role": "ADMIN", "wallet_balance": 0.0, "total_earnings": 0.0},
    ]
    for u in users:
        supabase.table("users").insert(u).execute()
        
    expires = "2029-12-31T23:59:59Z"
    sessions = [
        {"session_token": TOKEN_CREATOR, "user_id": CREATOR_ID, "expires_at": expires},
        {"session_token": TOKEN_EDITOR, "user_id": EDITOR_ID, "expires_at": expires},
        {"session_token": TOKEN_ADMIN, "user_id": ADMIN_ID, "expires_at": expires},
    ]
    for s in sessions:
        supabase.table("sessions").insert(s).execute()

def test_money_flows():
    print("--- STARTING MONEY FLOW QA CHECKS ---")
    
    # 1. Test creator wallet deduction on campaign approval
    clean_database()
    setup_users(creator_bal=25000.0)
    
    # Create campaign (bounty: 15,000)
    camp_payload = {
        "title": "QA Test Campaign",
        "content_type": "YOUTUBE_SHORTS",
        "description": "Bounty pool check",
        "bounty_pool": 15000.0,
        "max_clips_per_editor": 5,
        "start_date": "2026-06-25",
        "end_date": "2026-07-05",
    }
    resp = client.post("/api/campaigns", json=camp_payload, cookies={"session_token": TOKEN_CREATOR})
    assert resp.status_code == 200, resp.text
    campaign_id = resp.json()["campaign_id"]
    
    # Publish campaign
    resp = client.post(f"/api/campaigns/{campaign_id}/publish", json={"payment_reference": "UTR_QA_1"}, cookies={"session_token": TOKEN_CREATOR})
    assert resp.status_code == 200
    
    # Approve funding (should deduct ₹15,000 from creator wallet: 25,000 -> 10,000)
    resp = client.post(f"/api/admin/campaigns/{campaign_id}/funding-decision", json={"decision": "APPROVE"}, cookies={"session_token": TOKEN_ADMIN})
    assert resp.status_code == 200
    
    creator = supabase.table("users").select("wallet_balance").eq("user_id", CREATOR_ID).single().execute().data
    print(f"Creator balance after approval: {creator['wallet_balance']} (Expected: 10000.0)")
    assert float(creator["wallet_balance"]) == 10000.0
    
    # 2. Test duplicate campaign approval (should raise 400)
    resp = client.post(f"/api/admin/campaigns/{campaign_id}/funding-decision", json={"decision": "APPROVE"}, cookies={"session_token": TOKEN_ADMIN})
    print(f"Duplicate approval status code: {resp.status_code} (Expected: 400)")
    print(f"Duplicate approval response body: {resp.text}")
    assert resp.status_code == 400
    
    # 3. Test creator refund on campaign rejection/cancellation
    # Transition to CANCELLED (should refund ₹15,000: 10,000 -> 25,000)
    resp = client.post(f"/api/admin/campaigns/{campaign_id}/status", json={"status": "CANCELLED"}, cookies={"session_token": TOKEN_ADMIN})
    assert resp.status_code == 200
    
    creator = supabase.table("users").select("wallet_balance").eq("user_id", CREATOR_ID).single().execute().data
    print(f"Creator balance after cancellation: {creator['wallet_balance']} (Expected: 25000.0)")
    assert float(creator["wallet_balance"]) == 25000.0
    
    # 4. Test creator insufficient balance error
    # Create another campaign (bounty: 30,000)
    camp_payload["bounty_pool"] = 30000.0
    resp = client.post("/api/campaigns", json=camp_payload, cookies={"session_token": TOKEN_CREATOR})
    campaign_id2 = resp.json()["campaign_id"]
    
    resp = client.post(f"/api/campaigns/{campaign_id2}/publish", json={"payment_reference": "UTR_QA_2"}, cookies={"session_token": TOKEN_CREATOR})
    
    # Approve (creator has 25,000 but bounty is 30,000 -> should raise 400)
    resp = client.post(f"/api/admin/campaigns/{campaign_id2}/funding-decision", json={"decision": "APPROVE"}, cookies={"session_token": TOKEN_ADMIN})
    print(f"Insufficient balance approval status code: {resp.status_code} (Expected: 400)")
    assert resp.status_code == 400
    assert "Insufficient creator wallet balance" in resp.json()["detail"]
    
    # 5. Test safe withdrawal approval when editor has NO pending participations
    # Editor starts with ₹5,000 wallet balance
    clean_database()
    setup_users(editor_bal=5000.0)
    
    # Request cashout of ₹3,000
    resp = client.post("/api/wallet/cashout", json={"amount": 3000.0}, cookies={"session_token": TOKEN_EDITOR})
    assert resp.status_code == 200
    wd_id = resp.json()["withdrawal"]["withdrawal_id"]
    
    # Editor has no pending participations. Admin approves withdrawal (should NOT crash!)
    resp = client.post(f"/api/admin/withdrawal-requests/{wd_id}/status", json={"status": "PAID", "payment_reference": "UTR_WD_QA"}, cookies={"session_token": TOKEN_ADMIN})
    print(f"Safe withdrawal approval status code: {resp.status_code} (Expected: 200)")
    assert resp.status_code == 200
    
    # Verify editor balances
    editor = supabase.table("users").select("wallet_balance,total_withdrawn").eq("user_id", EDITOR_ID).single().execute().data
    print(f"Editor wallet: {editor['wallet_balance']} (Expected: 2000.0)")
    print(f"Editor withdrawn: {editor['total_withdrawn']} (Expected: 3000.0)")
    assert float(editor["wallet_balance"]) == 2000.0
    assert float(editor["total_withdrawn"]) == 3000.0
    
    clean_database()
    print("--- ALL MONEY FLOW QA CHECKS PASSED ---")

if __name__ == "__main__":
    test_money_flows()
