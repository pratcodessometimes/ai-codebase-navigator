import React, { useEffect, useState } from "react";
import { creatorDashboard } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell,
         AreaChart, Area, PieChart, Pie, Legend } from "recharts";
import { Eye, Film, Users, Activity, IndianRupee, Crown, Play, ArrowUpRight } from "lucide-react";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));
const fmtViews = (n) => {
  n = Number(n || 0);
  if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "K";
  return String(n);
};

const TIER_COLORS = {
  DIAMOND:  "#BF00FF",  PLATINUM: "#2CFF05",  GOLD:    "#E8C500",
  SILVER:   "#C0C0C0",  BRONZE:   "#CD7F32",  ROOKIE:  "#2D2D2D",
};

export default function CreatorDashboard() {
  const [d, setD] = useState(null);
  useEffect(() => { creatorDashboard().then(setD); }, []);
  if (!d) return <p className="font-mono text-sm oc-pulse">LOADING…</p>;

  const { stats, top_clips, top_editors, timeline, content_type_distribution } = d;

  return (
    <div data-testid="creator-dashboard-page">
      <header className="mb-8">
        <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">CREATOR DASHBOARD</p>
        <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Campaign performance.</h1>
      </header>

      {/* TOP METRICS — clean enterprise cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-10" data-testid="top-metrics">
        <Metric icon={Eye}        label="Total Views"     value={fmtViews(stats.total_views)} accent="#2CFF05" />
        <Metric icon={Film}       label="Clips Submitted" value={fmt(stats.total_clips)}      accent="#BF00FF" />
        <Metric icon={Users}      label="Total Editors"   value={fmt(stats.total_editors)}    accent="#000000" />
        <Metric icon={Activity}   label="Avg Retention"   value={`${stats.avg_retention}%`}   accent="#2CFF05" />
        <Metric icon={IndianRupee}label="Campaign Spend"  value={`₹${fmt(stats.total_spend)}`} accent="#BF00FF" />
      </div>

      {/* TIMELINE + DISTRIBUTION */}
      <div className="grid lg:grid-cols-3 gap-6 mb-10">
        <div className="oc-card lg:col-span-2" data-testid="timeline-chart">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-display text-2xl font-black">Performance timeline</h3>
              <p className="text-xs text-[#2D2D2D] mt-1">Views & clips across the last 6 months</p>
            </div>
            <span className="oc-chip" style={{ background: "#000", color: "#2CFF05" }}>LIVE</span>
          </div>
          {(!timeline || timeline.length === 0) ? (
            <p className="text-sm text-[#2D2D2D] py-16 text-center font-mono">NO DATA YET — PUBLISH A CAMPAIGN</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={timeline} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="vG" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2CFF05" stopOpacity={0.55} />
                    <stop offset="100%" stopColor="#2CFF05" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="pG" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#BF00FF" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#BF00FF" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="month" stroke="#000" fontFamily="JetBrains Mono" fontSize={11} tickLine={false} />
                <YAxis stroke="#000" fontFamily="JetBrains Mono" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: "#000", border: "2px solid #2CFF05", color: "#fff", borderRadius: 8, fontFamily: "JetBrains Mono", fontSize: 12 }} />
                <Area type="monotone" dataKey="views" stroke="#2CFF05" strokeWidth={2.5} fill="url(#vG)" />
                <Area type="monotone" name="OCV" dataKey="ocv" stroke="#BF00FF" strokeWidth={2.5} fill="url(#pG)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="oc-card" data-testid="distribution-chart">
          <h3 className="font-display text-2xl font-black">Content mix</h3>
          <p className="text-xs text-[#2D2D2D] mt-1 mb-4">Your campaigns by category</p>
          {(!content_type_distribution || content_type_distribution.length === 0) ? (
            <p className="text-sm text-[#2D2D2D] py-12 text-center font-mono">NO CAMPAIGNS YET</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={content_type_distribution} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} stroke="#fff" strokeWidth={2}>
                  {content_type_distribution.map((_, i) => (
                    <Cell key={i} fill={["#2CFF05", "#BF00FF", "#000000", "#2D2D2D", "#7DFF63", "#D77FFF"][i % 6]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#000", border: "2px solid #2CFF05", color: "#fff", borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontFamily: "JetBrains Mono", fontSize: 10, paddingTop: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* CLIPS PER MONTH BAR + RETENTION TREND */}
      {timeline && timeline.length > 0 && (
        <div className="oc-card mb-10" data-testid="clips-bar">
          <h3 className="font-display text-2xl font-black">Monthly throughput</h3>
          <p className="text-xs text-[#2D2D2D] mt-1 mb-4">Clips submitted per month</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={timeline} margin={{ top: 6, right: 16, left: -10, bottom: 0 }}>
              <XAxis dataKey="month" stroke="#000" fontFamily="JetBrains Mono" fontSize={11} tickLine={false} />
              <YAxis stroke="#000" fontFamily="JetBrains Mono" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#000", border: "2px solid #2CFF05", color: "#fff", borderRadius: 8 }} />
              <Bar dataKey="clips" radius={[6, 6, 0, 0]}>
                {timeline.map((_, i) => <Cell key={i} fill={i % 2 === 0 ? "#000000" : "#2CFF05"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* TOP CLIPS */}
      <section className="mb-10" data-testid="top-clips-section">
        <h2 className="font-display text-3xl font-black mb-4">Top performing clips</h2>
        {top_clips.length === 0 ? (
          <div className="oc-card text-center py-12"><p className="font-mono text-xs tracking-[0.2em] text-[#2D2D2D]">NO CLIPS YET</p></div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {top_clips.map(cl => (
              <a key={cl.clip_id} href={cl.clip_url} target="_blank" rel="noreferrer"
                 className="oc-card hover:translate-y-[-2px] transition-transform" data-testid={`top-clip-${cl.clip_id}`}>
                <div className="aspect-video rounded-lg bg-black border-2 border-black mb-3 flex items-center justify-center overflow-hidden relative">
                  {cl.thumbnail ?
                    <img src={cl.thumbnail} className="w-full h-full object-cover" alt="" /> :
                    <Play size={32} className="text-[#2CFF05]" />}
                  <span className="absolute top-2 right-2 oc-chip" style={{ background: "rgba(0,0,0,0.85)", color: "#2CFF05" }}>
                    {cl.platform?.replace("_", " ")}
                  </span>
                </div>
                {cl.editor && (
                  <div className="flex items-center gap-2 mb-2">
                    <img src={cl.editor.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${cl.editor.name}`}
                         className="w-6 h-6 rounded-full border border-black" alt="" />
                    <p className="text-xs text-[#2D2D2D] truncate">{cl.editor.name}</p>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2 mt-3 text-center pt-3 border-t-2 border-black">
                  <div><p className="font-mono text-[9px] text-[#2D2D2D]">VIEWS</p><p className="font-display font-black">{fmtViews(cl.views)}</p></div>
                  <div><p className="font-mono text-[9px] text-[#2D2D2D]">RET</p><p className="font-display font-black">{cl.retention_pct}%</p></div>
                  <div><p className="font-mono text-[9px] text-[#2D2D2D]">ENG</p><p className="font-display font-black">{cl.engagement_pct}%</p></div>
                </div>
              </a>
            ))}
          </div>
        )}
      </section>

      {/* TOP EDITORS */}
      <section data-testid="top-editors-section">
        <h2 className="font-display text-3xl font-black mb-4">Top performing editors</h2>
        {top_editors.length === 0 ? (
          <div className="oc-card text-center py-12"><p className="font-mono text-xs tracking-[0.2em] text-[#2D2D2D]">NO DATA YET</p></div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {top_editors.map((t, i) => (
              <a key={t.editor.user_id} href={`/u/${t.editor.username}`} target="_blank" rel="noreferrer"
                 className="oc-card flex items-center gap-4 hover:translate-y-[-2px] transition-transform" data-testid={`top-editor-${t.editor.user_id}`}>
                <div className="relative">
                  <img src={t.editor.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${t.editor.name}`}
                       className="w-14 h-14 rounded-xl border-2 border-black" alt="" />
                  {i === 0 && <Crown size={16} className="absolute -top-2 -right-2 text-[#E8C500] fill-[#E8C500]" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-display font-black truncate">{t.editor.name}</p>
                    <span className="oc-chip" style={{ background: TIER_COLORS[t.tier], color: t.tier === "PLATINUM" ? "#000" : "#fff", fontSize: "0.6rem" }}>
                      {t.tier}
                    </span>
                  </div>
                  <p className="font-mono text-[10px] text-[#2D2D2D] mt-0.5">ELO {t.elo}</p>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                    <div><p className="font-mono text-[9px] text-[#2D2D2D]">VIEWS</p><p className="font-bold">{fmtViews(t.views_generated)}</p></div>
                    <div><p className="font-mono text-[9px] text-[#2D2D2D]">EARNED</p><p className="font-bold">₹{fmt(t.earnings_generated)}</p></div>
                  </div>
                </div>
                <ArrowUpRight size={16} className="text-[#2D2D2D]" />
              </a>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

const Metric = ({ icon: Icon, label, value, accent }) => (
  <div className="oc-card" data-testid={`metric-${label.toLowerCase().replace(/\s/g, "-")}`}>
    <div className="flex items-center justify-between mb-3">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center"
           style={{ background: accent, color: accent === "#2CFF05" ? "#000" : "#fff" }}>
        <Icon size={18} strokeWidth={2.5} />
      </div>
    </div>
    <p className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">{label.toUpperCase()}</p>
    <p className="font-display text-3xl font-black mt-1">{value}</p>
  </div>
);
