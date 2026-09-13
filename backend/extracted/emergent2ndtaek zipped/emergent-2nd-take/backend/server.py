client = """Outclip backend - merit-based bounty marketplace for short-form video editors.

Stack: FastAPI + MongoDB + Emergent Google OAuth + Emergent Object Storage + YouTube Data API v3.
Razorpay escrow & payouts are MOCKED for MVP.
"""
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Form, Cookie, Header, Query
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os, io, uuid, logging, re, requests
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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

app = FastAPI(title="Outclip API")
api = APIRouter(prefix="/api")

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

# ---------------- YouTube ----------------
YT_ID_RE = re.compile(r"(?:youtube\.com/(?:shorts/|watch\?v=)|youtu\.be/)([A-Za-z0-9_-]{11})")
YT_CHANNEL_HANDLE_RE = re.compile(r"youtube\.com/@([A-Za-z0-9._-]+)")
YT_CHANNEL_ID_RE = re.compile(r"youtube\.com/channel/(UC[A-Za-z0-9_-]{22})")

def yt_video_id(url: str) -> Optional[str]:
    m = YT_ID_RE.search(url or "")
    return m.group(1) if m else None

def fetch_youtube_channel(url_or_handle: str):
    """Fetch channel info by URL/@handle/UC id."""

    s = (url_or_handle or "").strip()
    if not s:
        return None

    handle = None
    channel_id = None

    m = YT_CHANNEL_ID_RE.search(s)
    if m:
        channel_id = m.group(1)
    else:
        m = YT_CHANNEL_HANDLE_RE.search(s)

        if m:
            handle = m.group(1)
        elif s.startswith("@"):
            handle = s[1:]
        elif s.startswith("UC") and len(s) >= 24:
            channel_id = s[:24]

    if not YOUTUBE_API_KEY:
        return {
            "channel_id": channel_id,
            "handle": handle,
            "title": handle or "YouTube Channel",
            "thumbnail": None,
            "url": s if s.startswith("http") else (
                f"https://youtube.com/@{handle}" if handle else None
            ),
            "verified": False,
        }

    try:
        params = {
            "part": "snippet,statistics",
            "key": YOUTUBE_API_KEY
        }

        if channel_id:
            params["id"] = channel_id
        elif handle:
            params["forHandle"] = handle
        else:
            return None

        print("========== YOUTUBE DEBUG ==========")
        print("YOUTUBE API KEY EXISTS:", bool(YOUTUBE_API_KEY))
        print("HANDLE:", handle)
        print("CHANNEL ID:", channel_id)
        print("PARAMS:", params)

        r = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params=params,
            timeout=15
        )

        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text)
        print("===================================")

        r.raise_for_status()

        items = r.json().get("items", [])

        if not items:
            print("NO CHANNEL FOUND")
            return None

        it = items[0]
        sn = it.get("snippet", {})
        description = sn.get("description", "")
        st = it.get("statistics", {})
        ch_id = it.get("id")

        return {
            "channel_id": ch_id,
            "handle": sn.get("customUrl", handle),
            "description": description,
            "title": sn.get("title", ""),
            "thumbnail": (
                sn.get("thumbnails", {})
                .get("default", {})
                .get("url")
            ),
            "url": f"https://youtube.com/channel/{ch_id}",
            "subscribers": (
                int(st.get("subscriberCount", 0))
                if not st.get("hiddenSubscriberCount")
                else None
            ),
            "verified": True,
        }

    except Exception as e:
        print("YOUTUBE ERROR:", str(e))
        logger.warning(f"YouTube channel fetch failed: {e}")
        return None
def fetch_youtube_stats(url: str):
    vid = yt_video_id(url)
    if not vid or not YOUTUBE_API_KEY:
        return None
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
        }
    except Exception as e:
        logger.warning(f"YouTube fetch failed: {e}")
        return None

# ---------------- Auth ----------------
async def get_current_user(request: Request,
                           session_token: Optional[str] = Cookie(None),
                           authorization: Optional[str] = Header(None)):

    token = session_token

    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]

    if not token:
        raise HTTPException(401, "Not authenticated")
    print("TOKEN:", token)
    sess_resp = (
        supabase.table("sessions")
        .select("user_id")
        .eq("session_token", token)
        .single()
        .execute()
    )

    if not sess_resp.data:
        raise HTTPException(401, "Invalid session")

    user_resp = (
        supabase.table("users")
        .select("*")
        .eq("user_id", sess_resp.data["user_id"])
        .single()
        .execute()
    )

    if not user_resp.data:
        raise HTTPException(401, "User not found")

    user = user_resp.data
    user["wallet_balance"] = 10000.0
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

class CreateCampaignIn(BaseModel):
    title: str
    content_type: str
    description: str
    clip_guidelines: str = ""
    bounty_pool: float
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
    views: int
    retention_pct: float
    engagement_pct: float
    analytics_screen_path: Optional[str] = None

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
            "role": None,  # set during onboarding
            "bio": "",
            "lifetime_points": 0.0,
            "total_earnings": 0.0,
            "active_platforms": [],
            "is_earnings_public": False,
            "payout_upi": "",
            "created_at": now_iso(),
        }
        supabase.table("users").insert(user).execute()
    token = data["session_token"]
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    # await db.user_sessions.insert_one({
    #     "user_id": user["user_id"], "session_token": token,
    #     "expires_at": expires.isoformat(), "created_at": now_iso(),
    # })
    supabase.table("sessions").insert({
        "session_token": token,
        "user_id": user["user_id"],
        "expires_at": expires.isoformat(),
        "created_at": now_iso(),
    }).execute()
    response.set_cookie("session_token", token, httponly=True, secure=True,
                        samesite="none", path="/", max_age=7 * 24 * 60 * 60)
    return clean_doc(user)

@api.get("/auth/me")
async def auth_me(request: Request, session_token: Optional[str] = Cookie(None),
                  authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, session_token, authorization)
    return clean_doc(user)

@api.post("/auth/logout")
async def auth_logout(response: Response, session_token: Optional[str] = Cookie(None)):
    response.delete_cookie("session_token", path="/")
    return {"ok": True}

@api.post("/auth/set-role")
async def set_role(payload: SetRoleIn, request: Request,
                   session_token: Optional[str] = Cookie(None),
                   authorization: Optional[str] = Header(None)):
    user = await get_current_user(request, session_token, authorization)
    if payload.role not in ("EDITOR", "CREATOR"):
        raise HTTPException(400, "Invalid role")
    supabase.table("users").update({
    "role": payload.role
    }).eq("user_id", user["user_id"]).execute()
    user["role"] = payload.role
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
    # Ensure the campaign history is not exposed per spec
    public_profile.pop("campaign_history", None)
    return public_profile


# ---------------- Upload ----------------
@api.post("/wallet/cashout")
async def cashout(
    payload: CashoutIn,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """MOCK cashout — debits the user's `total_earnings` and creates a withdrawal record.
    """
    user = await get_current_user(request, session_token, authorization)

    amt = float(payload.amount)
    if amt <= 0:
        raise HTTPException(400, "Amount must be > 0")

    bal = float(user.get("total_earnings", 0))
    if amt > bal:
        raise HTTPException(
            400, f"Insufficient balance. Available: ₹{bal:.2f}"
        )

    # ---- Update the user's balance (non‑atomic) ----
    new_balance = round(bal - amt, 2)
    supabase.table("users").update(
        {"total_earnings": new_balance}
    ).eq("user_id", user["user_id"]).execute()

    # ---- Record the withdrawal ----
    rec = {
        "withdrawal_id": new_id("wd"),
        "user_id": user["user_id"],
        "amount": round(amt, 2),
        "status": "COMPLETED",
        "razorpay_payout_id": f"pout_mock_{uuid.uuid4().hex[:8]}",
        "created_at": now_iso(),
    }
    supabase.table("withdrawals").insert(rec).execute()

    return {
        "ok": True,
        "withdrawal": clean_doc(rec),
        "remaining_balance": new_balance,
    }


@api.get("/wallet/withdrawals")
async def list_withdrawals(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    """
    List the current user's withdrawal records.
    Replaces the MongoDB `find` + `sort` call with a Supabase query.
    """
    user = await get_current_user(request, session_token, authorization)
    # Retrieve withdrawals for the user, most recent first, limit to 200
    resp = (
        supabase.table("withdrawals")
        .select("*")
        .eq("user_id", user["user_id"])
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )
    # Supabase returns a dict with a `data` key containing the rows
    docs = resp.data if hasattr(resp, "data") else resp.get("data", [])
    return docs

@api.get("/wallet/transactions")
async def wallet_transactions(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
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

    withdrawals = resp.data or []

    transactions = []

    for w in withdrawals:
        transactions.append({
            "id": w["withdrawal_id"],
            "type": "WITHDRAWAL",
            "amount": w["amount"],
            "status": w["status"],
            "created_at": w["created_at"],
        })

    return transactions

@api.get("/wallet/creator-summary")
async def creator_wallet_summary(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    user = await get_current_user(request, session_token, authorization)

    if user.get("role") != "CREATOR":
        raise HTTPException(403, "Creator account required")

    camps_resp = (
        supabase.table("campaigns")
        .select("*")
        .eq("creator_id", user["user_id"])
        .execute()
    )

    campaigns = camps_resp.data or []

    total_spent = sum(
        float(c.get("bounty_pool", 0))
        for c in campaigns
    )

    return {
        "balance": 10000.0,
        "available_balance": 10000.0,
        "total_spent": total_spent,
        "campaigns_created": len(campaigns),
    }




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
            "status": "OPEN",
            "created_at": now_iso(),
        }
        full_campaign = {
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
            "min_duration_days": payload.min_duration_days,
            # Preserve possible legacy field; will be filtered out if not in schema
            "early_close_penalty_pct": getattr(payload, "early_close_penalty_pct", None),
            "clip_guidelines": payload.clip_guidelines,
            "source_video_urls": payload.source_video_urls,
            "status": "OPEN",
            "created_at": now_iso(),
        }

        # Insert the campaign using the already built schema‑matched dict
        result = supabase.table("campaigns").insert(campaign).execute()
        print("SUPABASE INSERT RESPONSE:", result)
        return clean_doc(campaign)
    except Exception as e:
        print("CREATE CAMPAIGN ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@api.post("/campaigns/{campaign_id}/publish")
async def publish_campaign(
    campaign_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
):
    """Publish a campaign. Only the creator can publish. Sets status to 'PUBLISHED'."""
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
    if campaign.get("creator_id") != user.get("user_id"):
        raise HTTPException(403, "Only the creator can publish this campaign")
    supabase.table("campaigns").update({"status": "OPEN"}).eq("campaign_id", campaign_id).execute()
    return {"ok": True, "campaign_id": campaign_id}



# ---------------- Creator Dashboard ----------------
def _tier(points: float) -> str:
    if points >= 50000: return "DIAMOND"
    if points >= 20000: return "PLATINUM"
    if points >= 10000: return "GOLD"
    if points >= 5000:  return "SILVER"
    if points >= 1000:  return "BRONZE"
    return "ROOKIE"

def _elo(points: float) -> int:
    # simple deterministic mapping
    return int(1000 + min(points, 50000) * 0.06)

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
    top_clips = sorted(clips, key=lambda x: x.get("points", 0), reverse=True)[:6]
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
            {"views": 0, "points": 0, "earnings": 0.0, "clips": 0},
        )
        agg["views"] += cl.get("views", 0)
        agg["points"] += cl.get("points", 0)
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
        by_editor.items(), key=lambda x: x[1]["points"], reverse=True
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
        lp = float((ed or {}).get("lifetime_points", 0))
        enriched_editors.append(
            {
                "editor": clean_doc(ed) if ed else None,
                "views_generated": agg["views"],
                "earnings_generated": round(agg["earnings"], 2),
                "points": round(agg["points"], 2),
                "elo": _elo(lp),
                "tier": _tier(lp),
            }
        )

    # ------------------------------------------------------------------
    # 7️⃣  Timeline (last 6 months) – uses `submitted_at` & YYYY‑MM format
    # ------------------------------------------------------------------
    from collections import defaultdict

    bucket = defaultdict(lambda: {"views": 0, "clips": 0, "points": 0})
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

    if camp.get("status") not in ("OPEN", "CLOSING_SOON"):
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
            params={"id": video_id, "part": "snippet,statistics", "key": YOUTUBE_API_KEY},
            timeout=15,
        )
        yt_resp.raise_for_status()
        yt_items = yt_resp.json().get("items", [])
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
    response = youtube.videos().list(
    part="snippet,statistics",
    id=video_id
).execute()

    item = response["items"][0]

    video_title = item["snippet"]["title"]
    video_channel_id = item["snippet"]["channelId"]

    views = int(
    item.get("statistics", {})
        .get("viewCount", 0)
)
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
        "views": views,
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

@api.delete("/campaigns/{campaign_id}/submit-short/{clip_id}")
async def delete_submission(
    campaign_id: str,
    clip_id: str,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
):
    # Authenticate user
    user = await get_current_user(request, session_token, authorization)
    # Verify participation
    part_resp = (
        supabase.table("participations")
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("editor_id", user["user_id"]).execute()
    )
    parts = part_resp.data if hasattr(part_resp, "data") else part_resp.get("data", [])
    if not parts:
        raise HTTPException(403, "You must join the campaign before deleting a submission.")
    # Delete the clip
    del_resp = (
        supabase.table("clips")
        .delete()
        .eq("clip_id", clip_id)
        .eq("campaign_id", campaign_id)
        .eq("editor_id", user["user_id"]).execute()
    )
    if not del_resp.data:
        raise HTTPException(404, "Submission not found.")
    # Recompute aggregates
    await recompute_campaign(campaign_id)
    return {"success": True, "message": "Submission deleted"}

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
        .limit(10000)
        .execute()
    )
    clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])

    # ------------------------------------------------------------------
    # 2️⃣ Aggregate points per editor and total points
    # ------------------------------------------------------------------
    editor_totals: dict[str, float] = {}
    total_points: float = 0.0
    for clip in clips:
        pts = clip.get("points", 0.0)
        editor_id = clip.get("editor_id")
        editor_totals[editor_id] = editor_totals.get(editor_id, 0.0) + pts
        total_points += pts

    # ------------------------------------------------------------------
    # 3️⃣ Update the campaign's total_points field
    # ------------------------------------------------------------------
    supabase.table("campaigns") \
        .update({"total_points": round(total_points, 2)}) \
        .eq("campaign_id", campaign_id) \
        .execute()

    # ------------------------------------------------------------------
    # 4️⃣ Sort editors by points and write participation updates
    # ------------------------------------------------------------------
    sorted_parts = sorted(editor_totals.items(), key=lambda x: x[1], reverse=True)
    for rank, (editor_id, pts) in enumerate(sorted_parts, start=1):
        share_pct = (pts / total_points * 100) if total_points > 0 else 0.0
        supabase.table("participations") \
            .update({
                "total_points": round(pts, 2),
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
    if c["status"] not in ("OPEN", "CLOSING_SOON"):
        raise HTTPException(400, "Campaign not accepting clips")

    # ------------------------------------------------------------------
    # 3️⃣ Verify editor has joined the campaign
    #    (Supabase replacement for `db.participations.find_one`)
    # ------------------------------------------------------------------
    part_resp = (
        supabase.table("participations")
        .select("*")
        .eq("campaign_id", payload.campaign_id)
        .eq("editor_id", user["user_id"])
        .single()
        .execute()
    )
    existing_participations = part_resp.data or []

    if existing_participations:
        raise HTTPException(
            400,
            "You have already joined this campaign."
        )

    # ------------------------------------------------------------------
    # 4️⃣ Enforce max‑clips‑per‑editor limit
    #    (Supabase replacement for `db.clips.count_documents`)
    # ------------------------------------------------------------------
    existing_clips_resp = (
        supabase.table("clips")
        .select("clip_id")
        .eq("campaign_id", payload.campaign_id)
        .eq("editor_id", user["user_id"])
        .execute()
    )
    existing_count = len(existing_clips_resp.data or [])
    if existing_count >= c["max_clips_per_editor"]:
        raise HTTPException(400, "Max clips reached")

    # ------------------------------------------------------------------
    # 5️⃣ Compute points & optional YouTube verification
    # ------------------------------------------------------------------
    pts = calc_points(payload.views, payload.retention_pct, payload.engagement_pct)
    yt_meta = (
        fetch_youtube_stats(payload.clip_url)
        if payload.platform == "YOUTUBE_SHORTS"
        else None
    )

    # ------------------------------------------------------------------
    # 6️⃣ Auto‑verify YouTube channel matches editor’s connected channel for this campaign
    # ------------------------------------------------------------------
    if payload.platform == "YOUTUBE_SHORTS" and yt_meta and yt_meta.get("channel_id"):
        connected = (part or {}).get("yt_channel") or {}
        connected_id = connected.get("channel_id")
        connected_handle = (connected.get("handle") or "").lstrip("@").lower()
        clip_channel_id = yt_meta["channel_id"]
        clip_channel_title = (yt_meta.get("channel_title") or "").lower()
        ok = False
        if connected_id and connected_id == clip_channel_id:
            ok = True
        elif connected_handle and connected_handle in clip_channel_title:
            ok = True
        if not ok:
            raise HTTPException(
                400,
                f"Channel mismatch — clip is from '{yt_meta.get('channel_title')}' "
                f"but your connected channel is '{connected.get('title') or connected.get('handle')}'. "
                "Upload from your connected channel or reconnect a different channel for this campaign.",
            )

    # ------------------------------------------------------------------
    # 7️⃣ Build the clip document
    # ------------------------------------------------------------------
    doc = {
        "clip_id": new_id("clip"),
        "campaign_id": payload.campaign_id,
        "editor_id": user["user_id"],
        "platform": payload.platform,
        "clip_url": payload.clip_url,
        "views": payload.views,
        "retention_pct": payload.retention_pct,
        "engagement_pct": payload.engagement_pct,
        "points": pts["points"],
        "retention_mult": pts["retention_mult"],
        "engagement_mult": pts["engagement_mult"],
        "hit_mult": pts["hit_mult"],
        "analytics_screen_path": payload.analytics_screen_path,
        "analytics_verified": bool(yt_meta),  # auto‑verified if YT API confirmed
        "yt_meta": yt_meta,
        "submitted_at": now_iso(),
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
    # Load editor's clips (Supabase)
    clips_resp = (
        supabase.table("clips")
        .select("*")
        .eq("editor_id", uid)
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
        history.append({
            "campaign_id": c["campaign_id"],
            "title": c["title"],
            "status": c["status"],
            "rank": p.get("rank"),
            "points": p.get("total_points", 0),
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
        "badges": badges,
        "campaign_history": history,
        "created_at": user.get("created_at"),
    }

# ---------------- Leaderboard ----------------
@api.get("/leaderboard/campaign/{campaign_id}")
async def leaderboard_campaign(campaign_id: str):
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
    total = camp.get("total_points", 0.0) if camp else 0.0

    # -------------------------------------------------
    # 3️⃣  Assemble the leaderboard entries.
    # -------------------------------------------------
    out = []
    for i, p in enumerate(parts, start=1):
        # Editor (user) info
        editor_resp = (
            supabase.table("users")
            .select("user_id,name,username,avatar_url")
            .eq("user_id", p["editor_id"]).single()
            .execute()
        )
        editor = editor_resp.data if hasattr(editor_resp, "data") else editor_resp.get("data")
        # Clips submitted by this editor in this campaign
        clips_resp = (
            supabase.table("clips")
            .select("points,views")
            .eq("campaign_id", campaign_id)
            .eq("editor_id", p["editor_id"])
            .limit(100)
            .execute()
        )
        clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])
        # Best clip (by points)
        best = max(clips, key=lambda x: x.get("points", 0), default=None)
        # Share of total points
        share = (p["total_points"] / total) if total > 0 else 0.0

        out.append(
            {
                "rank": i,
                "editor": clean_doc(editor) if editor else None,
                "yt_channel": p.get("yt_channel"),
                "total_points": p["total_points"],
                "clips_submitted": len(clips),
                "best_clip": {"points": best["points"], "views": best["views"]} if best else None,
                "reward_share_pct": round(share * 100, 2),
                "projected_payout": round(pool_net * share, 2),
            }
        )
    return out

@api.get("/leaderboard/lifetime")
async def leaderboard_lifetime(limit: int = 25):
    """Lifetime editor leaderboard – ordered by `lifetime_points` descending.
    Returns rank, a cleaned `editor` object, `lifetime_points`, and
    `total_earnings` for each editor.
    """
    resp = (
        supabase.table("users")
        .select("*")
        .eq("role", "EDITOR")
        .order("lifetime_points", desc=True)
        .limit(limit)
        .execute()
    )
    users = resp.data if hasattr(resp, "data") else resp.get("data", [])
    out = []
    for i, u in enumerate(users, start=1):
        out.append(
            {
                "rank": i,
                "editor": clean_doc(u),
                "lifetime_points": u.get("lifetime_points", 0.0),
                "total_earnings": u.get("total_earnings", 0.0),
            }
        )
    return out

@api.get("/leaderboard/monthly")
async def leaderboard_monthly(limit: int = 25):
    # Start of the current month (UTC)
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Fetch all clips from the start of the month onward using Supabase
    clips_resp = (
        supabase.table("clips")
        .select("editor_id,points,submitted_at")
        .gte("submitted_at", start.isoformat())
        .execute()
    )
    clips = clips_resp.data if hasattr(clips_resp, "data") else clips_resp.get("data", [])
    # Aggregate points and clip counts per editor in Python
    editor_stats: dict[str, dict] = {}
    for clip in clips:
        editor_id = clip.get("editor_id")
        if not editor_id:
            continue
        stats = editor_stats.setdefault(editor_id, {"points": 0.0, "clips": 0})
        stats["points"] += clip.get("points", 0.0)
        stats["clips"] += 1
    # Sort editors by points descending and respect the limit
    sorted_editors = sorted(editor_stats.items(), key=lambda x: x[1]["points"], reverse=True)[:limit]
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
            "clips": stats["clips"],
        })
    return out

# ---------------- Dashboard ----------------
@api.get("/dashboard")
async def dashboard(request: Request,
                    session_token: Optional[str] = Cookie(None),
                    authorization: Optional[str] = Header(None)):

    user = await get_current_user(request, session_token, authorization)

    return {
        "role": user.get("role"),
        "stats": {},
        "active_campaigns": [],
        "recent_clips": [],
        "my_campaigns": [],
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
            .order("points", desc=True)
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

    verification_code = user.get("yt_verification_code")

    if not verification_code:
        raise HTTPException(
            400,
            "Generate a verification code first."
        )

    description = channel.get("description", "")

    if verification_code not in description:
        raise HTTPException(
            400,
            "Verification code not found in channel description."
        )

    # Check duplicate across all users
    try:
        users_resp = supabase.table("users").select("user_id, verified_yt_channels").execute()
        all_users = users_resp.data if hasattr(users_resp, "data") else users_resp.get("data", []) or []
        ch_id = channel.get("channel_id")
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
    if channel.get("channel_id") and channel["channel_id"] in existing_ids:
        raise HTTPException(400, "This channel is already verified.")
    if channel.get("handle") and channel["handle"].lower() in existing_handles:
        raise HTTPException(400, "This channel is already verified.")

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

    # Check duplicate across all users before starting
    try:
        users_resp = supabase.table("users").select("user_id, verified_yt_channels").execute()
        all_users = users_resp.data if hasattr(users_resp, "data") else users_resp.get("data", []) or []
        ch_id = channel.get("channel_id")
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

    import uuid
    verification_code = f"OUTCLIP-{uuid.uuid4().hex[:6].upper()}"

    supabase.table("users").update({
        "yt_verification_code": verification_code
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



# ---------------- Mount ----------------


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.warning(f"Storage init failed (will retry on first upload): {e}")


@app.on_event("shutdown")
async def shutdown():
    pass


app.include_router(api)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

    