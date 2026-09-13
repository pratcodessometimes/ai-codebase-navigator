import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getCampaign, joinCampaign, publishCampaign, cancelCampaign, approvePayout,
         submitClip, submitShort, listClips, lbCampaign, ytFetch, uploadFile, getVerificationStatus,
         deleteSubmission } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { ArrowLeft, Upload, Play, Trophy, Youtube } from "lucide-react";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));

export default function CampaignDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [c, setC] = useState(null);
  const [clips, setClips] = useState([]);
  const [lb, setLb] = useState([]);
  const [tab, setTab] = useState("OVERVIEW");
  const [showSubmit, setShowSubmit] = useState(false);
  const [showJoin, setShowJoin] = useState(false);
  const [showVerifyPrompt, setShowVerifyPrompt] = useState(false);
  const [showShortModal, setShowShortModal] = useState(false);
  const [toast, setToast] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const [cc, cl, l] = await Promise.all([getCampaign(id), listClips({ campaign_id: id }), lbCampaign(id)]);
    setC(cc); setClips(cl); setLb(l);
  };
  useEffect(() => { refresh(); }, [id]);

  if (!c) return <p className="font-mono text-sm oc-pulse">LOADING…</p>;

  const myPart = lb.find(r => r.editor?.user_id === user?.user_id);
  const isCreator = user?.user_id === c.creator_id;
  const isEditor = user?.role === "EDITOR";
  const joined = !!myPart;
  const acceptingClips = ["OPEN", "CLOSING_SOON"].includes(c.status);

  const handleJoin = async (channel) => {
    setBusy(true);
    try {
      await joinCampaign(id, channel);
      setShowJoin(false);
      await refresh();
    } catch (e) { alert(e.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  const handleJoinClick = async () => {
  if (!user) {
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(window.location.origin + "/auth/callback")}`;
    return;
  }
  // If user already has verified YouTube channels, join directly using the first one
  const verifiedChannels = user?.verified_yt_channels || [];
  if (verifiedChannels.length > 0) {
    // Use the first verified channel URL or handle
    const channel = verifiedChannels[0].url || verifiedChannels[0].handle || verifiedChannels[0].channel_id;
    await handleJoin(channel);
    return;
  }
  // Otherwise, check verification status via backend
  try {
    const status = await getVerificationStatus();
    if (status.youtube_verified) {
      setShowJoin(true);
    } else {
      setShowVerifyPrompt(true);
    }
  } catch {
    // If check fails (e.g., network), fall through to join modal
    setShowJoin(true);
  }
};
    /* Duplicate verification block removed */  
  const handlePublish = async () => { setBusy(true); try { await publishCampaign(id); await refresh(); } finally { setBusy(false); } };
  const handleCancel = async () => { setBusy(true); try { await cancelCampaign(id); await refresh(); } finally { setBusy(false); } };
  const handlePayout = async () => { setBusy(true); try { await approvePayout(id); await refresh(); } finally { setBusy(false); } };

  return (
    <div data-testid="campaign-detail">
      <button onClick={() => navigate(-1)} className="font-mono text-xs tracking-[0.2em] flex items-center gap-1 mb-6" data-testid="back-btn">
        <ArrowLeft size={14}/> BACK
      </button>

      <div className="grid lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 oc-card">
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <span className="oc-chip" style={{ background: c.status === "OPEN" ? "#2CFF05" : c.status === "CLOSING_SOON" ? "#BF00FF" : "#2D2D2D",
              color: c.status === "OPEN" ? "#000" : "#fff" }}>{c.status.replace("_", " ")}</span>
            <span className="oc-chip" style={{ background: "#fff", color: "#000", border: "1.5px solid #000" }}>{c.content_type}</span>
            {c.escrow_funded && <span className="oc-chip" style={{ background: "#000", color: "#2CFF05" }}>ESCROW FUNDED</span>}
          </div>
          <h1 className="font-display text-4xl md:text-5xl font-black">{c.title}</h1>
          {c.creator && <p className="text-[#2D2D2D] mt-3">by {c.creator.name}</p>}
          <div className="mt-6 grid grid-cols-3 gap-4">
            <div><p className="font-mono text-[10px] text-[#2D2D2D]">BOUNTY POOL</p><p className="font-display font-black text-2xl">₹{fmt(c.bounty_pool)}</p></div>
            <div><p className="font-mono text-[10px] text-[#2D2D2D]">EDITORS</p><p className="font-display font-black text-2xl">{c.participant_count}</p></div>
            <div><p className="font-mono text-[10px] text-[#2D2D2D]">CLIPS</p><p className="font-display font-black text-2xl">{c.clip_count}</p></div>
          </div>
          <div className="mt-6 border-t-2 border-black pt-5">
            <h3 className="font-display text-xl font-black mb-2">Brief</h3>
            <p className="text-sm whitespace-pre-wrap">{c.description}</p>
            <h3 className="font-display text-xl font-black mt-5 mb-2">Clip guidelines</h3>
            <p className="text-sm whitespace-pre-wrap">{c.clip_guidelines}</p>
            {c.source_video_urls?.length > 0 && (
              <>
                <h3 className="font-display text-xl font-black mt-5 mb-2">Source videos</h3>
                <ul className="space-y-2">
                  {c.source_video_urls.map((u, i) => (
                    <li key={i}><a href={u} target="_blank" rel="noreferrer"
                      className="oc-link font-mono text-sm break-all" data-testid={`source-${i}`}>{u}</a></li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </div>

        <div className="space-y-4">
          {(!user || isEditor) && acceptingClips && !joined && (
            <button onClick={handleJoinClick} disabled={busy} className="oc-btn oc-btn-primary w-full" data-testid="join-btn">
              {busy ? "Joining…" : "Join campaign"}
            </button>
          )}
          {/* Indicator for verified YouTube channel */}
          {user && user.verified_yt_channels && user.verified_yt_channels.length > 0 && (
            <div className="flex items-center gap-2 mt-2" data-testid="verified-yt-indicator">
              <span className="font-mono text-xs tracking-[0.2em] text-[#2CFF05]">✔ Verified YouTube Channel Connected</span>
            </div>
          )}



          {joined && myPart && (
            <div className="oc-card" style={{ background: "#2CFF05", color: "#000" }} data-testid="my-status">
              <p className="font-mono text-[10px] tracking-[0.25em]">YOUR STATUS</p>
              <p className="font-display text-4xl font-black mt-2">#{myPart.rank}</p>
              <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div><p className="font-mono text-[9px]">POINTS</p><p className="font-display font-black">{fmt(myPart.total_points)}</p></div>
                <div><p className="font-mono text-[9px]">PROJECTED</p><p className="font-display font-black">₹{fmt(myPart.projected_payout)}</p></div>
              </div>
            </div>
          )}
          {isEditor && joined && acceptingClips && (
            <button onClick={() => setShowShortModal(true)} className="oc-btn oc-btn-primary w-full" data-testid="submit-short-btn">
              <Youtube size={16}/> Submit Short
            </button>
          )}
          {isCreator && c.status === "DRAFT" && (
            <button onClick={handlePublish} disabled={busy} className="oc-btn oc-btn-primary w-full" data-testid="publish-btn">
              {busy ? "Publishing…" : "Publish (mock escrow)"}
            </button>
          )}
          {isCreator && ["OPEN", "CLOSING_SOON", "UNDER_REVIEW"].includes(c.status) && (
            <button onClick={handlePayout} disabled={busy} className="oc-btn oc-btn-secondary w-full" data-testid="approve-payout-btn">
              {busy ? "Processing…" : "Close & distribute payouts"}
            </button>
          )}
          {isCreator && c.status === "DRAFT" && (
            <button onClick={handleCancel} disabled={busy} className="oc-btn oc-btn-ghost w-full" data-testid="cancel-btn">
              Cancel campaign
            </button>
          )}
        </div>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        {["OVERVIEW", "BRIEF", "ASSETS", "REWARDS", "LEADERBOARD", "SUBMISSIONS"].map(t => (
          <button key={t} onClick={() => setTab(t)} className={`oc-tab ${tab === t ? "active" : ""}`} data-testid={`tab-${t}`}>{t}</button>
        ))}
      </div>

      {tab === "SUBMISSIONS" && <ClipsList clips={clips} user={user} />}
      {tab === "LEADERBOARD" && <CampaignBoard rows={lb} meId={user?.user_id} />}
      {tab === "OVERVIEW" && (
        <div className="oc-card space-y-4">
          <div>
            <h3 className="font-display text-xl font-black">Description</h3>
            <p className="text-sm whitespace-pre-wrap mt-2">{c.description || "—"}</p>
          </div>
          <div className="grid sm:grid-cols-3 gap-3 pt-3 border-t-2 border-black">
            <div><p className="font-mono text-[10px] text-[#2D2D2D]">START</p><p className="font-display font-black">{(c.start_date || "").slice(0,10)}</p></div>
            <div><p className="font-mono text-[10px] text-[#2D2D2D]">END</p><p className="font-display font-black">{(c.end_date || "").slice(0,10)}</p></div>
            <div><p className="font-mono text-[10px] text-[#2D2D2D]">MAX CLIPS / EDITOR</p><p className="font-display font-black">{c.max_clips_per_editor}</p></div>
          </div>
          <div className="pt-3 border-t-2 border-black">
            <h3 className="font-display text-xl font-black">Points formula</h3>
            <p className="font-mono text-sm mt-2">Points = Views × RetentionMult × EngagementMult × HitMult</p>
            <p className="text-sm text-[#2D2D2D] mt-2">Reward share = your points ÷ total campaign points. Pool net of {c.platform_fee_percent || 15}% platform fee.</p>
          </div>
          {(c.min_duration_days || c.early_close_penalty_pct) && (
            <div className="pt-3 border-t-2 border-black">
              <h3 className="font-display text-xl font-black">Lock window</h3>
              <p className="text-sm text-[#2D2D2D] mt-2">
                Minimum duration: <b>{c.min_duration_days || 7} days</b> · Early-close penalty: <b>{c.early_close_penalty_pct || 20}%</b>
              </p>
            </div>
          )}
        </div>
      )}
      {tab === "BRIEF" && <BriefView brief={c.brief || {}} clipGuidelines={c.clip_guidelines} />}
      {tab === "ASSETS" && <AssetsView assets={c.assets || {}} sourceUrls={c.source_video_urls || []} />}
      {tab === "REWARDS" && <RewardsView c={c} />}

      {showSubmit && <SubmitClipModal campaign={c} onClose={() => setShowSubmit(false)} onDone={async () => { setShowSubmit(false); await refresh(); }} />}
      {showJoin && <JoinModal busy={busy} onClose={() => setShowJoin(false)} onJoin={handleJoin} />}
      {showVerifyPrompt && <VerifyPromptModal onClose={() => setShowVerifyPrompt(false)} onGoVerify={() => navigate("/app/social-verification")} />}
      {showShortModal && (
        <SubmitShortModal
          campaignId={id}
          onClose={() => setShowShortModal(false)}
          onDone={async () => {
            setShowShortModal(false);
            setToast("Short submitted successfully!");
            setTimeout(() => setToast(null), 4000);
            await refresh();
          }}
        />
      )}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl border-2 border-black font-mono text-sm tracking-wide"
             style={{ background: "#2CFF05", color: "#000" }} data-testid="toast">
          {toast}
        </div>
      )}
    </div>
  );
}

/* ─── Verify Prompt Modal (shown when editor has no verified YouTube channels) ─── */
const VerifyPromptModal = ({ onClose, onGoVerify }) => (
  <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" data-testid="verify-prompt-modal">
    <div className="bg-white w-full max-w-md rounded-2xl border-2 border-black overflow-hidden">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-[#FFF8E5] border-2 border-[#E8C500] flex items-center justify-center flex-shrink-0">
            <span className="text-xl">🔗</span>
          </div>
          <h2 className="font-display text-2xl font-black">Verification required</h2>
        </div>
        <p className="text-sm text-[#2D2D2D]">
          Please verify a YouTube account before participating in this campaign.
          Go to Social Verification to connect your channel.
        </p>
        <div className="mt-6 flex gap-3">
          <button onClick={onClose} className="oc-btn oc-btn-ghost flex-1" data-testid="verify-prompt-cancel">Cancel</button>
          <button onClick={onGoVerify} className="oc-btn oc-btn-primary flex-1" data-testid="verify-prompt-go">
            Go To Verification
          </button>
        </div>
      </div>
    </div>
  </div>
);

const JoinModal = ({ busy, onClose, onJoin }) => {
  const [stage, setStage] = useState("intro"); // intro | connect
  const [channel, setChannel] = useState("");
  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" data-testid="join-modal">
      <div className="bg-white w-full max-w-md rounded-2xl border-2 border-black overflow-hidden">
        {/* OAuth-style header */}
        <div className="px-6 py-4 border-b-2 border-black flex items-center gap-3 bg-[#F8F8F8]">
          <svg width="20" height="20" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
          </svg>
          <span className="font-mono text-xs tracking-[0.15em] text-[#2D2D2D]">accounts.google.com</span>
        </div>

        {stage === "intro" ? (
          <div className="p-6">
            <h2 className="font-display text-2xl font-black">Connect your YouTube channel</h2>
            <p className="text-sm text-[#2D2D2D] mt-2">
              Outclip will use your channel to verify that submitted clips were uploaded by you.
              You can use a different channel for each campaign.
            </p>
            <div className="mt-5 p-4 border-2 border-black rounded-lg bg-[#FAFAFA]">
              <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D] mb-2">OUTCLIP WILL BE ABLE TO:</p>
              <ul className="text-sm space-y-1.5">
                <li className="flex items-start gap-2"><span className="text-[#2CFF05] mt-0.5">✓</span> See your YouTube channel ID & display name</li>
                <li className="flex items-start gap-2"><span className="text-[#2CFF05] mt-0.5">✓</span> Verify clip uploads originate from your channel</li>
                <li className="flex items-start gap-2"><span className="text-[#2D2D2D] mt-0.5">✗</span> Post, edit or delete videos on your behalf</li>
              </ul>
            </div>
            <div className="mt-6 flex gap-3">
              <button onClick={onClose} className="oc-btn oc-btn-ghost flex-1" data-testid="join-cancel">Cancel</button>
              <button onClick={() => setStage("connect")} className="oc-btn oc-btn-primary flex-1" data-testid="join-continue">
                Continue with Google
              </button>
            </div>
          </div>
        ) : (
          <div className="p-6">
            <h2 className="font-display text-2xl font-black">Choose your channel</h2>
            <p className="text-sm text-[#2D2D2D] mt-2">
              Paste your channel URL or <span className="font-mono">@handle</span>. We'll verify it against YouTube.
            </p>
            <label className="block mt-5">
              <span className="font-mono text-[10px] tracking-[0.2em]">YOUTUBE CHANNEL</span>
              <input value={channel} onChange={e => setChannel(e.target.value)}
                     placeholder="@scortamo  or  https://youtube.com/@scortamo"
                     className="w-full mt-1 p-3 border-2 border-black rounded-lg font-mono text-sm"
                     data-testid="join-channel-input" autoFocus />
            </label>
            <div className="mt-2 p-2.5 rounded-md bg-[#FFF8E5] border border-[#E8C500]">
              <p className="font-mono text-[10px] tracking-[0.1em] text-[#7A5A00]">
                MVP NOTE: full Google consent flow ships when OAuth credentials are configured. For now, we verify your handle directly via YouTube Data API.
              </p>
            </div>
            <div className="mt-6 flex gap-3">
              <button onClick={() => setStage("intro")} className="oc-btn oc-btn-ghost flex-1" data-testid="join-back">← Back</button>
              <button onClick={() => onJoin(channel)} disabled={busy || !channel.trim()}
                      className="oc-btn oc-btn-primary flex-1" data-testid="join-confirm">
                {busy ? "Verifying…" : "Connect & join"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const ClipsList = ({ clips, user }) => (
  <div className="oc-card" data-testid="clips-list">
    {clips.length === 0 ? (
      <p className="font-mono text-xs tracking-[0.2em] py-8 text-center">NO CLIPS YET</p>
    ) : (
      <ul className="space-y-3">
        {clips.map(cl => (
          <li key={cl.clip_id} className="flex items-center gap-3 border-2 border-black rounded-lg p-3" data-testid={`clip-${cl.clip_id}`}>
            <img src={cl.editor?.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${cl.editor?.name}`} className="w-10 h-10 rounded-full border-2 border-black" alt="" />
            <div className="flex-1 min-w-0">
              <p className="font-bold truncate">{cl.editor?.name}</p>
              <a href={cl.clip_url} target="_blank" rel="noreferrer" className="font-mono text-[11px] text-[#BF00FF] truncate block">{cl.clip_url}</a>
            </div>
            <div className="text-right flex flex-col items-end">
              <p className="font-display font-black text-lg">{fmt(cl.points)}</p>
              <p className="font-mono text-[10px] text-[#2D2D2D]">{fmt(cl.views)} VIEWS</p>
              {cl.editor?.user_id === user?.user_id && (
                <button
                  onClick={async () => {
                    if (!window.confirm('Delete this submission?')) return;
                    try {
                      await deleteSubmission(cl.campaign_id, cl.clip_id);
                      await refresh();
                      setToast('Submission deleted');
                      setTimeout(() => setToast(null), 4000);
                    } catch (e) {
                      alert(e.response?.data?.detail || 'Delete failed');
                    }
                  }}
                  className="oc-btn oc-btn-ghost text-xs mt-1"
                  data-testid={`delete-${cl.clip_id}`}
                >
                  Delete
                </button>
              )}
            </div>
            {cl.analytics_verified && <span className="oc-chip" style={{ background: "#2CFF05", color: "#000" }}>VERIFIED</span>}
          </li>
        ))}
      </ul>
    )}
  </div>
);




const BriefView = ({ brief, clipGuidelines }) => {
  const rows = [
    ["Objective", brief.objective],
    ["Target audience", brief.target_audience],
    ["Content style", brief.content_style],
    ["Topics to focus on", brief.topics_focus],
    ["Topics to avoid", brief.topics_avoid],
    ["Hook style", brief.hook_style],
    ["Clip length", brief.length_guidelines],
    ["Caption guidelines", brief.caption_guidelines || clipGuidelines],
    ["Video type wanted", brief.video_type],
  ];
  const hasAny = rows.some(([_, v]) => v);
  return (
    <div className="oc-card" data-testid="brief-view">
      <h3 className="font-display text-xl font-black mb-4">Campaign brief</h3>
      {!hasAny ? (
        <p className="font-mono text-xs tracking-[0.2em] py-6 text-center text-[#2D2D2D]">NO BRIEF PROVIDED</p>
      ) : (
        <div className="space-y-4">
          {rows.map(([label, value]) => value ? (
            <div key={label} className="border-b border-[#2D2D2D] pb-3 last:border-0">
              <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">{label.toUpperCase()}</p>
              <p className="text-sm mt-1.5 whitespace-pre-wrap">{value}</p>
            </div>
          ) : null)}
        </div>
      )}
    </div>
  );
};

const AssetsView = ({ assets, sourceUrls }) => (
  <div className="oc-card" data-testid="assets-view">
    <h3 className="font-display text-xl font-black mb-4">Assets</h3>
    {sourceUrls.length > 0 && (
      <div className="mb-5">
        <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D] mb-2">SOURCE VIDEOS</p>
        <ul className="space-y-1.5">
          {sourceUrls.map((u, i) => (
            <li key={i}>
              <a href={u} target="_blank" rel="noreferrer" className="oc-link font-mono text-sm break-all text-[#BF00FF]">{u}</a>
            </li>
          ))}
        </ul>
      </div>
    )}
    {Object.entries({
      "Raw footage notes": assets.raw_footage,
      "Logos": assets.logos,
      "Brand assets": assets.brand_assets,
      "Additional notes": assets.notes,
    }).map(([k, v]) => v ? (
      <div key={k} className="border-t-2 border-black pt-3 mt-3">
        <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">{k.toUpperCase()}</p>
        <p className="text-sm mt-1.5 whitespace-pre-wrap break-words">{v}</p>
      </div>
    ) : null)}
    {sourceUrls.length === 0 && !Object.values(assets).some(Boolean) && (
      <p className="font-mono text-xs tracking-[0.2em] py-6 text-center text-[#2D2D2D]">NO ASSETS UPLOADED</p>
    )}
  </div>
);

const RewardsView = ({ c }) => {
  const pool = c.bounty_pool || 0;
  const fee = pool * (c.platform_fee_percent || 15) / 100;
  const net = pool - fee;
  const ep = c.editor_pool_pct || 60;
  const pp = c.performance_pool_pct || 30;
  const bp = c.bonus_pool_pct || 10;
  const items = [
    { label: "CAMPAIGN BUDGET", value: pool, color: "#000", fg: "#fff" },
    { label: `PLATFORM FEE (${c.platform_fee_percent || 15}%)`, value: fee, color: "#2D2D2D", fg: "#fff" },
    { label: `EDITOR POOL (${ep}%)`, value: net * ep / 100, color: "#2CFF05", fg: "#000" },
    { label: `PERFORMANCE POOL (${pp}%)`, value: net * pp / 100, color: "#BF00FF", fg: "#fff" },
    { label: `BONUS POOL (${bp}%)`, value: net * bp / 100, color: "#fff", fg: "#000" },
  ];
  return (
    <div className="oc-card" data-testid="rewards-view">
      <h3 className="font-display text-xl font-black mb-4">Reward structure</h3>
      <div className="grid sm:grid-cols-5 gap-3">
        {items.map((it, i) => (
          <div key={i} className="p-4 rounded-lg" style={{ background: it.color, color: it.fg, border: it.color === "#fff" ? "2px solid #000" : "none" }}>
            <p className="font-mono text-[9px] tracking-[0.15em] opacity-80">{it.label}</p>
            <p className="font-display text-xl font-black mt-1">₹{fmt(it.value)}</p>
          </div>
        ))}
      </div>
      <p className="text-sm text-[#2D2D2D] mt-5">
        Reward per editor = (your points ÷ total campaign points) × Editor Pool. Performance and Bonus pools
        may be triggered by additional thresholds set by the creator.
      </p>
    </div>
  );
};

const CampaignBoard = ({ rows, meId }) => (
  <div className="oc-card" data-testid="campaign-leaderboard">
    {rows.length === 0 ? <p className="font-mono text-xs tracking-[0.2em] py-8 text-center">EMPTY — BE FIRST TO SUBMIT</p> :
      <ol className="space-y-2">
        {rows.map(r => {
          const isMe = r.editor?.user_id === meId;
          const bg = r.rank === 1 ? "#2CFF05" : r.rank === 2 ? "#BF00FF" : r.rank === 3 ? "#2D2D2D" : (isMe ? "#000" : "#fff");
          const fg = r.rank <= 3 ? (r.rank === 1 ? "#000" : "#fff") : (isMe ? "#2CFF05" : "#000");
          const ch = r.yt_channel || {};
          const chLabel = ch.title || (ch.handle ? `@${ch.handle}` : null);
          const chipBg = r.rank <= 3 ? "rgba(0,0,0,0.55)" : (isMe ? "#2D2D2D" : "#000");
          return (
            <li key={r.editor?.user_id} className="flex items-center gap-4 p-3 rounded-lg border-2 border-black"
              style={{ background: bg, color: fg }} data-testid={`lb-row-${r.rank}`}>
              <span className="font-display font-black text-2xl w-10">#{r.rank}</span>
              <img src={r.editor?.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${r.editor?.name}`} className="w-9 h-9 rounded-full border-2 border-black" alt="" />
              <div className="flex-1 min-w-0">
                <p className="font-bold truncate">{r.editor?.name} {isMe && <span className="font-mono text-[10px]">(YOU)</span>}</p>
                <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                  <p className="font-mono text-[10px] opacity-80">{r.clips_submitted} clips</p>
                  {chLabel && (
                    <a href={ch.url || (ch.handle ? `https://youtube.com/@${ch.handle}` : "#")}
                       target="_blank" rel="noreferrer"
                       onClick={(e) => e.stopPropagation()}
                       className="oc-chip inline-flex items-center gap-1"
                       style={{ background: chipBg, color: "#2CFF05", fontSize: "0.6rem" }}
                       data-testid={`lb-channel-${r.rank}`}>
                      <Youtube size={10}/> {chLabel}
                      {ch.verified && <span title="API-verified">✓</span>}
                    </a>
                  )}
                </div>
              </div>
              <div className="text-right">
                <p className="font-display font-black">{fmt(r.total_points)} pts</p>
                <p className="font-mono text-[10px] opacity-80">₹{fmt(r.projected_payout)} · {r.reward_share_pct}%</p>
              </div>
            </li>
          );
        })}
      </ol>}
  </div>
);

const SubmitClipModal = ({ campaign, onClose, onDone }) => {
  const [form, setForm] = useState({ platform: "YOUTUBE_SHORTS", clip_url: "", views: 0, retention_pct: 0, engagement_pct: 0 });
  const [busy, setBusy] = useState(false);
  const [autoMsg, setAutoMsg] = useState("");

  const tryAuto = async () => {
    if (!form.clip_url) return;
    setAutoMsg("Fetching from YouTube…");
    try {
      const r = await ytFetch(form.clip_url);
      if (r.ok) {
        setForm(f => ({ ...f, views: r.views, engagement_pct: r.engagement_pct }));
        setAutoMsg(`Auto-filled views & engagement for "${r.title.slice(0, 40)}…"`);
      } else { setAutoMsg(r.message || "Auto-fetch unavailable, enter manually."); }
    } catch { setAutoMsg("Auto-fetch failed, enter manually."); }
  };

  const submit = async () => {
    setBusy(true);
    try {
      await submitClip({
        campaign_id: campaign.campaign_id, ...form,
        views: Number(form.views), retention_pct: Number(form.retention_pct), engagement_pct: Number(form.engagement_pct),
      });
      onDone();
    } catch (e) { alert(e.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" data-testid="submit-modal">
      <div className="oc-card w-full max-w-2xl bg-white max-h-[90vh] overflow-y-auto">
        <h2 className="font-display text-2xl font-black mb-1">Submit a clip</h2>
        <p className="text-sm text-[#2D2D2D] mb-4">Just the URL — we'll verify the channel & fetch metrics automatically.</p>
        <div className="space-y-3 text-sm">
          <label className="block">
            <span className="font-mono text-[10px] tracking-[0.2em]">PLATFORM</span>
            <select value={form.platform} onChange={e => setForm({ ...form, platform: e.target.value })}
              className="w-full mt-1 p-3 border-2 border-black rounded-lg font-medium" data-testid="clip-platform">
              <option value="YOUTUBE_SHORTS">YouTube Shorts</option>
              <option value="TIKTOK">TikTok</option>
              <option value="INSTAGRAM_REELS">Instagram Reels</option>
            </select>
          </label>
          <label className="block">
            <span className="font-mono text-[10px] tracking-[0.2em]">CLIP URL</span>
            <input value={form.clip_url} onChange={e => setForm({ ...form, clip_url: e.target.value })}
              onBlur={() => form.platform === "YOUTUBE_SHORTS" && tryAuto()}
              placeholder="https://youtube.com/shorts/..." className="w-full mt-1 p-3 border-2 border-black rounded-lg" data-testid="clip-url" />
          </label>
          {autoMsg && <p className="font-mono text-[10px] tracking-[0.15em] text-[#BF00FF]">{autoMsg}</p>}
          <div className="grid grid-cols-3 gap-3">
            {[["views", "VIEWS"], ["retention_pct", "RETENTION %"], ["engagement_pct", "ENGAGEMENT %"]].map(([k, l]) => (
              <label key={k} className="block">
                <span className="font-mono text-[10px] tracking-[0.2em]">{l}</span>
                <input type="number" value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}
                  className="w-full mt-1 p-3 border-2 border-black rounded-lg" data-testid={`clip-${k}`} />
              </label>
            ))}
          </div>
        </div>
        <div className="mt-5 flex gap-3 justify-end">
          <button onClick={onClose} className="oc-btn oc-btn-ghost" data-testid="cancel-submit">Cancel</button>
          <button onClick={submit} disabled={busy || !form.clip_url} className="oc-btn oc-btn-primary" data-testid="confirm-submit">
            {busy ? "Submitting…" : "Submit clip"}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Submit Short Modal (YouTube Shorts URL-only submission with channel verification) ─── */
const SubmitShortModal = ({ campaignId, onClose, onDone }) => {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!url.trim()) return;
    setBusy(true);
    setError("");
    try {
      await submitShort(campaignId, url.trim());
      onDone();
    } catch (e) {
      setError(e.response?.data?.detail || "Submission failed. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" data-testid="submit-short-modal">
      <div className="bg-white w-full max-w-md rounded-2xl border-2 border-black overflow-hidden">
        <div className="px-6 py-4 border-b-2 border-black flex items-center gap-3 bg-[#F8F8F8]">
          <Youtube size={20} className="text-red-600" />
          <h2 className="font-display text-xl font-black">Submit YouTube Short</h2>
        </div>
        <div className="p-6">
          <p className="text-sm text-[#2D2D2D] mb-4">
            Paste the URL of your YouTube Short. We'll verify it was uploaded on the channel you used to join this campaign.
          </p>
          <label className="block">
            <span className="font-mono text-[10px] tracking-[0.2em]">YOUTUBE SHORTS URL</span>
            <input
              value={url}
              onChange={e => { setUrl(e.target.value); setError(""); }}
              placeholder="https://youtube.com/shorts/..."
              className="w-full mt-1 p-3 border-2 border-black rounded-lg font-mono text-sm"
              data-testid="short-url-input"
              autoFocus
            />
          </label>
          {error && (
            <div className="mt-3 p-3 rounded-lg bg-red-50 border border-red-300" data-testid="short-error">
              <p className="font-mono text-xs text-red-700">{error}</p>
            </div>
          )}
          <div className="mt-6 flex gap-3">
            <button onClick={onClose} className="oc-btn oc-btn-ghost flex-1" data-testid="short-cancel">
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={busy || !url.trim()}
              className="oc-btn oc-btn-primary flex-1"
              data-testid="short-confirm"
            >
              {busy ? "Verifying…" : "Submit"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
