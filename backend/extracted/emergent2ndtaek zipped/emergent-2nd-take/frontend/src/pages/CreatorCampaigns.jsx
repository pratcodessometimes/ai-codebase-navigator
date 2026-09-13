import React, { useEffect, useState } from "react";
import { listCampaigns, cloneCampaign } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Plus, Copy, Eye, Megaphone, IndianRupee, Users, Activity } from "lucide-react";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));
const fmtViews = (n) => {
  n = Number(n || 0);
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return String(n);
};

const daysLeft = (iso) => {
  const d = new Date(iso) - new Date();
  return Math.max(0, Math.ceil(d / (1000 * 60 * 60 * 24)));
};

export default function CreatorCampaigns() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const load = () => listCampaigns({ mine: true }).then(setItems);
  useEffect(() => { load(); }, []);

  const active = items.filter(c => ["OPEN", "CLOSING_SOON", "UNDER_REVIEW"].includes(c.status));
  const totalBudget = items.filter(c => c.escrow_funded).reduce((s, c) => s + (c.bounty_pool || 0), 0);
  const totalEditors = items.reduce((s, c) => s + (c.participant_count || 0), 0);
  const totalViews = items.reduce((s, c) => s + (c.total_views || 0), 0);

  const handleClone = async (id) => {
    const c = await cloneCampaign(id);
    navigate(`/app/campaigns/${c.campaign_id}`);
  };

  return (
    <div data-testid="creator-campaigns-page">
      <header className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <div>
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">CAMPAIGNS · CREATOR</p>
          <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Your workspace.</h1>
        </div>
        <button onClick={() => navigate("/app/campaigns/new")} className="oc-btn oc-btn-primary" data-testid="create-campaign-btn">
          <Plus size={16}/> Create Campaign
        </button>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8" data-testid="campaign-stats">
        <Metric icon={Megaphone}   label="Active Campaigns" value={active.length} />
        <Metric icon={IndianRupee} label="Budget Deployed"  value={`₹${fmt(totalBudget)}`} />
        <Metric icon={Eye}         label="Views Generated"  value={fmtViews(totalViews)} />
        <Metric icon={Users}       label="Editors Active"   value={fmt(totalEditors)} />
      </div>

      {items.length === 0 ? (
        <div className="oc-card text-center py-20">
          <Megaphone size={40} className="mx-auto text-[#2D2D2D]" />
          <p className="font-mono text-xs tracking-[0.25em] text-[#2D2D2D] mt-4">NO CAMPAIGNS YET</p>
          <p className="text-sm text-[#2D2D2D] mt-2">Post your first bounty to start sourcing clips.</p>
          <button onClick={() => navigate("/app/campaigns/new")} className="oc-btn oc-btn-primary mt-5">
            <Plus size={16}/> Create your first campaign
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-5">
          {items.map(c => <CreatorCampaignCard key={c.campaign_id} c={c} onClone={handleClone} navigate={navigate} />)}
        </div>
      )}
    </div>
  );
}

const Metric = ({ icon: Icon, label, value }) => (
  <div className="oc-card">
    <Icon size={18} className="text-[#2D2D2D]" />
    <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D] mt-3">{label.toUpperCase()}</p>
    <p className="font-display text-2xl font-black mt-1">{value}</p>
  </div>
);

const CreatorCampaignCard = ({ c, onClone, navigate }) => {
  const status = c.status;
  const sBg = status === "OPEN" ? "#2CFF05" : status === "CLOSING_SOON" ? "#BF00FF" :
              status === "COMPLETED" ? "#000" : "#2D2D2D";
  const sFg = status === "OPEN" ? "#000" : "#fff";
  const days = daysLeft(c.end_date);
  // progress: total_points / theoretical_target (use participant_count*1000 as soft target)
  const target = Math.max(1, (c.participant_count || 1) * 5000);
  const progress = Math.min(100, ((c.total_points || 0) / target) * 100);

  return (
    <div className="oc-card" data-testid={`creator-camp-${c.campaign_id}`}>
      <div className="flex items-start justify-between mb-3">
        <span className="oc-chip" style={{ background: sBg, color: sFg }}>{status.replace("_", " ")}</span>
        <span className="oc-chip" style={{ background: "#fff", color: "#000", border: "1.5px solid #000" }}>{c.content_type}</span>
      </div>
      <h3 className="font-display text-xl font-black leading-tight">{c.title}</h3>

      <div className="mt-5 grid grid-cols-3 gap-3 text-xs">
        <Stat label="BUDGET" value={`₹${fmt(c.bounty_pool)}`} />
        <Stat label="POINTS" value={fmt(c.total_points || 0)} />
        <Stat label="EDITORS" value={c.participant_count || 0} />
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between mb-1.5">
          <span className="font-mono text-[9px] tracking-[0.2em] text-[#2D2D2D]">CAMPAIGN PROGRESS</span>
          <span className="font-mono text-[10px] font-bold">{progress.toFixed(0)}%</span>
        </div>
        <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden border border-black">
          <div className="h-full transition-all" style={{ width: `${progress}%`, background: "linear-gradient(90deg, #2CFF05, #BF00FF)" }} />
        </div>
      </div>

      <div className="mt-5 flex items-center justify-between border-t-2 border-black pt-4">
        <div className="font-mono text-[10px] text-[#2D2D2D]">
          {status === "COMPLETED" ? "ENDED" : `${days}d remaining`}
        </div>
        <div className="flex gap-2">
          <button onClick={() => onClone(c.campaign_id)} className="oc-btn oc-btn-ghost px-3 py-1.5 text-xs"
                  data-testid={`clone-${c.campaign_id}`}>
            <Copy size={12}/> Clone
          </button>
          <button onClick={() => navigate(`/app/campaigns/${c.campaign_id}`)}
                  className="oc-btn oc-btn-primary px-3 py-1.5 text-xs"
                  data-testid={`view-${c.campaign_id}`}>
            View
          </button>
        </div>
      </div>
    </div>
  );
};

const Stat = ({ label, value }) => (
  <div className="text-center p-2 border border-black rounded-md">
    <p className="font-mono text-[9px] text-[#2D2D2D]">{label}</p>
    <p className="font-display font-black mt-0.5">{value}</p>
  </div>
);
