import React, { useEffect, useState } from "react";
import {
  adminGetOverview,
  adminGetCreators,
  adminGetEditors,
  adminListAllCampaigns,
  adminSetCampaignStatus,
  adminApprovalDecision,
  adminListWithdrawalRequests,
  adminSetWithdrawalStatus,
  adminSuspendUser
} from "@/lib/api";
import {
  ShieldCheck,
  Megaphone,
  Users,
  Wallet as WalletIcon,
  Clock,
  Search,
  Pause,
  X,
  Check,
  Info,
  Calendar,
  Lock,
  ArrowUpRight,
  TrendingUp,
  AlertTriangle,
  Mail,
  User as UserIcon,
  ChevronRight,
  Ban
} from "lucide-react";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));
const fmtDate = (iso) => {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
};

export default function AdminDashboard() {
  // Navigation & Tabs
  const [viewMode, setViewMode] = useState("CREATOR"); // CREATOR | EDITOR
  const [creatorTab, setCreatorTab] = useState("PENDING"); // PENDING | ACTIVE | DIRECTORY
  const [editorTab, setEditorTab] = useState("WITHDRAWALS"); // WITHDRAWALS | DIRECTORY | LEADERBOARD

  // Core Data
  const [overview, setOverview] = useState(null);
  const [creators, setCreators] = useState([]);
  const [editors, setEditors] = useState([]);
  const [pendingCamps, setPendingCamps] = useState([]);
  const [activeCamps, setActiveCamps] = useState([]);
  const [withdrawalRequests, setWithdrawalRequests] = useState([]);
  
  // Loading & Busy States
  const [loading, setLoading] = useState(true);
  const [actionBusyId, setActionBusyId] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Modals / Details Views
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [selectedEditor, setSelectedEditor] = useState(null);
  const [selectedCreator, setSelectedCreator] = useState(null);

  // Leaderboard filters
  const [leaderboardRankBy, setLeaderboardRankBy] = useState("earnings"); // earnings | points

  // Load everything initial or on refresh
  const loadData = async () => {
    setLoading(true);
    try {
      const [over, crs, eds, acs, wds] = await Promise.all([
        adminGetOverview(),
        adminGetCreators(),
        adminGetEditors(),
        adminListAllCampaigns("ACTIVE"),
        adminListWithdrawalRequests("PENDING")
      ]);
      setOverview(over);
      setCreators(crs);
      setEditors(eds);
      setActiveCamps(acs);
      setWithdrawalRequests(wds);
      
      // Load pending campaigns
      const pendingRes = await adminListAllCampaigns("PENDING_APPROVAL");
      setPendingCamps(pendingRes);
    } catch (e) {
      console.error("Failed to load admin data", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Campaign Approval/Rejection
  const handleCampaignApproval = async (id, decision) => {
    setActionBusyId(id);
    try {
      await adminApprovalDecision(id, decision);
      await loadData();
    } catch (e) {
      alert(e.response?.data?.detail || "Action failed");
    } finally {
      setActionBusyId(null);
    }
  };

  // Campaign pause / cancel
  const handleCampaignStatus = async (id, newStatus) => {
    setActionBusyId(id);
    try {
      await adminSetCampaignStatus(id, newStatus);
      await loadData();
    } catch (e) {
      alert(e.response?.data?.detail || "Action failed");
    } finally {
      setActionBusyId(null);
    }
  };

  // Withdrawal approve / reject
  const handleWithdrawal = async (requestId, status) => {
    setActionBusyId(requestId);
    try {
      await adminSetWithdrawalStatus(requestId, status);
      await loadData();
    } catch (e) {
      alert(e.response?.data?.detail || "Action failed");
    } finally {
      setActionBusyId(null);
    }
  };

  // Suspend Creator / Editor
  const handleSuspendUser = async (userId) => {
    if (!window.confirm("Are you sure you want to suspend this user?")) return;
    setActionBusyId(userId);
    try {
      const res = await adminSuspendUser(userId);
      alert(res.message || "User suspended successfully!");
    } catch (e) {
      alert(e.response?.data?.detail || "Action failed");
    } finally {
      setActionBusyId(null);
    }
  };

  return (
    <div data-testid="admin-dashboard-page" className="max-w-7xl mx-auto pb-20">
      
      {/* HEADER SECTION */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
        <div>
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">ADMINISTRATIVE PANEL</p>
          <h1 className="font-display text-4xl md:text-5xl font-black mt-1">
            Admin <span className="text-white bg-black px-2 pb-1 rounded">Dashboard</span>.
          </h1>
        </div>

        {/* VIEW SEGMENTED TOGGLE */}
        <div className="flex bg-[#F3F4F6] p-1 border-2 border-black rounded-full max-w-sm self-start md:self-auto shadow-[4px_4px_0_0_#000]">
          <button
            onClick={() => setViewMode("CREATOR")}
            className={`px-4 py-2 rounded-full font-bold text-sm tracking-wider transition-all ${
              viewMode === "CREATOR"
                ? "bg-black text-[#2CFF05]"
                : "text-gray-500 hover:text-black"
            }`}
            data-testid="toggle-creator-ops"
          >
            Creator Operations
          </button>
          <button
            onClick={() => setViewMode("EDITOR")}
            className={`px-4 py-2 rounded-full font-bold text-sm tracking-wider transition-all ${
              viewMode === "EDITOR"
                ? "bg-black text-[#2CFF05]"
                : "text-gray-500 hover:text-black"
            }`}
            data-testid="toggle-editor-ops"
          >
            Editor Operations
          </button>
        </div>
      </header>

      {/* PLATFORM OVERVIEW CARDS */}
      {overview && (
        <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-10" data-testid="platform-overview">
          <div className="oc-card oc-card-offset flex flex-col justify-between" style={{ minHeight: "110px" }}>
            <div className="flex items-center justify-between text-gray-500">
              <Users size={16} />
              <span className="font-mono text-[9px] tracking-wider uppercase">Creators</span>
            </div>
            <div>
              <p className="font-display text-2xl font-black mt-2">{overview.total_creators}</p>
              <p className="text-[10px] text-gray-400 font-mono">registered</p>
            </div>
          </div>

          <div className="oc-card oc-card-offset flex flex-col justify-between" style={{ minHeight: "110px" }}>
            <div className="flex items-center justify-between text-gray-500">
              <Users size={16} />
              <span className="font-mono text-[9px] tracking-wider uppercase">Editors</span>
            </div>
            <div>
              <p className="font-display text-2xl font-black mt-2">{overview.total_editors}</p>
              <p className="text-[10px] text-gray-400 font-mono">registered</p>
            </div>
          </div>

          <div className="oc-card oc-card-offset flex flex-col justify-between" style={{ minHeight: "110px" }}>
            <div className="flex items-center justify-between text-gray-500">
              <Megaphone size={16} />
              <span className="font-mono text-[9px] tracking-wider uppercase">Active Camps</span>
            </div>
            <div>
              <p className="font-display text-2xl font-black mt-2">{overview.active_campaigns}</p>
              <p className="text-[10px] text-gray-400 font-mono">running</p>
            </div>
          </div>

          <div className="oc-card oc-card-offset flex flex-col justify-between" style={{ minHeight: "110px" }} data-testid="overview-pending-campaigns">
            <div className="flex items-center justify-between text-gray-500">
              <Clock size={16} />
              <span className="font-mono text-[9px] tracking-wider uppercase">Pending Camps</span>
            </div>
            <div>
              <p className="font-display text-2xl font-black mt-2 text-amber-500">{overview.pending_campaigns}</p>
              <p className="text-[10px] text-gray-400 font-mono">needs approval</p>
            </div>
          </div>

          <div className="oc-card oc-card-offset flex flex-col justify-between" style={{ minHeight: "110px", background: "#2CFF05" }}>
            <div className="flex items-center justify-between text-black/60">
              <WalletIcon size={16} />
              <span className="font-mono text-[9px] tracking-wider uppercase font-bold text-black font-semibold">Earnings</span>
            </div>
            <div>
              <p className="font-display text-xl font-black mt-2">₹ {fmt(overview.total_platform_earnings)}</p>
              <p className="text-[10px] text-black/60 font-mono font-semibold">total settled</p>
            </div>
          </div>

          <div className="oc-card oc-card-offset flex flex-col justify-between" style={{ minHeight: "110px", background: overview.pending_withdrawals > 0 ? "#BF00FF" : "#fff", color: overview.pending_withdrawals > 0 ? "#fff" : "#000" }}>
            <div className="flex items-center justify-between opacity-80">
              <Clock size={16} />
              <span className="font-mono text-[9px] tracking-wider uppercase">Pending Wds</span>
            </div>
            <div>
              <p className="font-display text-2xl font-black mt-2">{overview.pending_withdrawals}</p>
              <p className="text-[10px] opacity-75 font-mono">unresolved requests</p>
            </div>
          </div>
        </section>
      )}

      {loading ? (
        <div className="text-center py-20">
          <p className="font-mono text-sm oc-pulse tracking-widest text-[#2D2D2D]">SYNCHRONIZING PLATFORM CONTROL PANEL...</p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-4 gap-8">
          
          {/* TAB SIDE NAVIGATION */}
          <aside className="lg:col-span-1 space-y-6">
            <div className="oc-card p-4 space-y-1">
              <p className="font-mono text-[10px] text-gray-400 tracking-[0.2em] px-3 mb-2 uppercase">
                {viewMode} OPERATIONS
              </p>
              
              {viewMode === "CREATOR" ? (
                <>
                  <button
                    onClick={() => setCreatorTab("PENDING")}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-bold transition-all ${
                      creatorTab === "PENDING"
                        ? "bg-black text-[#2CFF05]"
                        : "hover:bg-[#F3F4F6] text-black"
                    }`}
                  >
                    <span>Pending Campaigns</span>
                    <span className="bg-amber-100 text-amber-800 text-[10px] font-mono px-2 py-0.5 rounded-full font-bold">
                      {pendingCamps.length}
                    </span>
                  </button>
                  
                  <button
                    onClick={() => setCreatorTab("ACTIVE")}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-bold transition-all ${
                      creatorTab === "ACTIVE"
                        ? "bg-black text-[#2CFF05]"
                        : "hover:bg-[#F3F4F6] text-black"
                    }`}
                  >
                    <span>Active Campaigns</span>
                    <span className="bg-gray-100 text-gray-800 text-[10px] font-mono px-2 py-0.5 rounded-full font-bold">
                      {activeCamps.length}
                    </span>
                  </button>

                  <button
                    onClick={() => setCreatorTab("DIRECTORY")}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-bold transition-all ${
                      creatorTab === "DIRECTORY"
                        ? "bg-black text-[#2CFF05]"
                        : "hover:bg-[#F3F4F6] text-black"
                    }`}
                  >
                    <span>Creator Directory</span>
                    <ChevronRight size={14} />
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setEditorTab("WITHDRAWALS")}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-bold transition-all ${
                      editorTab === "WITHDRAWALS"
                        ? "bg-black text-[#2CFF05]"
                        : "hover:bg-[#F3F4F6] text-black"
                    }`}
                  >
                    <span>Withdrawal Requests</span>
                    <span className="bg-purple-100 text-purple-800 text-[10px] font-mono px-2 py-0.5 rounded-full font-bold">
                      {withdrawalRequests.length}
                    </span>
                  </button>

                  <button
                    onClick={() => setEditorTab("DIRECTORY")}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-bold transition-all ${
                      editorTab === "DIRECTORY"
                        ? "bg-black text-[#2CFF05]"
                        : "hover:bg-[#F3F4F6] text-black"
                    }`}
                  >
                    <span>Editor Directory</span>
                    <ChevronRight size={14} />
                  </button>

                  <button
                    onClick={() => setEditorTab("LEADERBOARD")}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-bold transition-all ${
                      editorTab === "LEADERBOARD"
                        ? "bg-black text-[#2CFF05]"
                        : "hover:bg-[#F3F4F6] text-black"
                    }`}
                  >
                    <span>Top Editors</span>
                    <ChevronRight size={14} />
                  </button>
                </>
              )}
            </div>

            {/* FUTURE-READY OPERATIONS PANEL (PLACEHOLDERS) */}
            <div className="oc-card p-4 space-y-3">
              <p className="font-mono text-[10px] text-gray-400 tracking-[0.2em] px-3 uppercase">
                Future Operations
              </p>
              
              <div className="space-y-1.5 text-xs text-[#2D2D2D] opacity-60">
                <div className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-not-allowed">
                  <Lock size={12} />
                  <span>User Reports (0)</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-not-allowed">
                  <Lock size={12} />
                  <span>Disputes System</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-not-allowed">
                  <Lock size={12} />
                  <span>Creator Verification</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-not-allowed">
                  <Lock size={12} />
                  <span>Editor Verification</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-not-allowed">
                  <Lock size={12} />
                  <span>Platform Announcements</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-not-allowed">
                  <Lock size={12} />
                  <span>Featured Campaigns</span>
                </div>
              </div>
            </div>
          </aside>

          {/* MAIN OPERATIONS WORKSPACE */}
          <main className="lg:col-span-3 space-y-6">
            
            {/* SEARCH / FILTER SUB-HEADER (only shown for directory views) */}
            {((viewMode === "CREATOR" && creatorTab === "DIRECTORY") || 
              (viewMode === "EDITOR" && editorTab === "DIRECTORY")) && (
              <div className="flex items-center gap-3 bg-white p-3 border-2 border-black rounded-xl">
                <Search size={18} className="text-[#2D2D2D]" />
                <input
                  type="text"
                  placeholder="Search profiles by name or username..."
                  className="flex-1 outline-none text-sm font-medium"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchQuery && (
                  <button onClick={() => setSearchQuery("")} className="p-1 hover:bg-gray-100 rounded">
                    <X size={14} />
                  </button>
                )}
              </div>
            )}

            {/* ======================================================== */}
            {/* CREATOR OPERATIONS WORKSPACE */}
            {/* ======================================================== */}
            {viewMode === "CREATOR" && (
              <div className="space-y-6">
                
                {/* 1. Pending Campaigns */}
                {creatorTab === "PENDING" && (
                  <div className="oc-card" data-testid="pending-campaigns-section">
                    <h2 className="font-display text-2xl font-black mb-4">Pending approvals</h2>
                    {pendingCamps.length === 0 ? (
                      <p className="text-sm text-gray-500 py-10 text-center font-mono">NO CAMPAIGNS AWAITING REVIEW</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                          <thead>
                            <tr className="border-b-2 border-black font-mono text-[9px] tracking-wider text-[#2D2D2D]">
                              <th className="pb-3">CAMPAIGN NAME</th>
                              <th className="pb-3">CREATOR</th>
                              <th className="pb-3 text-right">BUDGET</th>
                              <th className="pb-3 text-center">SUBMITTED</th>
                              <th className="pb-3 text-right">ACTIONS</th>
                            </tr>
                          </thead>
                          <tbody>
                            {pendingCamps.map((c) => (
                              <tr key={c.campaign_id} className="border-b border-gray-100 hover:bg-gray-50/50" data-testid={`pending-campaign-row-${c.campaign_id}`}>
                                <td className="py-4">
                                  <button
                                    onClick={() => setSelectedCampaign(c)}
                                    className="font-bold hover:underline text-left text-sm"
                                  >
                                    {c.title}
                                  </button>
                                </td>
                                <td className="py-4 text-xs font-semibold">{c.creator_name || "—"}</td>
                                <td className="py-4 text-right font-bold text-sm">₹{fmt(c.bounty_pool)}</td>
                                <td className="py-4 text-center font-mono text-[11px]">{fmtDate(c.created_at)}</td>
                                <td className="py-4 text-right">
                                  <div className="flex gap-2 justify-end">
                                    <button
                                      disabled={actionBusyId !== null}
                                      onClick={() => handleCampaignApproval(c.campaign_id, "APPROVE")}
                                      className="p-1 px-2.5 bg-[#2CFF05] text-black border border-black font-bold text-xs rounded hover:brightness-105"
                                      data-testid={`approve-campaign-btn-${c.campaign_id}`}
                                    >
                                      Approve
                                    </button>
                                    <button
                                      disabled={actionBusyId !== null}
                                      onClick={() => handleCampaignApproval(c.campaign_id, "REJECT")}
                                      className="p-1 px-2.5 bg-white text-red-600 border border-red-500 font-bold text-xs rounded hover:bg-red-50"
                                      data-testid={`reject-campaign-btn-${c.campaign_id}`}
                                    >
                                      Reject
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* 2. Active Campaigns */}
                {creatorTab === "ACTIVE" && (
                  <div className="oc-card" data-testid="active-campaigns-section">
                    <h2 className="font-display text-2xl font-black mb-4">Active campaigns</h2>
                    {activeCamps.length === 0 ? (
                      <p className="text-sm text-gray-500 py-10 text-center font-mono">NO ACTIVE CAMPAIGNS</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                          <thead>
                            <tr className="border-b-2 border-black font-mono text-[9px] tracking-wider text-[#2D2D2D]">
                              <th className="pb-3">CAMPAIGN NAME</th>
                              <th className="pb-3">CREATOR</th>
                              <th className="pb-3 text-right">BUDGET</th>
                              <th className="pb-3 text-center">LAUNCH DATE</th>
                              <th className="pb-3 text-right">ACTIONS</th>
                            </tr>
                          </thead>
                          <tbody>
                            {activeCamps.map((c) => (
                              <tr key={c.campaign_id} className="border-b border-gray-100 hover:bg-gray-50/50">
                                <td className="py-4">
                                  <button
                                    onClick={() => setSelectedCampaign(c)}
                                    className="font-bold hover:underline text-left text-sm"
                                  >
                                    {c.title}
                                  </button>
                                </td>
                                <td className="py-4 text-xs font-semibold">{c.creator_name || "—"}</td>
                                <td className="py-4 text-right font-bold text-sm">₹{fmt(c.bounty_pool)}</td>
                                <td className="py-4 text-center font-mono text-[11px]">{fmtDate(c.created_at)}</td>
                                <td className="py-4 text-right">
                                  <div className="flex gap-2 justify-end">
                                    <button
                                      disabled={actionBusyId !== null}
                                      onClick={() => handleCampaignStatus(c.campaign_id, "PAUSED")}
                                      className="p-1 px-2.5 bg-amber-100 text-amber-700 font-bold text-xs rounded hover:bg-amber-200"
                                    >
                                      Pause
                                    </button>
                                    <button
                                      disabled={actionBusyId !== null}
                                      onClick={() => handleCampaignStatus(c.campaign_id, "CANCELLED")}
                                      className="p-1 px-2.5 bg-red-100 text-red-700 font-bold text-xs rounded hover:bg-red-200"
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* 3. Creator Directory */}
                {creatorTab === "DIRECTORY" && (
                  <div className="oc-card" data-testid="creator-directory-section">
                    <h2 className="font-display text-2xl font-black mb-4">Creator Profiles</h2>
                    
                    {creators.filter(c => 
                      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      c.username.toLowerCase().includes(searchQuery.toLowerCase())
                    ).length === 0 ? (
                      <p className="text-sm text-gray-500 py-10 text-center font-mono">NO CREATORS FOUND</p>
                    ) : (
                      <div className="space-y-4">
                        {creators
                          .filter(c => 
                            c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            c.username.toLowerCase().includes(searchQuery.toLowerCase())
                          )
                          .map((c) => (
                            <div key={c.user_id} className="border-2 border-black rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
                              <div className="flex items-center gap-3">
                                <img
                                  src={c.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${c.name}`}
                                  className="w-10 h-10 rounded-full border-2 border-black"
                                  alt=""
                                />
                                <div>
                                  <p className="font-bold text-base leading-tight">{c.name}</p>
                                  <p className="font-mono text-xs text-gray-500">@{c.username || "no-username"}</p>
                                </div>
                              </div>

                              <div className="flex gap-8 text-center">
                                <div>
                                  <span className="font-mono text-[9px] text-gray-400 block uppercase">Campaigns</span>
                                  <span className="font-bold text-sm">{c.campaigns_count}</span>
                                </div>
                                <div>
                                  <span className="font-mono text-[9px] text-gray-400 block uppercase">Total Spent</span>
                                  <span className="font-bold text-sm">₹{fmt(c.total_spend)}</span>
                                </div>
                              </div>

                              <div className="flex gap-2">
                                <button
                                  onClick={() => setSelectedCreator(c)}
                                  className="p-1 px-3 bg-black text-white rounded text-xs font-bold hover:bg-gray-800"
                                >
                                  View History
                                </button>
                                <button
                                  onClick={() => handleSuspendUser(c.user_id)}
                                  className="p-1 px-2 text-red-600 hover:bg-red-50 border border-red-500 rounded text-xs font-bold"
                                  title="Suspend Creator (Future-Ready UI)"
                                >
                                  Suspend
                                </button>
                              </div>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ======================================================== */}
            {/* EDITOR OPERATIONS WORKSPACE */}
            {/* ======================================================== */}
            {viewMode === "EDITOR" && (
              <div className="space-y-6">
                
                {/* 1. Withdrawal Requests */}
                {editorTab === "WITHDRAWALS" && (
                  <div className="oc-card" data-testid="withdrawal-requests-section">
                    <h2 className="font-display text-2xl font-black mb-4">Pending withdrawals</h2>
                    {withdrawalRequests.length === 0 ? (
                      <p className="text-sm text-gray-500 py-10 text-center font-mono">NO PENDING PAYOUT REQUESTS</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse" data-testid="withdrawals-table">
                          <thead>
                            <tr className="border-b-2 border-black font-mono text-[9px] tracking-wider text-[#2D2D2D]">
                              <th className="pb-3">EDITOR</th>
                              <th className="pb-3 text-right">AMOUNT</th>
                              <th className="pb-3 text-center">REQUEST DATE</th>
                              <th className="pb-3 text-center">STATUS</th>
                              <th className="pb-3 text-right">ACTIONS</th>
                            </tr>
                          </thead>
                          <tbody>
                            {withdrawalRequests.map((r) => (
                              <tr key={r.request_id} className="border-b border-gray-100 hover:bg-gray-50/50" data-testid={`withdrawal-row-${r.request_id}`}>
                                <td className="py-4 font-bold text-sm">
                                  {r.editor_name}
                                  <span className="font-mono text-xs font-normal text-gray-400 block">@{r.editor_username}</span>
                                </td>
                                <td className="py-4 text-right font-display font-bold text-sm">₹{fmt(r.amount)}</td>
                                <td className="py-4 text-center font-mono text-[11px] text-gray-500">{fmtDate(r.created_at)}</td>
                                <td className="py-4 text-center">
                                  <span className="oc-chip bg-amber-100 text-amber-700 text-[10px] tracking-wide py-0.5">{r.status}</span>
                                </td>
                                <td className="py-4 text-right">
                                  <div className="flex gap-2 justify-end">
                                    <button
                                      disabled={actionBusyId !== null}
                                      onClick={() => handleWithdrawal(r.request_id, "PAID")}
                                      className="p-1 px-3 bg-[#2CFF05] text-black border border-black font-bold text-xs rounded hover:brightness-105"
                                      data-testid={`approve-wd-btn-${r.request_id}`}
                                    >
                                      Approve
                                    </button>
                                    <button
                                      disabled={actionBusyId !== null}
                                      onClick={() => handleWithdrawal(r.request_id, "REJECTED")}
                                      className="p-1 px-3 bg-white text-red-600 border border-red-500 font-bold text-xs rounded hover:bg-red-50"
                                      data-testid={`reject-wd-btn-${r.request_id}`}
                                    >
                                      Reject
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* 2. Editor Directory */}
                {editorTab === "DIRECTORY" && (
                  <div className="oc-card" data-testid="editor-directory-section">
                    <h2 className="font-display text-2xl font-black mb-4">Editor Profiles</h2>
                    
                    {editors.filter(e => 
                      e.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      e.username.toLowerCase().includes(searchQuery.toLowerCase())
                    ).length === 0 ? (
                      <p className="text-sm text-gray-500 py-10 text-center font-mono">NO EDITORS FOUND</p>
                    ) : (
                      <div className="space-y-4">
                        {editors
                          .filter(e => 
                            e.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            e.username.toLowerCase().includes(searchQuery.toLowerCase())
                          )
                          .map((e) => (
                            <div key={e.user_id} className="border-2 border-black rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
                              <div className="flex items-center gap-3">
                                <img
                                  src={e.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${e.name}`}
                                  className="w-10 h-10 rounded-full border-2 border-black"
                                  alt=""
                                />
                                <div>
                                  <p className="font-bold text-base leading-tight">{e.name}</p>
                                  <p className="font-mono text-xs text-gray-500">@{e.username || "no-username"}</p>
                                </div>
                              </div>

                              <div className="flex gap-6 text-center">
                                <div>
                                  <span className="font-mono text-[9px] text-gray-400 block uppercase">Total Earned</span>
                                  <span className="font-bold text-sm">₹{fmt(e.total_earnings)}</span>
                                </div>
                                <div>
                                  <span className="font-mono text-[9px] text-gray-400 block uppercase">Lifetime OCV</span>
                                  <span className="font-bold text-sm text-purple-600">{fmt(e.lifetime_points)}</span>
                                </div>
                              </div>

                              <div className="flex gap-2">
                                <button
                                  onClick={() => setSelectedEditor(e)}
                                  className="p-1 px-3 bg-black text-white rounded text-xs font-bold hover:bg-gray-800"
                                >
                                  Full Details
                                </button>
                                <button
                                  onClick={() => handleSuspendUser(e.user_id)}
                                  className="p-1 px-2 text-red-600 hover:bg-red-50 border border-red-500 rounded text-xs font-bold"
                                  title="Suspend Editor"
                                >
                                  Suspend
                                </button>
                              </div>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 3. Top Editors (Leaderboard) */}
                {editorTab === "LEADERBOARD" && (
                  <div className="oc-card" data-testid="editor-leaderboard-section">
                    <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
                      <h2 className="font-display text-2xl font-black">Top Editors</h2>
                      
                      <div className="flex bg-[#F3F4F6] p-0.5 border border-black rounded-lg text-xs font-semibold">
                        <button
                          onClick={() => setLeaderboardRankBy("earnings")}
                          className={`px-3 py-1.5 rounded-md ${
                            leaderboardRankBy === "earnings" ? "bg-black text-[#2CFF05]" : "text-gray-500"
                          }`}
                        >
                          Rank by Earnings
                        </button>
                        <button
                          onClick={() => setLeaderboardRankBy("points")}
                          className={`px-3 py-1.5 rounded-md ${
                            leaderboardRankBy === "points" ? "bg-black text-[#2CFF05]" : "text-gray-500"
                          }`}
                        >
                          Rank by OCV
                        </button>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {[...editors]
                        .sort((a, b) => {
                          if (leaderboardRankBy === "earnings") return b.total_earnings - a.total_earnings;
                          return b.lifetime_points - a.lifetime_points;
                        })
                        .slice(0, 10)
                        .map((e, idx) => (
                          <div
                            key={e.user_id}
                            className={`border-2 border-black rounded-xl p-3 flex items-center justify-between transition-all ${
                              idx === 0 ? "bg-[#2CFF05]/10 border-[#2CFF05]" : idx === 1 ? "bg-purple-50" : ""
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <span className="font-display font-black text-lg w-6 text-center">#{idx + 1}</span>
                              <img
                                src={e.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${e.name}`}
                                className="w-8 h-8 rounded-full border border-black"
                                alt=""
                              />
                              <div>
                                <p className="font-bold text-sm leading-tight">{e.name}</p>
                                <p className="font-mono text-[10px] text-gray-500">@{e.username}</p>
                              </div>
                            </div>
                            
                            <div className="text-right">
                              {leaderboardRankBy === "earnings" ? (
                                <p className="font-display font-bold text-sm">₹{fmt(e.total_earnings)}</p>
                              ) : (
                                <p className="font-mono font-bold text-xs text-purple-600">{fmt(e.lifetime_points)} OCV</p>
                              )}
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </main>
        </div>
      )}

      {/* ======================================================== */}
      {/* CAMPAIGN REVIEW DETAILED MODAL */}
      {/* ======================================================== */}
      {selectedCampaign && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white border-2 border-black rounded-2xl w-full max-w-lg p-6 shadow-[8px_8px_0_0_#000] relative animate-in fade-in zoom-in duration-200">
            <button
              onClick={() => setSelectedCampaign(null)}
              className="absolute top-4 right-4 p-1 hover:bg-gray-100 rounded-full border border-black"
            >
              <X size={16} />
            </button>

            <span className="font-mono text-[9px] text-[#BF00FF] tracking-wider block uppercase mb-1">
              Campaign review
            </span>
            <h3 className="font-display text-xl font-black mb-4 leading-tight">{selectedCampaign.title}</h3>

            <div className="space-y-4 text-sm mb-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                  <span className="font-mono text-[9px] text-gray-400 block uppercase">BUDGET</span>
                  <span className="font-display font-bold text-lg">₹ {fmt(selectedCampaign.bounty_pool)}</span>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                  <span className="font-mono text-[9px] text-gray-400 block uppercase">STATUS</span>
                  <span className="font-bold text-sm text-[#BF00FF] block mt-1 uppercase font-mono">
                    {selectedCampaign.status}
                  </span>
                </div>
              </div>

              <div>
                <span className="font-mono text-[9px] text-gray-400 block uppercase">CREATOR INFORMATION</span>
                <p className="font-bold">{selectedCampaign.creator_name || "Unknown Creator"}</p>
                <p className="text-xs text-gray-500 font-mono">ID: {selectedCampaign.creator_id}</p>
              </div>

              <div>
                <span className="font-mono text-[9px] text-gray-400 block uppercase">STATUS HISTORY</span>
                <ul className="mt-2 space-y-1.5 font-mono text-xs text-[#2D2D2D]">
                  <li className="flex items-center gap-2">
                    <Check size={12} className="text-green-500" />
                    <span>Created: {fmtDate(selectedCampaign.created_at)}</span>
                  </li>
                  {selectedCampaign.status === "PENDING_APPROVAL" && (
                    <li className="flex items-center gap-2">
                      <Clock size={12} className="text-amber-500" />
                      <span>Submitted for manual approval queue</span>
                    </li>
                  )}
                </ul>
              </div>
            </div>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setSelectedCampaign(null)}
                className="p-2 px-4 bg-white border border-black rounded-lg text-xs font-bold hover:bg-gray-50"
              >
                Close
              </button>
              {selectedCampaign.status === "PENDING_APPROVAL" && (
                <>
                  <button
                    onClick={() => {
                      handleCampaignApproval(selectedCampaign.campaign_id, "APPROVE");
                      setSelectedCampaign(null);
                    }}
                    className="p-2 px-4 bg-[#2CFF05] text-black border border-black rounded-lg text-xs font-bold hover:brightness-105"
                  >
                    Approve & Activate
                  </button>
                  <button
                    onClick={() => {
                      handleCampaignApproval(selectedCampaign.campaign_id, "REJECT");
                      setSelectedCampaign(null);
                    }}
                    className="p-2 px-4 bg-red-600 text-white rounded-lg text-xs font-bold hover:bg-red-700"
                  >
                    Reject
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* CREATOR HISTORY / DETAIL MODAL */}
      {/* ======================================================== */}
      {selectedCreator && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white border-2 border-black rounded-2xl w-full max-w-xl p-6 shadow-[8px_8px_0_0_#000] relative max-h-[85vh] flex flex-col animate-in fade-in zoom-in duration-200">
            <button
              onClick={() => setSelectedCreator(null)}
              className="absolute top-4 right-4 p-1 hover:bg-gray-100 rounded-full border border-black"
            >
              <X size={16} />
            </button>

            <header className="mb-4">
              <span className="font-mono text-[9px] text-[#BF00FF] tracking-wider block uppercase">
                Creator Management Profile
              </span>
              <h3 className="font-display text-xl font-black">{selectedCreator.name}</h3>
              <p className="text-xs text-gray-500 font-mono">@{selectedCreator.username || "no-username"} · {selectedCreator.email}</p>
            </header>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-gray-50 p-3 rounded-lg border border-gray-100 text-center">
                <span className="font-mono text-[9px] text-gray-400 block uppercase">Campaigns Published</span>
                <span className="font-display font-bold text-lg">{selectedCreator.campaigns_count}</span>
              </div>
              <div className="bg-gray-50 p-3 rounded-lg border border-gray-100 text-center">
                <span className="font-mono text-[9px] text-gray-400 block uppercase">Total Distributed Spend</span>
                <span className="font-display font-bold text-lg text-green-600">₹{fmt(selectedCreator.total_spend)}</span>
              </div>
            </div>

            <h4 className="font-mono text-[10px] text-gray-400 tracking-[0.2em] mb-2 uppercase">Campaign History</h4>
            <div className="flex-1 overflow-y-auto border border-gray-100 rounded-lg p-2 space-y-2 mb-4">
              {selectedCreator.campaign_history.length === 0 ? (
                <p className="text-xs text-gray-400 py-6 text-center">No campaign history recorded.</p>
              ) : (
                selectedCreator.campaign_history.map(c => (
                  <div key={c.campaign_id} className="bg-gray-50 p-3 rounded border border-gray-100 flex items-center justify-between text-xs">
                    <div>
                      <p className="font-bold">{c.title}</p>
                      <p className="text-[10px] text-gray-400 font-mono">Created: {fmtDate(c.created_at)}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold">₹{fmt(c.bounty_pool)}</p>
                      <span className={`inline-block text-[9px] font-mono font-semibold uppercase ${
                        c.status === "ACTIVE" ? "text-green-600" : c.status === "PENDING_APPROVAL" ? "text-amber-500" : "text-gray-400"
                      }`}>{c.status}</span>
                    </div>
                  </div>
                ))
              )}
            </div>

            <footer className="flex justify-between items-center mt-auto pt-2 border-t">
              <button
                onClick={() => handleSuspendUser(selectedCreator.user_id)}
                className="flex items-center gap-1.5 p-1.5 px-3 bg-red-100 text-red-700 font-bold text-xs rounded hover:bg-red-200 border border-red-300"
              >
                <Ban size={12} /> Suspend Account
              </button>
              <button
                onClick={() => setSelectedCreator(null)}
                className="p-1.5 px-4 bg-black text-white rounded text-xs font-bold hover:bg-gray-800"
              >
                Close
              </button>
            </footer>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* EDITOR PROFILE / WITHDRAWAL HISTORY DETAILED MODAL */}
      {/* ======================================================== */}
      {selectedEditor && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white border-2 border-black rounded-2xl w-full max-w-xl p-6 shadow-[8px_8px_0_0_#000] relative max-h-[85vh] flex flex-col animate-in fade-in zoom-in duration-200">
            <button
              onClick={() => setSelectedEditor(null)}
              className="absolute top-4 right-4 p-1 hover:bg-gray-100 rounded-full border border-black"
            >
              <X size={16} />
            </button>

            <header className="mb-4">
              <span className="font-mono text-[9px] text-[#BF00FF] tracking-wider block uppercase">
                Editor Profile Summary
              </span>
              <h3 className="font-display text-xl font-black">{selectedEditor.name}</h3>
              <p className="text-xs text-gray-500 font-mono">@{selectedEditor.username || "no-username"} · {selectedEditor.email}</p>
            </header>

            <div className="grid grid-cols-4 gap-2 mb-4 text-center">
              <div className="bg-gray-50 p-2 rounded border border-gray-100">
                <span className="font-mono text-[8px] text-gray-400 block uppercase leading-none mb-1">Wallet Bal</span>
                <span className="font-bold text-xs">₹{fmt(selectedEditor.wallet_balance)}</span>
              </div>
              <div className="bg-gray-50 p-2 rounded border border-gray-100">
                <span className="font-mono text-[8px] text-gray-400 block uppercase leading-none mb-1">Total Earned</span>
                <span className="font-bold text-xs">₹{fmt(selectedEditor.total_earnings)}</span>
              </div>
              <div className="bg-gray-50 p-2 rounded border border-gray-100">
                <span className="font-mono text-[8px] text-gray-400 block uppercase leading-none mb-1">Withdrawn</span>
                <span className="font-bold text-xs text-green-600">₹{fmt(selectedEditor.total_withdrawn)}</span>
              </div>
              <div className="bg-gray-50 p-2 rounded border border-gray-100">
                <span className="font-mono text-[8px] text-gray-400 block uppercase leading-none mb-1">OCV</span>
                <span className="font-bold text-xs text-purple-600">{fmt(selectedEditor.lifetime_points)}</span>
              </div>
            </div>

            <h4 className="font-mono text-[10px] text-gray-400 tracking-[0.2em] mb-2 uppercase">Withdrawal History</h4>
            <div className="flex-1 overflow-y-auto border border-gray-100 rounded-lg p-2 space-y-2 mb-4">
              {selectedEditor.withdrawal_history.length === 0 ? (
                <p className="text-xs text-gray-400 py-6 text-center">No withdrawals recorded.</p>
              ) : (
                selectedEditor.withdrawal_history.map(w => (
                  <div key={w.request_id} className="bg-gray-50 p-3 rounded border border-gray-100 flex items-center justify-between text-xs">
                    <div>
                      <p className="font-bold">₹{fmt(w.amount)}</p>
                      <p className="text-[10px] text-gray-400 font-mono">Date: {fmtDate(w.created_at)}</p>
                    </div>
                    <div>
                      <span className={`oc-chip text-[9px] ${
                        w.status === "PAID" ? "bg-green-100 text-green-700" : w.status === "PENDING" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"
                      }`}>{w.status}</span>
                    </div>
                  </div>
                ))
              )}
            </div>

            <footer className="flex justify-between items-center mt-auto pt-2 border-t">
              <button
                onClick={() => handleSuspendUser(selectedEditor.user_id)}
                className="flex items-center gap-1.5 p-1.5 px-3 bg-red-100 text-red-700 font-bold text-xs rounded hover:bg-red-200 border border-red-300"
              >
                <Ban size={12} /> Suspend Account
              </button>
              <button
                onClick={() => setSelectedEditor(null)}
                className="p-1.5 px-4 bg-black text-white rounded text-xs font-bold hover:bg-gray-800"
              >
                Close
              </button>
            </footer>
          </div>
        </div>
      )}

    </div>
  );
}
