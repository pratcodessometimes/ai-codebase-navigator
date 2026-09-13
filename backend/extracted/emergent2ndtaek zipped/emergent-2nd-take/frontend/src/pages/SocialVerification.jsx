import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Youtube, Instagram, Shield, CheckCircle, Plus, Trash2, Clock, AlertCircle } from "lucide-react";
import { getVerifiedChannels, startYoutubeVerification, verifyYoutube, removeVerifiedChannel } from "@/lib/api";

const fmt_date = (iso) => {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  } catch { return iso.slice(0, 10); }
};

/* ─── Add YouTube Channel Modal ─── */
const AddYouTubeModal = ({ onClose, onAdded }) => {
  const [stage, setStage] = useState("enter"); // enter | verify
  const [channelInput, setChannelInput] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [channelData, setChannelData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const handleStartVerification = async () => {
    if (!channelInput.trim()) return;
    setBusy(true);
    setError("");
    try {
      const res = await startYoutubeVerification(channelInput.trim());
      setVerificationCode(res.verification_code);
      setChannelData(res.channel);
      setStage("verify");
    } catch (e) {
      setError(e.response?.data?.detail || "Could not resolve YouTube channel. Paste full channel URL or @handle.");
    } finally {
      setBusy(false);
    }
  };

  const handleConfirmVerification = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await verifyYoutube(channelInput.trim());
      onAdded(res.channel);
      onClose();
    } catch (e) {
      setError(e.response?.data?.detail || "Verification failed. Make sure the code is pasted into your channel description.");
    } finally {
      setBusy(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(verificationCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" data-testid="add-youtube-modal">
      <div className="bg-white w-full max-w-md rounded-2xl border-2 border-black overflow-hidden">
        {/* OAuth-style header matching existing JoinModal */}
        <div className="px-6 py-4 border-b-2 border-black flex items-center gap-3 bg-[#F8F8F8]">
          <svg width="20" height="20" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
          </svg>
          <span className="font-mono text-xs tracking-[0.15em] text-[#2D2D2D]">accounts.google.com</span>
        </div>

        {stage === "enter" ? (
          <div className="p-6">
            <h2 className="font-display text-2xl font-black">Verify YouTube Channel</h2>
            <p className="text-sm text-[#2D2D2D] mt-2">
              To verify ownership, you will add a unique code to your YouTube channel description temporarily.
            </p>
            <label className="block mt-5">
              <span className="font-mono text-[10px] tracking-[0.2em]">YOUTUBE CHANNEL / HANDLE</span>
              <input
                value={channelInput}
                onChange={e => setChannelInput(e.target.value)}
                placeholder="@scortamo  or  https://youtube.com/@scortamo"
                className="w-full mt-1 p-3 border-2 border-black rounded-lg font-mono text-sm"
                data-testid="add-yt-channel-input"
                autoFocus
                onKeyDown={e => e.key === "Enter" && handleStartVerification()}
              />
            </label>
            {error && (
              <div className="mt-2 p-2.5 rounded-md bg-red-50 border border-red-300 flex items-center gap-2">
                <AlertCircle size={14} className="text-red-500 flex-shrink-0" />
                <p className="font-mono text-[10px] tracking-[0.1em] text-red-700">{error}</p>
              </div>
            )}
            <div className="mt-6 flex gap-3">
              <button onClick={onClose} className="oc-btn oc-btn-ghost flex-1" data-testid="add-yt-cancel">Cancel</button>
              <button
                onClick={handleStartVerification}
                disabled={busy || !channelInput.trim()}
                className="oc-btn oc-btn-primary flex-1"
                data-testid="start-verification-btn"
              >
                {busy ? "Resolving…" : "Start Verification"}
              </button>
            </div>
          </div>
        ) : (
          <div className="p-6">
            <h2 className="font-display text-2xl font-black">Verify Ownership</h2>
            
            {channelData && (
              <div className="mt-4 flex items-center gap-3 p-3 border-2 border-black rounded-lg bg-[#FAFAFA]">
                {channelData.thumbnail ? (
                  <img src={channelData.thumbnail} alt="" className="w-12 h-12 rounded-full border-2 border-black" />
                ) : (
                  <div className="w-12 h-12 rounded-full border-2 border-black bg-[#FF0000] flex items-center justify-center">
                    <Youtube size={20} color="#fff" />
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <p className="font-bold truncate text-base">{channelData.title || channelData.handle || "YouTube Channel"}</p>
                  <p className="font-mono text-xs text-[#2D2D2D] mt-0.5">
                    {channelData.handle ? `@${channelData.handle}` : channelData.channel_id}
                  </p>
                </div>
              </div>
            )}

            <div className="mt-5">
              <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">YOUR VERIFICATION CODE</span>
              <div className="flex gap-2 mt-1">
                <div className="flex-1 p-3 bg-gray-100 border-2 border-black rounded-lg font-mono text-lg font-bold text-center tracking-wider bg-[#F8F8F8]">
                  {verificationCode}
                </div>
                <button
                  onClick={handleCopy}
                  className="px-4 py-2 border-2 border-black rounded-lg font-mono text-xs font-bold bg-[#E8C500] hover:bg-[#FFF8E5] transition-colors"
                >
                  {copied ? "COPIED!" : "COPY"}
                </button>
              </div>
            </div>

            <p className="text-xs text-[#2D2D2D] mt-4 leading-relaxed bg-[#FFF8E5] border border-[#E8C500] p-3 rounded-lg">
              Paste this verification code anywhere in your YouTube channel description and save the channel.
            </p>

            {error && (
              <div className="mt-3 p-2.5 rounded-md bg-red-50 border border-red-300 flex items-center gap-2">
                <AlertCircle size={14} className="text-red-500 flex-shrink-0" />
                <p className="font-mono text-[10px] tracking-[0.1em] text-red-700">{error}</p>
              </div>
            )}

            <div className="mt-6 flex gap-3">
              <button 
                onClick={() => setStage("enter")} 
                disabled={busy}
                className="oc-btn oc-btn-ghost flex-1"
              >
                ← Back
              </button>
              <button
                onClick={handleConfirmVerification}
                disabled={busy}
                className="oc-btn oc-btn-primary flex-1"
                data-testid="confirm-verification-btn"
              >
                {busy ? "Checking…" : "I have updated my description"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/* ─── Coming Soon Platform Card ─── */
const ComingSoonCard = ({ name, icon: Icon, color }) => (
  <div className="oc-card opacity-60" data-testid={`platform-card-${name.toLowerCase()}`}>
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center border-2 border-black" style={{ background: color }}>
          <Icon size={20} color="#fff" strokeWidth={2.2} />
        </div>
        <div>
          <h3 className="font-display text-lg font-black">{name}</h3>
          <p className="text-xs text-[#2D2D2D]">Coming soon</p>
        </div>
      </div>
      <span className="oc-chip" style={{ background: "#2D2D2D", color: "#fff" }}>
        <Clock size={10} /> COMING SOON
      </span>
    </div>
    <div className="border-t-2 border-black pt-4">
      <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">NO ACCOUNTS CONNECTED</p>
      <button disabled className="oc-btn oc-btn-ghost mt-3 text-sm opacity-40 cursor-not-allowed">
        <Plus size={14} /> Connect {name}
      </button>
    </div>
  </div>
);

/* ─── TikTok Icon (lucide doesn't have it) ─── */
const TikTokIcon = ({ size = 20, color = "#fff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
    <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.27 6.27 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.2 8.2 0 004.79 1.53V6.77a4.85 4.85 0 01-1.02-.08z"/>
  </svg>
);

/* ─── X (Twitter) Icon ─── */
const XIcon = ({ size = 20, color = "#fff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.259 5.63 5.905-5.63zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
  </svg>
);

/* ─── Main Page ─── */
export default function SocialVerification() {
  const navigate = useNavigate();
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [removingId, setRemovingId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getVerifiedChannels();
      setChannels(res.youtube || []);
    } catch (e) {
      // Not critical
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleAdded = (ch) => {
    setChannels(prev => [...prev, ch]);
  };

  const handleRemove = async (channelId) => {
    setRemovingId(channelId);
    try {
      await removeVerifiedChannel(channelId);
      setChannels(prev => prev.filter(c => c.id !== channelId));
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to remove channel.");
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <div data-testid="social-verification-page">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-display text-4xl md:text-5xl font-black">Social Verification</h1>
        <p className="text-[#2D2D2D] mt-2">Verify social accounts before participating in campaigns.</p>
      </div>

      <div className="space-y-6">
        {/* ─── YouTube Card ─── */}
        <div className="oc-card" data-testid="platform-card-youtube">
          <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center border-2 border-black bg-[#FF0000]">
                <Youtube size={20} color="#fff" strokeWidth={2.2} />
              </div>
              <div>
                <h3 className="font-display text-lg font-black">YouTube</h3>
                <p className="text-xs text-[#2D2D2D]">Verify ownership of your YouTube channel.</p>
              </div>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="oc-btn oc-btn-primary text-sm"
              data-testid="add-youtube-btn"
            >
              <Plus size={15} /> Add YouTube Account
            </button>
          </div>

          <div className="border-t-2 border-black pt-4">
            {loading ? (
              <p className="font-mono text-xs tracking-[0.2em] oc-pulse py-4">LOADING…</p>
            ) : channels.length === 0 ? (
              <div className="py-4 flex items-center gap-2 text-[#2D2D2D]" data-testid="no-yt-accounts">
                <AlertCircle size={16} />
                <span className="font-mono text-xs tracking-[0.15em]">NO VERIFIED YOUTUBE ACCOUNTS</span>
              </div>
            ) : (
              <ul className="space-y-3" data-testid="yt-channels-list">
                {channels.map((ch) => (
                  <li
                    key={ch.id}
                    className="flex items-center gap-4 p-3 rounded-xl border-2 border-black"
                    data-testid={`yt-channel-${ch.id}`}
                  >
                    {ch.thumbnail ? (
                      <img src={ch.thumbnail} alt="" className="w-10 h-10 rounded-full border-2 border-black" />
                    ) : (
                      <div className="w-10 h-10 rounded-full border-2 border-black bg-[#FF0000] flex items-center justify-center">
                        <Youtube size={16} color="#fff" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-bold truncate">{ch.title || ch.handle || "YouTube Channel"}</p>
                        <span className="oc-chip" style={{ background: "#2CFF05", color: "#000", fontSize: "0.6rem" }}>
                          <CheckCircle size={10} /> VERIFIED
                        </span>
                      </div>
                      <p className="font-mono text-[10px] text-[#2D2D2D] mt-0.5">
                        {ch.handle ? `@${ch.handle}` : ch.channel_id || ""}
                        {ch.subscribers !== undefined && ch.subscribers !== null && (
                          <span className="ml-2">· {ch.subscribers.toLocaleString()} subscribers</span>
                        )}
                        {ch.verified_at && <span className="ml-2">· Verified {fmt_date(ch.verified_at)}</span>}
                      </p>
                    </div>
                    {ch.url && (
                      <a
                        href={ch.url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-mono text-[10px] text-[#BF00FF] hover:underline hidden sm:block"
                      >
                        Visit ↗
                      </a>
                    )}
                    <button
                      onClick={() => handleRemove(ch.id)}
                      disabled={removingId === ch.id}
                      className="p-2 rounded-lg border-2 border-black hover:bg-red-50 hover:border-red-400 transition-colors"
                      title="Remove channel"
                      data-testid={`remove-yt-${ch.id}`}
                    >
                      {removingId === ch.id
                        ? <span className="font-mono text-[10px]">…</span>
                        : <Trash2 size={14} />
                      }
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* ─── Placeholder cards ─── */}
        <div className="grid md:grid-cols-3 gap-4">
          <ComingSoonCard
            name="Instagram"
            icon={Instagram}
            color="#E1306C"
          />
          <div className="oc-card opacity-60" data-testid="platform-card-tiktok">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center border-2 border-black bg-black">
                  <TikTokIcon size={20} color="#fff" />
                </div>
                <div>
                  <h3 className="font-display text-lg font-black">TikTok</h3>
                  <p className="text-xs text-[#2D2D2D]">Coming soon</p>
                </div>
              </div>
              <span className="oc-chip" style={{ background: "#2D2D2D", color: "#fff" }}>
                <Clock size={10} /> COMING SOON
              </span>
            </div>
            <div className="border-t-2 border-black pt-4">
              <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">NO ACCOUNTS CONNECTED</p>
              <button disabled className="oc-btn oc-btn-ghost mt-3 text-sm opacity-40 cursor-not-allowed">
                <Plus size={14} /> Connect TikTok
              </button>
            </div>
          </div>
          <div className="oc-card opacity-60" data-testid="platform-card-x">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center border-2 border-black bg-black">
                  <XIcon size={18} color="#fff" />
                </div>
                <div>
                  <h3 className="font-display text-lg font-black">X (Twitter)</h3>
                  <p className="text-xs text-[#2D2D2D]">Coming soon</p>
                </div>
              </div>
              <span className="oc-chip" style={{ background: "#2D2D2D", color: "#fff" }}>
                <Clock size={10} /> COMING SOON
              </span>
            </div>
            <div className="border-t-2 border-black pt-4">
              <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">NO ACCOUNTS CONNECTED</p>
              <button disabled className="oc-btn oc-btn-ghost mt-3 text-sm opacity-40 cursor-not-allowed">
                <Plus size={14} /> Connect X
              </button>
            </div>
          </div>
        </div>
      </div>

      {showAddModal && (
        <AddYouTubeModal
          onClose={() => setShowAddModal(false)}
          onAdded={handleAdded}
        />
      )}
    </div>
  );
}
