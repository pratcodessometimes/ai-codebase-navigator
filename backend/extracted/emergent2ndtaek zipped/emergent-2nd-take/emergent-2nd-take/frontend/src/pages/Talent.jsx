import React, { useEffect, useState } from "react";
import { listTalent } from "@/lib/api";
import { Search, Award, TrendingUp, Eye, Wallet, ChevronRight } from "lucide-react";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));
const fmtViews = (n) => {
  n = Number(n || 0);
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return String(n);
};

const TIERS = ["ALL", "DIAMOND", "PLATINUM", "GOLD", "SILVER", "BRONZE", "ROOKIE"];
const TIER_BG = {
  DIAMOND:  "#BF00FF", PLATINUM: "#2CFF05", GOLD: "#E8C500",
  SILVER: "#C0C0C0", BRONZE: "#CD7F32", ROOKIE: "#2D2D2D",
};

export default function Talent() {
  const [tier, setTier] = useState("ALL");
  const [niche, setNiche] = useState("");
  const [minViews, setMinViews] = useState(0);
  const [minRet, setMinRet] = useState(0);
  const [sort, setSort] = useState("elo_desc");
  const [items, setItems] = useState([]);

  const load = () => {
    const params = { sort_by: sort };
    if (tier !== "ALL") params.tier = tier;
    if (niche) params.niche = niche;
    if (minViews > 0) params.min_lifetime_views = minViews;
    if (minRet > 0) params.min_retention = minRet;
    listTalent(params).then(setItems);
  };

  useEffect(() => { load(); }, [tier, niche, minViews, minRet, sort]);

  return (
    <div data-testid="talent-page">
      <header className="mb-8">
        <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">TALENT</p>
        <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Discover editors.</h1>
        <p className="text-sm text-[#2D2D2D] mt-3 max-w-xl">
          Browse top editors by Elo, tier, retention, and earnings. Click any card to view their full portfolio.
        </p>
      </header>

      {/* FILTERS */}
      <div className="oc-card mb-6" data-testid="filters">
        <div className="grid md:grid-cols-5 gap-3">
          <label className="block md:col-span-2">
            <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">SEARCH NICHE / BIO</span>
            <div className="relative mt-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#2D2D2D]" />
              <input value={niche} onChange={e => setNiche(e.target.value)}
                     placeholder="gaming, podcast, sports…"
                     className="w-full pl-9 p-2.5 border-2 border-black rounded-lg text-sm"
                     data-testid="filter-niche" />
            </div>
          </label>
          <label className="block">
            <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">MIN LIFETIME VIEWS</span>
            <input type="number" value={minViews} onChange={e => setMinViews(Number(e.target.value))}
                   className="w-full mt-1 p-2.5 border-2 border-black rounded-lg text-sm" data-testid="filter-views" />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">MIN RETENTION %</span>
            <input type="number" value={minRet} onChange={e => setMinRet(Number(e.target.value))}
                   className="w-full mt-1 p-2.5 border-2 border-black rounded-lg text-sm" data-testid="filter-retention" />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">SORT BY</span>
            <select value={sort} onChange={e => setSort(e.target.value)}
                    className="w-full mt-1 p-2.5 border-2 border-black rounded-lg text-sm" data-testid="filter-sort">
              <option value="elo_desc">Elo (high → low)</option>
              <option value="views_desc">Lifetime views</option>
              <option value="retention_desc">Retention rate</option>
            </select>
          </label>
        </div>
        <div className="flex flex-wrap gap-2 mt-4">
          {TIERS.map(t => (
            <button key={t} onClick={() => setTier(t)}
                    className={`oc-tab ${tier === t ? "active" : ""}`}
                    style={tier === t && t !== "ALL" ? { background: TIER_BG[t], color: t === "PLATINUM" ? "#000" : "#fff", borderColor: "#000" } : undefined}
                    data-testid={`tier-${t}`}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* GRID */}
      {items.length === 0 ? (
        <div className="oc-card text-center py-16"><p className="font-mono text-xs tracking-[0.25em] text-[#2D2D2D]">NO EDITORS MATCH</p></div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="talent-grid">
          {items.map(ed => <EditorCard key={ed.user_id} ed={ed} />)}
        </div>
      )}
    </div>
  );
}

const EditorCard = ({ ed }) => (
  <div className="oc-card flex flex-col" data-testid={`talent-${ed.user_id}`}>
    <div className="flex items-start gap-4">
      <img src={ed.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${ed.name}`}
           className="w-16 h-16 rounded-xl border-2 border-black flex-shrink-0" alt="" />
      <div className="flex-1 min-w-0">
        <p className="font-display text-lg font-black truncate">{ed.name}</p>
        <p className="font-mono text-[10px] text-[#BF00FF] truncate">@{ed.username}</p>
        <div className="flex items-center gap-2 mt-2">
          <span className="oc-chip" style={{ background: TIER_BG[ed.tier], color: ed.tier === "PLATINUM" ? "#000" : "#fff" }}>
            {ed.tier}
          </span>
          <span className="oc-chip" style={{ background: "#000", color: "#2CFF05" }}>
            <Award size={10}/> ELO {ed.elo}
          </span>
        </div>
      </div>
    </div>

    {ed.bio && <p className="text-xs text-[#2D2D2D] mt-3 line-clamp-2">{ed.bio}</p>}

    <div className="mt-4 grid grid-cols-2 gap-2">
      <Stat icon={Eye}        label="LIFETIME VIEWS"  value={fmtViews(ed.lifetime_views)} />
      <Stat icon={Wallet}     label="LIFETIME EARN"   value={`₹${fmt(ed.lifetime_earnings)}`} />
      <Stat icon={TrendingUp} label="AVG RETENTION"   value={`${ed.avg_retention}%`} />
      <Stat icon={Award}      label="CAMPAIGNS"       value={ed.campaigns_completed} />
    </div>

    <div className="mt-4 flex gap-2 pt-4 border-t-2 border-black">
      <a href={`/u/${ed.username}`} target="_blank" rel="noreferrer"
         className="oc-btn oc-btn-ghost flex-1 text-xs py-2" data-testid={`view-profile-${ed.user_id}`}>
        View Profile
      </a>
      <a href={`mailto:hello@outclip.io?subject=Hire ${ed.name}&body=I'd like to hire @${ed.username} for a campaign.`}
         className="oc-btn oc-btn-primary flex-1 text-xs py-2" data-testid={`hire-${ed.user_id}`}>
        Hire <ChevronRight size={12}/>
      </a>
    </div>
  </div>
);

const Stat = ({ icon: Icon, label, value }) => (
  <div className="p-2 border border-black rounded-md">
    <div className="flex items-center gap-1.5"><Icon size={10} className="text-[#2D2D2D]" />
      <p className="font-mono text-[9px] text-[#2D2D2D] tracking-[0.1em]">{label}</p>
    </div>
    <p className="font-display font-black text-sm mt-1">{value}</p>
  </div>
);
