import os
import sys
import uuid
import datetime
import requests
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
backend_env_path = Path(__file__).parent.parent / 'backend' / '.env'
load_dotenv(dotenv_path=backend_env_path)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
API_BASE = 'http://127.0.0.1:8000/api'

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in backend/.env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Track created IDs for cleanup
created_users = []
created_sessions = []
created_campaigns = []

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def create_test_user(role: str):
    user_id = new_id('user')
    email = f"test_{role.lower()}_{uuid.uuid4().hex[:6]}@example.com"
    username = f"test_{role.lower()}_{uuid.uuid4().hex[:4]}"
    user = {
        "user_id": user_id,
        "email": email,
        "name": f"Test {role}",
        "username": username,
        "avatar_url": "",
        "role": role,
        "bio": "",
        "lifetime_points": 0,
        "wallet_balance": 0,
        "total_earnings": 0,
        "total_withdrawn": 0,
        "active_platforms": [],
        "is_earnings_public": False,
        "payout_upi": "",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    
    res = supabase.table('users').insert(user).execute()
    if not res.data:
        raise Exception(f"Failed to create {role} user: {res}")
    created_users.append(user_id)
    
    # Create session token
    token = "test_token_" + uuid.uuid4().hex
    expires = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).isoformat()
    sess = {
        "session_token": token,
        "user_id": user_id,
        "expires_at": expires,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    supabase.table('sessions').insert(sess).execute()
    created_sessions.append(token)
    
    return {
        "user_id": user_id,
        "token": token,
        "email": email,
        "username": username
    }

def api_call(method, path, token, json_data=None, params=None):
    url = f"{API_BASE}{path}"
    cookies = {"session_token": token}
    headers = {"Content-Type": "application/json"}
    resp = requests.request(method, url, json=json_data, params=params, cookies=cookies, headers=headers)
    return resp

def run_tests():
    print("=" * 60)
    print("RUNNING MANUAL APPROVAL WORKFLOW TESTS")
    print("=" * 60)

    # 1. Create test roles
    creator = create_test_user('CREATOR')
    editor = create_test_user('EDITOR')
    admin = create_test_user('ADMIN')

    print(f"Created users: Creator={creator['user_id']}, Editor={editor['user_id']}, Admin={admin['user_id']}")

    # 2. Creator creates a campaign (draft)
    campaign_payload = {
        "title": "Approval Workflow Test Campaign",
        "content_type": "VIDEO",
        "description": "A campaign to test the manual approval workflow",
        "brief": {},
        "assets": {},
        "bounty_pool": 2000,
        "max_clips_per_editor": 3,
        "start_date": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat(),
        "end_date": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10)).isoformat(),
        "editor_pool_pct": 50,
        "performance_pool_pct": 30,
        "bonus_pool_pct": 20,
        "clip_guidelines": "Follow guidelines",
        "source_video_urls": []
    }
    
    print("\n[Step 1] Creating Campaign as Creator...")
    resp = api_call('POST', '/campaigns', creator['token'], json_data=campaign_payload)
    assert resp.status_code in (200, 201), f"Failed to create campaign: {resp.text}"
    campaign = resp.json()
    campaign_id = campaign.get('campaign_id')
    created_campaigns.append(campaign_id)
    print(f"Campaign created: ID={campaign_id}, Status={campaign.get('status')}")
    assert campaign.get('status') == 'DRAFT', "New campaign status is not DRAFT"

    # 3. Verify editor cannot see DRAFT campaign
    print("\n[Step 2] Verifying Editor visibility for DRAFT...")
    resp = api_call('GET', '/campaigns', editor['token'])
    assert resp.status_code == 200, f"Editor failed to list campaigns: {resp.text}"
    editor_campaigns = resp.json()
    found = any(c.get('campaign_id') == campaign_id for c in editor_campaigns)
    print(f"Editor sees campaign: {found} (Expected: False)")
    assert not found, "Editor is able to see DRAFT campaign"

    # 4. Creator publishes campaign
    print("\n[Step 3] Publishing Campaign (No Payment Proof / UTR required)...")
    resp = api_call('POST', f'/campaigns/{campaign_id}/publish', creator['token'])
    assert resp.status_code == 200, f"Failed to publish campaign: {resp.text}"
    publish_result = resp.json()
    print(f"Publish response: {publish_result}")
    assert publish_result.get('status') == 'PENDING_APPROVAL', "Published campaign status is not PENDING_APPROVAL"

    # Verify status via API
    resp_detail = api_call('GET', f'/campaigns/{campaign_id}', creator['token'])
    assert resp_detail.status_code == 200
    db_campaign = resp_detail.json()
    print(f"Campaign status via API: {db_campaign.get('status')}")
    assert db_campaign.get('status') == 'PENDING_APPROVAL', "Campaign status is not PENDING_APPROVAL"

    # 5. Verify editor cannot see PENDING_APPROVAL campaign
    print("\n[Step 4] Verifying Editor visibility for PENDING_APPROVAL...")
    resp = api_call('GET', '/campaigns', editor['token'])
    assert resp.status_code == 200
    editor_campaigns = resp.json()
    found = any(c.get('campaign_id') == campaign_id for c in editor_campaigns)
    print(f"Editor sees campaign: {found} (Expected: False)")
    assert not found, "Editor is able to see PENDING_APPROVAL campaign"

    # 6. Verify admin can see it in pending campaigns list
    print("\n[Step 5] Verifying Admin Pending Campaigns View...")
    resp = api_call('GET', '/admin/pending-campaigns', admin['token'])
    assert resp.status_code == 200, f"Admin failed to fetch pending: {resp.text}"
    pending_list = resp.json()
    pending_ids = [c.get('campaign_id') for c in pending_list]
    print(f"Pending list campaign IDs: {pending_ids}")
    assert campaign_id in pending_ids, "Campaign is not in admin pending list"

    # 7. Admin approves campaign
    print("\n[Step 6] Admin Approves Campaign...")
    approval_payload = {"decision": "APPROVE"}
    resp = api_call('POST', f'/admin/campaigns/{campaign_id}/approval-decision', admin['token'], json_data=approval_payload)
    assert resp.status_code == 200, f"Admin approval failed: {resp.text}"
    print(f"Approval response: {resp.json()}")
    assert resp.json().get('status') == 'ACTIVE', "Approved campaign status is not ACTIVE"

    # Verify database state (status=ACTIVE, escrow_funded=True)
    db_campaign = supabase.table('campaigns').select('*').eq('campaign_id', campaign_id).single().execute().data
    print(f"Approved campaign status in DB: {db_campaign.get('status')}, Escrow Funded: {db_campaign.get('escrow_funded')}")
    assert db_campaign.get('status') == 'ACTIVE', "Status in DB not ACTIVE after approval"
    assert db_campaign.get('escrow_funded') is True, "escrow_funded not True after approval"

    # 8. Verify editor CAN now see the campaign
    print("\n[Step 7] Verifying Editor visibility for ACTIVE campaign...")
    resp = api_call('GET', '/campaigns', editor['token'])
    assert resp.status_code == 200
    editor_campaigns = resp.json()
    found = any(c.get('campaign_id') == campaign_id for c in editor_campaigns)
    print(f"Editor sees campaign: {found} (Expected: True)")
    assert found, "Editor cannot see ACTIVE campaign"

    # 9. Test Campaign Rejection Flow
    print("\n[Step 8] Testing Campaign Rejection flow...")
    # Create another campaign
    resp = api_call('POST', '/campaigns', creator['token'], json_data=campaign_payload)
    campaign2_id = resp.json().get('campaign_id')
    created_campaigns.append(campaign2_id)
    
    # Publish it
    resp = api_call('POST', f'/campaigns/{campaign2_id}/publish', creator['token'])
    assert resp.status_code == 200
    
    # Admin rejects it
    rejection_payload = {"decision": "REJECT"}
    resp = api_call('POST', f'/admin/campaigns/{campaign2_id}/approval-decision', admin['token'], json_data=rejection_payload)
    assert resp.status_code == 200
    print(f"Rejection response: {resp.json()}")
    assert resp.json().get('status') == 'REJECTED', "Rejected campaign status is not REJECTED"
    
    # Verify status via API
    resp_detail2 = api_call('GET', f'/campaigns/{campaign2_id}', creator['token'])
    assert resp_detail2.status_code == 200
    db_campaign2 = resp_detail2.json()
    print(f"Rejected campaign status via API: {db_campaign2.get('status')}")
    assert db_campaign2.get('status') == 'REJECTED', "Status is not REJECTED after rejection"
    
    # Verify editor cannot see REJECTED campaign
    resp = api_call('GET', '/campaigns', editor['token'])
    assert resp.status_code == 200
    found = any(c.get('campaign_id') == campaign2_id for c in resp.json())
    print(f"Editor sees rejected campaign: {found} (Expected: False)")
    assert not found, "Editor is able to see REJECTED campaign"

    print("\nALL WORKFLOW TESTS PASSED SUCCESSFULLY!")

def cleanup():
    print("\nCleaning up created test records...")
    # Delete campaigns
    if created_campaigns:
        res = supabase.table('campaigns').delete().in_('campaign_id', created_campaigns).execute()
        print(f"Deleted {len(created_campaigns)} campaigns.")
    # Delete sessions
    if created_sessions:
        res = supabase.table('sessions').delete().in_('session_token', created_sessions).execute()
        print(f"Deleted {len(created_sessions)} sessions.")
    # Delete users
    if created_users:
        res = supabase.table('users').delete().in_('user_id', created_users).execute()
        print(f"Deleted {len(created_users)} users.")

if __name__ == '__main__':
    try:
        run_tests()
    except Exception as e:
        print(f"\nTEST RUN FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()
