import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getCampaign, submitClip, listClips, ytFetch } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { ArrowLeft, Plus, ExternalLink, Calendar, Eye, Award } from "lucide-react";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));
const fmtOcv = (n) => n !== undefined && n !== null ? Number(n).toFixed(2) : "0.00";
const fmtDate = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" });
};

const getThumbnail = (clip) => {
  if (clip.video_id) {
    return `https://i.ytimg.com/vi/${clip.video_id}/mqdefault.jpg`;
  }
  const url = clip.clip_url || "";
  const match = url.match(/(?:shorts\/|v=|\/vi\/|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
  if (match && match[1]) {
    return `https://i.ytimg.com/vi/${match[1]}/mqdefault.jpg`;
  }
  return `https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=400&q=80`;
};

const SubmitClipModal = ({ campaign, onClose, onDone }) => {
  const [form, setForm] = useState({ platform: "YOUTUBE_SHORTS", clip_url: "" });
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      await submitClip({
        campaign_id: campaign.campaign_id,
        platform: form.platform,
        clip_url: form.clip_url,
      });
      onDone();
    } catch (e) {
      console.log("Full backend response:", e.response?.data);
      let errMsg = "Failed to submit clip";
      if (e.response?.data) {
        const data = e.response.data;
        if (data.detail) {
          if (Array.isArray(data.detail)) {
            // Render array of validation errors as readable text
            errMsg = data.detail.map(err => {
              const field = err.loc ? err.loc.join(".") : "error";
              return `${field}: ${err.msg}`;
            }).join("\n");
          } else if (typeof data.detail === "string") {
            errMsg = data.detail;
          } else {
            errMsg = JSON.stringify(data.detail);
          }
        } else if (data.message) {
          errMsg = data.message;
        } else {
          errMsg = JSON.stringify(data);
        }
      } else if (e.message) {
        errMsg = e.message;
      }
      alert(errMsg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" data-testid="submit-modal">
      <div className="oc-card w-full max-w-2xl bg-white max-h-[90vh] overflow-y-auto">
        <h2 className="font-display text-2xl font-black mb-1">Submit a clip</h2>
        <p className="text-sm text-[#2D2D2D] mb-4">Just the URL — we'll verify the channel & fetch metrics automatically.</p>
        
        <div className="space-y-4 text-sm">
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
              placeholder="https://youtube.com/shorts/..." className="w-full mt-1 p-3 border-2 border-black rounded-lg" data-testid="clip-url" />
          </label>
          
          <div className="p-4 bg-black/5 rounded-lg border border-black/10">
            <p className="font-mono text-[11px] text-[#BF00FF] tracking-wide leading-relaxed">
              ℹ We automatically verify ownership, fetch performance metrics, calculate OCV, and track earnings.
            </p>
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

export default function CampaignSubmissions() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [c, setC] = useState(null);
  const [clips, setClips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showSubmit, setShowSubmit] = useState(false);

  const refresh = async () => {
    try {
      const [campaignData, clipsData] = await Promise.all([
        getCampaign(id),
        listClips({ campaign_id: id })
      ]);
      setC(campaignData);
      setClips(clipsData);
    } catch (e) {
      console.error("Failed to load submissions page data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, [id]);

  if (loading || !c) return <p className="font-mono text-sm oc-pulse p-10">LOADING SUBMISSIONS…</p>;

  // Filter My Clips
  const myClips = user ? clips.filter(cl => cl.editor_id === user.user_id) : [];

  // Sort Top Clips by OCV descending, excluding soft-deleted ones
  const topClips = [...clips]
    .filter(cl => !cl.is_deleted)
    .sort((a, b) => (b.ocv || 0) - (a.ocv || 0));

  // expected earnings formula helper
  const getExpectedEarnings = (clipOcv, isDeleted) => {
    if (isDeleted) return 0;
    const netPool = c.bounty_pool * (1 - (c.platform_fee_percent || 15) / 100);
    const totalCampaignOcv = clips
      .filter(cl => !cl.is_deleted)
      .reduce((acc, cl) => acc + (cl.ocv || 0), 0);
    if (totalCampaignOcv <= 0) return 0;
    return (clipOcv / totalCampaignOcv) * netPool;
  };

  const getClipRank = (clipId) => {
    const idx = topClips.findIndex(cl => cl.clip_id === clipId);
    return idx !== -1 ? idx + 1 : "—";
  };

  return (
    <div data-testid="campaign-submissions-page" className="space-y-8">
      <header className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <button onClick={() => navigate(`/app/campaigns/${id}`)} className="font-mono text-xs tracking-[0.2em] flex items-center gap-1 mb-3" data-testid="back-btn">
            <ArrowLeft size={14}/> BACK TO CAMPAIGN
          </button>
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D] uppercase">{c.title}</p>
          <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Submissions</h1>
        </div>
        
        {c.status === "ACTIVE" && user?.role === "EDITOR" && (
          <button 
            onClick={() => setShowSubmit(true)} 
            className="oc-btn oc-btn-primary flex items-center gap-2" 
            data-testid="submit-new-clip-btn"
          >
            <Plus size={16}/> Submit New Clip
          </button>
        )}
      </header>

      {/* Submit New Clip Hero Box */}
      {c.status === "ACTIVE" && user?.role === "EDITOR" && (
        <div className="oc-card bg-[#2CFF05] text-black border-2 border-black flex flex-col md:flex-row items-center justify-between p-6 gap-4" data-testid="submit-hero">
          <div>
            <h2 className="font-display text-2xl font-black">[ Submit New Clip ]</h2>
            <p className="text-sm mt-1">Submit your Shorts or Reels link to fetch metrics and earn rewards from the pool.</p>
          </div>
          <button 
            onClick={() => setShowSubmit(true)} 
            className="oc-btn oc-btn-secondary whitespace-nowrap"
            data-testid="submit-hero-btn"
          >
            Submit Clip
          </button>
        </div>
      )}

      {/* Grid for My Clips & Top Clips */}
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left: My Clips */}
        <div className="space-y-4">
          <h3 className="font-display text-2xl font-black flex items-center gap-2">
            <Award size={20}/> My Clips
          </h3>
          
          {!user ? (
            <div className="oc-card text-center py-12">
              <p className="font-mono text-xs tracking-[0.2em]">PLEASE SIGN IN TO VIEW YOUR CLIPS</p>
            </div>
          ) : myClips.length === 0 ? (
            <div className="oc-card text-center py-12" data-testid="my-clips-empty">
              <p className="font-mono text-xs tracking-[0.2em]">YOU HAVEN'T SUBMITTED ANY CLIPS YET</p>
            </div>
          ) : (
            <div className="space-y-4">
              {myClips.map(cl => {
                const thumbnail = getThumbnail(cl);
                return (
                  <div key={cl.clip_id} className={`oc-card border-2 border-black p-4 flex flex-col sm:flex-row gap-4 ${cl.is_deleted ? "opacity-60" : ""}`} data-testid={`my-clip-${cl.clip_id}`}>
                    <div className="w-full sm:w-36 aspect-video rounded-lg overflow-hidden border-2 border-black relative flex-shrink-0 bg-black">
                      <img src={thumbnail} className="w-full h-full object-cover" alt={cl.title || "Clip thumbnail"} />
                      <div className="absolute top-2 left-2 bg-[#BF00FF] text-white px-2 py-0.5 rounded font-display font-black text-xs border border-black shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]">
                        {fmtOcv(cl.ocv)} OCV
                      </div>
                    </div>
                    
                    <div className="flex-1 min-w-0 flex flex-col justify-between">
                      <div className="space-y-1">
                        <div className="flex items-start justify-between gap-4">
                          <a href={cl.clip_url} target="_blank" rel="noreferrer" className="font-display font-black text-sm text-black hover:text-[#BF00FF] hover:underline flex items-center gap-1 truncate" title={cl.title || cl.clip_url}>
                            {cl.title || cl.clip_url.replace("https://", "")} <ExternalLink size={12} className="flex-shrink-0 inline" />
                          </a>
                          {cl.is_deleted && (
                            <span className="font-mono text-[9px] bg-red-600 text-white border border-black px-1.5 py-0.5 rounded shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] font-black uppercase flex-shrink-0">
                              Unavailable
                            </span>
                          )}
                        </div>
                        {cl.channel_name && (
                          <p className="font-mono text-[10px] text-gray-500">by {cl.channel_name}</p>
                        )}
                        <span className="font-mono text-[10px] text-gray-400 flex items-center gap-1 mt-1">
                          <Calendar size={12}/> {fmtDate(cl.submitted_at)}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-black/10">
                        <div>
                          <p className="font-mono text-[9px] text-gray-500">VIEWS</p>
                          <p className="font-display font-black text-sm md:text-base">{fmt(cl.views)}</p>
                        </div>
                        <div>
                          <p className="font-mono text-[9px] text-gray-500">PROJECTED</p>
                          <p className="font-display font-black text-xs md:text-sm text-[#2CFF05] bg-black px-1.5 py-0.5 rounded inline-block">₹{fmt(getExpectedEarnings(cl.ocv, cl.is_deleted))}</p>
                        </div>
                        <div>
                          <p className="font-mono text-[9px] text-gray-500">OCV</p>
                          <p className="font-display font-black text-sm md:text-base">{fmtOcv(cl.ocv)}</p>
                        </div>
                        <div>
                          <p className="font-mono text-[9px] text-gray-500">RANK</p>
                          <p className="font-display font-black text-sm md:text-base">#{getClipRank(cl.clip_id)}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Top Clips */}
        <div className="space-y-4">
          <h3 className="font-display text-2xl font-black flex items-center gap-2">
            <Eye size={20}/> Top Clips
          </h3>
          
          {topClips.length === 0 ? (
            <div className="oc-card text-center py-12" data-testid="top-clips-empty">
              <p className="font-mono text-xs tracking-[0.2em]">NO SUBMISSIONS YET</p>
            </div>
          ) : (
            <div className="space-y-4">
              {topClips.map((cl, idx) => {
                const rank = idx + 1;
                const isMe = user && cl.editor_id === user.user_id;
                const badgeBg = rank === 1 ? "#2CFF05" : rank === 2 ? "#BF00FF" : rank === 3 ? "#2D2D2D" : "#fff";
                const badgeFg = rank === 1 ? "#000" : rank === 2 ? "#fff" : rank === 3 ? "#fff" : "#000";
                const thumbnail = getThumbnail(cl);
                
                return (
                  <div key={cl.clip_id} className={`oc-card border-2 border-black p-4 flex flex-col sm:flex-row items-center gap-4 ${isMe ? "bg-black/5" : ""}`} data-testid={`top-clip-${cl.clip_id}`}>
                    <div className="flex items-center gap-3 w-full sm:w-auto">
                      <div 
                        className="w-10 h-10 rounded-full border-2 border-black flex items-center justify-center font-display font-black text-xl flex-shrink-0 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                        style={{ background: badgeBg, color: badgeFg }}
                      >
                        #{rank}
                      </div>

                      <div className="w-28 aspect-video rounded-lg overflow-hidden border-2 border-black relative flex-shrink-0 bg-black sm:hidden block">
                        <img src={thumbnail} className="w-full h-full object-cover" alt={cl.title || "Clip thumbnail"} />
                        <div className="absolute bottom-1 right-1 bg-black text-[#2CFF05] px-1 rounded font-display font-bold text-[10px] border border-black">
                          {fmtOcv(cl.ocv)} OCV
                        </div>
                      </div>
                    </div>
                    
                    <div className="w-28 aspect-video rounded-lg overflow-hidden border-2 border-black relative flex-shrink-0 bg-black hidden sm:block">
                      <img src={thumbnail} className="w-full h-full object-cover" alt={cl.title || "Clip thumbnail"} />
                      <div className="absolute bottom-1 right-1 bg-black text-[#2CFF05] px-1 rounded font-display font-bold text-[10px] border border-black">
                        {fmtOcv(cl.ocv)} OCV
                      </div>
                    </div>

                    <div className="flex-1 min-w-0 w-full sm:w-auto">
                      <div className="flex items-center gap-2">
                        <img 
                          src={cl.editor?.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${cl.editor?.name || "editor"}`} 
                          className="w-6 h-6 rounded-full border border-black" 
                          alt="" 
                        />
                        <p className="text-sm font-semibold truncate">{cl.editor?.name || "Anonymous"}</p>
                        {isMe && (
                          <span className="font-mono text-[9px] bg-[#2CFF05] text-black border border-black px-1 rounded">YOU</span>
                        )}
                      </div>
                      <a href={cl.clip_url} target="_blank" rel="noreferrer" className="font-mono text-xs text-[#BF00FF] truncate hover:underline block mt-1.5" title={cl.title || cl.clip_url}>
                        {cl.title || cl.clip_url.replace("https://", "")}
                      </a>
                    </div>
                    
                    <div className="text-right flex-shrink-0 w-full sm:w-auto flex sm:flex-col justify-between sm:justify-center border-t sm:border-t-0 pt-2 sm:pt-0 border-black/10">
                      <p className="font-mono text-[9px] text-gray-500 hidden sm:block">VIEWS</p>
                      <span className="font-mono text-[10px] text-gray-500 sm:hidden">VIEWS</span>
                      <p className="font-display font-black text-base">{fmt(cl.views)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {showSubmit && (
        <SubmitClipModal 
          campaign={c} 
          onClose={() => setShowSubmit(false)} 
          onDone={async () => { 
            setShowSubmit(false); 
            await refresh(); 
          }} 
        />
      )}
    </div>
  );
}
