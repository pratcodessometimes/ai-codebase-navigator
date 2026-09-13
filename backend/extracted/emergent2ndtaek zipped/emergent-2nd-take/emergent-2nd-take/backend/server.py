client = """Outclip backend - merit-based bounty marketplace for short-form video editors.

Stack: FastAPI + MongoDB + Emergent Google OAuth + Emergent Object Storage + YouTube Data API v3.
Razorpay escrow & payouts are MOCKED for MVP.
"""
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Form, Cookie, Header, Query, Body
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os, io, uuid, logging, re, requests
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal

from typing import List, Optional, Any
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

api = APIRouter(prefix="/api")
# ---------------- Config ----------------
# MONGO_URL = os.environ['MONGO_URL']
# DB_NAME = os.environ['DB_NAME']

EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY')
APP_NAME = os.environ.get('APP_NAME', 'outclip')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
PLATFORM_FEE = float(os.environ.get('PLATFORM_FEE_PERCENT', '15'))

EMERGENT_AUTH_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"

# client = AsyncIOMotorClient(MONGO_URL)
# db = client[DB_NAME]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("outclip")

# ---------------- Storage ----------------
_storage_key: Optional[str] = None

def init_storage():
    global _storage_key
    if _storage_key:
        return _storage_key
    if not EMERGENT_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY missing")
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key, "Content-Type": content_type},
                        data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# ---------------- Helpers ----------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def map_db_campaign(c: dict) -> dict:
    if not c:
        return c
    status = c.get("status")
    escrow = c.get("escrow_order_id")
    if status == "PENDING_PAYMENT":
        c["status"] = "AWAITING_FUNDING"
    elif status == "DRAFT":
        if escrow == "PENDING_APPROVAL":
            c["status"] = "PENDING_APPROVAL"
        elif escrow == "REJECTED":
            c["status"] = "REJECTED"
        elif escrow == "CANCELLED":
            c["status"] = "CANCELLED"
        elif escrow == "PAUSED":
            c["status"] = "PAUSED"
    return c

def map_db_campaigns(camps: list) -> list:
    if not camps:
        return []
    return [map_db_campaign(c) for c in camps]

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.warning(f"Storage init failed (will retry on first upload): {e}")
    yield

app = FastAPI(title="Outclip API", lifespan=lifespan)

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def parse_dt(v):
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v
    if isinstance(v, str):
        d = datetime.fromisoformat(v.replace('Z', '+00:00'))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    return None

def clean_doc(d):
    if not d:
        return d
    d.pop('_id', None)
    return d

# ---------------- Points engine ----------------
def retention_mult(p: float) -> float:
    if p < 20: return 0.8
    if p < 35: return 1.0
    if p < 50: return 1.2
    if p < 65: return 1.4
    if p < 80: return 1.5
    return 1.6

def engagement_mult(p: float) -> float:
    if p < 1: return 0.95
    if p < 3: return 1.0
    if p < 5: return 1.1
    if p < 8: return 1.15
    if p < 12: return 1.2
    return 1.25

def hit_mult(views: int) -> float:
    if views >= 1_000_000: return 1.50
    if views >= 500_000:   return 1.25
    if views >= 100_000:   return 1.10
    if views >= 50_000:    return 1.05
    return 1.0

def calc_points(views: int, retention_pct: float, engagement_pct: float):
    rm = retention_mult(retention_pct)
    em = engagement_mult(engagement_pct)
    hm = hit_mult(views)
    pts = float(views) * rm * em * hm
    return {"points": round(pts, 2), "retention_mult": rm, "engagement_mult": em, "hit_mult": hm}

# ---------------- OCV (Outclip Value) Helper Functions ----------------
def get_retention_multiplier(retention_pct: float) -> float:
    if retention_pct < 25.0:
        return 0.60
    elif retention_pct < 40.0:
        return 0.80
    elif retention_pct < 55.0:
        return 0.95
    elif retention_pct < 70.0:
        return 1.00
    elif retention_pct < 85.0:
        return 1.15
    else:
        return 1.30

def get_engagement_multiplier(engagement_pct: float) -> float:
    if engagement_pct < 0.5:
        return 0.80
    elif engagement_pct < 1.0:
        return 0.90
    elif engagement_pct < 2.5:
        return 1.00
    elif engagement_pct < 4.0:
        return 1.10
    elif engagement_pct < 6.0:
        return 1.20
    else:
        return 1.30

def calculate_ocv(views: int, retention_pct: float, engagement_pct: float) -> float:
    ret_mult = get_retention_multiplier(retention_pct)
    eng_mult = get_engagement_multiplier(engagement_pct)
    ocv = float(views) * ret_mult * eng_mult
    return round(ocv, 2)

def enrich_campaign_ocv_metrics(campaign: dict) -> dict:
    if not campaign:
        return campaign
    bounty = float(campaign.get("bounty_pool") or 0.0)
    target = bounty * 10.0
    campaign["target_ocv"] = round(target, 2)
    if "total_ocv" not in campaign:
        try:
            c_clips_resp = supabase.table("clips").select("ocv").eq("campaign_id", campaign["campaign_id"]).eq("is_deleted", False).execute()
            c_clips = c_clips_resp.data or []
            campaign["total_ocv"] = round(sum(float(c.get("ocv") or 0.0) for c in c_clips), 2)
        except Exception:
            campaign["total_ocv"] = 0.0
    campaign["current_ocv"] = campaign["total_ocv"]
    if target > 0:
        campaign["progress_percentage"] = min(round((campaign["current_ocv"] / target) * 100.0, 2), 100.0)
    else:
        campaign["progress_percentage"] = 0.0
    return campaign

# ---------------- YouTube ----------------
YT_ID_RE = re.compile(r"(?:youtube\.com/(?:shorts/|watch\?v=)|youtu\.be/)([A-Za-z0-9_-]{11})")
YT_CHANNEL_HANDLE_RE = re.compile(r"youtube\.com/@([A-Za-z0-9._-]+)")
YT_CHANNEL_ID_RE = re.compile(r"youtube\.com/channel/(UC[A-Za-z0-9_-]{22})")

def yt_video_id(url: str) -> Optional[str]:
    m = YT_ID_RE.search(url or "")
    return m.group(1) if m else None

def fetch_youtube_channel(url_or_handle: str):
    """Parse a YouTube channel URL or @handle and return deterministic metadata.
    Supports:
    * https://www.youtube.com/@handle
    * https://www.youtube.com/channel/CHANNEL_ID
    * plain @handle (or handle without @)
    Returns a dict with keys: channel_id, title, handle, thumbnail.
    """
    if not url_or_handle:
        return None
    # Plain handle (no scheme)
    handle_match = re.fullmatch(r"@?([A-Za-z0-9._-]+)", url_or_handle.strip())
    if handle_match and not url_or_handle.startswith("http"):
        handle = handle_match.group(1)
        return {
            "channel_id": "",
            "title": f"Channel {handle}",
            "handle": f"@{handle}",
            "thumbnail": "https://yt3.ggpht.com/a/default-user=s800-c-k-c0x00ffffff-no-rj",
        }
    # Channel ID URL
    m_id = YT_CHANNEL_ID_RE.search(url_or_handle)
    if m_id:
        cid = m_id.group(1)
        return {
            "channel_id": cid,
            "title": f"Channel {cid}",
            "handle": "",
            "thumbnail": "https://yt3.ggpht.com/a/default-user=s800-c-k-c0x00ffffff-no-rj",
        }
    # Handle URL
    m_handle = YT_CHANNEL_HANDLE_RE.search(url_or_handle)
    if m_handle:
        handle = m_handle.group(1)
        return {
            "channel_id": "",
            "title": f"Channel {handle}",
            "handle": f"@{handle}",
            "thumbnail": "https://yt3.ggpht.com/a/default-user=s800-c-k-c0x00ffffff-no-rj",
        }
    return None
def fetch_youtube_stats(url: str):
    """Return deterministic mock YouTube video stats for testing.
    This bypasses external API calls and provides consistent data.
    """
    vid = yt_video_id(url)
    if not vid:
        return None
    # Return mock stats irrespective of API key
    return {
        "video_id": vid,
        "title": f"Mock Video {vid}",
        "channel_id": "UCcmV1rN_n79xld1cPti4QUA",
        "channel_title": "Dhruv Bangera",
        "views": 1500,
        "likes": 120,
        "comments": 15,
        "published_at": "2026-06-10T12:00:00Z",
    }

    vid = yt_video_id(url)
    if not vid:
        return None
    if not YOUTUBE_API_KEY:
        # Return mocked statistics so local testing/dev works without an API key
        return {
            "video_id": vid,
            "title": f"Mock Video {vid}",
            "channel_id": "UCcmV1rN_n79xld1cPti4QUA",  # Matches the seed database channel ID
            "channel_title": "Dhruv Bangera",
            "views": 1500,
            "likes": 120,
            "comments": 15,
            "published_at": "2026-06-10T12:00:00Z"
        }
    try:
        r = requests.get("https://www.googleapis.com/youtube/v3/videos",
                         params={"id": vid, "part": "statistics,snippet", "key": YOUTUBE_API_KEY},
                         timeout=15)
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            return None
        s = items[0].get("statistics", {})
        sn = items[0].get("snippet", {})
        return {
            "video_id": vid,
            "title": sn.get("title", ""),
            "channel_id": sn.get("channelId"),
            "channel_title": sn.get("channelTitle"),
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "comments": int(s.get("commentCount", 0)),
            "published_at": sn.get("publishedAt"),
        }
    except Exception as e:
        logger.warning(f"YouTube fetch failed: {e}")
        return None

def fetch_youtube_stats_batch(video_ids: list[str]) -> tuple[dict[str, dict], bool]:
    if not video_ids:
        return {}, True
    
    video_ids = video_ids[:50]
    
    if not YOUTUBE_API_KEY:
        res = {}
        for vid in video_ids:
            res[vid] = {
                "video_id": vid,
                "title": f"Mock Video {vid}",
                "channel_id": "UCcmV1rN_n79xld1cPti4QUA",
                "channel_title": "Dhruv Bangera",
                "views": 1500,
                "likes": 120,
                "comments": 15,
                "published_at": "2026-06-10T12:00:00Z"
            }
        return res, True
        
    try:
        ids_str = ",".join(video_ids)
        r = requests.get("https://www.googleapis.com/youtube/v3/videos",
                         params={"id": ids_str, "part": "statistics,snippet", "key": YOUTUBE_API_KEY},
                         timeout=15)
        r.raise_for_status()
        items = r.json().get("items", [])
        
        res = {}
        for item in items:
            vid = item.get("id")
            s = item.get("statistics", {})
            sn = item.get("snippet", {})
            res[vid] = {
                "video_id": vid,
                "title": sn.get("title", ""),
                "channel_id": sn.get("channelId"),
                "channel_title": sn.get("channelTitle"),
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
                "published_at": sn.get("publishedAt"),
            }
        return res, True
    except Exception as e:
        logger.warning(f"YouTube batch fetch failed: {e}")
        return {}, False

# ---------------- Auth ----------------
async def get_current_user(request: Request,
                           session_token: Optional[str] = Cookie(None),
                           authorization: Optional[str] = Header(None)):

    token = session_token

    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]

    print(f"DEBUG AUTH: Received cookie token={session_token}, auth_header={authorization}, final token={token}")

    if not token:
        print("DEBUG AUTH: No token found in request")
        raise HTTPException(401, "Not authenticated")
    print(f"DEBUG AUTH: [token value received] = {token}")
    sess_resp = (
        supabase.table("sessions")
        .select("*")
        .eq("session_token", token)
        .maybe_single()
        .execute()
    )
    print(f"DEBUG AUTH: [full sess_resp.data from sessions table lookup] = {sess_resp.data if sess_resp else None}")

    if not sess_resp or not sess_resp.data:
        print("DEBUG AUTH: Session token not found in sessions table (Failing request at sessions check)")
        raise HTTPException(401, "Not authenticated")

    user_resp = (
        supabase.table("users")
        .select("*")
        .eq("user_id", sess_resp.data["user_id"])
        .maybe_single()
        .execute()
    )
    print(f"DEBUG AUTH: [full user lookup result] = {user_resp.data if user_resp else None}")

    if not user_resp or not user_resp.data:
        print("DEBUG AUTH: User record not found for user_id (Failing request at user check)")
        raise HTTPException(401, "Not authenticated")

    user = user_resp.data
    user["wallet_balance"] = float(user.get("wallet_balance") or 0.0)
    user["total_earnings"] = float(user.get("total_earnings") or 0.0)
    user["total_withdrawn"] = float(user.get("total_withdrawn") or 0.0)
    return user
async def require_role(user: dict, role: str):
    if user.get("role") != role and user.get("role") != "ADMIN":
        raise HTTPException(403, f"Requires role: {role}")

# ---------------- Schemas ----------------
class SetRoleIn(BaseModel):
    role: str  # EDITOR | CREATOR

class UpdateProfileIn(BaseModel):
    username: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    active_platforms: Optional[List[str]] = None
    is_earnings_public: Optional[bool] = None
    payout_upi: Optional[str] = None
    avatar_url: Optional[str] = None
    socials: Optional[dict] = None  # {tiktok, youtube, instagram, twitter, discord}

class FeaturedClipIn(BaseModel):
    title: str
    platform: str  # YOUTUBE_SHORTS | TIKTOK | INSTAGRAM_REELS
    views: int = 0
    points: float = 0
    ocv: Optional[float] = 0.0
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None

class JoinCampaignIn(BaseModel):
    youtube_channel: str  # URL or @handle

class VerifyYouTubeIn(BaseModel):
    youtube_channel: str  # URL or @handle
class StartYouTubeVerificationIn(BaseModel):
    youtube_channel: str
class CashoutIn(BaseModel):
    amount: float

class CampaignStatusIn(BaseModel):
    status: str

class WithdrawalStatusIn(BaseModel):
    status: str
    payment_reference: Optional[str] = None

class PublishCampaignIn(BaseModel):
    payment_method: str = "BANK_TRANSFER"
    payment_reference: str

class ApprovalDecisionIn(BaseModel):
    decision: Literal["APPROVE", "REJECT"]

class FundingDecisionIn(BaseModel):
    decision: Literal["APPROVE", "REJECT"]

class PayEditorIn(BaseModel):
    payment_reference: str

class BankDetailsIn(BaseModel):
    payout_method: str = "UPI"  # UPI | BANK
    upi_id: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
    bank_ifsc: Optional[str] = None

class CreateCampaignIn(BaseModel):
    title: str
    content_type: str
    description: str
    clip_guidelines: str = ""
    bounty_pool: float = Field(..., ge=1000.0)
    max_clips_per_editor: int = 10
    start_date: str
    end_date: str
    source_video_urls: List[str] = []
    allowed_platforms: List[str] = ["YOUTUBE_SHORTS", "TIKTOK", "INSTAGRAM_REELS"]
    # Brief
    brief: Optional[dict] = None  # { objective, target_audience, content_style, topics_focus, topics_avoid, hook_style, length_guidelines, caption_guidelines, video_type }
    # Assets
    assets: Optional[dict] = None  # { drive_links, raw_footage, logos, brand_assets, notes }
    # Funding split (optional; if absent computed from bounty_pool)
    editor_pool_pct: float = 60.0
    performance_pool_pct: float = 30.0
    bonus_pool_pct: float = 10.0
    # Lock window
    min_duration_days: int = 7
    early_close_penalty_pct: float = 20.0

class SubmitClipIn(BaseModel):
    campaign_id: str
    platform: str
    clip_url: str

class CreatorApplyIn(BaseModel):
    name: str
    email: str
    youtube: Optional[str] = None
    instagram: Optional[str] = None
    tiktok: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None
    content_type: str
    how_heard_about_us: Optional[str] = None

# ---------------- Auth routes ----------------
@api.post("/auth/session")
async def auth_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id required")
    r = requests.get(EMERGENT_AUTH_SESSION_URL, headers={"X-Session-ID": session_id}, timeout=15)
    if r.status_code != 200:
        raise HTTPException(401, "Invalid session_id")
    data = r.json()
    email = data["email"]
    print(f"DEBUG AUTH: Logging in user email={email}")
    existing_resp = supabase.table("users").select("*").eq("email", email).execute()
    existing = existing_resp.data[0] if existing_resp.data else None
    if existing:
        user = existing
        supabase.table("users").update({
            "name": data.get("name"),
            "avatar_url": data.get("picture")
        }).eq("user_id", user["user_id"]).execute()
        user["name"] = data.get("name")
        user["avatar_url"] = data.get("picture")
    else:
        user = {
            "user_id": new_id("user"),
            "email": email,
            "name": data.get("name") or email.split("@")[0],
            "username": (data.get("name") or email.split("@")[0]).replace(" ", "_").lower() + "_" + uuid.uuid4().hex[:4],
            "avatar_url": data.get("picture"),
            "role": "EDITOR",  # default role for new users
            "bio": "",
            "lifetime_points": 0.0,
            "wallet_balance": 0.0,
            "total_earnings": 0.0,
            "total_withdrawn": 0.0,
            "active_platforms": [],
            "is_earnings_public": False,
            "payout_upi": "",
            "created_at": now_iso(),
        }
        supabase.table("users").insert(user).execute()
    token = data["session_token"]
    print(f"DEBUG AUTH: Generated session token={token}")
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    # await db.user_sessions.insert_one({
    #     "user_id": user["user_id"], "session_token": token,
    #     "expires_at": expires.isoformat(), "created_at": now_iso(),
    # })
    insert_res = supabase.table("sessions").insert({
        "session_token": token,
        "user_id": user["user_id"],
        "expires_at": expires.isoformat(),
        "created_at": now_iso(),
    }).execute()
    print(f"DEBUG AUTH: Insert sessions table result: {insert_res.data if insert_res else None}")
    response.set_cookie("session_token", token, httponly=True, secure=True,
                        samesite="none", path="/", max_age=7 * 24 * 60 * 60)
    return clean_doc(user)

@api.post("/auth/logout")
async def auth_logout(
    response: Response,
    session_token: Optional[str] = Cookie(None)
):
    if session_token:
        supabase.table("sessions").delete().eq("session_token", session_token).execute()
    
    response.delete_cookie(
        "session_token",
        path="/"
    )
    return {"ok": True}

@api.get("/auth/me")
async def auth_me(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    user = await get_current_user(request, session_token, authorization)
    return clean_doc(user)

@api.put("/auth/profile")
async def update_profile(payload: UpdateProfileIn, request: Request,
                         session_token: Optional[str] = Cookie(None),
                         authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, session_token, authorization)
    upd = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    # username uniqueness
    if "username" in upd and upd["username"] != user.get("username"):
        dup = supabase.table("users").select("user_id").eq("username", upd["username"]).neq("user_id", user["user_id"]).execute()
        if dup.data:
            raise HTTPException(400, "Username already taken")
    if "bio" in upd and len(upd["bio"]) > 160:
        raise HTTPException(400, "Bio too long (max 160)")
    if upd:
        supabase.table("users").update(upd).eq("user_id", user["user_id"]).execute()
    user2_resp = supabase.table("users").select("*").eq("user_id", user["user_id"]).execute()
    user2 = user2_resp.data[0] if user2_resp.data else {}
    return clean_doc(user2)

# ---------------- Featured clips on profile ----------------
@api.post("/profile/featured-clips")
async def add_featured_clip(
    payload: FeaturedClipIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """
    Add a featured clip to the current user's profile.
    Replaces the MongoDB `update_one` call with a Supabase update.
    """
    user = await get_current_user(request, session_token, authorization)
    # Current list of featured clips (may be empty)
    fc = user.get("featured_clips") or []
    if len(fc) >= 6:
        raise HTTPException(400, "Max 6 featured clips")
    # Build the new featured‑clip entry
    item = dict(payload.model_dump())
    item["id"] = new_id("fc")
    fc.append(item)
    # Persist the updated list via Supabase
    supabase.table("users").update({"featured_clips": fc}).eq(
        "user_id", user["user_id"]
    ).execute()
    return item


@api.delete("/profile/featured-clips/{clip_id}")
async def remove_featured_clip(
    clip_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """
    Remove a featured clip from the current user's profile.
    Replaces the MongoDB `update_one` call with a Supabase update.
    """
    user = await get_current_user(request, session_token, authorization)
    # Filter out the clip to be removed
    fc = [c for c in (user.get("featured_clips") or []) if c.get("id") != clip_id]
    # Persist the updated list via Supabase
    supabase.table("users").update({"featured_clips": fc}).eq(
        "user_id", user["user_id"]
    ).execute()
    return {"ok": True}

# ---------------- Badges ----------------
BADGES = [
    {"id": "first_blood", "name": "First Blood", "icon": "🏆", "description": "Submitted your first clip"},
    {"id": "viral_hit",   "name": "Viral Hit",   "icon": "⚡", "description": "A clip crossed 100K views"},
    {"id": "hot_streak",  "name": "Hot Streak",  "icon": "🔥", "description": "Submitted clips in 3 campaigns consecutively"},
    {"id": "top_3",       "name": "Top 3 Finish","icon": "💎", "description": "Finished Top 3 in any campaign"},
    {"id": "winner",      "name": "Campaign Winner","icon":"👑", "description": "Finished #1 in a campaign"},
    {"id": "midnight",    "name": "Midnight Grinder","icon":"🌙","description": "Submitted a clip between 12am–4am"},
]

async def compute_badges(user_id: str):
    """
    Compute badge earn‑status for a user.
    Replaces the MongoDB `find` calls with Supabase queries.
    """
    # ------------------------------------------------------------------
    # Fetch the user's clips from Supabase
    # ------------------------------------------------------------------
    clips_resp = (
        supabase.table("clips")
        .select("*")
        .eq("editor_id", user_id)
        .eq("is_deleted", False)
        .execute()
    )
    clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])

    # ------------------------------------------------------------------
    # Fetch the user's participations from Supabase
    # ------------------------------------------------------------------
    parts_resp = (
        supabase.table("participations")
        .select("*")
        .eq("editor_id", user_id)
        .execute()
    )
    parts = parts_resp.data if hasattr(parts_resp, "data") else parts_resp.get("data", [])

    # ------------------------------------------------------------------
    # Badge calculation logic (unchanged)
    # ------------------------------------------------------------------
    earned = set()

    if clips:
        earned.add("first_blood")

    if any(c.get("views", 0) >= 100_000 for c in clips):
        earned.add("viral_hit")

    if len(parts) >= 3:
        earned.add("hot_streak")

    ranks = [p.get("rank") for p in parts if p.get("rank")]
    if any(r <= 3 for r in ranks):
        earned.add("top_3")
    if any(r == 1 for r in ranks):
        earned.add("winner")

    for c in clips:
        ts = c.get("submitted_at", "")
        try:
            hour = datetime.fromisoformat(ts.replace("Z", "+00:00")).hour
            if 0 <= hour < 4:
                earned.add("midnight")
                break
        except Exception:
            pass

    # Return the badge list with an `earned` flag per badge
    return [{**b, "earned": b["id"] in earned} for b in BADGES]
# ---------------- Public profile ----------------
    return clean_doc(doc)


@api.get("/profile/me/full")
async def my_full_profile(request: Request,
                          session_token: Optional[str] = Cookie(None),
                          authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, session_token, authorization)
    return await build_public_profile(user)

@api.get("/profile/by-username/{username}")
async def profile_by_username(username: str):
    """
    Retrieve a public profile by username.
    Replaces the MongoDB lookup with a Supabase query.
    """
    # Fetch the user record from Supabase
    resp = supabase.table("users").select("*").eq("username", username).execute()
    user = resp.data[0] if resp.data else None
    if not user:
        raise HTTPException(404, "User not found")
    # Build the public profile using existing helper (which may query other tables)
    public_profile = await build_public_profile(user)
    # Ensure the campaign history is not exposed for editors per spec
    if public_profile.get("role") != "CREATOR":
        public_profile.pop("campaign_history", None)
    return public_profile


# ---------------- Earnings & Payouts ----------------

@api.get("/earnings")
async def get_earnings(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    if user.get("role") != "EDITOR":
        raise HTTPException(403, "Editor account required")
        
    # Query all participations for this editor
    parts_resp = (
        supabase.table("participations")
        .select("*, campaign:campaigns(title, status, bounty_pool)")
        .eq("editor_id", user["user_id"])
        .execute()
    )
    parts = parts_resp.data or []

    # Fetch clips to identify empty campaigns (no clips submitted by this editor)
    clips_resp = (
        supabase.table("clips")
        .select("campaign_id")
        .eq("editor_id", user["user_id"])
        .eq("is_deleted", False)
        .execute()
    )
    clips = clips_resp.data or []
    submitted_campaign_ids = {c["campaign_id"] for c in clips if c.get("campaign_id")}

    # Filter parts according to specifications:
    # 1. Remove all payout history entries where: payout_amount = 0 AND payout_status = 'NONE'
    # 2. Do not render empty campaigns as payout records (i.e., editor submitted 0 clips)
    filtered_parts = []
    for p in parts:
        payout_amt = float(p.get("payout_amount") or 0.0)
        payout_status = p.get("payout_status") or "NONE"
        if payout_amt == 0.0 and payout_status == "NONE":
            continue
        if p.get("campaign_id") not in submitted_campaign_ids:
            continue
        filtered_parts.append(p)
    
    # Calculate totals
    paid_earnings = sum(float(p.get("payout_amount") or 0.0) for p in filtered_parts if p.get("payout_status") == "COMPLETED")
    pending_earnings = sum(float(p.get("payout_amount") or 0.0) for p in filtered_parts if p.get("payout_status") == "PENDING")
    
    history = []
    for p in filtered_parts:
        camp = p.get("campaign") or {}
        history.append({
            "participation_id": p["participation_id"],
            "campaign_id": p["campaign_id"],
            "campaign_title": camp.get("title", "Unknown Campaign"),
            "campaign_status": camp.get("status", "Unknown Status"),
            "bounty_pool": camp.get("bounty_pool", 0.0),
            "payout_amount": p["payout_amount"],
            "payout_status": "PAID" if p["payout_status"] == "COMPLETED" else "PENDING",
            "payment_reference": p.get("payment_reference"),
            "paid_at": p.get("paid_at")
        })
        
    socials = user.get("socials") or {}
    bank_details = socials.get("bank_details") or {}
    payout_method = bank_details.get("payout_method") or "UPI"
    upi_id = bank_details.get("upi_id") or user.get("payout_upi")
    bank_name = bank_details.get("bank_name")
    bank_account_number = bank_details.get("bank_account_number")
    bank_account_name = bank_details.get("bank_account_name")
    bank_ifsc = bank_details.get("bank_ifsc")

    return {
        "paid_earnings": round(paid_earnings, 2),
        "pending_earnings": round(pending_earnings, 2),
        "payout_method": payout_method,
        "upi_id": upi_id,
        "bank_name": bank_name,
        "bank_account_number": bank_account_number,
        "bank_account_name": bank_account_name,
        "bank_ifsc": bank_ifsc,
        "bank_details": {
            "payout_method": payout_method,
            "upi_id": upi_id,
            "bank_name": bank_name,
            "bank_account_number": bank_account_number,
            "bank_account_name": bank_account_name,
            "bank_ifsc": bank_ifsc
        },
        "history": history
    }



@api.post("/profile/bank-details")
async def save_bank_details(
    payload: BankDetailsIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "EDITOR")
    
    p_method = (payload.payout_method or "UPI").upper()
    if p_method not in ("UPI", "BANK"):
        raise HTTPException(400, "Invalid payout_method. Must be 'UPI' or 'BANK'.")
        
    if p_method == "UPI":
        if not payload.upi_id or not payload.upi_id.strip():
            raise HTTPException(400, "UPI ID is required when payout method is UPI.")
    else: # BANK
        if not payload.bank_name or not payload.bank_name.strip():
            raise HTTPException(400, "Bank name is required when payout method is BANK.")
        if not payload.bank_account_number or not payload.bank_account_number.strip():
            raise HTTPException(400, "Bank account number is required when payout method is BANK.")
        if not payload.bank_account_name or not payload.bank_account_name.strip():
            raise HTTPException(400, "Account holder name is required when payout method is BANK.")
        if not payload.bank_ifsc or not payload.bank_ifsc.strip():
            raise HTTPException(400, "Bank IFSC is required when payout method is BANK.")
            
    bank_data = {
        "payout_method": p_method,
        "upi_id": payload.upi_id,
        "bank_name": payload.bank_name,
        "bank_account_number": payload.bank_account_number,
        "bank_account_name": payload.bank_account_name,
        "bank_ifsc": payload.bank_ifsc
    }
    
    # Store bank details inside the user's socials JSONB column
    user_socials = user.get("socials") or {}
    user_socials["bank_details"] = bank_data
    
    upd = {
        "socials": user_socials
    }
    if p_method == "UPI" and payload.upi_id:
        upd["payout_upi"] = payload.upi_id

    supabase.table("users").update(upd).eq("user_id", user["user_id"]).execute()
    return {"ok": True, "bank_details": bank_data}


@api.post("/wallet/cashout")
async def cashout(
    payload: CashoutIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    if user.get("role") != "EDITOR":
        raise HTTPException(403, "Editor account required")
    amt = float(payload.amount)
    if amt <= 0:
        raise HTTPException(400, "Amount must be > 0")
    
    bal = float(user.get("wallet_balance") or 0.0)
    if amt > bal:
        raise HTTPException(400, f"Insufficient balance. Available: ₹{bal:.2f}")
        
    new_balance = round(bal - amt, 2)
    supabase.table("users").update({"wallet_balance": new_balance}).eq("user_id", user["user_id"]).execute()
    
    withdrawal_id = new_id("wd")
    rec = {
        "withdrawal_id": withdrawal_id,
        "user_id": user["user_id"],
        "amount": round(amt, 2),
        "status": "PENDING",
        "razorpay_payout_id": f"pout_mock_{uuid.uuid4().hex[:8]}",
        "payment_reference": None,
        "created_at": now_iso()
    }
    supabase.table("withdrawals").insert(rec).execute()
    
    res_rec = dict(rec)
    res_rec["withdrawal_id"] = withdrawal_id
    
    return {
        "ok": True,
        "withdrawal": res_rec,
        "remaining_balance": new_balance
    }

@api.get("/wallet/withdrawals")
async def list_withdrawals(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    resp = (
        supabase.table("withdrawals")
        .select("*")
        .eq("user_id", user["user_id"])
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )
    docs = resp.data or []
    for row in docs:
        # row["request_id"] = row["withdrawal_id"]  # alias removed
        # map status
        row_status = row.get("status")
        payout_id = row.get("razorpay_payout_id")
        api_status = "PENDING"
        if row_status == "COMPLETED":
            if payout_id == "REJECTED":
                api_status = "REJECTED"
            else:
                api_status = "PAID"
        row["status"] = api_status
    return docs





@api.post("/creator/apply")
async def creator_apply(payload: CreatorApplyIn):
    # Prevent duplicate pending applications
    existing = (
        supabase.table("creator_applications")
        .select("application_id")
        .eq("email", payload.email)
        .eq("status", "PENDING")
        .execute()
    )

    if existing.data:
        raise HTTPException(
            400,
            "Application already submitted and awaiting review"
        )
    app_id = new_id("app")
    rec = {
        "application_id": app_id,
        "name": payload.name,
        "email": payload.email,
        "youtube": payload.youtube,
        "instagram": payload.instagram,
        "tiktok": payload.tiktok,
        "twitter": payload.twitter,
        "linkedin": payload.linkedin,
        "website": payload.website,
        "content_type": payload.content_type,
        "how_heard_about_us": payload.how_heard_about_us,
        "status": "PENDING",
        "created_at": now_iso()
    }
    supabase.table("creator_applications").insert(rec).execute()
    return {"ok": True, "application_id": app_id}

@api.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """
    Handle file uploads.
    Replaces the MongoDB `insert_one` with a Supabase insert.
    """
    user = await get_current_user(request, session_token, authorization)
    # Determine file extension and storage path
    ext = (file.filename or "bin").rsplit(".", 1)[-1].lower()
    path = f"{APP_NAME}/uploads/{user['user_id']}/{uuid.uuid4().hex}.{ext}"
    # Read file contents
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 8MB)")
    # Store the file in the object storage layer
    result = put_object(path, data, file.content_type or "application/octet-stream")
    # Insert metadata into Supabase instead of MongoDB
    supabase.table("files").insert(
        {
            "file_id": new_id("file"),
            "owner_id": user["user_id"],
            "storage_path": result["path"],
            "original_filename": file.filename,
            "content_type": file.content_type,
            "size": result["size"],
            "is_deleted": False,
            "created_at": now_iso(),
        }
    ).execute()
    return {"path": result["path"], "size": result["size"]}

@api.get("/files/{path:path}")
async def serve_file(path: str):
    data, ct = get_object(path)
    return Response(content=data, media_type=ct)

# ---------------- Campaigns ----------------

@api.get("/campaigns")
async def list_campaigns(
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    sort_by: str = "bounty_desc",
    mine: bool = False,
    enrolled: bool = False,
    request: Request = None,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    query = supabase.table("campaigns").select("*")

    if status:
        if status in ("DRAFT", "PENDING_APPROVAL", "REJECTED", "CANCELLED"):
            user_role = None
            try:
                user = await get_current_user(request, session_token, authorization)
                user_role = user.get("role")
            except Exception:
                pass
            if user_role not in ("ADMIN", "CREATOR"):
                raise HTTPException(403, "Access denied")
        if status in ("PENDING_APPROVAL", "REJECTED", "CANCELLED"):
            query = query.eq("status", "DRAFT").eq("escrow_order_id", status)
        else:
            query = query.eq("status", status)

    if content_type:
        query = query.eq("content_type", content_type)

    if mine:
        user = await get_current_user(request, session_token, authorization)
        query = query.eq("creator_id", user["user_id"])

    # --- Enrolled filter: only campaigns the current user has joined ---
    enrolled_campaign_ids: Optional[list] = None
    if enrolled:
        user = await get_current_user(request, session_token, authorization)
        parts_resp = (
            supabase.table("participations")
            .select("campaign_id")
            .eq("editor_id", user["user_id"])
            .execute()
        )
        enrolled_campaign_ids = [
            p["campaign_id"] for p in (parts_resp.data or [])
        ]
        if enrolled_campaign_ids:
            query = query.in_("campaign_id", enrolled_campaign_ids)
        else:
            # User has no participations — return empty list immediately
            return []

    if sort_by == "bounty_desc":
        query = query.order("bounty_pool", desc=True)
    elif sort_by == "ending_soon":
        query = query.order("end_date")
    elif sort_by == "newest":
        query = query.order("created_at", desc=True)

    result = query.execute()
    docs = result.data or []
    docs = map_db_campaigns(docs)
    if status == "DRAFT":
        docs = [d for d in docs if d.get("status") == "DRAFT"]

    # Enforce role-based security rules on the result set
    caller_id = None
    caller_role = None
    try:
        user = await get_current_user(request, session_token, authorization)
        caller_id = user.get("user_id")
        caller_role = user.get("role")
    except Exception:
        pass

    filtered_docs = []
    for d in docs:
        d_status = d.get("status")
        d_creator_id = d.get("creator_id")
        if d_status in ("DRAFT", "PENDING_APPROVAL", "REJECTED"):
            if caller_role == "ADMIN" or (caller_role == "CREATOR" and caller_id == d_creator_id):
                filtered_docs.append(d)
        else:
            if caller_role == "EDITOR" or not caller_role:
                if d_status == "ACTIVE":
                    filtered_docs.append(d)
            else:
                filtered_docs.append(d)
    docs = filtered_docs


    for d in docs:
        creator_result = (
            supabase.table("users")
            .select("user_id,name,avatar_url,username")
            .eq("user_id", d["creator_id"])
            .limit(1)
            .execute()
        )

        d["creator"] = (
            creator_result.data[0]
            if creator_result.data
            else None
        )

        participants = (
            supabase.table("participations")
            .select("participation_id")
            .eq("campaign_id", d["campaign_id"])
            .execute()
        )

        d["participant_count"] = len(participants.data or [])

        # Dynamic OCV metrics enrichment
        enrich_campaign_ocv_metrics(d)

    return docs

@api.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    """Return a single campaign with enriched data."""
    resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("campaign_id", campaign_id)
        .single()
        .execute()
    )
    campaign = resp.data if hasattr(resp, "data") else resp.get("data")
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    campaign = map_db_campaign(campaign)

    caller_id = None
    caller_role = None
    try:
        user = await get_current_user(request, session_token, authorization)
        caller_id = user.get("user_id")
        caller_role = user.get("role")
    except Exception:
        pass

    status = campaign.get("status", "DRAFT")
    if status in ("DRAFT", "PENDING_APPROVAL", "REJECTED"):
        if caller_role != "ADMIN" and (caller_role != "CREATOR" or caller_id != campaign.get("creator_id")):
            raise HTTPException(403, "Access denied")
    else:
        if caller_role == "EDITOR" or not caller_role:
            if status != "ACTIVE":
                raise HTTPException(403, "Access denied")

    creator_resp = (
        supabase.table("users")
        .select("user_id,name,avatar_url,username")
        .eq("user_id", campaign["creator_id"])
        .limit(1)
        .execute()
    )
    campaign["creator"] = creator_resp.data[0] if creator_resp.data else None
    participants = (
        supabase.table("participations")
        .select("participation_id")
        .eq("campaign_id", campaign["campaign_id"])
        .execute()
    )
    campaign["participant_count"] = len(participants.data or [])

    # Dynamic OCV metrics enrichment
    enrich_campaign_ocv_metrics(campaign)
    return clean_doc(campaign)

@api.post("/campaigns")
async def create_campaign(
    payload: CreateCampaignIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    """Create a new campaign. Only creators may create campaigns."""
    try:
        print("=== ACTIVE CREATE ROUTE ===")
        user = await get_current_user(request, session_token, authorization)
        await require_role(user, "CREATOR")
        # Validate minimum budget (₹1000)
        if payload.bounty_pool < 1000:
            raise HTTPException(400, "Campaign budget must be at least ₹1000")
        # Build campaign dict matching Supabase schema
        campaign = {
            "campaign_id": new_id("camp"),
            "creator_id": user["user_id"],
            "title": payload.title,
            "content_type": payload.content_type,
            "description": payload.description,
            "brief": payload.brief,
            "assets": payload.assets,
            "bounty_pool": payload.bounty_pool,
            "max_clips_per_editor": payload.max_clips_per_editor,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "editor_pool_pct": payload.editor_pool_pct,
            "performance_pool_pct": payload.performance_pool_pct,
            "bonus_pool_pct": payload.bonus_pool_pct,
            "clip_guidelines": payload.clip_guidelines,
            "source_video_urls": payload.source_video_urls,
            "status": "DRAFT",
            "created_at": now_iso(),
            "escrow_funded": False
        }

        # Insert the campaign using the already built schema‑matched dict
        result = supabase.table("campaigns").insert(campaign).execute()
        print("SUPABASE INSERT RESPONSE:", result)
        enrich_campaign_ocv_metrics(campaign)
        return clean_doc(campaign)
    except HTTPException as http_exc:
        # Propagate permission-related HTTPExceptions unchanged
        raise http_exc
    except Exception as e:
        print("CREATE CAMPAIGN ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@api.post("/campaigns/{campaign_id}/publish")
async def publish_campaign(
    campaign_id: str,
    request: Request,
    payload: dict = Body(...),  # expects {'payment_reference': str}
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    """Publish a campaign for manual admin approval.
    Creator provides a payment reference which becomes the escrow_order_id.
    Status transitions from DRAFT to PENDING_PAYMENT.
    """
    if not payload or "payment_reference" not in payload:
        raise HTTPException(400, "payment_reference is required")
    user = await get_current_user(request, session_token, authorization)
    camp_resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("campaign_id", campaign_id)
        .single()
        .execute()
    )
    campaign = camp_resp.data if hasattr(camp_resp, "data") else camp_resp.get("data")
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    campaign = map_db_campaign(campaign)
    if campaign.get("creator_id") != user.get("user_id"):
        raise HTTPException(403, "Only the creator can publish this campaign")
    if campaign.get("status") != "DRAFT":
        raise HTTPException(400, "Only draft campaigns can be published")
    upd = {
        "status": "PENDING_PAYMENT",
        "escrow_order_id": payload["payment_reference"],
        "published_at": now_iso()
    }
    supabase.table("campaigns").update(upd).eq("campaign_id", campaign_id).execute()
    return {"ok": True, "campaign_id": campaign_id, "status": "PENDING_PAYMENT", "escrow_order_id": payload["payment_reference"]}

async def complete_campaign_and_credit_wallets(campaign_id: str) -> dict:
    camp_resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("campaign_id", campaign_id)
        .single()
        .execute()
    )
    campaign = camp_resp.data
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    campaign = map_db_campaign(campaign)
    if campaign.get("status") in ("PENDING_PAYMENT", "COMPLETED"):
        raise HTTPException(400, "Campaign already settling or completed")

    clips_resp = (
        supabase.table("clips")
        .select("editor_id,ocv")
        .eq("campaign_id", campaign_id)
        .eq("is_deleted", False)
        .limit(10000)
        .execute()
    )
    clips = clips_resp.data or []
    editor_ocv: dict[str, float] = {}
    total_campaign_ocv = 0.0
    for clip in clips:
        ocv = float(clip.get("ocv") or 0.0)
        editor_id = clip.get("editor_id")
        if not editor_id:
            continue
        editor_ocv[editor_id] = editor_ocv.get(editor_id, 0.0) + ocv
        total_campaign_ocv += ocv

    reward_pool = round(float(campaign.get("bounty_pool") or 0.0) * 0.85, 2)
    payouts = []

    for editor_id, ocv in editor_ocv.items():
        amount = round((ocv / total_campaign_ocv) * reward_pool, 2) if total_campaign_ocv > 0 else 0.0
        
        # Update participation record with payout info and status
        supabase.table("participations").update({
            "payout_amount": amount,
            "payout_status": "PENDING",
        }).eq("campaign_id", campaign_id).eq("editor_id", editor_id).execute()
        # Credit editor wallet
        user = supabase.table("users").select("wallet_balance,total_earnings").eq("user_id", editor_id).single().execute().data
        new_balance = round(float(user.get("wallet_balance") or 0) + amount, 2)
        new_total = round(float(user.get("total_earnings") or 0) + amount, 2)
        supabase.table("users").update({"wallet_balance": new_balance, "total_earnings": new_total}).eq("user_id", editor_id).execute()
        
        payouts.append({
            "editor_id": editor_id,
            "editor_ocv": round(ocv, 2),
            "amount": amount,
        })

    # Create settlement log entry
    # Update campaign status to COMPLETED (settlement completed)
    supabase.table("campaigns").update({
        "status": "COMPLETED",
    }).eq("campaign_id", campaign_id).execute()

    return {
        "ok": True,
        "campaign_id": campaign_id,
        "status": "COMPLETED",
        "reward_pool": reward_pool,
        "total_campaign_ocv": round(total_campaign_ocv, 2),
        "payouts": payouts,
    }


@api.post("/admin/campaigns/{campaign_id}/status")
async def admin_set_campaign_status(
    campaign_id: str,
    payload: CampaignStatusIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    status = payload.status.upper()
    allowed = {"DRAFT", "PENDING_APPROVAL", "ACTIVE", "COMPLETED", "CANCELLED", "REJECTED", "PAUSED"}
    if status not in allowed:
        raise HTTPException(400, "Invalid campaign status")
        
    camp_resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("campaign_id", campaign_id)
        .single()
        .execute()
    )
    campaign = camp_resp.data
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    campaign = map_db_campaign(campaign)
        
    # Check if previously funded/active
    is_funded = campaign.get("escrow_funded") is True or campaign.get("status") == "ACTIVE"

    upd = {"status": status}
    if status == "ACTIVE":
        upd["escrow_funded"] = True
        upd["escrow_order_id"] = None
    elif status in ("PENDING_APPROVAL", "REJECTED", "CANCELLED", "PAUSED"):
        upd["status"] = "DRAFT"
        upd["escrow_order_id"] = status
        # Refund creator wallet if previously funded/active campaign is cancelled or rejected
        if is_funded:
            creator_id = campaign.get("creator_id")
            creator_resp = supabase.table("users").select("wallet_balance").eq("user_id", creator_id).single().execute()
            creator = creator_resp.data
            if creator:
                bounty = float(campaign.get("bounty_pool") or 0.0)
                new_bal = round(float(creator.get("wallet_balance") or 0.0) + bounty, 2)
                supabase.table("users").update({"wallet_balance": new_bal}).eq("user_id", creator_id).execute()
            upd["escrow_funded"] = False
    elif status == "DRAFT":
        upd["escrow_order_id"] = None
        
    if status == "COMPLETED":
        return await complete_campaign_and_credit_wallets(campaign_id)
        
    supabase.table("campaigns").update(upd).eq("campaign_id", campaign_id).execute()
    return {"ok": True, "campaign_id": campaign_id, "status": status}


@api.post("/admin/campaigns/{campaign_id}/start-settlement")
async def start_settlement(
    campaign_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    return await complete_campaign_and_credit_wallets(campaign_id)

@api.post("/admin/participations/{participation_id}/pay")
async def pay_editor(
    participation_id: str,
    payload: PayEditorIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    
    part_resp = (
        supabase.table("participations")
        .select("*")
        .eq("participation_id", participation_id)
        .single()
        .execute()
    )
    part = part_resp.data
    if not part:
        raise HTTPException(404, "Participation not found")
        
    upd = {
        "payout_status": "COMPLETED",
        "payment_reference": payload.payment_reference,
        "paid_at": now_iso()
    }
    supabase.table("participations").update(upd).eq("participation_id", participation_id).execute()
    
    # Check if all other participants for this campaign are paid
    camp_id = part["campaign_id"]
    parts_resp = (
        supabase.table("participations")
        .select("payout_amount,payout_status")
        .eq("campaign_id", camp_id)
        .execute()
    )
    all_parts = parts_resp.data or []
    
    # If all participants who have clips/earnings are paid, mark campaign completed
    if all(p.get("payout_status") == "COMPLETED" for p in all_parts if float(p.get("payout_amount") or 0) > 0):
        supabase.table("campaigns").update({
            "status": "COMPLETED",
            "completed_at": now_iso()
        }).eq("campaign_id", camp_id).execute()
        
    return {"ok": True, "participation_id": participation_id, "payout_status": "PAID"}

@api.get("/admin/withdrawal-requests")
async def admin_list_withdrawal_requests(
    request: Request,
    status: Optional[str] = None,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    query = supabase.table("withdrawals").select("*, user:users(name, username)")
    resp = query.order("created_at", desc=True).limit(500).execute()
    data = resp.data or []
    
    results = []
    for row in data:
        row_status = row.get("status")
        payout_id = row.get("razorpay_payout_id")
        
        api_status = "PENDING"
        if row_status == "COMPLETED":
            if payout_id == "REJECTED":
                api_status = "REJECTED"
            else:
                api_status = "PAID"
                
        if status and status.upper() != api_status:
            continue
            
        editor = row.get("user") or {}
        results.append({
            "request_id": row["withdrawal_id"],
            "withdrawal_id": row["withdrawal_id"],
            "user_id": row["user_id"],
            "editor_name": editor.get("name") or editor.get("username") or "Unnamed Editor",
            "editor_username": editor.get("username") or "",
            "amount": row["amount"],
            "status": api_status,
            "created_at": row["created_at"]
        })
    return results

@api.post("/admin/withdrawal-requests/{request_id}/status")
async def admin_set_withdrawal_status(
    request_id: str,
    payload: WithdrawalStatusIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    status = payload.status.upper()
    if status not in {"PAID", "REJECTED"}:
        raise HTTPException(400, "Withdrawal status must be PAID or REJECTED")

    # Fetch withdrawal record
    req_resp = (
        supabase.table("withdrawals")
        .select("*")
        .eq("withdrawal_id", request_id)
        .single()
        .execute()
    )
    withdrawal = req_resp.data
    if not withdrawal:
        raise HTTPException(404, "Withdrawal request not found")

    # Guard against double processing – reject if already resolved
    if withdrawal.get("status") != "PENDING":
        raise HTTPException(400, "Withdrawal request is already resolved")

    # Prepare updates for the withdrawal row
    if status == "PAID":
        updates = {
            "status": "PAID",
            "razorpay_payout_id": f"pout_{uuid.uuid4().hex[:12]}",
            "payment_reference": payload.payment_reference,
        }
    else:
        updates = {
            "status": "REJECTED",
            "razorpay_payout_id": "REJECTED"
        }

    # Debug: print payload being sent to Supabase
    print("[DEBUG] Withdrawal update payload:", updates)
    try:
        # Update withdrawal status and payment reference
        supabase.table("withdrawals").update(updates).eq("withdrawal_id", request_id).execute()
        # Find a pending participation for this user (if any) and sync payment_reference
        part_resp = supabase.table("participations").select("participation_id").eq("editor_id", withdrawal["user_id"]).eq("payout_status", "PENDING").execute()
        parts = part_resp.data or []
        if parts:
            supabase.table("participations").update({"payment_reference": payload.payment_reference}).eq("participation_id", parts[0]["participation_id"]).execute()
    except Exception as e:
        print("[ERROR] Failed to update withdrawal:", e)
        raise

    # Fetch user row before update
    editor_resp = (
        supabase.table("users")
        .select("wallet_balance,total_withdrawn")
        .eq("user_id", withdrawal["user_id"])
        .single()
        .execute()
    )
    editor_before = editor_resp.data or {}
    print("[DEBUG] User before withdrawal update:", editor_before)

    amount = float(withdrawal.get("amount") or 0.0)
    if status == "PAID":
        total_withdrawn = round(float(editor_before.get("total_withdrawn") or 0.0) + amount, 2)
        update_payload = {"total_withdrawn": total_withdrawn}
        print("[DEBUG] Updating user total_withdrawn with:", update_payload)
        try:
            supabase.table("users").update(update_payload).eq("user_id", withdrawal["user_id"]).execute()
        except Exception as e:
            print("[ERROR] Failed to update user total_withdrawn:", e)
            raise
    else:
        wallet_balance = round(float(editor_before.get("wallet_balance") or 0.0) + amount, 2)
        update_payload = {"wallet_balance": wallet_balance}
        print("[DEBUG] Updating user wallet_balance with:", update_payload)
        try:
            supabase.table("users").update(update_payload).eq("user_id", withdrawal["user_id"]).execute()
        except Exception as e:
            print("[ERROR] Failed to update user wallet_balance:", e)
            raise

    # Fetch user row after update for verification
    editor_after_resp = (
        supabase.table("users")
        .select("wallet_balance,total_withdrawn")
        .eq("user_id", withdrawal["user_id"])
        .single()
        .execute()
    )
    editor_after = editor_after_resp.data or {}
    print("[DEBUG] User after withdrawal update:", editor_after)

    return {"ok": True, "request_id": request_id, "status": status}

@api.post("/admin/withdrawal-requests/{request_id}/approve")
async def admin_approve_withdrawal_request(
    request_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    payload = WithdrawalStatusIn(status="PAID")
    return await admin_set_withdrawal_status(request_id, payload, request, session_token, authorization)



# ------------------------------------------------------------
# Admin Manual Approval Queue
# ------------------------------------------------------------
@api.get("/admin/pending-campaigns")
async def get_pending_campaigns(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    """Return campaigns awaiting manual approval (ADMIN only)."""
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    resp = (
        supabase.table("campaigns")
        .select("campaign_id,title,creator_id,bounty_pool,created_at,status,escrow_order_id")
        .in_("status", ["PENDING_PAYMENT", "AWAITING_FUNDING"])
        .execute()
    )
    campaigns = resp.data or []
    campaigns = map_db_campaigns(campaigns)
    enriched = []
    for c in campaigns:
        creator_resp = (
            supabase.table("users")
            .select("name")
            .eq("user_id", c.get("creator_id"))
            .single()
            .execute()
        )
        creator_name = creator_resp.data.get("name") if creator_resp.data else None
        d = {
            "campaign_id": c.get("campaign_id"),
            "title": c.get("title"),
            "creator_id": c.get("creator_id"),
            "creator_name": creator_name,
            "bounty_pool": c.get("bounty_pool"),
            "created_at": c.get("created_at"),
            "status": c.get("status"),
        }
        enrich_campaign_ocv_metrics(d)
        enriched.append(d)
    return enriched

@api.post("/admin/campaigns/{campaign_id}/approval-decision")
async def admin_approval_decision(
    campaign_id: str,
    payload: ApprovalDecisionIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    """Admin approves or rejects a campaign's approval request.
    APPROVE -> status="ACTIVE", escrow_funded=True, escrow_order_id=None
    REJECT -> status="DRAFT", escrow_order_id="REJECTED"
    """
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    
    camp_resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("campaign_id", campaign_id)
        .single()
        .execute()
    )
    campaign = camp_resp.data if hasattr(camp_resp, "data") else camp_resp.get("data")
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    campaign = map_db_campaign(campaign)
    if campaign.get("status") != "PENDING_APPROVAL":
        raise HTTPException(400, "Campaign not pending approval")
        
    decision = payload.decision.upper()
    if decision == "APPROVE":
        upd = {"status": "ACTIVE", "escrow_funded": True, "escrow_order_id": None}
    elif decision == "REJECT":
        upd = {"status": "DRAFT", "escrow_order_id": "REJECTED"}
    else:
        raise HTTPException(400, "Invalid decision. Must be APPROVE or REJECT")
        
    supabase.table("campaigns").update(upd).eq("campaign_id", campaign_id).execute()
    return {"ok": True, "campaign_id": campaign_id, "status": "ACTIVE" if decision == "APPROVE" else "REJECTED"}


# ------------------------------------------------------------
# Admin Dashboard Core Operations
# ------------------------------------------------------------

@api.get("/admin/overview")
async def admin_overview(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    
    users_resp = supabase.table("users").select("role").execute()
    users = users_resp.data or []
    total_creators = sum(1 for u in users if u.get("role") == "CREATOR")
    total_editors = sum(1 for u in users if u.get("role") == "EDITOR")
    
    camps_resp = supabase.table("campaigns").select("status, escrow_order_id").execute()
    camps = camps_resp.data or []
    active_campaigns = sum(1 for c in camps if c.get("status") == "ACTIVE")
    pending_campaigns = sum(1 for c in camps if c.get("status") in ("PENDING_PAYMENT", "AWAITING_FUNDING"))
    
    parts_resp = supabase.table("participations").select("payout_amount").eq("payout_status", "COMPLETED").execute()
    total_platform_earnings = sum(float(p.get("payout_amount") or 0.0) for p in (parts_resp.data or []))
    
    withdrawals_resp = supabase.table("withdrawals").select("status").eq("status", "PENDING").execute()
    pending_withdrawals = len(withdrawals_resp.data or [])
    
    return {
        "total_creators": total_creators,
        "total_editors": total_editors,
        "active_campaigns": active_campaigns,
        "pending_campaigns": pending_campaigns,
        "total_platform_earnings": round(total_platform_earnings, 2),
        "pending_withdrawals": pending_withdrawals
    }

@api.get("/admin/creators")
async def admin_list_creators(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    
    users_resp = supabase.table("users").select("*").eq("role", "CREATOR").execute()
    creators = users_resp.data or []
    
    camps_resp = supabase.table("campaigns").select("*").execute()
    camps = map_db_campaigns(camps_resp.data or [])
    
    creator_camps = {}
    for c in camps:
        cid = c.get("creator_id")
        if cid:
            creator_camps.setdefault(cid, []).append(c)
            
    res = []
    for creator in creators:
        cid = creator["user_id"]
        my_camps = creator_camps.get(cid, [])
        total_spend = sum(float(c.get("bounty_pool") or 0.0) for c in my_camps if c.get("status") in ("ACTIVE", "COMPLETED"))
        
        res.append({
            "user_id": cid,
            "name": creator.get("name") or creator.get("username") or "Unnamed Creator",
            "username": creator.get("username") or "",
            "email": creator.get("email") or "",
            "avatar_url": creator.get("avatar_url") or "",
            "created_at": creator.get("created_at"),
            "campaigns_count": len(my_camps),
            "total_spend": round(total_spend, 2),
            "campaign_history": [
                {
                    "campaign_id": c["campaign_id"],
                    "title": c["title"],
                    "status": c["status"],
                    "bounty_pool": c["bounty_pool"],
                    "created_at": c["created_at"]
                }
                for c in my_camps
            ]
        })
    return res

@api.get("/admin/editors")
async def admin_list_editors(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    
    users_resp = supabase.table("users").select("*").eq("role", "EDITOR").execute()
    editors = users_resp.data or []
    
    withdrawals_resp = supabase.table("withdrawals").select("*").execute()
    wds = withdrawals_resp.data or []
    editor_wds = {}
    for w in wds:
        uid = w.get("user_id")
        if uid:
            editor_wds.setdefault(uid, []).append(w)
            
    res = []
    for ed in editors:
        uid = ed["user_id"]
        my_wds = editor_wds.get(uid, [])
        
        wd_history = []
        for w in my_wds:
            row_status = w.get("status")
            payout_id = w.get("razorpay_payout_id")
            api_status = "PENDING"
            if row_status == "COMPLETED":
                if payout_id == "REJECTED":
                    api_status = "REJECTED"
                else:
                    api_status = "PAID"
            wd_history.append({
                "request_id": w["withdrawal_id"],
                "amount": w["amount"],
                "status": api_status,
                "created_at": w["created_at"]
            })
            
        res.append({
            "user_id": uid,
            "name": ed.get("name") or ed.get("username") or "Unnamed Editor",
            "username": ed.get("username") or "",
            "email": ed.get("email") or "",
            "avatar_url": ed.get("avatar_url") or "",
            "wallet_balance": float(ed.get("wallet_balance") or 0.0),
            "total_earnings": float(ed.get("total_earnings") or 0.0),
            "total_withdrawn": float(ed.get("total_withdrawn") or 0.0),
            "lifetime_points": float(ed.get("lifetime_points") or 0.0),
            "created_at": ed.get("created_at"),
            "withdrawal_history": wd_history
        })
    return res

@api.get("/admin/campaigns")
async def admin_list_campaigns(
    status: Optional[str] = None,
    request: Request = None,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    
    query = supabase.table("campaigns").select("*, creator:users(name, email, username)")
    if status:
        if status in ("PENDING_APPROVAL", "REJECTED", "CANCELLED", "PAUSED"):
            query = query.eq("status", "DRAFT").eq("escrow_order_id", status)
        else:
            query = query.eq("status", status)
            
    resp = query.order("created_at", desc=True).execute()
    camps = resp.data or []
    camps = map_db_campaigns(camps)
    for c in camps:
        c["creator_name"] = c.get("creator", {}).get("name") or c.get("creator", {}).get("username")
        enrich_campaign_ocv_metrics(c)
    return camps

@api.post("/admin/users/{user_id}/suspend")
async def admin_suspend_user(
    user_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    return {"ok": True, "user_id": user_id, "suspended": True, "message": "User suspended successfully (future-ready)"}


# ------------------------------------------------------------
# Admin Funding Queue
# ------------------------------------------------------------
@api.get("/admin/funding-queue")
async def admin_funding_queue(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    """Return campaigns awaiting funding (ADMIN only)."""
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    resp = (
        supabase.table("campaigns")
        .select("campaign_id,title,creator_id,bounty_pool,escrow_order_id,created_at,status")
        .eq("status", "AWAITING_FUNDING")
        .execute()
    )
    campaigns = resp.data or []
    enriched = []
    for c in campaigns:
        creator_resp = (
            supabase.table("users")
            .select("name")
            .eq("user_id", c.get("creator_id"))
            .single()
            .execute()
        )
        creator_name = creator_resp.data.get("name") if creator_resp.data else None
        enriched.append({
            "campaign_id": c.get("campaign_id"),
            "title": c.get("title"),
            "creator_id": c.get("creator_id"),
            "creator_name": creator_name,
            "bounty_pool": c.get("bounty_pool"),
            "funding_reference": c.get("escrow_order_id"),
            "created_at": c.get("created_at"),
            "funding_status": c.get("status"),
        })
    return enriched

# ------------------------------------------------------------
# Admin Funding Decision Endpoint
# ------------------------------------------------------------

@api.post("/admin/campaigns/{campaign_id}/funding-decision")
async def admin_funding_decision(
    campaign_id: str,
    payload: FundingDecisionIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """Admin approves or rejects a campaign's funding.
    APPROVE -> escrow_funded=True, status="ACTIVE" (or pending approval if approval flow requires it)
    REJECT -> status="DRAFT"
    """
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    # Load campaign
    camp_resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("campaign_id", campaign_id)
        .single()
        .execute()
    )
    campaign = camp_resp.data if hasattr(camp_resp, "data") else camp_resp.get("data")
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    if campaign.get("status") not in ("AWAITING_FUNDING", "PENDING_PAYMENT"):
        raise HTTPException(400, "Campaign not awaiting funding")
        
    if payload.decision == "APPROVE":
        # Check if already approved (to prevent duplicate approvals)
        if campaign.get("escrow_funded") is True or campaign.get("status") == "ACTIVE":
            raise HTTPException(400, "Campaign is already funded and active")
            
        creator_id = campaign.get("creator_id")
        creator_resp = supabase.table("users").select("wallet_balance").eq("user_id", creator_id).single().execute()
        creator = creator_resp.data
        if not creator:
            raise HTTPException(404, "Campaign creator not found")
            
        bounty = float(campaign.get("bounty_pool") or 0.0)
        creator_bal = float(creator.get("wallet_balance") or 0.0)
        if creator_bal < bounty:
            raise HTTPException(400, f"Insufficient creator wallet balance (Bounty: {bounty:.2f}, Wallet: {creator_bal:.2f})")
            
        # Deduct bounty pool from creator's wallet
        new_bal = round(creator_bal - bounty, 2)
        supabase.table("users").update({"wallet_balance": new_bal}).eq("user_id", creator_id).execute()
        
        upd = {"escrow_funded": True, "status": "ACTIVE"}
    else:
        upd = {"status": "DRAFT"}
    supabase.table("campaigns").update(upd).eq("campaign_id", campaign_id).execute()
    return {"ok": True, "campaign_id": campaign_id, "decision": payload.decision}


# ------------------------------------------------------------
# Admin Settlement Queue
# ------------------------------------------------------------
@api.get("/admin/settlement-queue")
async def admin_settlement_queue(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    """Return campaigns ready for settlement (ADMIN only)."""
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "ADMIN")
    resp = (
        supabase.table("campaigns")
        .select("campaign_id,title,creator_id,bounty_pool,status")
        .eq("status", "ACTIVE")
        .execute()
    )
    campaigns = resp.data or []
    enriched = []
    for c in campaigns:
        parts_resp = (
            supabase.table("participations")
            .select("payout_amount,payout_status")
            .eq("campaign_id", c.get("campaign_id"))
            .execute()
        )
        parts = parts_resp.data or []
        unpaid = [p for p in parts if p.get("payout_status") != "COMPLETED"]
        unpaid_count = len(unpaid)
        unpaid_amount = round(sum(float(p.get("payout_amount") or 0) for p in unpaid), 2)
        creator_resp = (
            supabase.table("users")
            .select("name")
            .eq("user_id", c.get("creator_id"))
            .single()
            .execute()
        )
        creator_name = creator_resp.data.get("name") if creator_resp.data else None
        enriched.append({
            "campaign_id": c.get("campaign_id"),
            "title": c.get("title"),
            "creator_name": creator_name,
            "bounty_pool": c.get("bounty_pool"),
            "status": c.get("status"),
            "unpaid_count": unpaid_count,
            "unpaid_amount": unpaid_amount,
        })
    return enriched

# ---------------- Creator Dashboard ----------------
def _tier(ocv: float) -> str:
    if ocv >= 50.0: return "DIAMOND"
    if ocv >= 20.0: return "PLATINUM"
    if ocv >= 10.0: return "GOLD"
    if ocv >= 5.0:  return "SILVER"
    if ocv >= 1.0:  return "BRONZE"
    return "ROOKIE"

def _elo(ocv: float) -> int:
    # simple deterministic mapping based on ocv
    return int(1000 + min(ocv, 50.0) * 60)

@api.get("/dashboard/creator")
async def creator_dashboard(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """
    Creator dashboard – returns the exact same payload shape as the original
    MongoDB implementation, but all data is fetched via Supabase.
    """
    # ------------------------------------------------------------------
    # 1️⃣  Authentication & role check
    # ------------------------------------------------------------------
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "CREATOR")

    # ------------------------------------------------------------------
    # 2️⃣  Load creator's campaigns (limit 500)
    # ------------------------------------------------------------------
    camps_resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("creator_id", user["user_id"])
        .limit(500)
        .execute()
    )
    camps = camps_resp.data if hasattr(camps_resp, "data") else camps_resp.get("data", [])
    camp_ids = [c["campaign_id"] for c in camps]

    # ------------------------------------------------------------------
    # 3️⃣  Load all clips for those campaigns (limit 5 000)
    # ------------------------------------------------------------------
    clips_resp = (
        supabase.table("clips")
        .select("*")
        .in_("campaign_id", camp_ids)
        .eq("is_deleted", False)
        .limit(5000)
        .execute()
    )
    clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])

    # ---------------------------------------------------------------------------------------------
    # 4️⃣  Core aggregates
    # ---------------------------------------------------------------------------------------------
    total_views = sum(c.get("views", 0) for c in clips)
    total_clips = len(clips)
    editors_set = {c["editor_id"] for c in clips}
    avg_retention = (
        round(sum(c.get("retention_pct", 0) for c in clips) / len(clips), 2)
        if clips
        else 0.0
    )
    total_spend = sum(
        float(c.get("bounty_pool", 0)) for c in camps if c.get("escrow_funded")
    )

    # ------------------------------------------------------------------
    # 5️⃣  Top performing clips (max 6) with projected editor info
    # ------------------------------------------------------------------
    top_clips = sorted(clips, key=lambda x: float(x.get("ocv") or 0.0), reverse=True)[:6]
    enriched_clips = []
    for cl in top_clips:
        editor_resp = (
            supabase.table("users")
            .select("user_id,name,username,avatar_url")
            .eq("user_id", cl["editor_id"])
            .single()
            .execute()
        )
        ed = editor_resp.data if hasattr(editor_resp, "data") else editor_resp.get("data")
        enriched_clips.append(
            {
                "clip_id": cl.get("clip_id"),
                "clip_url": cl.get("clip_url"),
                "platform": cl.get("platform"),
                "views": cl.get("views"),
                "retention_pct": cl.get("retention_pct"),
                "engagement_pct": cl.get("engagement_pct"),
                "points": cl.get("points"),
                "ocv": float(cl.get("ocv") or 0.0),
                "thumbnail": (cl.get("yt_meta") or {}).get("thumbnail"),
                "editor": clean_doc(ed) if ed else None,
            }
        )

    # ------------------------------------------------------------------
    # 6️⃣  Top editors aggregation + earnings via participations
    # ------------------------------------------------------------------
    by_editor: dict[str, dict] = {}
    for cl in clips:
        agg = by_editor.setdefault(
            cl["editor_id"],
            {"views": 0, "points": 0, "ocv": 0.0, "earnings": 0.0, "clips": 0},
        )
        agg["views"] += cl.get("views", 0)
        agg["points"] += cl.get("points", 0)
        agg["ocv"] += float(cl.get("ocv") or 0.0)
        agg["clips"] += 1

    # Earnings: fetch all participations for the creator's campaigns
    parts_resp = (
        supabase.table("participations")
        .select("*")
        .in_("campaign_id", camp_ids)
        .limit(5000)
        .execute()
    )
    parts_all = parts_resp.data if hasattr(parts_resp, "data") else parts_resp.get("data", [])
    for p in parts_all:
        eid = p.get("editor_id")
        if eid in by_editor:
            by_editor[eid]["earnings"] += float(p.get("payout_amount", 0))

    top_editors = sorted(
        by_editor.items(), key=lambda x: x[1]["ocv"], reverse=True
    )[:6]
    enriched_editors = []
    for eid, agg in top_editors:
        editor_resp = (
            supabase.table("users")
            .select("user_id,name,username,avatar_url,lifetime_points")
            .eq("user_id", eid)
            .single()
            .execute()
        )
        ed = editor_resp.data if hasattr(editor_resp, "data") else editor_resp.get("data")
        # Compute lifetime ocv dynamically
        user_clips_resp = (
            supabase.table("clips")
            .select("ocv")
            .eq("editor_id", eid)
            .eq("is_deleted", False)
            .execute()
        )
        all_user_clips = user_clips_resp.data or []
        lifetime_ocv = sum(float(c.get("ocv") or 0.0) for c in all_user_clips)

        enriched_editors.append(
            {
                "editor": clean_doc(ed) if ed else None,
                "views_generated": agg["views"],
                "earnings_generated": round(agg["earnings"], 2),
                "points": round(agg["points"], 2),
                "ocv": round(agg["ocv"], 2),
                "elo": _elo(lifetime_ocv),
                "tier": _tier(lifetime_ocv),
            }
        )

    # ------------------------------------------------------------------
    # 7️⃣  Timeline (last 6 months) – uses `submitted_at` & YYYY‑MM format
    # ------------------------------------------------------------------
    from collections import defaultdict

    bucket = defaultdict(lambda: {"views": 0, "clips": 0, "points": 0, "ocv": 0.0})
    for cl in clips:
        ts = cl.get("submitted_at", "")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            key = dt.strftime("%Y-%m")
            bucket[key]["views"] += cl.get("views", 0)
            bucket[key]["clips"] += 1
            bucket[key]["points"] += cl.get("points", 0)
            bucket[key]["ocv"] += float(cl.get("ocv") or 0.0)
        except Exception:
            pass
    timeline = [{ "month": k, **v } for k, v in sorted(bucket.items())][-6:]

    # ------------------------------------------------------------------
    # 8️⃣  Content‑type distribution (pie‑chart data)
    # ------------------------------------------------------------------
    type_dist = defaultdict(int)
    for c in camps:
        type_dist[c.get("content_type", "OTHER")] += 1
    content_type_distribution = [
        {"name": k, "value": v} for k, v in type_dist.items()
    ]

    # ------------------------------------------------------------------
    # 9️⃣  Assemble final response (exact shape)
    # ------------------------------------------------------------------
    return {
        "stats": {
            "total_views": total_views,
            "total_clips": total_clips,
            "total_editors": len(editors_set),
            "avg_retention": avg_retention,
            "total_spend": round(total_spend, 2),
        },
        "top_clips": enriched_clips,
        "top_editors": enriched_editors,
        "timeline": timeline,
        "content_type_distribution": content_type_distribution,
    }

# ---------------- Talent (editor discovery) ----------------
# 1️⃣ Load up to 500 editors
@api.get("/talent")
async def talent(
    niche: Optional[str] = None,
    tier: Optional[str] = None,
    min_lifetime_views: int = 0,
    min_retention: float = 0.0,
    sort_by: str = "elo_desc"
):
    users_resp = (
        supabase.table("users")
        .select("*")
        .eq("role", "EDITOR")
        .limit(500)
        .execute()
    )
    users = users_resp.data if hasattr(users_resp, "data") else users_resp.get("data", [])

    out = []
    for u in users:
        uid = u["user_id"]

        # 2️⃣ Retrieve up to 2000 clips for this editor
        clips_resp = (
            supabase.table("clips")
            .select("*")
            .eq("editor_id", uid)
            .eq("is_deleted", False)
            .limit(2000)
            .execute()
        )
        clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])

        lifetime_views = sum(c.get("views", 0) for c in clips)
        avg_ret = (
            round(sum(c.get("retention_pct", 0) for c in clips) / len(clips), 2)
            if clips
            else 0.0
        )

        # 3️⃣ Number of campaigns the editor has completed
        count_resp = (
            supabase.table("participations")
            .select("*", count="exact")
            .eq("editor_id", uid)
            .execute()
        )
        camps_completed = (
            count_resp.count
            if hasattr(count_resp, "count")
            else count_resp.get("count", 0)
        )

        lp = float(u.get("lifetime_points", 0))
        t = _tier(lp)

        # 4️⃣ Apply filters
        if tier and t != tier:
            continue
        if niche and niche.lower() not in (u.get("bio", "") or "").lower():
            continue
        if lifetime_views < min_lifetime_views:
            continue
        if avg_ret < min_retention:
            continue

        # 5️⃣ Assemble output entry (exact shape)
        out.append(
            {
                "user_id": uid,
                "name": u.get("display_name") or u.get("name"),
                "username": u.get("username"),
                "avatar_url": u.get("avatar_url"),
                "bio": u.get("bio", ""),
                "lifetime_points": lp,
                "elo": _elo(lp),
                "tier": t,
                "lifetime_views": lifetime_views,
                "lifetime_earnings": float(u.get("total_earnings", 0)),
                "avg_retention": avg_ret,
                "campaigns_completed": camps_completed,
            }
        )

    # 6️⃣ Sorting according to the requested field
    if sort_by == "elo_desc":
        out.sort(key=lambda x: x["elo"], reverse=True)
    elif sort_by == "views_desc":
        out.sort(key=lambda x: x["lifetime_views"], reverse=True)
    elif sort_by == "retention_desc":
        out.sort(key=lambda x: x["avg_retention"], reverse=True)

    return out

# ---------------- Participations ----------------

@api.post("/campaigns/{campaign_id}/join")
async def join_campaign(
    payload: JoinCampaignIn,
    campaign_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    print("=== JOIN CAMPAIGN ===")
    print("Campaign:", campaign_id)

    user = await get_current_user(
        request,
        session_token,
        authorization
    )

    print("User:", user["user_id"])

    # rest of your code...
    """Join a campaign as an editor, linking a YouTube channel."""
    # ------------------------------------------------------------------
    # 1️⃣  Authentication & role check
    # ------------------------------------------------------------------
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "EDITOR")

    # ------------------------------------------------------------------
    # 2️⃣  Load the campaign (Supabase)
    # ------------------------------------------------------------------
    camp_resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("campaign_id", campaign_id)
        .single()
        .execute()
    )
    camp = camp_resp.data if hasattr(camp_resp, "data") else camp_resp.get("data")
    print("DEBUG 1")
    if not camp:
        raise HTTPException(404, "DEBUG_CAMPAIGN_NOT_FOUND")

    if camp.get("status") != "ACTIVE" or not camp.get("escrow_funded"):
        raise HTTPException(400, "Campaign not joinable")

    # ------------------------------------------------------------------
    # 3️⃣  Resolve YouTube channel
    # ------------------------------------------------------------------
    channel = fetch_youtube_channel(payload.youtube_channel)
    print("CHANNEL DATA:")
    print(channel)
    if not channel:
        raise HTTPException(
            400,
            "Could not resolve YouTube channel. Paste full channel URL or @handle.",
        )

    # ------------------------------------------------------------------
    # 4️⃣  Check for an existing participation
    # ------------------------------------------------------------------
    print("REACHED PARTICIPATION CHECK")
    part_resp = (
        supabase.table("participations")
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("editor_id", user["user_id"])
        .execute()
    )
    existing = part_resp.data or []
    if existing:
        # Update YouTube channel metadata on the existing participation
        upd = {
            "yt_channel": channel,
            "yt_channel_id": channel.get("channel_id"),
            "yt_channel_name": channel.get("title") or channel.get("handle"),
        }
        supabase.table("participations")\
            .update(upd)\
            .eq("participation_id", existing[0]["participation_id"])\
            .execute()
        print("Saving channel:", upd["yt_channel_id"], upd["yt_channel_name"])
        # Reflect updates in the returned object
        existing[0]["yt_channel"] = channel
        existing[0]["yt_channel_id"] = upd["yt_channel_id"]
        existing[0]["yt_channel_name"] = upd["yt_channel_name"]
        return clean_doc(existing[0])

    # ------------------------------------------------------------------
    # 5️⃣  Create a new participation document
    # ------------------------------------------------------------------
    doc = {
        "participation_id": new_id("part"),
        "campaign_id": campaign_id,
        "editor_id": user["user_id"],
        "yt_channel": channel,
        "yt_channel_id": channel.get("channel_id"),
        "yt_channel_name": channel.get("title") or channel.get("handle"),
        "joined_at": now_iso(),
        "total_points": 0.0,
        "rank": None,
        "reward_share_pct": None,
        "payout_amount": 0.0,
        "payout_status": "PENDING",
    }
    print("Saving channel:", doc["yt_channel_id"], doc["yt_channel_name"])
    supabase.table("participations").insert(doc).execute()
    return clean_doc(doc)

# ---------------- Submit Short ----------------

class SubmitShortIn(BaseModel):
    short_url: str

YT_SHORTS_RE = re.compile(r"youtube\.com/shorts/([A-Za-z0-9_-]{11})")

def extract_shorts_video_id(url: str) -> Optional[str]:
    """Extract the 11-char video ID from a YouTube Shorts URL."""
    m = YT_SHORTS_RE.search(url or "")
    return m.group(1) if m else None

@api.post("/campaigns/{campaign_id}/submit-short")
async def submit_short(
    campaign_id: str,
    payload: SubmitShortIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    # 1️⃣ Auth
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "EDITOR")
    # Ensure campaign is active and funded
    if camp.get("status") != "ACTIVE" or not camp.get("escrow_funded"):
        raise HTTPException(400, "Campaign is not active or not funded for short submission")

    # 2️⃣ Verify enrollment
    part_resp = (
        supabase.table("participations")
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("editor_id", user["user_id"])
        .execute()
    )
    parts = part_resp.data or []
    if not parts:
        raise HTTPException(403, "You must join the campaign before submitting.")
    participation = parts[0]

    # 3️⃣ Extract Shorts video ID
    video_id = extract_shorts_video_id(payload.short_url)
    if not video_id:
        raise HTTPException(400, "Invalid YouTube Shorts URL. Expected format: https://youtube.com/shorts/VIDEO_ID")

    # 4️⃣ Call YouTube Data API for video details
    if not YOUTUBE_API_KEY:
        raise HTTPException(500, "YouTube API key not configured.")

    try:
        yt_resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"id": video_id, "part": "snippet", "key": YOUTUBE_API_KEY},
            timeout=15,
        )
        yt_resp.raise_for_status()
        yt_items = yt_resp.json().get("items", [])
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.warning(f"YouTube API call failed: {e}")
        raise HTTPException(502, "Failed to verify video with YouTube.")

    if not yt_items:
        raise HTTPException(400, "Video not found on YouTube. Check the URL.")

    snippet = yt_items[0].get("snippet", {})
    video_channel_id = snippet.get("channelId")
    video_title = snippet.get("title", "")

    # Debug logs for verification
    print("Expected channel:", participation.get("yt_channel_id"))
    print("Video channel:", video_channel_id)

    # 5️⃣ Verify channel ownership
    enrolled_channel_id = participation.get("yt_channel_id")
    if not enrolled_channel_id or enrolled_channel_id != video_channel_id:
        raise HTTPException(
            400,
            "This Short was not uploaded on your verified channel.",
        )

    # 6️⃣ Duplicate protection (backend check before unique-index enforcement)
    dup_resp = (
        supabase.table("clips")
        .select("clip_id")
        .eq("campaign_id", campaign_id)
        .eq("video_id", video_id)
        .execute()
    )
    if dup_resp.data:
        raise HTTPException(400, "This Short has already been submitted.")

    # 7️⃣ Create clip
    doc = {
        "clip_id": new_id("clip"),
        "campaign_id": campaign_id,
        "editor_id": user["user_id"],
        "video_id": video_id,
        
        "clip_url": payload.short_url,
        "channel_id": video_channel_id,
        "title": video_title,
        "platform": "YOUTUBE_SHORTS",
        "views": 0,
        "retention_pct": 0.0,
        "engagement_pct": 0.0,
        "points": 0.0,
        "status": "PENDING",
        "submitted_at": now_iso(),
    }
    supabase.table("clips").insert(doc).execute()

    # 8️⃣ Recompute campaign aggregates
    await recompute_campaign(campaign_id)

    return clean_doc(doc)

# ---------------- Clips ----------------
async def recompute_campaign(campaign_id: str):
    """
    Recalculate the total points for a campaign and update each editor's
    participation record (total_points, rank, reward_share_pct) using Supabase.
    The response shape and business logic are identical to the original MongoDB version.
    """
    # ------------------------------------------------------------------
    # 1️⃣ Fetch all clips for the campaign (max 10 000)
    # ------------------------------------------------------------------
    clips_resp = (
        supabase.table("clips")
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("is_deleted", False)
        .limit(10000)
        .execute()
    )
    clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])

    # ------------------------------------------------------------------
    # 2️⃣ Aggregate points and OCV per editor and totals
    editor_points: dict[str, float] = {}
    editor_ocv: dict[str, float] = {}
    total_points: float = 0.0
    total_ocv: float = 0.0
    for clip in clips:
        pts = clip.get("points", 0.0)
        ocv = float(clip.get("ocv") or 0.0)
        editor_id = clip.get("editor_id")
        editor_points[editor_id] = editor_points.get(editor_id, 0.0) + pts
        editor_ocv[editor_id] = editor_ocv.get(editor_id, 0.0) + ocv
        total_points += pts
        total_ocv += ocv

    # 3️⃣ Update the campaign's total_points field
    supabase.table("campaigns") \
        .update({"total_points": round(total_points, 2)}) \
        .eq("campaign_id", campaign_id) \
        .execute()

    # 4️⃣ Sort editors by campaign OCV (descending) to assign rank and share percentage
    sorted_parts = sorted(editor_ocv.items(), key=lambda x: x[1], reverse=True)
    for rank, (editor_id, ed_ocv) in enumerate(sorted_parts, start=1):
        share_pct = (ed_ocv / total_ocv * 100) if total_ocv > 0 else 0.0
        pts = editor_points.get(editor_id, 0.0)
        supabase.table("participations") \
            .update({
                "total_points": round(pts, 2), # Maintain DB column compatibility
                "rank": rank,
                "reward_share_pct": round(share_pct, 2),
            }) \
            .eq("campaign_id", campaign_id) \
            .eq("editor_id", editor_id) \
            .execute()

    # ------------------------------------------------------------------
    # 5️⃣ Nothing to return (implicit None)
    # ------------------------------------------------------------------
    return

@api.post("/clips")
async def submit_clip(
    payload: SubmitClipIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    # ------------------------------------------------------------------
    # 1️⃣ Auth & role check
    # ------------------------------------------------------------------
    user = await get_current_user(request, session_token, authorization)
    await require_role(user, "EDITOR")

    # ------------------------------------------------------------------
    # 2️⃣ Load campaign (Supabase replacement for `db.campaigns.find_one`)
    # ------------------------------------------------------------------
    campaign_resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("campaign_id", payload.campaign_id)
        .single()
        .execute()
    )
    c = campaign_resp.data
    if not c:
        raise HTTPException(404, "Campaign not found")
    if c["status"] != "ACTIVE" or not c.get("escrow_funded"):
        raise HTTPException(400, "Campaign not accepting clips")

    # ------------------------------------------------------------------
    # 3️⃣ Verify editor has joined the campaign
    # ------------------------------------------------------------------
    part_resp = (
        supabase.table("participations")
        .select("*")
        .eq("campaign_id", payload.campaign_id)
        .eq("editor_id", user["user_id"])
        .maybe_single()
        .execute()
    )
    part = part_resp.data if hasattr(part_resp, "data") else part_resp.get("data")
    if not part:
        raise HTTPException(400, "Join the campaign first")

    # ------------------------------------------------------------------
    # 4️⃣ Enforce global daily submission limit (10 clips / day)
    # ------------------------------------------------------------------
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_clips_resp = (
        supabase.table("clips")
        .select("clip_id")
        .eq("editor_id", user["user_id"])
        .gte("submitted_at", start_of_today.isoformat())
        .execute()
    )
    today_count = len(today_clips_resp.data or [])
    if today_count >= 10:
        raise HTTPException(400, "Daily submission limit reached. You can submit up to 10 clips per day.")

    # ------------------------------------------------------------------
    # 5️⃣ Extract YouTube video ID & fetch stats automatically
    # ------------------------------------------------------------------
    if payload.platform != "YOUTUBE_SHORTS":
        raise HTTPException(400, "Only YouTube Shorts is supported for auto-verification at this time.")

    yt_meta = fetch_youtube_stats(payload.clip_url)
    if not yt_meta:
        raise HTTPException(400, "Could not fetch stats from YouTube video. Please check the URL.")

    # ------------------------------------------------------------------
    # 6️⃣ Verify ownership against editor's verified YouTube channels
    # ------------------------------------------------------------------
    verified_channels = user.get("verified_yt_channels") or []
    clip_channel_id = yt_meta.get("channel_id")
    is_owner = False
    for ch in verified_channels:
        ch_id = ch.get("channel_id") or ch.get("id")
        ch_handle = (ch.get("handle") or "").lstrip("@").lower()
        clip_channel_title = (yt_meta.get("channel_title") or "").lower()
        
        if ch_id and ch_id == clip_channel_id:
            is_owner = True
            break
        if ch_handle and ch_handle in clip_channel_title:
            is_owner = True
            break

    if not is_owner:
        raise HTTPException(
            400,
            f"Channel mismatch — clip is from '{yt_meta.get('channel_title')}' (ID: {clip_channel_id}) "
            f"which is not in your verified YouTube channels. "
            "Please link this channel to your account first."
        )

    # Compute metrics automatically using backend OCV/points logic
    views = yt_meta.get("views", 0)
    likes = yt_meta.get("likes", 0)
    comments = yt_meta.get("comments", 0)
    
    # Calculate engagement_pct and points
    engagement_pct = round((likes + comments) / views * 100.0, 2) if views > 0 else 0.0
    retention_pct = 0.0  # Default to 0.0 since it cannot be fetched via public API
    
    pts = calc_points(views, retention_pct, engagement_pct)
    ocv_val = calculate_ocv(views, retention_pct, engagement_pct)

    # ------------------------------------------------------------------
    # 7️⃣ Build the clip document
    # ------------------------------------------------------------------
    doc = {
        "clip_id": new_id("clip"),
        "campaign_id": payload.campaign_id,
        "editor_id": user["user_id"],
        "platform": payload.platform,
        "clip_url": payload.clip_url,
        "views": views,
        "retention_pct": retention_pct,
        "engagement_pct": engagement_pct,
        "points": pts["points"],
        "retention_mult": pts["retention_mult"],
        "engagement_mult": pts["engagement_mult"],
        "hit_mult": pts["hit_mult"],
        "ocv": ocv_val,
        "analytics_screen_path": None,  # Removed manual input
        "analytics_verified": True,     # Auto-verified since it matched verified channels & API
        "yt_meta": yt_meta,
        "submitted_at": now_iso(),
        "video_id": yt_meta.get("video_id"),
        "channel_id": clip_channel_id,
        "title": yt_meta.get("title"),
        "channel_name": yt_meta.get("channel_title"),
        "is_deleted": False,
        "deleted_at": None,
    }

    # ------------------------------------------------------------------
    # 8️⃣ Persist the clip (Supabase replacement for `db.clips.insert_one`)
    # ------------------------------------------------------------------
    supabase.table("clips").insert(doc).execute()

    # ------------------------------------------------------------------
    # 9️⃣ Re‑compute campaign aggregates (unchanged)
    # ------------------------------------------------------------------
    await recompute_campaign(payload.campaign_id)

    # ------------------------------------------------------------------
    # 🔟 Update editor’s lifetime points (Supabase replacements for
    #    `db.clips.find` + `db.users.update_one`)
    # ------------------------------------------------------------------
    total_lifetime = 0.0
    clips_resp = (
        supabase.table("clips")
        .select("points")
        .eq("editor_id", user["user_id"])
        .eq("is_deleted", False)
        .execute()
    )
    for cl in clips_resp.data or []:
        total_lifetime += cl.get("points", 0)

    supabase.table("users").update(
        {"lifetime_points": round(total_lifetime, 2)}
    ).eq("user_id", user["user_id"]).execute()

    # ------------------------------------------------------------------
    # 11️⃣ Return the freshly created clip (shape unchanged)
    # ------------------------------------------------------------------
    return clean_doc(doc)

@api.get("/clips")
async def list_clips(campaign_id: Optional[str] = None, editor_id: Optional[str] = None):
    """Return up to 500 clips, optionally filtered by campaign or editor,
    ordered by newest (`submitted_at` descending). Each clip includes a
    lightweight `editor` sub‑object."""
    query = supabase.table("clips").select("*")
    if campaign_id:
        query = query.eq("campaign_id", campaign_id)
    if editor_id:
        query = query.eq("editor_id", editor_id)

    resp = (
        query.order("submitted_at", desc=True)
        .limit(500)
        .execute()
    )
    clips = resp.data if hasattr(resp, "data") else resp.get("data", [])

    for cl in clips:
        ed_resp = (
            supabase.table("users")
            .select("user_id,name,username,avatar_url")
            .eq("user_id", cl.get("editor_id"))
            .single()
            .execute()
        )
        ed = ed_resp.data if hasattr(ed_resp, "data") else ed_resp.get("data")
        cl["editor"] = clean_doc(ed) if ed else None

    return clips

@api.post("/youtube/fetch")
async def youtube_fetch(payload: dict, request: Request,
                        session_token: Optional[str] = Cookie(None),
                        authorization: Optional[str] = Header(None)):
    _ = await get_current_user(request, session_token, authorization)
    meta = fetch_youtube_stats(payload.get("clip_url", ""))
    if not meta:
        return {"ok": False, "message": "Could not fetch. Enter analytics manually."}
    # estimated engagement %: (likes+comments)/views *100
    engagement = 0.0
    if meta["views"] > 0:
        engagement = round((meta["likes"] + meta["comments"]) / meta["views"] * 100.0, 2)
    return {"ok": True, "views": meta["views"], "likes": meta["likes"],
            "comments": meta["comments"], "engagement_pct": engagement,
            "title": meta["title"]}

async def build_public_profile(user: dict):
    """Return a public profile for the user (Supabase version)."""
    uid = user["user_id"]
    role = user.get("role")
    
    if role == "CREATOR":
        # 1. Fetch campaigns
        camps_resp = (
            supabase.table("campaigns")
            .select("*")
            .eq("creator_id", uid)
            .limit(500)
            .execute()
        )
        camps = camps_resp.data if hasattr(camps_resp, "data") else camps_resp.get("data", [])
        camps = map_db_campaigns(camps)
        camp_ids = [c["campaign_id"] for c in camps]
        
        # 2. Fetch clips
        clips = []
        if camp_ids:
            clips_resp = (
                supabase.table("clips")
                .select("clip_id, campaign_id")
                .in_("campaign_id", camp_ids)
                .eq("is_deleted", False)
                .limit(5000)
                .execute()
            )
            clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])
            
        # 3. Fetch participations
        parts = []
        if camp_ids:
            parts_resp = (
                supabase.table("participations")
                .select("campaign_id, payout_amount")
                .in_("campaign_id", camp_ids)
                .execute()
            )
            parts = parts_resp.data if hasattr(parts_resp, "data") else parts_resp.get("data", [])
            
        # Helper maps
        clips_by_camp = {}
        for c in clips:
            cid = c["campaign_id"]
            clips_by_camp[cid] = clips_by_camp.get(cid, 0) + 1
            
        spend_by_camp = {}
        for p in parts:
            cid = p["campaign_id"]
            spend_by_camp[cid] = spend_by_camp.get(cid, 0.0) + float(p.get("payout_amount") or 0.0)
            
        # Assemble campaign history for creator
        history = []
        for c in camps:
            cid = c["campaign_id"]
            history.append({
                "campaign_id": cid,
                "title": c.get("title"),
                "description": c.get("description") or "",
                "status": c.get("status"),
                "bounty_pool": float(c.get("bounty_pool") or 0.0),
                "thumbnail_url": c.get("thumbnail_url") or "",
                "amount_distributed": spend_by_camp.get(cid, 0.0),
                "submissions_count": clips_by_camp.get(cid, 0),
                "created_at": c.get("created_at"),
            })
            
        # Sort by creation date descending
        history.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        
        total_budget_distributed = sum(spend_by_camp.values())
        total_clips_received = len(clips)
        active_campaigns = sum(1 for c in camps if c.get("status") == "ACTIVE")
        
        return {
            "user_id": uid,
            "username": user.get("username"),
            "display_name": user.get("display_name") or user.get("name"),
            "name": user.get("name"),
            "avatar_url": user.get("avatar_url"),
            "bio": user.get("bio", ""),
            "role": role,
            "socials": user.get("socials") or {},
            "website_url": user.get("website") or "",
            "creator_stats": {
                "campaigns_created": len(camps),
                "total_budget_distributed": total_budget_distributed,
                "total_clips_received": total_clips_received,
                "active_campaigns": active_campaigns
            },
            "campaign_history": history,
            "created_at": user.get("created_at"),
        }
    # Load editor's clips (Supabase)
    clips_resp = (
        supabase.table("clips")
        .select("*")
        .eq("editor_id", uid)
        .eq("is_deleted", False)
        .limit(2000)
        .execute()
    )
    clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])
    # Load editor's participations (Supabase)
    parts_resp = (
        supabase.table("participations")
        .select("*")
        .eq("editor_id", uid)
        .limit(2000)
        .execute()
    )
    parts = parts_resp.data if hasattr(parts_resp, "data") else parts_resp.get("data", [])
    # Core aggregates
    total_views = sum(c.get("views", 0) for c in clips) + sum((fc.get("views") or 0) for fc in (user.get("featured_clips") or []))
    total_points = user.get("lifetime_points") or sum(c.get("points", 0) for c in clips)
    lifetime_ocv = sum(float(c.get("ocv") or 0.0) for c in clips)
    badges = await compute_badges(uid)
    # Batch fetch campaigns referenced by participations
    campaign_ids = list({p["campaign_id"] for p in parts if p.get("campaign_id")})
    campaigns_map: dict[str, dict] = {}
    if campaign_ids:
        camps_resp = (
            supabase.table("campaigns")
            .select("campaign_id,title,status")
            .in_("campaign_id", campaign_ids)
            .execute()
        )
        camps = camps_resp.data if hasattr(camps_resp, "data") else camps_resp.get("data", [])
        campaigns_map = {c["campaign_id"]: c for c in camps}
    # Assemble campaign history (preserving original shape)
    history = []
    for p in parts:
        cid = p.get("campaign_id")
        c = campaigns_map.get(cid)
        if not c:
            continue
        # Calculate OCV for this campaign
        camp_ocv = sum(float(cl.get("ocv") or 0.0) for cl in clips if cl.get("campaign_id") == cid)
        history.append({
            "campaign_id": c["campaign_id"],
            "title": c["title"],
            "status": c["status"],
            "rank": p.get("rank"),
            "points": p.get("total_points", 0),
            "ocv": round(camp_ocv, 2),
            "payout": p.get("payout_amount", 0),
        })
    history.sort(key=lambda x: (x.get("rank") or 999))
    # Return the exact payload expected by the client
    return {
        "user_id": uid,
        "username": user.get("username"),
        "display_name": user.get("display_name") or user.get("name"),
        "name": user.get("name"),
        "avatar_url": user.get("avatar_url"),
        "bio": user.get("bio", ""),
        "role": user.get("role"),
        "socials": user.get("socials") or {},
        "featured_clips": user.get("featured_clips") or [],
        "total_views_generated": total_views,
        "total_points_earned": round(total_points, 2),
        "lifetime_ocv": round(lifetime_ocv, 2),
        "badges": badges,
        "campaign_history": history,
        "created_at": user.get("created_at"),
    }

# ---------------- Leaderboard ----------------
@api.get("/leaderboard/campaign/{campaign_id}")
async def leaderboard_campaign(
    campaign_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    # -------------------------------------------------
    # Check if user is Admin for bank details access
    # -------------------------------------------------
    is_admin = False
    try:
        current_user = await get_current_user(request, session_token, authorization)
        is_admin = current_user.get("role") == "ADMIN"
    except Exception:
        pass

    # -------------------------------------------------
    # 1️⃣  Fetch all participations for the campaign,
    #    ordered by total points (descending).
    # -------------------------------------------------
    parts_resp = (
        supabase.table("participations")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("total_points", desc=True)
        .limit(200)
        .execute()
    )
    parts = parts_resp.data if hasattr(parts_resp, "data") else parts_resp.get("data", [])

    # -------------------------------------------------
    # 2️⃣  Load the campaign document to compute pool & total.
    # -------------------------------------------------
    camp_resp = (
        supabase.table("campaigns")
        .select("bounty_pool,total_points")
        .eq("campaign_id", campaign_id)
        .single()
        .execute()
    )
    camp = camp_resp.data if hasattr(camp_resp, "data") else camp_resp.get("data")
    pool_net = (camp["bounty_pool"] * (1 - PLATFORM_FEE / 100.0)) if camp else 0.0

    # Fetch all clips in this campaign to sum the total campaign OCV
    all_clips_resp = (
        supabase.table("clips")
        .select("ocv")
        .eq("campaign_id", campaign_id)
        .eq("is_deleted", False)
        .limit(10000)
        .execute()
    )
    all_clips = all_clips_resp.data if hasattr(all_clips_resp, "data") else all_clips_resp.get("data", [])
    total_campaign_ocv = sum(float(c.get("ocv") or 0.0) for c in all_clips)

    # -------------------------------------------------
    # 3️⃣  Assemble the leaderboard entries.
    # -------------------------------------------------
    out = []
    for p in parts:
        # Editor (user) info
        editor_resp = (
            supabase.table("users")
            .select("user_id,name,username,avatar_url,payout_upi,socials")
            .eq("user_id", p["editor_id"]).single()
            .execute()
        )
        editor = editor_resp.data if hasattr(editor_resp, "data") else editor_resp.get("data")
        
        # Strip bank details if not admin, pack into dictionary if admin
        if editor:
            socials = editor.get("socials") or {}
            bank_details = socials.get("bank_details") or {}
            p_method = bank_details.get("payout_method") or "UPI"
            u_id = bank_details.get("upi_id") or editor.get("payout_upi")
            b_name = bank_details.get("bank_name")
            b_acc_num = bank_details.get("bank_account_number")
            b_acc_name = bank_details.get("bank_account_name")
            b_ifsc = bank_details.get("bank_ifsc")
            
            if is_admin:
                editor["bank_details"] = {
                    "payout_method": p_method,
                    "upi_id": u_id,
                    "bank_name": b_name,
                    "bank_account_number": b_acc_num,
                    "bank_account_name": b_acc_name,
                    "bank_ifsc": b_ifsc
                }
            else:
                editor.pop("payout_upi", None)
                editor.pop("socials", None)

        # Clips submitted by this editor in this campaign
        clips_resp = (
            supabase.table("clips")
            .select("points,views,ocv")
            .eq("campaign_id", campaign_id)
            .eq("editor_id", p["editor_id"])
            .eq("is_deleted", False)
            .limit(100)
            .execute()
        )
        clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])
        # Best clip (by points)
        best = max(clips, key=lambda x: x.get("points", 0), default=None)
        # Calculate total OCV for this editor in this campaign
        total_ocv = sum(float(c.get("ocv") or 0.0) for c in clips)
        # Share of total campaign OCV
        share = (total_ocv / total_campaign_ocv) if total_campaign_ocv > 0 else 0.0

        out.append(
            {
                "editor": clean_doc(editor) if editor else None,
                "yt_channel": p.get("yt_channel"),
                "total_points": p["total_points"],
                "total_ocv": round(total_ocv, 2),
                "clips_submitted": len(clips),
                "best_clip": {"points": best["points"], "views": best["views"]} if best else None,
                "reward_share_pct": round(share * 100, 2),
                "projected_payout": round(pool_net * share, 2),
                "participation_id": p.get("participation_id"),
                "payout_status": "PAID" if p.get("payout_status") == "COMPLETED" else "PENDING",
                "payout_amount": p.get("payout_amount"),
                "payment_reference": p.get("payment_reference"),
                "paid_at": p.get("paid_at")
            }
        )

    # Sort by total_ocv descending
    out.sort(key=lambda x: x["total_ocv"], reverse=True)

    # Update displayed rank based on sorted OCV
    for rank, entry in enumerate(out, start=1):
        entry["rank"] = rank

    return out

@api.get("/leaderboard/lifetime")
async def leaderboard_lifetime(limit: int = 25):
    """Lifetime editor leaderboard – ordered by lifetime OCV descending.
    Returns rank, a cleaned `editor` object, `lifetime_points`, `lifetime_ocv`, and
    `total_earnings` for each editor.
    """
    users_resp = (
        supabase.table("users")
        .select("*")
        .eq("role", "EDITOR")
        .limit(1000)
        .execute()
    )
    users = users_resp.data or []

    # Fetch active clips to sum OCV
    clips_resp = (
        supabase.table("clips")
        .select("editor_id,ocv")
        .eq("is_deleted", False)
        .limit(10000)
        .execute()
    )
    clips = clips_resp.data or []

    editor_ocvs = {}
    for c in clips:
        eid = c.get("editor_id")
        if eid:
            editor_ocvs[eid] = editor_ocvs.get(eid, 0.0) + float(c.get("ocv") or 0.0)

    standings = []
    for u in users:
        eid = u["user_id"]
        ocv_val = editor_ocvs.get(eid, 0.0)
        standings.append({
            "editor": clean_doc(u),
            "lifetime_points": u.get("lifetime_points", 0.0),
            "lifetime_ocv": round(ocv_val, 2),
            "total_earnings": u.get("total_earnings", 0.0),
        })

    # Sort standings by lifetime OCV descending
    standings.sort(key=lambda x: x["lifetime_ocv"], reverse=True)

    # Assign ranks and limit
    out = []
    for i, entry in enumerate(standings[:limit], start=1):
        entry["rank"] = i
        out.append(entry)
    return out

@api.get("/leaderboard/monthly")
async def leaderboard_monthly(limit: int = 25):
    # Start of the current month (UTC)
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Fetch all clips from the start of the month onward using Supabase
    clips_resp = (
        supabase.table("clips")
        .select("editor_id,points,submitted_at,ocv")
        .gte("submitted_at", start.isoformat())
        .eq("is_deleted", False)
        .execute()
    )
    clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])
    # Aggregate points and clip counts per editor in Python
    editor_stats: dict[str, dict] = {}
    for clip in clips:
        editor_id = clip.get("editor_id")
        if not editor_id:
            continue
        stats = editor_stats.setdefault(editor_id, {"points": 0.0, "clips": 0, "ocv": 0.0})
        stats["points"] += clip.get("points", 0.0)
        stats["clips"] += 1
        stats["ocv"] += float(clip.get("ocv") or 0.0)
    # Sort editors by monthly OCV descending and respect the limit
    sorted_editors = sorted(editor_stats.items(), key=lambda x: x[1]["ocv"], reverse=True)[:limit]
    out = []
    for i, (editor_id, stats) in enumerate(sorted_editors, start=1):
        user_resp = (
            supabase.table("users")
            .select("*")
            .eq("user_id", editor_id)
            .single()
            .execute()
        )
        user = user_resp.data if hasattr(user_resp, "data") else user_resp.get("data")
        out.append({
            "rank": i,
            "editor": clean_doc(user) if user else None,
            "monthly_points": round(stats["points"], 2),
            "monthly_ocv": round(stats["ocv"], 2),
            "clips": stats["clips"],
        })
    return out

# ---------------- Dashboard ----------------
@api.get("/dashboard")
async def dashboard(request: Request,
                    session_token: Optional[str] = Cookie(None),
                    authorization: Optional[str] = Header(None)):

    user = await get_current_user(request, session_token, authorization)
    if not user.get("role"):
        return {"needs_role": True}

    if user.get("role") == "EDITOR":
        parts_resp = (
            supabase.table("participations")
            .select("*")
            .eq("editor_id", user["user_id"])
            .limit(500)
            .execute()
        )
        parts = parts_resp.data or []
        clips_resp = (
            supabase.table("clips")
            .select("*")
            .eq("editor_id", user["user_id"])
            .order("submitted_at", desc=True)
            .limit(50)
            .execute()
        )
        clips = clips_resp.data or []
        # Calculate paid and pending earnings dynamically
        paid_earnings = sum(float(p.get("payout_amount") or 0.0) for p in parts if p.get("payout_status") == "COMPLETED")
        pending_earnings = sum(float(p.get("payout_amount") or 0.0) for p in parts if p.get("payout_status") == "PENDING")

        camp_ids = [p["campaign_id"] for p in parts if p.get("campaign_id")]
        campaigns_map = {}
        if camp_ids:
            camps_resp = (
                supabase.table("campaigns")
                .select("*")
                .in_("campaign_id", camp_ids)
                .limit(500)
                .execute()
            )
            campaigns_map = {c["campaign_id"]: c for c in (camps_resp.data or [])}

        # Calculate lifetime ocv dynamically
        all_user_clips_resp = (
            supabase.table("clips")
            .select("ocv")
            .eq("editor_id", user["user_id"])
            .eq("is_deleted", False)
            .execute()
        )
        all_user_clips = all_user_clips_resp.data or []
        lifetime_ocv = sum(float(c.get("ocv") or 0.0) for c in all_user_clips)

        active_campaigns = []
        for p in parts:
            campaign = campaigns_map.get(p.get("campaign_id"))
            if not campaign or campaign.get("status") != "ACTIVE":
                continue
            my_campaign_clips = [c for c in clips if c.get("campaign_id") == campaign["campaign_id"]]
            my_clips = len(my_campaign_clips)
            total_ocv = sum(float(c.get("ocv") or 0.0) for c in my_campaign_clips)

            p_enriched = dict(p)
            p_enriched["total_ocv"] = round(total_ocv, 2)

            active_campaigns.append({
                "campaign": campaign,
                "participation": p_enriched,
                "my_clips": my_clips,
            })

        return {
            "role": "EDITOR",
            "stats": {
                "paid_earnings": round(paid_earnings, 2),
                "pending_earnings": round(pending_earnings, 2),
                "lifetime_ocv": round(lifetime_ocv, 2),
                "campaigns_joined": len(parts),
                "current_rank": min([p.get("rank") for p in parts if p.get("rank")] or [0]),
            },
            "active_campaigns": active_campaigns,
            "recent_clips": clips[:8],
            "withdrawal_requests": [],
            "my_campaigns": [],
            "top_editors": []
        }

    camps_resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("creator_id", user["user_id"])
        .limit(500)
        .execute()
    )
    camps = camps_resp.data or []
    camp_ids = [c["campaign_id"] for c in camps]
    clips = []
    if camp_ids:
        clips_resp = (
            supabase.table("clips")
            .select("*")
            .in_("campaign_id", camp_ids)
            .eq("is_deleted", False)
            .limit(5000)
            .execute()
        )
        clips = clips_resp.data or []

    total_paid_out = 0.0
    for c in camps:
        if c.get("status") == "COMPLETED":
            total_paid_out += float(c.get("bounty_pool") or 0.0) * 0.85

    return {
        "role": user.get("role"),
        "stats": {
            "campaigns_posted": len(camps),
            "total_clips": len(clips),
            "total_paid_out": round(total_paid_out, 2),
            "in_escrow": round(sum(float(c.get("bounty_pool") or 0.0) for c in camps if c.get("status") == "ACTIVE"), 2),
        },
        "active_campaigns": [],
        "recent_clips": [],
        "my_campaigns": camps,
        "top_editors": []
    }

# ---------------- Profile ----------------
@api.get("/users/{user_id}")
async def get_user_profile(user_id: str):
# 1️⃣ Load base user document
    user_resp = (
        supabase.table("users")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    u = user_resp.data if hasattr(user_resp, "data") else user_resp.get("data")
    if not u:
        raise HTTPException(404, "Not found")

    # 2️⃣ Editor‑specific data
    if u.get("role") == "EDITOR":
        # a) Recent top‑scoring clips (max 12)
        clips_resp = (
            supabase.table("clips")
            .select("*")
            .eq("editor_id", user_id)
            .eq("is_deleted", False)
            .order("ocv", desc=True)
            .limit(12)
            .execute()
        )
        clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])
        # b) Number of campaigns the editor has participated in
        count_resp = (
            supabase.table("participations")
            .select("*", count="exact")
            .eq("editor_id", user_id)
            .execute()
        )
        campaigns_played = (
            count_resp.count
            if hasattr(count_resp, "count")
            else count_resp.get("count", 0)
        )
        # Calculate lifetime_ocv dynamically from all editor clips
        all_clips_resp = (
            supabase.table("clips")
            .select("ocv")
            .eq("editor_id", user_id)
            .eq("is_deleted", False)
            .execute()
        )
        all_clips = all_clips_resp.data or []
        lifetime_ocv = sum(float(c.get("ocv") or 0.0) for c in all_clips)
        u["lifetime_ocv"] = round(lifetime_ocv, 2)

        u["clips"] = clips
        u["campaigns_played"] = campaigns_played

    # 3️⃣ Creator‑specific data
    elif u.get("role") == "CREATOR":
        # a) List of campaigns created by this user (max 50)
        camps_resp = (
            supabase.table("campaigns")
            .select("*")
            .eq("creator_id", user_id)
            .limit(50)
            .execute()
        )
        camps = camps_resp.data if hasattr(camps_resp, "data") else camps_resp.get("data", [])
        u["campaigns"] = camps
        # b) Total amount paid out across all creator's campaigns
        total_paid = 0.0
        for c in camps:
            payouts_resp = (
                supabase.table("payouts")
                .select("amount")
                .eq("campaign_id", c["campaign_id"]) 
                .limit(200)
                .execute()
            )
            payouts = payouts_resp.data if hasattr(payouts_resp, "data") else payouts_resp.get("data", [])
            total_paid += sum(p.get("amount", 0) for p in payouts)
        u["total_paid_out"] = round(total_paid, 2)

    # 4️⃣ Return cleaned document
    return clean_doc(u)

# ---------------- Social Verification ----------------
@api.get("/social/verified-channels")
async def get_verified_channels(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """Return the list of verified YouTube channels for the current editor."""
    user = await get_current_user(request, session_token, authorization)
    channels = user.get("verified_yt_channels") or []
    return {"youtube": channels}

@api.post("/social/verify-youtube")
async def add_verified_youtube(
    payload: VerifyYouTubeIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """Verify a YouTube channel and add it to the editor's verified channels list."""
    user = await get_current_user(request, session_token, authorization)
    channel = fetch_youtube_channel(payload.youtube_channel)

    if not channel:
        raise HTTPException(
            400,
            "Could not resolve YouTube channel."
        )

    db_code = user.get("yt_verification_code")

    if not db_code:
        raise HTTPException(
            400,
            "Generate a verification code first."
        )

    if ":" in db_code:
        verification_code, ch_id = db_code.split(":", 1)
    else:
        verification_code = db_code
        ch_id = None

    # Fetch channel description via YouTube Data API (if API key is set)
    description = ""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        # If ch_id wasn't stored/resolved during start step, try to resolve it now
        if not ch_id and channel.get("handle"):
            try:
                resp = requests.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={"part": "snippet", "forHandle": channel.get("handle"), "key": api_key},
                    timeout=5,
                )
                resp.raise_for_status()
                channel_data = resp.json()
                items = channel_data.get("items", [])
                if items:
                    ch_id = items[0].get("id")
                    channel["channel_id"] = ch_id
                    description = items[0]["snippet"].get("description", "")
                    snippet = items[0]["snippet"]
                    if snippet.get("title"):
                        channel["title"] = snippet["title"]
                    if snippet.get("thumbnails", {}).get("default", {}).get("url"):
                        channel["thumbnail"] = snippet["thumbnails"]["default"]["url"]
            except Exception as e:
                logger.warning(f"Failed to resolve channel via forHandle: {e}")
        elif ch_id:
            try:
                resp = requests.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={"part": "snippet", "id": ch_id, "key": api_key},
                    timeout=5,
                )
                resp.raise_for_status()
                channel_data = resp.json()
                items = channel_data.get("items", [])
                if items:
                    description = items[0]["snippet"].get("description", "")
                    snippet = items[0]["snippet"]
                    if snippet.get("title"):
                        channel["title"] = snippet["title"]
                    if snippet.get("thumbnails", {}).get("default", {}).get("url"):
                        channel["thumbnail"] = snippet["thumbnails"]["default"]["url"]
                    channel["channel_id"] = ch_id
            except Exception as e:
                logger.debug(f"YT verification debug: entered_handle={channel.get('handle')}, resolved_channel_id={ch_id}, verification_code={verification_code}, description_len={len(description)}, description_repr={repr(description)}, code_in_description={verification_code in description}") 
                logger.warning(f"Failed to fetch channel description: {e}")
    else:
        if not ch_id:
            ch_id = channel.get("channel_id")

    # Log debug information
    logger.debug(
        f"YT verification debug: entered_handle={channel.get('handle')}, resolved_channel_id={ch_id}, verification_code={verification_code}, description_repr={repr(description)}, code_in_description={verification_code in description}"
    )
    if verification_code not in description:
        raise HTTPException(400, "Verification code not found in channel description.")

    # Check duplicate across all users
    try:
        users_resp = supabase.table("users").select("user_id, verified_yt_channels").execute()
        all_users = users_resp.data if hasattr(users_resp, "data") else users_resp.get("data", []) or []
        ch_handle = (channel.get("handle") or "").lower()
        for u in all_users:
            u_channels = u.get("verified_yt_channels") or []
            for uc in u_channels:
                if (ch_id and uc.get("channel_id") == ch_id) or \
                   (ch_handle and (uc.get("handle") or "").lower() == ch_handle):
                    raise HTTPException(400, "This channel is already verified.")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Error checking duplicate channel verification: {e}")

    channels = list(user.get("verified_yt_channels") or [])
    
    # Deduplicate within user's own list just in case
    existing_ids = {c.get("channel_id") for c in channels if c.get("channel_id")}
    existing_handles = {(c.get("handle") or "").lower() for c in channels}
    if ch_id and ch_id in existing_ids:
        raise HTTPException(400, "This channel is already verified.")
    if channel.get("handle") and channel["handle"].lower() in existing_handles:
        raise HTTPException(400, "This channel is already verified.")

    channel["channel_id"] = ch_id
    channel["verified_at"] = now_iso()
    channel["id"] = new_id("ytch")
    channels.append(channel)

    supabase.table("users").update({
        "verified_yt_channels": channels,
        "yt_verification_code": None
    }).eq(
        "user_id",
        user["user_id"]
    ).execute()

    return {"ok": True, "channel": channel}

@api.post("/social/start-youtube-verification")
async def start_youtube_verification(
    payload: StartYouTubeVerificationIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    user = await get_current_user(
        request,
        session_token,
        authorization
    )

    channel = fetch_youtube_channel(
        payload.youtube_channel
    )

    if not channel:
        raise HTTPException(
            400,
            "Channel not found"
        )

    # Resolve exact channel details from YouTube if API key is set
    api_key = os.getenv("YOUTUBE_API_KEY")
    ch_id = channel.get("channel_id")
    if api_key:
        if not ch_id and channel.get("handle"):
            try:
                resp = requests.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={"part": "snippet", "forHandle": channel.get("handle"), "key": api_key},
                    timeout=5,
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get("items", [])
                if items:
                    ch_id = items[0].get("id")
                    channel["channel_id"] = ch_id
                    snippet = items[0].get("snippet", {})
                    if snippet.get("title"):
                        channel["title"] = snippet["title"]
                    if snippet.get("thumbnails", {}).get("default", {}).get("url"):
                        channel["thumbnail"] = snippet["thumbnails"]["default"]["url"]
                else:
                    raise HTTPException(400, f"YouTube channel with handle {channel.get('handle')} not found.")
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Failed to resolve channel info for handle {channel.get('handle')}: {e}")
        elif ch_id:
            try:
                resp = requests.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={"part": "snippet", "id": ch_id, "key": api_key},
                    timeout=5,
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get("items", [])
                if items:
                    snippet = items[0].get("snippet", {})
                    if snippet.get("title"):
                        channel["title"] = snippet["title"]
                    if snippet.get("thumbnails", {}).get("default", {}).get("url"):
                        channel["thumbnail"] = snippet["thumbnails"]["default"]["url"]
                else:
                    raise HTTPException(400, f"YouTube channel with ID {ch_id} not found.")
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Failed to fetch metadata for channel ID {ch_id}: {e}")

    # Check duplicate across all users before starting
    try:
        users_resp = supabase.table("users").select("user_id, verified_yt_channels").execute()
        all_users = users_resp.data if hasattr(users_resp, "data") else users_resp.get("data", []) or []
        ch_handle = (channel.get("handle") or "").lower()
        for u in all_users:
            u_channels = u.get("verified_yt_channels") or []
            for uc in u_channels:
                if (ch_id and uc.get("channel_id") == ch_id) or \
                   (ch_handle and (uc.get("handle") or "").lower() == ch_handle):
                    raise HTTPException(400, "This channel is already verified.")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Error checking duplicate channel verification: {e}")

    logger.debug(f"Start verification: entered_handle={channel.get('handle')}, resolved_channel_id={ch_id}")
    import uuid
    verification_code = f"OUTCLIP-{uuid.uuid4().hex[:6].upper()}"

    db_verification_code = f"{verification_code}:{ch_id or ''}"

    supabase.table("users").update({
        "yt_verification_code": db_verification_code
    }).eq(
        "user_id",
        user["user_id"]
    ).execute()

    return {
        "channel": channel,
        "verification_code": verification_code
    }
@api.delete("/social/verified-channels/{channel_id}")
async def remove_verified_channel(
    channel_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """Remove a verified YouTube channel from the editor's list."""
    user = await get_current_user(request, session_token, authorization)
    channels = [c for c in (user.get("verified_yt_channels") or []) if c.get("id") != channel_id]
    supabase.table("users").update({"verified_yt_channels": channels}).eq("user_id", user["user_id"]).execute()
    return {"ok": True}

@api.get("/social/verification-status")
async def verification_status(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """Check if the current editor has at least one verified YouTube channel."""
    user = await get_current_user(request, session_token, authorization)
    channels = user.get("verified_yt_channels") or []
    return {"youtube_verified": len(channels) > 0, "channel_count": len(channels)}

# ---------------- Resources (static seed) ----------------
@api.get("/resources")
async def list_resources():
    return [
        {"id": "yt-algo-2026", "category": "Platform Guides",
         "title": "YouTube Shorts Algorithm — 2026 Edition",
         "summary": "How retention swipe-away, Average View Duration and hook strength move you up the curve.",
         "read_minutes": 8, "tag": "YOUTUBE"},
        {"id": "tiktok-2026", "category": "Platform Guides",
         "title": "TikTok For You Page Mechanics",
         "summary": "Why first-3-seconds retention matters more than likes. Practical hooks that work today.",
         "read_minutes": 6, "tag": "TIKTOK"},
        {"id": "hook-construction", "category": "Editing Techniques",
         "title": "Hook Construction in 7 Patterns",
         "summary": "Pattern library: pattern interrupt, controversy, payoff promise, contrast cut, etc.",
         "read_minutes": 10, "tag": "CRAFT"},
        {"id": "cut-timing", "category": "Editing Techniques",
         "title": "Cut Timing & Rhythm",
         "summary": "Beat-mapped cuts, J-cuts, L-cuts — when and why.", "read_minutes": 7, "tag": "CRAFT"},
        {"id": "points-system", "category": "Outclip Guides",
         "title": "The Outclip Points Formula Explained",
         "summary": "Views × Retention × Engagement × Hit Multiplier. What moves the needle the most.",
         "read_minutes": 5, "tag": "OUTCLIP"},
        {"id": "analytics-screens", "category": "Outclip Guides",
         "title": "Submitting Verifiable Analytics Screenshots",
         "summary": "What we need to see, how to capture it, common mistakes.",
         "read_minutes": 4, "tag": "OUTCLIP"},
        {"id": "captions-overlays", "category": "Editing Techniques",
         "title": "Captions & Overlays That Convert",
         "summary": "Font weight, position, color contrast — measurable retention gains.",
         "read_minutes": 6, "tag": "CRAFT"},
        {"id": "ig-reels-2026", "category": "Platform Guides",
         "title": "Instagram Reels — Native vs Repurposed",
         "summary": "Why a TikTok watermark can suppress reach. How to repackage cleanly.",
         "read_minutes": 5, "tag": "INSTAGRAM"},
    ]

async def sync_clips_internal() -> dict:
    """
    Core business logic to find stale clips in ACTIVE campaigns,
    refresh their metrics using batched YouTube API queries,
    and recalculate points, OCV, campaign totals, and user lifetime points.
    """
    act_camps_resp = (
        supabase.table("campaigns")
        .select("campaign_id")
        .eq("status", "ACTIVE")
        .execute()
    )
    act_camps = act_camps_resp.data or []
    if not act_camps:
        return {"status": "success", "synced_clips_count": 0, "message": "No active campaigns found"}

    camp_ids = [c["campaign_id"] for c in act_camps]

    clips_resp = (
        supabase.table("clips")
        .select("*")
        .in_("campaign_id", camp_ids)
        .limit(10000)
        .execute()
    )
    all_clips = clips_resp.data or []
    if not all_clips:
        return {"status": "success", "synced_clips_count": 0, "message": "No clips found in active campaigns"}

    now = datetime.now(timezone.utc)
    stale_clips = []

    for clip in all_clips:
        submitted_at_str = clip.get("submitted_at")
        if not submitted_at_str:
            continue
        try:
            submitted_at = datetime.fromisoformat(submitted_at_str.replace("Z", "+00:00"))
        except Exception:
            submitted_at = now

        age = now - submitted_at
        age_hours = age.total_seconds() / 3600.0

        last_synced_at_str = clip.get("last_synced_at")
        if not last_synced_at_str:
            stale_clips.append(clip)
            continue

        try:
            last_synced_at = datetime.fromisoformat(last_synced_at_str.replace("Z", "+00:00"))
        except Exception:
            stale_clips.append(clip)
            continue

        since_sync = now - last_synced_at
        since_sync_hours = since_sync.total_seconds() / 3600.0

        if age_hours < 24:
            if since_sync_hours >= 1.0:
                stale_clips.append(clip)
        elif age_hours < 168:
            if since_sync_hours >= 4.0:
                stale_clips.append(clip)
        else:
            if since_sync_hours >= 12.0:
                stale_clips.append(clip)

    if not stale_clips:
        return {"status": "success", "synced_clips_count": 0, "message": "All active clips are up to date"}

    affected_campaigns = set()
    affected_editors = set()
    synced_clip_ids = []

    for idx in range(0, len(stale_clips), 50):
        batch = stale_clips[idx:idx+50]
        video_ids = []
        video_to_clip = {}
        for c_doc in batch:
            v_id = c_doc.get("video_id")
            if v_id:
                video_ids.append(v_id)
                video_to_clip[v_id] = c_doc

        if not video_ids:
            for c_doc in batch:
                supabase.table("clips").update({
                    "last_synced_at": now.isoformat()
                }).eq("clip_id", c_doc["clip_id"]).execute()
            continue

        stats_map, success = fetch_youtube_stats_batch(video_ids)
        if not success:
            logger.error(f"YouTube stats query failed for batch. Skipping updates to prevent accidental soft-deletions.")
            continue

        for c_doc in batch:
            v_id = c_doc.get("video_id")
            yt_data = stats_map.get(v_id)
            if not yt_data:
                supabase.table("clips").update({
                    "last_synced_at": now.isoformat(),
                    "is_deleted": True,
                    "deleted_at": now.isoformat(),
                    "ocv": 0.0,
                    "points": 0.0
                }).eq("clip_id", c_doc["clip_id"]).execute()
                
                synced_clip_ids.append(c_doc["clip_id"])
                affected_campaigns.add(c_doc["campaign_id"])
                affected_editors.add(c_doc["editor_id"])
                continue

            views = yt_data.get("views", 0)
            likes = yt_data.get("likes", 0)
            comments = yt_data.get("comments", 0)
            published_at = yt_data.get("published_at")

            engagement_pct = round((likes + comments) / views * 100.0, 2) if views > 0 else 0.0
            retention_pct = 0.0

            pts = calc_points(views, retention_pct, engagement_pct)
            ocv_val = calculate_ocv(views, retention_pct, engagement_pct)

            upd_data = {
                "views": views,
                "likes": likes,
                "comments": comments,
                "engagement_pct": engagement_pct,
                "points": pts["points"],
                "retention_mult": pts["retention_mult"],
                "engagement_mult": pts["engagement_mult"],
                "hit_mult": pts["hit_mult"],
                "ocv": ocv_val,
                "published_at": published_at,
                "last_synced_at": now.isoformat(),
                "yt_meta": yt_data
            }

            supabase.table("clips").update(upd_data).eq("clip_id", c_doc["clip_id"]).execute()
            
            synced_clip_ids.append(c_doc["clip_id"])
            affected_campaigns.add(c_doc["campaign_id"])
            affected_editors.add(c_doc["editor_id"])

    for campaign_id in affected_campaigns:
        await recompute_campaign(campaign_id)

    for editor_id in affected_editors:
        total_lifetime = 0.0
        c_resp = (
            supabase.table("clips")
            .select("points")
            .eq("editor_id", editor_id)
            .eq("is_deleted", False)
            .execute()
        )
        for cl in c_resp.data or []:
            total_lifetime += cl.get("points", 0)
        
        supabase.table("users").update({
            "lifetime_points": round(total_lifetime, 2)
        }).eq("user_id", editor_id).execute()

    return {
        "status": "success",
        "synced_clips_count": len(synced_clip_ids),
        "synced_clip_ids": synced_clip_ids,
        "affected_campaigns": list(affected_campaigns),
        "affected_editors": list(affected_editors)
    }

@app.post("/internal/sync-clips")
async def sync_clips_endpoint(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_internal_key: Optional[str] = Header(None)
):
    """Trigger periodic clip sync and metrics refresh."""
    is_authorized = False
    secret_key = os.environ.get("INTERNAL_SYNC_TOKEN")
    
    if secret_key and x_internal_key == secret_key:
        is_authorized = True
        
    if not is_authorized:
        try:
            cookie_token = request.cookies.get("session_token")
            user = await get_current_user(request, cookie_token, authorization)
            await require_role(user, "ADMIN")
            is_authorized = True
        except Exception:
            pass

    if not is_authorized:
        raise HTTPException(401, "Not authorized to trigger internal sync")

    return await sync_clips_internal()

# ---------------- Mount ----------------

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

    
