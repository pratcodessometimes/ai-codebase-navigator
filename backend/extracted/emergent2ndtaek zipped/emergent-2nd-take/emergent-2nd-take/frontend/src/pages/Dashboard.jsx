import React, { useEffect, useState } from "react";
import { getDashboard } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from "recharts";
import { ArrowUpRight, Plus, Wallet as WalletIcon, Receipt, CheckCircle2, X } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));
const fmtOcv = (n) => n !== undefined && n !== null ? Number(n).toFixed(2) : "0.00";
const fmtDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { day: "2-digit", month: "short" }) + " · " +
         d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
};

const Stat = ({ label, value, bg, color, tid }) => (
  <div className="oc-card oc-card-offset" style={{ background: bg, color, borderColor: "#000" }} data-testid={tid}>
    <p className="font-mono text-[10px] tracking-[0.25em] uppercase opacity-80">{label}</p>
    <p className="font-display text-4xl md:text-5xl font-black mt-2">{value}</p>
  </div>
);

export default function Dashboard() {
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  const load = () => getDashboard().then(setData);
  useEffect(() => { load(); }, []);

  if (!data) return <p className="font-mono text-sm oc-pulse">LOADING DASHBOARD…</p>;

  if (data.role === "EDITOR") return <EditorDash data={data} onReload={load} />;
  return <CreatorDash data={data} navigate={navigate} />;
}


const EditorDash = ({ data, onReload }) => {
  const { stats, active_campaigns, recent_clips } = data;
  const chartData = (recent_clips || []).slice(0, 8).reverse().map((c, i) => ({
    name: `C${i + 1}`, ocv: c.ocv || 0, views: c.views || 0,
  }));
  return (
    <div data-testid="editor-dashboard">
      <header className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <div>
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">DASHBOARD</p>
          <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Where you're climbing.</h1>
        </div>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-10">
        <Stat tid="stat-paid" label="Paid Earnings" value={`₹ ${fmt(stats.paid_earnings)}`} bg="#2CFF05" color="#000" />
        <Stat tid="stat-pending" label="Pending Settlement" value={`₹ ${fmt(stats.pending_earnings)}`} bg="#BF00FF" color="#fff" />
        <Stat tid="stat-campaigns" label="Campaigns Joined" value={stats.campaigns_joined} bg="#2D2D2D" color="#fff" />
      </div>

      {/* Active campaigns FIRST */}
      <div className="mb-10">
        <h3 className="font-display text-2xl font-black mb-4">Active campaigns</h3>
        {active_campaigns.length === 0 ? (
          <div className="oc-card text-center py-12" data-testid="empty-campaigns">
            <p className="font-mono text-xs tracking-[0.2em]">YOU HAVEN'T JOINED ANY CAMPAIGNS YET</p>
            <a href="/app/campaigns" className="oc-btn oc-btn-primary mt-5">Browse campaigns</a>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-5">
            {active_campaigns.map(({ campaign, participation, my_clips }) => (
              <a key={campaign.campaign_id} href={`/app/campaigns/${campaign.campaign_id}`}
                 className="oc-card hover:translate-y-[-2px] transition-transform" data-testid={`active-camp-${campaign.campaign_id}`}>
                <div className="flex items-start justify-between">
                  <h4 className="font-display text-xl font-black">{campaign.title}</h4>
                  <span className="oc-chip" style={{ background: "#2CFF05", color: "#000" }}>#{participation?.rank || "—"}</span>
                </div>
                <div className="grid grid-cols-3 gap-3 mt-4 text-sm">
                  <div><p className="font-mono text-[10px] text-[#2D2D2D]">OCV</p><p className="font-display font-black text-lg">{fmtOcv(participation?.total_ocv)}</p></div>
                  <div><p className="font-mono text-[10px] text-[#2D2D2D]">CLIPS</p><p className="font-display font-black text-lg">{my_clips}</p></div>
                  <div><p className="font-mono text-[10px] text-[#2D2D2D]">POOL</p><p className="font-display font-black text-lg">₹{fmt(campaign.bounty_pool)}</p></div>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Recent Clip OCV BELOW Active campaigns */}
      <div className="oc-card" data-testid="points-chart" data-test-ocv-chart="true">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display text-2xl font-black">Recent clip OCV</h3>
          <span className="oc-chip" style={{ background: "#000", color: "#2CFF05" }}>LAST 8 CLIPS</span>
        </div>
        {chartData.length === 0 ? (
          <p className="text-sm text-[#2D2D2D] py-12 text-center font-mono">NO CLIPS YET — SUBMIT YOUR FIRST.</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData}>
              <XAxis dataKey="name" stroke="#000" fontFamily="JetBrains Mono" fontSize={11} />
              <YAxis stroke="#000" fontFamily="JetBrains Mono" fontSize={11} />
              <Tooltip contentStyle={{ background: "#000", border: "2px solid #2CFF05", color: "#fff", borderRadius: 8 }} />
              <Bar dataKey="ocv" name="OCV" radius={[6, 6, 0, 0]}>
                {chartData.map((_, i) => <Cell key={i} fill={i % 2 === 0 ? "#2CFF05" : "#BF00FF"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

const CreatorDash = ({ data, navigate }) => {
  const { stats, my_campaigns, top_editors } = data;
  return (
    <div data-testid="creator-dashboard">
      <header className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <div>
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">DASHBOARD · CREATOR</p>
          <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Your campaigns at a glance.</h1>
        </div>
        <button className="oc-btn oc-btn-primary" onClick={() => navigate("/app/campaigns/new")} data-testid="new-campaign-btn">
          <Plus size={16}/> New campaign
        </button>
      </header>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-10">
        <Stat tid="stat-camps" label="Campaigns Posted" value={stats.campaigns_posted} bg="#2CFF05" color="#000" />
        <Stat tid="stat-clips" label="Total Clips Received" value={fmt(stats.total_clips)} bg="#BF00FF" color="#fff" />
        <Stat tid="stat-paid" label="Total Paid Out" value={`₹ ${fmt(stats.total_paid_out)}`} bg="#2D2D2D" color="#fff" />
        <Stat tid="stat-escrow" label="In Escrow" value={`₹ ${fmt(stats.in_escrow)}`} bg="#fff" color="#000" />
      </div>
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="oc-card lg:col-span-2" data-testid="my-campaigns">
          <h3 className="font-display text-2xl font-black mb-4">My campaigns</h3>
          {my_campaigns.length === 0 ? <p className="font-mono text-xs tracking-[0.2em] py-8 text-center">NO CAMPAIGNS YET</p> :
            <div className="space-y-3">
              {my_campaigns.map(c => (
                <a key={c.campaign_id} href={`/app/campaigns/${c.campaign_id}`}
                   className="flex items-center justify-between p-4 border-2 border-black rounded-lg hover:bg-[#2CFF05] transition-colors group">
                  <div>
                    <p className="font-display text-lg font-black">{c.title}</p>
                    <p className="font-mono text-[10px] text-[#2D2D2D] tracking-[0.2em] mt-1">{c.status} · {c.content_type}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-display font-black text-2xl">₹{fmt(c.bounty_pool)}</p>
                    <p className="font-mono text-[10px] text-[#2D2D2D]">BOUNTY</p>
                  </div>
                </a>
              ))}
            </div>}
        </div>
        <div className="oc-card" data-testid="top-editors">
          <h3 className="font-display text-2xl font-black mb-4">Top editors</h3>
          {top_editors.length === 0 ? <p className="font-mono text-xs tracking-[0.2em] py-8 text-center">NO DATA YET</p> :
            <ol className="space-y-3">
              {top_editors.map((t, i) => (
                <li key={t.editor.user_id} className="flex items-center gap-3 p-3 rounded-lg"
                    style={{ background: i === 0 ? "#2CFF05" : i === 1 ? "#BF00FF" : "#2D2D2D", color: i === 0 ? "#000" : "#fff" }}>
                  <span className="font-display font-black text-2xl">#{i + 1}</span>
                  <img src={t.editor.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${t.editor.name}`}
                       className="w-9 h-9 rounded-full border-2 border-black" alt="" />
                  <div className="flex-1 min-w-0">
                    <p className="font-bold truncate">{t.editor.name}</p>
                    <p className="font-mono text-[10px] opacity-80">{fmtOcv(t.ocv)} OCV</p>
                  </div>
                  <ArrowUpRight size={18} />
                </li>
              ))}
            </ol>}
        </div>
      </div>
    </div>
  );
};
