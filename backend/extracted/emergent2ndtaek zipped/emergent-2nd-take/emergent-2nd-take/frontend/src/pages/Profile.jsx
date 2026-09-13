import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getMyFullProfile, getProfileByUsername, updateProfile,
         addFeaturedClip, removeFeaturedClip, uploadFile } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Share2, Pencil, Plus, Trash2, Lock, ChevronDown, ChevronUp,
         Youtube, Instagram, Twitter, MessageCircle, Music2, Check, X, ExternalLink, Link } from "lucide-react";

const fmtViews = (n) => {
  n = Number(n || 0);
  if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "K";
  return String(n);
};
const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));

const PLATFORMS = [
  { key: "youtube",   label: "YouTube",  Icon: Youtube,        color: "#FF0033" },
  { key: "tiktok",    label: "TikTok",   Icon: Music2,         color: "#000000" },
  { key: "instagram", label: "Instagram",Icon: Instagram,      color: "#BF00FF" },
  { key: "twitter",   label: "Twitter/X",Icon: Twitter,        color: "#000000" },
  { key: "discord",   label: "Discord",  Icon: MessageCircle,  color: "#BF00FF" },
  { key: "website",   label: "Website",  Icon: Link,           color: "#2CFF05" },
];

const CLIP_PLATFORMS = [
  { value: "YOUTUBE_SHORTS",   label: "YouTube Shorts", Icon: Youtube },
  { value: "TIKTOK",           label: "TikTok",         Icon: Music2 },
  { value: "INSTAGRAM_REELS",  label: "Instagram Reels", Icon: Instagram },
];

// Theme tokens
const TH = {
  light: {
   card: "bg-white border-2 border-black rounded-3xl p-8 md:p-10",
    textPri: "text-black", textMuted: "text-[#2D2D2D]", textHint: "text-[#2D2D2D]",
    bodyText: "text-[#2D2D2D]",
    inputBase: "w-full p-3 bg-white border-2 border-black rounded-lg text-black",
    inputInline: "bg-transparent border-b-2 border-[#2CFF05] text-black",
    badgeEarnedBorder: "#000",
    bioInput: "w-full p-3 bg-white border-2 border-black rounded-lg text-black",
  },
  dark: {
    card: "bg-[#0A0A0A] border border-[#2D2D2D] rounded-2xl p-4",
    textPri: "text-white", textMuted: "text-gray-400", textHint: "text-[#2D2D2D]",
    bodyText: "text-gray-300",
    inputBase: "w-full p-3 bg-black border border-[#2D2D2D] rounded-lg text-white",
    inputInline: "bg-transparent border-b-2 border-[#2CFF05] text-white",
    badgeEarnedBorder: "#2CFF05",
    bioInput: "w-full p-3 bg-black border-2 border-[#2CFF05] rounded-lg text-white resize-none",
  },
};

// ===== Public profile page wrapper (dark theme) =====
export function PublicProfile() {
  const { username } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    getProfileByUsername(username).then(setData).catch(() => setErr("not found"));
  }, [username]);
  if (err) return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center" data-testid="public-404">
      <div className="text-center">
        <p className="font-display text-5xl font-black">404</p>
        <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D] mt-5">EDITOR NOT FOUND</p>
        <a href="/" className="oc-btn oc-btn-primary mt-6">Go home</a>
      </div>
    </div>
  );
  if (!data) return <div className="min-h-screen bg-black text-white p-10 font-mono text-sm oc-pulse">LOADING…</div>;
  return (
    <div className="min-h-screen bg-black text-white" data-testid="public-profile">
      <header className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
        <a href="/" className="font-display font-black text-xl tracking-tight">
          OUT<span className="text-[#2CFF05]">CLIPPED</span>
        </a>
        <a href="/" className="font-mono text-xs tracking-[0.2em] text-[#2D2D2D] hover:text-[#2CFF05]" data-testid="public-back">
          ← BACK TO OUTCLIPPED
        </a>
      </header>
      <div className="max-w-6xl mx-auto px-6 pb-20">
        <ProfileView data={data} editable={false} theme="dark" />
      </div>
    </div>
  );
}

// ===== Editable profile page (light theme, in app shell) =====
export default function Profile() {
  const { user, setUser } = useAuth();
  const [data, setData] = useState(null);
  const load = () => getMyFullProfile().then(setData);
  useEffect(() => { load(); }, []);
  if (!data) return <p className="font-mono text-sm oc-pulse">LOADING PROFILE…</p>;
  return <ProfileView data={data} editable={true} theme="light" onReload={load} setUser={setUser} />;
}

const getStatusBadge = (status) => {
  const s = (status || "").toUpperCase();
  if (s === "COMPLETED") {
    return (
      <span className="px-3 py-1 text-xs font-semibold rounded-full bg-green-500/10 text-green-500 border border-green-500/20">
        Completed
      </span>
    );
  }
  if (s === "ACTIVE" || s === "IN_PROGRESS" || s === "SETTLING") {
    return (
      <span className="px-3 py-1 text-xs font-semibold rounded-full bg-orange-500/10 text-orange-500 border border-orange-500/20">
        Active
      </span>
    );
  }
  return (
    <span className="px-3 py-1 text-xs font-semibold rounded-full bg-gray-500/10 text-gray-400 border border-gray-500/20">
      Draft
    </span>
  );
};

const CampaignThumbnail = ({ url, title }) => {
  if (url) {
    return <img src={url} className="w-12 h-12 rounded-xl object-cover border border-black/10 flex-shrink-0" alt={title} />;
  }
  const letter = (title || "C").charAt(0).toUpperCase();
  return (
    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center text-white font-display font-black text-lg border border-black/10 shadow-sm flex-shrink-0">
      {letter}
    </div>
  );
};

// ===== Shared view =====
const ProfileView = ({ data, editable, theme = "light", onReload, setUser }) => {
  const navigate = useNavigate();
  const t = TH[theme];
  const isCreator = data.role === "CREATOR";
  const [editing, setEditing] = useState({ name: false, bio: false });
  const [draft, setDraft] = useState({
    display_name: data.display_name, bio: data.bio, socials: { ...(data.socials || {}) },
  });
  const [toast, setToast] = useState(null);
  const [showAddClip, setShowAddClip] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    setDraft({ display_name: data.display_name, bio: data.bio, socials: { ...(data.socials || {}) } });
  }, [data]);

  const flash = (msg) => { setToast(msg); setTimeout(() => setToast(null), 1800); };

  const saveField = async (patch) => {
    const u = await updateProfile(patch);
    if (setUser) setUser(u);
    if (onReload) await onReload();
    flash("Saved");
  };

  const copyShare = () => {
    const url = `${window.location.origin}/u/${data.username}`;
    navigator.clipboard.writeText(url).then(() => flash("Link copied!"));
  };

  const handleAvatarUpload = async (file) => {
    if (!file) return;
    try {
      const up = await uploadFile(file);
      const src = `/api/files/${up.path}`;
      await saveField({ avatar_url: src });
    } catch { flash("Upload failed"); }
  };

  const removeClip = async (id) => {
    await removeFeaturedClip(id);
    if (onReload) await onReload();
    flash("Removed");
  };

  return (
    <div
  className="max-w-7xl mx-auto space-y-12"
  data-testid={editable ? "profile-edit" : "profile-view"}
    >   
      {toast && (
        <div className="fixed top-6 right-6 z-50 px-5 py-3 rounded-full font-bold text-sm"
             style={{ background: "#2CFF05", color: "#000", boxShadow: "0 4px 0 #000" }} data-testid="profile-toast">
          {toast}
        </div>
      )}

      {/* HERO */}
      <section className={`${t.card} mb-12`} data-testid="hero">
        <div className="flex flex-col md:flex-row items-start gap-10 md:gap-14">
          <div className="relative flex-shrink-0">
            <img src={data.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${data.display_name || data.name}`}
                 className="w-40 h-40 md:w-48 md:h-48 rounded-2xl object-cover border-2 border-[#2CFF05]"
                 alt="" data-testid="profile-avatar" />
            {editable && (
              <label className="absolute -bottom-2 -right-2 w-10 h-10 rounded-full bg-[#2CFF05] text-black border-2 border-black flex items-center justify-center cursor-pointer hover:scale-110 transition-transform"
                     data-testid="avatar-upload">
                <Pencil size={16} />
                <input type="file" accept="image/*" className="hidden"
                       onChange={e => handleAvatarUpload(e.target.files[0])} />
              </label>
            )}
          </div>

          <div className="flex-1 min-w-0 w-full">
            {editing.name ? (
              <div className="flex items-center gap-2">
                <input value={draft.display_name || ""}
                       onChange={e => setDraft({ ...draft, display_name: e.target.value })}
                       className={`${t.inputInline} font-display text-3xl md:text-5xl font-black outline-none flex-1`}
                       data-testid="name-input" />
                <button onClick={async () => { await saveField({ display_name: draft.display_name }); setEditing({ ...editing, name: false }); }}
                        className="text-[#2CFF05]"><Check /></button>
                <button onClick={() => setEditing({ ...editing, name: false })} className={t.textHint}><X /></button>
              </div>
            ) : (
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className={`font-display text-3xl md:text-5xl font-black ${t.textPri} tracking-tight uppercase break-words`}
                    data-testid="display-name">{data.display_name || data.name}</h1>
                {editable && (
                  <button onClick={() => setEditing({ ...editing, name: true })} className={`${t.textHint} hover:text-[#2CFF05]`}
                          data-testid="edit-name-btn"><Pencil size={16} /></button>
                )}
              </div>
            )}

            <div className="mt-5 flex items-center gap-3 flex-wrap">
              <p className="font-mono text-sm text-[#BF00FF]" data-testid="username">@{data.username}</p>
              <span className="oc-chip" style={{ background: theme === "dark" ? "transparent" : "#000", color: "#2CFF05", border: `1px solid ${theme === "dark" ? "#2D2D2D" : "#000"}` }}>
                {data.role || "—"}
              </span>
            </div>

            <div className="mt-4">
              {editing.bio ? (
                <div>
                  <textarea value={draft.bio || ""}
                            maxLength={160}
                            onChange={e => setDraft({ ...draft, bio: e.target.value })}
                            rows={2}
                            className={`${t.bioInput} resize-none`}
                            data-testid="bio-input" />
                  <div className="flex items-center justify-between mt-2">
                    <span className={`font-mono text-[10px] ${t.textHint}`}>{(draft.bio || "").length}/160</span>
                    <div className="flex gap-2">
                      <button onClick={() => setEditing({ ...editing, bio: false })} className={`font-mono text-xs ${t.textHint}`}>CANCEL</button>
                      <button onClick={async () => { await saveField({ bio: draft.bio }); setEditing({ ...editing, bio: false }); }}
                              className="font-mono text-xs text-[#2CFF05]">SAVE</button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-2">
                  <p className={`text-base ${t.bodyText} max-w-2xl`} data-testid="bio-text">
                    {data.bio || (editable ? <span className={`italic ${t.textHint}`}>Add a bio…</span> : "")}
                  </p>
                  {editable && (
                    <button onClick={() => setEditing({ ...editing, bio: true })} className={`${t.textHint} hover:text-[#2CFF05] mt-1`}
                            data-testid="edit-bio-btn"><Pencil size={14} /></button>
                  )}
                </div>
              )}
            </div>

            {/* SOCIAL LINKS (shown on both, website too) */}
            <div className="mt-4 flex items-center gap-4 text-gray-400">
              {PLATFORMS.map(({ key, Icon }) => {
                const url = (data.socials || {})[key];
                if (!url) return null;
                return (
                  <a key={key} href={url} target="_blank" rel="noreferrer" className="hover:text-[#2CFF05] transition-colors" title={key.toUpperCase()}>
                    <Icon size={20} />
                  </a>
                );
              })}
            </div>

            <div className="mt-6 flex items-center gap-3 flex-wrap">
              <button onClick={copyShare} className="oc-btn oc-btn-primary" data-testid="share-btn">
                <Share2 size={16} /> Share profile
              </button>
              {editable && (
                <span className={`font-mono text-[10px] tracking-[0.2em] ${t.textHint}`}>/u/{data.username}</span>
              )}
            </div>
          </div>
        </div>
      </section>

      {isCreator ? (
        <>
          {/* CREATOR STATS */}
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-5 mb-12" data-testid="creator-stats">
            <div className={t.card}>
              <p className={`font-mono text-[10px] tracking-[0.3em] ${t.textHint}`}>CAMPAIGNS CREATED</p>
              <p className={`font-display text-3xl md:text-4xl font-black mt-2 ${t.textPri}`}>{data.creator_stats?.campaigns_created || 0}</p>
            </div>
            <div className={t.card}>
              <p className={`font-mono text-[10px] tracking-[0.3em] ${t.textHint}`}>TOTAL BUDGET DISTRIBUTED</p>
              <p className={`font-display text-3xl md:text-4xl font-black mt-2 ${t.textPri}`}>₹{fmt(data.creator_stats?.total_budget_distributed || 0)}</p>
            </div>
            <div className={t.card}>
              <p className={`font-mono text-[10px] tracking-[0.3em] ${t.textHint}`}>TOTAL CLIPS RECEIVED</p>
              <p className={`font-display text-3xl md:text-4xl font-black mt-2 ${t.textPri}`}>{fmtViews(data.creator_stats?.total_clips_received || 0)}</p>
            </div>
            <div className={t.card}>
              <p className={`font-mono text-[10px] tracking-[0.3em] ${t.textHint}`}>ACTIVE CAMPAIGNS</p>
              <p className={`font-display text-3xl md:text-4xl font-black mt-2 ${t.textPri}`}>{data.creator_stats?.active_campaigns || 0}</p>
            </div>
          </section>

          {/* CAMPAIGN HISTORY (CREATOR) */}
          <section className="mb-12" data-testid="creator-campaign-history">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className={`font-display text-2xl font-black ${t.textPri}`}>Campaigns</h2>
                <p className={`font-mono text-xs ${t.textHint} mt-1`}>Campaigns you've created and managed.</p>
              </div>
              {editable && (
                <button onClick={() => navigate("/app/campaigns/new")} className="oc-btn oc-btn-primary" data-testid="new-campaign-btn">
                  <Plus size={16} /> New Campaign
                </button>
              )}
            </div>

            <div className={`${t.card} overflow-x-auto`}>
              {(data.campaign_history || []).length === 0 ? (
                <div className="text-center py-14">
                  <p className={`font-mono text-xs tracking-[0.25em] ${t.textHint}`}>NO CAMPAIGNS CREATED YET</p>
                  {editable && <p className={`text-sm ${t.bodyText} mt-2`}>Click "New Campaign" to create one.</p>}
                </div>
              ) : (
                <table className="w-full text-left border-collapse" data-testid="creator-campaigns-table">
                  <thead>
                    <tr className="border-b border-[#F0F0F0]/10 font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">
                      <th className="pb-4 font-bold text-left">CAMPAIGN</th>
                      <th className="pb-4 font-bold text-left">STATUS</th>
                      <th className="pb-4 font-bold text-right">TOTAL BUDGET</th>
                      <th className="pb-4 font-bold text-right">SPENT</th>
                      <th className="pb-4 font-bold text-right">SUBMITTED CLIPS</th>
                      <th className="pb-4 font-bold text-right">CREATED ON</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.campaign_history || []).map(c => (
                      <tr key={c.campaign_id} className="border-b border-[#F0F0F0]/5 hover:bg-[#F9F9F9]/5 transition-colors">
                        <td className="py-4 flex items-center gap-3">
                          <CampaignThumbnail url={c.thumbnail_url} title={c.title} />
                          <div>
                            <p className={`font-display font-black text-base ${t.textPri}`}>{c.title}</p>
                            <p className={`text-xs ${t.textHint} max-w-xs truncate`}>{c.description || "No description"}</p>
                          </div>
                        </td>
                        <td className="py-4">
                          {getStatusBadge(c.status)}
                        </td>
                        <td className={`py-4 text-right font-semibold ${t.textPri}`}>
                          ₹{fmt(c.bounty_pool)}
                        </td>
                        <td className={`py-4 text-right font-semibold ${t.textPri}`}>
                          ₹{fmt(c.amount_distributed || 0)}
                        </td>
                        <td className={`py-4 text-right ${t.textPri}`}>
                          {c.submissions_count || 0}
                        </td>
                        <td className={`py-4 text-right ${t.textPri}`}>
                          {c.created_at ? new Date(c.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>

          {/* SOCIALS EDITING FOR CREATORS (editable only) */}
          {editable && (
            <section className={`${t.card} mb-12`} data-testid="socials">
              <h3 className={`font-display text-2xl font-black ${t.textPri} mb-5`}>Manage Social & Website Links</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                {PLATFORMS.map(({ key, label, Icon, color }) => {
                  const url = (data.socials || {})[key];
                  return (
                    <SocialItem key={key} editable={editable} theme={theme}
                                platformKey={key} label={label} Icon={Icon} color={color}
                                url={url}
                                onSave={async (v) => {
                                  const next = { ...(data.socials || {}), [key]: v };
                                  await saveField({ socials: next });
                                }} />
                  );
                })}
              </div>
            </section>
          )}
        </>
      ) : (
        <>
          {/* METRICS */}
          <section className="grid sm:grid-cols-2 gap-5 mb-12" data-testid="metrics">
            <div className={t.card}>
              <p className={`font-mono text-[10px] tracking-[0.3em] ${t.textHint}`}>TOTAL VIEWS GENERATED</p>
              <p className={`font-display text-4xl md:text-5xl font-black mt-2 ${t.textPri}`}>{fmtViews(data.total_views_generated)}</p>
              <p className="font-mono text-xs text-[#2CFF05] mt-2">↗ ALL-TIME</p>
            </div>
            <div className={t.card}>
              <p className={`font-mono text-[10px] tracking-[0.3em] ${t.textHint}`}>LIFETIME OCV</p>
              <p className={`font-display text-4xl md:text-5xl font-black mt-2 ${t.textPri}`}>{Number(data.lifetime_ocv || 0).toFixed(2)}</p>
              <p className="font-mono text-xs text-[#2CFF05] mt-2">VERIFIED VIEWS</p>
            </div>
          </section>

          {/* SOCIALS */}
          <section className={`${t.card} mb-12`} data-testid="socials">
            <h3 className={`font-display text-2xl font-black ${t.textPri} mb-5`}>Socials</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {PLATFORMS.map(({ key, label, Icon, color }) => {
                const url = (data.socials || {})[key];
                if (!editable && !url) return null;
                return (
                  <SocialItem key={key} editable={editable} theme={theme}
                              platformKey={key} label={label} Icon={Icon} color={color}
                              url={url}
                              onSave={async (v) => {
                                const next = { ...(data.socials || {}), [key]: v };
                                  await saveField({ socials: next });
                              }} />
                );
              })}
            </div>
            {!editable && Object.values(data.socials || {}).filter(Boolean).length === 0 && (
              <p className={`font-mono text-xs tracking-[0.2em] ${t.textHint} py-4`}>NO SOCIALS LISTED</p>
            )}
          </section>

          {/* BEST CLIPS */}
          <section className="mb-12" data-testid="featured-clips">
            <div className="flex items-center justify-between mb-4">
              <h2 className={`font-display text-3xl font-black ${t.textPri}`}>Best Clips</h2>
              {editable && (data.featured_clips?.length || 0) < 6 && (
                <button onClick={() => setShowAddClip(true)} className="oc-btn oc-btn-primary" data-testid="add-clip-btn">
                  <Plus size={16} /> Add clip
                </button>
              )}
            </div>
            {(data.featured_clips || []).length === 0 ? (
              <div className={`${t.card} text-center py-14`} data-testid="clips-empty">
                <p className={`font-mono text-xs tracking-[0.25em] ${t.textHint}`}>NO FEATURED CLIPS YET</p>
                {editable && <p className={`text-sm ${t.bodyText} mt-2`}>Add up to 6 of your best clips.</p>}
              </div>
            ) : (
              <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6">
                {(data.featured_clips || []).map(c => (
                  <FeaturedClipCard key={c.id} clip={c} editable={editable} theme={theme} t={t} onRemove={() => removeClip(c.id)} />
                ))}
              </div>
            )}
          </section>

          {/* AWARDS */}
          <section className="mb-12" data-testid="awards">
            <h2 className={`font-display text-3xl font-black ${t.textPri} mb-4`}>Awards</h2>
            <div className="flex gap-4 overflow-x-auto pb-3 -mx-2 px-2" data-testid="awards-row">
              {(data.badges || []).map(b => (
                <div key={b.id}
                     className={`flex-shrink-0 w-52 ${t.card} relative`}
                     style={{ opacity: b.earned ? 1 : 0.45,
                              borderColor: b.earned ? t.badgeEarnedBorder : (theme === "dark" ? "#2D2D2D" : "#2D2D2D") }}
                     data-testid={`badge-${b.id}`}>
                  {!b.earned && <Lock size={14} className={`absolute top-3 right-3 ${t.textHint}`} />}
                  <div className="text-4xl">{b.icon}</div>
                  <p className={`font-display font-black text-lg mt-2 ${t.textPri}`}>{b.name}</p>
                  <p className={`text-xs ${t.bodyText} mt-1`}>{b.description}</p>
                  {b.earned && <p className="font-mono text-[10px] tracking-[0.2em] text-[#2CFF05] mt-5">EARNED</p>}
                </div>
              ))}
            </div>
          </section>

          {/* CAMPAIGN HISTORY — edit only */}
          {editable && (
            <section data-testid="campaign-history">
              <button onClick={() => setShowHistory(!showHistory)}
                      className="oc-btn oc-btn-ghost" data-testid="toggle-history">
                View Campaign History {showHistory ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
              {showHistory && (
                <div className={`mt-4 ${t.card}`}>
                  {(data.campaign_history || []).length === 0 ? (
                    <p className={`font-mono text-xs tracking-[0.2em] ${t.textHint} py-6 text-center`}>NO CAMPAIGN HISTORY YET</p>
                  ) : (
                    <table className="w-full text-sm" data-testid="history-table">
                      <thead>
                        <tr className={`text-left font-mono text-[10px] tracking-[0.2em] ${t.textHint}`}>
                          <th className="pb-3">CAMPAIGN</th>
                          <th className="pb-3 text-right">RANK</th>
                          <th className="pb-3 text-right">OCV</th>
                          <th className="pb-3 text-right">PAYOUT</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.campaign_history.map(h => (
                          <tr key={h.campaign_id} className={`border-t ${theme === "dark" ? "border-[#2D2D2D]" : "border-black"}`}>
                            <td className={`py-3 ${t.textPri}`}>{h.title}</td>
                            <td className="py-3 text-right font-display font-black text-[#BF00FF]">{h.rank ? `#${h.rank}` : "—"}</td>
                            <td className={`py-3 text-right ${t.textPri}`}>{Number(h.ocv || 0).toFixed(2)}</td>
                            <td className={`py-3 text-right ${t.textPri}`}>₹{fmt(h.payout)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </section>
          )}
        </>
      )}

      {showAddClip && <AddClipModal theme={theme}
                                    onClose={() => setShowAddClip(false)}
                                    onDone={async () => { setShowAddClip(false); if (onReload) await onReload(); flash("Clip added"); }} />}
    </div>
  );
};

// ===== Featured clip card =====
const FeaturedClipCard = ({ clip, editable, theme, t, onRemove }) => {
  const Plat = CLIP_PLATFORMS.find(p => p.value === clip.platform)?.Icon || Youtube;
  return (
    <div className={`${t.card} group relative`} data-testid={`clip-card-${clip.id}`}>
      {editable && (
        <button onClick={onRemove}
                className={`absolute top-3 right-3 w-8 h-8 rounded-full ${theme === "dark" ? "bg-black border border-[#2D2D2D]" : "bg-white border-2 border-black"} flex items-center justify-center text-[#BF00FF] opacity-0 group-hover:opacity-100 transition-opacity z-10`}
                data-testid={`remove-clip-${clip.id}`}>
          <Trash2 size={14} />
        </button>
      )}
      <div className={`aspect-video rounded-lg overflow-hidden ${theme === "dark" ? "bg-black border border-[#2D2D2D]" : "bg-[#2D2D2D] border-2 border-black"} mb-4 flex items-center justify-center relative`}>
        {clip.thumbnail_url ? (
          <img src={clip.thumbnail_url} className="w-full h-full object-cover" alt="" />
        ) : clip.video_url ? (
          <a href={clip.video_url} target="_blank" rel="noreferrer" className="text-[#2CFF05] hover:scale-110 transition-transform flex flex-col items-center">
            <ExternalLink size={32} />
            <span className="font-mono text-[10px] mt-2 tracking-[0.2em]">OPEN VIDEO</span>
          </a>
        ) : (
          <Plat size={48} className="text-white opacity-30" />
        )}
        <span className="absolute bottom-3 left-3 oc-chip" style={{ background: "rgba(0,0,0,0.85)", color: "#fff" }}>
          <Plat size={12} /> {(clip.platform || "").replace("_", " ")}
        </span>
      </div>
      <h3 className={`font-display text-lg font-black leading-tight ${t.textPri}`}>{clip.title}</h3>
      <div className="mt-5 flex items-center justify-between">
        <p className={`font-mono text-xs ${t.bodyText}`}>{fmtViews(clip.views)} views</p>
        <span className="oc-chip" style={{ background: "#BF00FF", color: "#fff" }}>{Number(clip.ocv || clip.points || 0).toFixed(2)} OCV</span>
      </div>
    </div>
  );
};

// ===== Social item =====
const SocialItem = ({ editable, theme, platformKey, label, Icon, color, url, onSave }) => {
  const t = TH[theme];
  const [open, setOpen] = useState(false);
  const [val, setVal] = useState(url || "");
  const active = !!url;
  if (!editable) {
    return (
      <a href={url} target="_blank" rel="noreferrer"
         className={`${t.card} hover:border-[#2CFF05] flex items-center gap-3 transition-colors`}
         data-testid={`social-${platformKey}-public`}>
        <Icon size={20} style={{ color }} />
        <span className={`font-mono text-xs tracking-[0.1em] ${t.textPri}`}>{label.toUpperCase()}</span>
      </a>
    );
  }
  return (
    <div>
      {!open ? (
        <button onClick={() => setOpen(true)}
                className={`${t.card} w-full flex items-center gap-3 transition-colors`}
                style={{ borderColor: active ? "#2CFF05" : undefined }}
                data-testid={`social-${platformKey}`}>
          <Icon size={20} style={{ color: active ? "#2CFF05" : color }} />
          <span className={`font-mono text-xs tracking-[0.1em] ${t.textPri} truncate`}>{label.toUpperCase()}</span>
          {active && <Check size={14} className="ml-auto text-[#2CFF05]" />}
        </button>
      ) : (
        <div className={t.card}>
          <div className="flex items-center gap-2 mb-2">
            <Icon size={18} style={{ color }} />
            <span className={`font-mono text-[10px] tracking-[0.2em] ${t.textHint}`}>{label.toUpperCase()} URL</span>
          </div>
          <input value={val} onChange={e => setVal(e.target.value)}
                 placeholder={`https://${platformKey}.com/...`}
                 className={`${t.inputBase} text-sm`}
                 data-testid={`social-${platformKey}-input`} />
          <div className="flex gap-2 mt-2 justify-end">
            <button onClick={() => { setOpen(false); setVal(url || ""); }} className={`font-mono text-xs ${t.textHint}`}>CANCEL</button>
            <button onClick={async () => { await onSave(val.trim()); setOpen(false); }}
                    className="font-mono text-xs text-[#2CFF05]" data-testid={`social-${platformKey}-save`}>SAVE</button>
          </div>
        </div>
      )}
    </div>
  );
};

// ===== Add clip modal =====
const AddClipModal = ({ theme, onClose, onDone }) => {
  const t = TH[theme];
  const [form, setForm] = useState({
    title: "", platform: "YOUTUBE_SHORTS", views: 0, ocv: 0.0, video_url: "", thumbnail_url: "",
  });
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!form.title) return;
    setBusy(true);
    try {
      let thumbnail_url = form.thumbnail_url;
      if (file) {
        const up = await uploadFile(file);
        thumbnail_url = `/api/files/${up.path}`;
      }
      await addFeaturedClip({
        title: form.title, platform: form.platform,
        views: Number(form.views),
        ocv: Number(form.ocv),
        points: Number(form.ocv),
        video_url: form.video_url || null, thumbnail_url: thumbnail_url || null,
      });
      onDone();
    } catch (e) { alert(e.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" data-testid="add-clip-modal">
      <div className={`${t.card} w-full max-w-lg max-h-[90vh] overflow-y-auto`}>
        <h2 className={`font-display text-2xl font-black ${t.textPri} mb-4`}>Add featured clip</h2>
        <div className="space-y-3">
          <Field t={t} label="CLIP TITLE">
            <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} className={t.inputBase} data-testid="add-title" />
          </Field>
          <Field t={t} label="PLATFORM">
            <select value={form.platform} onChange={e => setForm({ ...form, platform: e.target.value })} className={t.inputBase} data-testid="add-platform">
              {CLIP_PLATFORMS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field t={t} label="VIEW COUNT">
              <input type="number" value={form.views} onChange={e => setForm({ ...form, views: e.target.value })} className={t.inputBase} data-testid="add-views" />
            </Field>
            <Field t={t} label="OCV">
              <input type="number" step="0.01" value={form.ocv} onChange={e => setForm({ ...form, ocv: e.target.value })} className={t.inputBase} data-testid="add-ocv" />
            </Field>
          </div>
          <Field t={t} label="VIDEO URL (optional)">
            <input value={form.video_url} onChange={e => setForm({ ...form, video_url: e.target.value })}
                   placeholder="https://youtube.com/shorts/..." className={t.inputBase} data-testid="add-url" />
          </Field>
          <Field t={t} label="THUMBNAIL UPLOAD (optional)">
            <input type="file" accept="image/*" onChange={e => setFile(e.target.files[0])}
                   className={t.inputBase} data-testid="add-thumbnail" />
          </Field>
        </div>
        <div className="mt-5 flex gap-3 justify-end">
          <button onClick={onClose} className={`font-mono text-xs ${t.textHint}`} data-testid="cancel-add">CANCEL</button>
          <button onClick={submit} disabled={busy || !form.title} className="oc-btn oc-btn-primary" data-testid="save-add">
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
};

const Field = ({ t, label, children }) => (
  <label className="block">
    <span className={`font-mono text-[10px] tracking-[0.2em] ${t.textHint}`}>{label}</span>
    <div className="mt-1">{children}</div>
  </label>
);
