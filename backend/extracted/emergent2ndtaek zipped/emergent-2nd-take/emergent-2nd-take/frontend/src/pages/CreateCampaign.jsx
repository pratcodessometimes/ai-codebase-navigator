import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createCampaign, publishCampaign } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Check, Info, FileText, FolderOpen, IndianRupee, AlertTriangle } from "lucide-react";

const TYPES = ["GAMING", "PODCAST", "COMMENTARY", "IRL", "SPORTS", "EDUCATION", "OTHER"];
const STEPS = [
  { id: 1, label: "Campaign Info",  icon: Info },
  { id: 2, label: "Campaign Brief", icon: FileText },
  { id: 3, label: "Assets",         icon: FolderOpen },
  { id: 4, label: "Funding",        icon: IndianRupee },
];
const MIN_DAYS = 7;          // editor-protected window
const EARLY_PENALTY = 20;    // %

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));

export default function CreateCampaign() {
  const navigate = useNavigate();
  const { user, refresh } = useAuth();
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [utr, setUtr] = useState("");

  const [form, setForm] = useState({
    // step 1
    title: "", content_type: "GAMING", description: "",
    // step 2 - brief
    brief: {
      objective: "", target_audience: "", content_style: "",
      topics_focus: "", topics_avoid: "",
      hook_style: "", length_guidelines: "", caption_guidelines: "",
      video_type: "",
    },
    // step 3 - assets
    assets: {
      drive_links: "", raw_footage: "", logos: "", brand_assets: "", notes: "",
    },
    // step 4 - funding
    bounty_pool: 10000,
    max_clips_per_editor: 10,
    start_date: new Date().toISOString(),
    end_date: new Date(Date.now() + 14 * 86400e3).toISOString(),
    editor_pool_pct: 60,
    performance_pool_pct: 30,
    bonus_pool_pct: 10,
    min_duration_days: MIN_DAYS,
    early_close_penalty_pct: EARLY_PENALTY,
    clip_guidelines: "",
    source_video_urls: [],
  });

  const setF  = (k, v) => setForm(s => ({ ...s, [k]: v }));
  const setB  = (k, v) => setForm(s => ({ ...s, brief:  { ...s.brief,  [k]: v } }));
  const setA  = (k, v) => setForm(s => ({ ...s, assets: { ...s.assets, [k]: v } }));

  const submit = async (publish) => {
    setBusy(true);
    try {
      const drive_links = (form.assets.drive_links || "")
        .split(/[\n,]/).map(s => s.trim()).filter(Boolean);
      const payload = {
        ...form,
        clip_guidelines: form.brief.caption_guidelines || form.clip_guidelines,
        source_video_urls: drive_links,
      };
      const c = await createCampaign(payload);
      if (publish) {
        await publishCampaign(c.campaign_id);
        alert("Your campaign has been submitted for review and is awaiting activation.");
      }
      await refresh();
      navigate(`/app/campaigns/${c.campaign_id}`);
    } catch (e) {
      alert(e.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  const fee = (form.bounty_pool || 0) * 0.15;
  const net = (form.bounty_pool || 0) - fee;
  const canPublish = true;

  return (
    <div data-testid="create-campaign">
      <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">NEW CAMPAIGN</p>
      <h1 className="font-display text-4xl md:text-5xl font-black mt-1 mb-8">Post a bounty.</h1>

      {/* stepper */}
      <div className="flex items-center gap-2 mb-10 max-w-4xl overflow-x-auto">
        {STEPS.map((s, i) => (
          <React.Fragment key={s.id}>
            <button onClick={() => s.id < step && setStep(s.id)}
                    className={`flex items-center gap-2 px-4 py-2.5 rounded-full border-2 border-black flex-shrink-0
                                ${step === s.id ? "bg-[#2CFF05] text-black" : step > s.id ? "bg-black text-white" : "bg-white text-[#2D2D2D]"}`}
                    data-testid={`step-${s.id}`}>
              {step > s.id ? <Check size={14} /> : <s.icon size={14} />}
              <span className="font-mono text-[10px] tracking-[0.2em] font-bold">{s.label.toUpperCase()}</span>
            </button>
            {i < STEPS.length - 1 && <div className={`flex-1 h-0.5 min-w-[20px] ${step > s.id ? "bg-black" : "bg-[#E0E0E0]"}`} />}
          </React.Fragment>
        ))}
      </div>

      <div className="oc-card max-w-4xl">
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="font-display text-2xl font-black">Campaign information</h2>
            <Field label="CAMPAIGN NAME"><input value={form.title} onChange={e => setF("title", e.target.value)} className="oc-input" data-testid="f-title" /></Field>
            <Field label="CONTENT CATEGORY">
              <select value={form.content_type} onChange={e => setF("content_type", e.target.value)} className="oc-input" data-testid="f-type">
                {TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="CAMPAIGN DESCRIPTION">
              <textarea rows={5} value={form.description} onChange={e => setF("description", e.target.value)}
                        placeholder="What's this campaign about? Who's the creator? Why now?"
                        className="oc-input" data-testid="f-desc" />
            </Field>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h2 className="font-display text-2xl font-black">Campaign brief</h2>
            <p className="text-sm text-[#2D2D2D]">Your SOPs — visible publicly to every participating editor.</p>
            <Field label="OBJECTIVE">
              <input value={form.brief.objective} onChange={e => setB("objective", e.target.value)}
                     placeholder="What outcome do you want? e.g. drive 10M views to the main channel." className="oc-input" data-testid="b-obj" />
            </Field>
            <div className="grid md:grid-cols-2 gap-3">
              <Field label="TARGET AUDIENCE"><input value={form.brief.target_audience} onChange={e => setB("target_audience", e.target.value)} placeholder="18-28, gaming, NA/EU" className="oc-input" data-testid="b-aud" /></Field>
              <Field label="CONTENT STYLE"><input value={form.brief.content_style} onChange={e => setB("content_style", e.target.value)} placeholder="Fast-cut, meme-y, podcast hooks" className="oc-input" data-testid="b-style" /></Field>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              <Field label="TOPICS TO FOCUS ON"><textarea rows={3} value={form.brief.topics_focus} onChange={e => setB("topics_focus", e.target.value)} className="oc-input" data-testid="b-focus" /></Field>
              <Field label="TOPICS TO AVOID"><textarea rows={3} value={form.brief.topics_avoid} onChange={e => setB("topics_avoid", e.target.value)} className="oc-input" data-testid="b-avoid" /></Field>
            </div>
            <div className="grid md:grid-cols-3 gap-3">
              <Field label="HOOK STYLE"><input value={form.brief.hook_style} onChange={e => setB("hook_style", e.target.value)} placeholder="Pattern interrupt, payoff promise…" className="oc-input" data-testid="b-hook" /></Field>
              <Field label="CLIP LENGTH"><input value={form.brief.length_guidelines} onChange={e => setB("length_guidelines", e.target.value)} placeholder="30-60s ideal" className="oc-input" data-testid="b-len" /></Field>
              <Field label="CAPTION GUIDELINES"><input value={form.brief.caption_guidelines} onChange={e => setB("caption_guidelines", e.target.value)} placeholder="Bold, centered, 2-line max" className="oc-input" data-testid="b-cap" /></Field>
            </div>
            <Field label="WHAT TYPE OF VIDEOS DO YOU WANT DISTRIBUTED?">
              <textarea rows={4} value={form.brief.video_type} onChange={e => setB("video_type", e.target.value)}
                        placeholder="what type of videos do you want to be distributed…"
                        className="oc-input" data-testid="b-videotype" />
            </Field>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h2 className="font-display text-2xl font-black">Assets</h2>
            <p className="text-sm text-[#2D2D2D]">Make sure all Drive links are set to "Anyone with the link can view".</p>
            <Field label="GOOGLE DRIVE LINKS (one per line or comma-separated)">
              <textarea rows={3} value={form.assets.drive_links} onChange={e => setA("drive_links", e.target.value)}
                        placeholder="https://drive.google.com/file/d/…" className="oc-input" data-testid="a-drive" />
            </Field>
            <Field label="RAW FOOTAGE NOTES"><textarea rows={2} value={form.assets.raw_footage} onChange={e => setA("raw_footage", e.target.value)} className="oc-input" data-testid="a-raw" /></Field>
            <div className="grid md:grid-cols-2 gap-3">
              <Field label="LOGOS (links)"><input value={form.assets.logos} onChange={e => setA("logos", e.target.value)} className="oc-input" data-testid="a-logos" /></Field>
              <Field label="BRAND ASSETS (links)"><input value={form.assets.brand_assets} onChange={e => setA("brand_assets", e.target.value)} className="oc-input" data-testid="a-brand" /></Field>
            </div>
            <Field label="ADDITIONAL NOTES"><textarea rows={3} value={form.assets.notes} onChange={e => setA("notes", e.target.value)} className="oc-input" data-testid="a-notes" /></Field>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <h2 className="font-display text-2xl font-black">Funding</h2>

            <div className="grid md:grid-cols-2 gap-3">
              <Field label="CAMPAIGN BUDGET (₹)">
                <input type="number" value={form.bounty_pool} onChange={e => setF("bounty_pool", Number(e.target.value))} className="oc-input" data-testid="f-pool" />
              </Field>
              <Field label="DAILY SUBMISSION LIMIT">
                <input type="text" value="10 Clips / Day" disabled className="oc-input bg-[#F3F3F3] text-[#888888] cursor-not-allowed" data-testid="f-maxclips" />
              </Field>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              <Field label="START DATE"><input type="date" value={form.start_date.slice(0,10)} onChange={e => setF("start_date", new Date(e.target.value).toISOString())} className="oc-input" data-testid="f-start" /></Field>
              <Field label="END DATE"><input type="date" value={form.end_date.slice(0,10)} onChange={e => setF("end_date", new Date(e.target.value).toISOString())} className="oc-input" data-testid="f-end" /></Field>
            </div>

            {/* Lock window notice */}
            <div className="p-4 rounded-lg border-2 border-[#BF00FF] bg-[#FAF0FF]" data-testid="lock-notice">
              <div className="flex items-start gap-3">
                <AlertTriangle size={20} className="text-[#BF00FF] flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-display font-black text-sm">Campaign lock-in</p>
                  <p className="text-sm text-[#2D2D2D] mt-1">
                    You cannot close this campaign before <b>{form.min_duration_days} days</b> from publish. Closing earlier
                    triggers a <b>{form.early_close_penalty_pct}% platform penalty</b> on the remaining bounty pool. This protects
                    editors who've already committed their time.
                  </p>
                </div>
              </div>
            </div>

            {/* Fund split */}
            <div className="grid md:grid-cols-3 gap-3" data-testid="fund-split">
              <Pill label="CAMPAIGN BUDGET" value={`₹${fmt(form.bounty_pool)}`} bg="#000" fg="#fff" />
              <Pill label="PLATFORM FEE (15%)" value={`₹${fmt(fee)}`} bg="#2D2D2D" fg="#fff" />
              <Pill label="NET EDITOR POOL (85%)" value={`₹${fmt(net)}`} bg="#2CFF05" fg="#000" />
            </div>

            <div className="p-4 border-2 border-black rounded-lg bg-[#F8F8F8] space-y-4">
              <div>
                <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D] uppercase font-bold">Manual Campaign Approval</p>
                <p className="text-sm text-[#2D2D2D] mt-2">
                  Upon publishing, your campaign will be submitted to the Outclipped administrators for manual review and activation. 
                </p>
                <p className="text-sm text-[#2D2D2D] mt-1 font-bold">
                  No payment details, proof of transfer, or UTR transaction reference codes are required at this stage.
                </p>
              </div>
              {form.bounty_pool < 1000 && (
                <p className="font-mono text-[11px] text-red-600 font-bold mt-2">
                  Campaign budget must be at least ₹1,000.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="mt-6 flex gap-3 max-w-4xl">
        {step > 1 && <button onClick={() => setStep(step - 1)} className="oc-btn oc-btn-ghost" data-testid="prev-step">Back</button>}
        {step < 4 && <button onClick={() => setStep(step + 1)} className="oc-btn oc-btn-primary" data-testid="next-step">Continue →</button>}
        {step === 4 && (
          <>
            <button onClick={() => submit(false)} disabled={busy || !form.title || form.bounty_pool < 1000} className="oc-btn oc-btn-ghost" data-testid="save-draft">Save as draft</button>
            <button onClick={() => submit(true)} disabled={busy || !form.title || form.bounty_pool < 1000} className="oc-btn oc-btn-primary" data-testid="publish-now">
              {busy ? "Publishing…" : "Publish for Review"}
            </button>
          </>
        )}
      </div>

      <style><style>{`
.oc-input{
  width:100%;
  padding:.7rem 1rem;
  border:2px solid #000;
  border-radius:.5rem;
  font-family:'IBM Plex Sans';
  font-size:.9rem;
  background:#fff;
  color:#000 !important;
  -webkit-text-fill-color:#000 !important;
  caret-color:#000;
}

.oc-input:focus{
  outline:none;
  border-color:#BF00FF;
}
`}</style></style>
    </div>
  );
}

const Field = ({ label, children }) => (
  <label className="block">
    <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">{label}</span>
    <div className="mt-1.5">{children}</div>
  </label>
);

const Pill = ({ label, value, bg, fg, border }) => (
  <div className="p-3 rounded-lg" style={{ background: bg, color: fg, border: border ? "2px solid #000" : "none" }}>
    <p className="font-mono text-[9px] tracking-[0.15em] opacity-80">{label}</p>
    <p className="font-display text-lg font-black mt-1 leading-tight">{value}</p>
  </div>
);
