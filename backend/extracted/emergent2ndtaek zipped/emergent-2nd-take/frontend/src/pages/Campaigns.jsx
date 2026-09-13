import React, { useEffect, useState } from "react";
import { listCampaigns } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Clock, Users, Plus } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));
const CREATOR_STATUSES = ["ALL", "OPEN", "CLOSING_SOON", "UNDER_REVIEW", "COMPLETED"];

const daysLeft = (iso) => {
  const d = new Date(iso) - new Date();
  return Math.max(0, Math.ceil(d / (1000 * 60 * 60 * 24)));
};

export default function Campaigns() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isEditor = user?.role === "EDITOR";

  // Editor filters
  const [editorTab, setEditorTab] = useState("ALL"); // ALL | ENROLLED
  // Creator filters
  const [status, setStatus] = useState("ALL");
  const [sort, setSort] = useState("bounty_desc");
  const [mine, setMine] = useState(false);

  const [items, setItems] = useState([]);

  const load = () => {
    const params = {};
    if (isEditor) {
      if (editorTab === "ENROLLED") params.enrolled = true;
    } else {
      params.sort_by = sort;
      if (status !== "ALL") params.status = status;
      if (mine) params.mine = true;
    }
    listCampaigns(params).then(setItems);
  };

  useEffect(() => { load(); }, [editorTab, status, sort, mine, isEditor]);

  return (
    <div data-testid="campaigns-page">
      <header className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <div>
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">CAMPAIGNS</p>
          <h1 className="font-display text-4xl md:text-5xl font-black mt-1">
            {isEditor
              ? (editorTab === "ENROLLED" ? "Your enrolled campaigns." : "Bounties open right now.")
              : (mine ? "My campaigns." : "Bounties open right now.")}
          </h1>
        </div>
        {user?.role === "CREATOR" ? (
          <button className="oc-btn oc-btn-primary" onClick={() => navigate("/app/campaigns/new")} data-testid="new-campaign-btn">
            <Plus size={16}/> New campaign
          </button>
        ) : (
          <button className="oc-btn oc-btn-primary" onClick={() => navigate("/creator-apply")} data-testid="create-campaign-btn">
            <Plus size={16}/> Create Campaign
          </button>
        )}
      </header>

      <div className="flex flex-wrap items-center gap-3 mb-8">
        {isEditor ? (
          <>
            <button onClick={() => setEditorTab("ALL")}
              className={`oc-tab ${editorTab === "ALL" ? "green active" : ""}`} data-testid="editor-tab-all">
              All
            </button>
            <button onClick={() => setEditorTab("ENROLLED")}
              className={`oc-tab ${editorTab === "ENROLLED" ? "purple active" : ""}`} data-testid="editor-tab-enrolled">
              Enrolled
            </button>
          </>
        ) : (
          <>
            {CREATOR_STATUSES.map(s => (
              <button key={s} onClick={() => setStatus(s)}
                className={`oc-tab ${status === s ? (s === "OPEN" ? "green active" : "active") : ""}`}
                data-testid={`status-${s}`}>
                {s.replace("_", " ")}
              </button>
            ))}
            <select value={sort} onChange={e => setSort(e.target.value)} data-testid="sort-by"
              className="oc-tab cursor-pointer">
              <option value="bounty_desc">Highest bounty</option>
              <option value="ending_soon">Ending soon</option>
              <option value="newest">Newest</option>
            </select>
            {user && (
              <button onClick={() => setMine(!mine)}
                className={`oc-tab ${mine ? "purple active" : ""}`} data-testid="mine-toggle">
                {mine ? "Showing mine" : "Show mine"}
              </button>
            )}
          </>
        )}
      </div>

      {items.length === 0 ? (
        <div className="oc-card text-center py-16" data-testid="empty-state">
          <p className="font-mono text-xs tracking-[0.2em]">
            {isEditor && editorTab === "ENROLLED" ? "YOU HAVEN'T ENROLLED IN ANY CAMPAIGNS" : "NO CAMPAIGNS FOUND"}
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map(c => <CampaignCard key={c.campaign_id} c={c} />)}
        </div>
      )}
    </div>
  );
}

const statusColor = (s) => ({
  OPEN: { bg: "#2CFF05", fg: "#000" }, CLOSING_SOON: { bg: "#BF00FF", fg: "#fff" },
  DRAFT: { bg: "#2D2D2D", fg: "#fff" }, UNDER_REVIEW: { bg: "#2D2D2D", fg: "#fff" },
  COMPLETED: { bg: "#000", fg: "#2CFF05" }, CANCELLED: { bg: "#000", fg: "#fff" },
})[s] || { bg: "#000", fg: "#fff" };

const CampaignCard = ({ c }) => {
  const days = daysLeft(c.end_date);
  const sc = statusColor(c.status);
  return (
    <a href={`/app/campaigns/${c.campaign_id}`} className="oc-card hover:translate-y-[-3px] transition-transform block" data-testid={`camp-card-${c.campaign_id}`}>
      <div className="flex items-start justify-between mb-3">
        <span className="oc-chip" style={{ background: sc.bg, color: sc.fg }}>{c.status.replace("_", " ")}</span>
        <span className="oc-chip" style={{ background: "#fff", color: "#000", border: "1.5px solid #000" }}>{c.content_type}</span>
      </div>
      <h3 className="font-display text-2xl font-black leading-tight">{c.title}</h3>
      {c.creator && (
        <div className="flex items-center gap-2 mt-3">
          <img src={c.creator.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${c.creator.name}`}
               className="w-6 h-6 rounded-full border border-black" alt="" />
          <p className="text-sm text-[#2D2D2D]">{c.creator.name}</p>
        </div>
      )}
      <div className="mt-5 flex items-end justify-between">
        <div>
          <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">BOUNTY POOL</p>
          <p className="font-display text-3xl font-black">₹{fmt(c.bounty_pool)}</p>
        </div>
        <div className="text-right">
          <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D] flex items-center gap-1 justify-end"><Clock size={11}/> ENDS IN</p>
          <p className="font-display font-black text-xl" style={{ color: days < 2 ? "#BF00FF" : "#000" }}>{days}d</p>
        </div>
      </div>
      <div className="mt-4 pt-4 border-t-2 border-black flex items-center justify-between text-xs font-mono">
        <span className="flex items-center gap-1"><Users size={12}/> {c.participant_count} editors</span>
        <span className="text-[#BF00FF]">VIEW →</span>
      </div>
    </a>
  );
};
