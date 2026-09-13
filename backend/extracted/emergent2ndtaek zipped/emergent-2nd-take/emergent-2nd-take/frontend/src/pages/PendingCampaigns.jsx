import React, { useEffect, useState } from "react";
import { adminGetPendingCampaigns, adminApprovalDecision } from "@/lib/api";
import { ShieldCheck, Check, X, Megaphone, Calendar } from "lucide-react";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));

export default function PendingCampaigns() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  const load = () => {
    setLoading(true);
    adminGetPendingCampaigns()
      .then(setItems)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleDecision = async (id, decision) => {
    setBusyId(id);
    try {
      await adminApprovalDecision(id, decision);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div data-testid="admin-pending-page" className="max-w-6xl mx-auto">
      <header className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <div>
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">ADMIN · PENDING APPROVAL</p>
          <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Pending Campaigns.</h1>
        </div>
      </header>

      {loading ? (
        <p className="font-mono text-sm oc-pulse">LOADING PENDING CAMPAIGNS…</p>
      ) : items.length === 0 ? (
        <div className="oc-card text-center py-20" data-testid="empty-pending">
          <Megaphone size={40} className="mx-auto text-[#2D2D2D]" />
          <p className="font-mono text-xs tracking-[0.25em] text-[#2D2D2D] mt-4">NO PENDING CAMPAIGNS</p>
          <p className="text-sm text-[#2D2D2D] mt-2">All campaigns are currently active or processed.</p>
        </div>
      ) : (
        <div className="oc-card overflow-x-auto">
          <table className="w-full text-left border-collapse" data-testid="pending-table">
            <thead>
              <tr className="border-b-2 border-black font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">
                <th className="pb-3 text-left">CAMPAIGN NAME</th>
                <th className="pb-3 text-left">CREATOR</th>
                <th className="pb-3 text-right">BUDGET</th>
                <th className="pb-3 text-center">SUBMISSION DATE</th>
                <th className="pb-3 text-center">STATUS</th>
                <th className="pb-3 text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.campaign_id} className="border-b border-black/10 hover:bg-[#F9F9F9] transition-colors" data-testid={`pending-row-${c.campaign_id}`}>
                  <td className="py-4 font-display font-black text-lg">{c.title}</td>
                  <td className="py-4 text-sm text-[#2D2D2D]">{c.creator_name || "—"}</td>
                  <td className="py-4 text-right font-display font-black text-lg">₹{fmt(c.bounty_pool)}</td>
                  <td className="py-4 text-center font-mono text-xs text-[#2D2D2D]">
                    {c.created_at ? new Date(c.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                  </td>
                  <td className="py-4 text-center">
                    <span className="px-3 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-700 border border-amber-200">
                      Pending Approval
                    </span>
                  </td>
                  <td className="py-4 text-right">
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => handleDecision(c.campaign_id, "APPROVE")}
                        disabled={busyId !== null}
                        className="oc-btn px-3 py-1.5 text-xs flex items-center gap-1 border-2 border-black hover:bg-[#2CFF05]"
                        style={{ background: "#fff", color: "#000" }}
                        data-testid={`approve-btn-${c.campaign_id}`}
                      >
                        <Check size={14} /> Approve
                      </button>
                      <button
                        onClick={() => handleDecision(c.campaign_id, "REJECT")}
                        disabled={busyId !== null}
                        className="oc-btn px-3 py-1.5 text-xs flex items-center gap-1 border-2 border-red-600 hover:bg-red-500 hover:text-white"
                        style={{ background: "#fff", color: "#E02424" }}
                        data-testid={`reject-btn-${c.campaign_id}`}
                      >
                        <X size={14} /> Reject
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
  );
}
