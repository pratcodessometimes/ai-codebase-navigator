import React, { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { updateProfile, listWithdrawals } from "@/lib/api";
import { Receipt, CheckCircle2, Clock } from "lucide-react";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));
const fmtDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" }) +
         " · " + d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
};

export default function Settings() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    username: user?.username || "", bio: user?.bio || "",
    payout_upi: user?.payout_upi || "", is_earnings_public: !!user?.is_earnings_public,
  });
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [withdrawals, setWithdrawals] = useState(null);

  useEffect(() => { listWithdrawals().then(setWithdrawals); }, []);

  const save = async () => {
    setBusy(true);
    try {
      const u = await updateProfile(form);
      setUser(u); setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally { setBusy(false); }
  };

  return (
    <div data-testid="settings-page">
      <header className="mb-8">
        <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">SETTINGS</p>
        <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Account.</h1>
      </header>

      <div className="grid lg:grid-cols-5 gap-6">
        <div className="oc-card lg:col-span-3 space-y-4">
          <h3 className="font-display text-2xl font-black">Profile</h3>
          {["username", "bio", "payout_upi"].map(k => (
            <label key={k} className="block">
              <span className="font-mono text-[10px] tracking-[0.2em]">{k.toUpperCase().replace("_", " ")}</span>
              {k === "bio" ?
                <textarea value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })} rows={3}
                  className="w-full mt-1 p-3 border-2 border-black rounded-lg" data-testid={`set-${k}`} /> :
                <input value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}
                  className="w-full mt-1 p-3 border-2 border-black rounded-lg" data-testid={`set-${k}`} />}
            </label>
          ))}
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={form.is_earnings_public} onChange={e => setForm({ ...form, is_earnings_public: e.target.checked })}
              className="w-5 h-5" data-testid="set-public" />
            <span className="text-sm">Show my earnings publicly on profile</span>
          </label>
          <button onClick={save} disabled={busy} className="oc-btn oc-btn-primary" data-testid="save-settings">
            {busy ? "Saving…" : saved ? "Saved ✓" : "Save changes"}
          </button>
        </div>

        <div className="oc-card lg:col-span-2" data-testid="withdrawal-history">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-2xl font-black">Withdrawal history</h3>
            <Receipt size={20} />
          </div>

          {withdrawals === null ? (
            <p className="font-mono text-xs tracking-[0.2em] py-6 oc-pulse">LOADING…</p>
          ) : withdrawals.length === 0 ? (
            <div className="text-center py-10 border-2 border-dashed border-[#2D2D2D] rounded-lg" data-testid="wd-empty">
              <Receipt size={28} className="mx-auto text-[#2D2D2D]" />
              <p className="font-mono text-[10px] tracking-[0.25em] text-[#2D2D2D] mt-3">NO WITHDRAWALS YET</p>
              <p className="text-xs text-[#2D2D2D] mt-2">Cash out from the Wallet on your dashboard.</p>
            </div>
          ) : (
            <>
              <div className="oc-card oc-card-offset mb-4" style={{ background: "#BF00FF", color: "#fff", borderColor: "#000" }} data-testid="wd-total">
                <p className="font-mono text-[10px] tracking-[0.25em]">TOTAL WITHDRAWN</p>
                <p className="font-display text-3xl font-black mt-2">
                  ₹ {fmt(withdrawals.reduce((s, w) => s + (w.amount || 0), 0))}
                </p>
                <p className="font-mono text-[10px] mt-1 opacity-80">{withdrawals.length} TRANSACTIONS</p>
              </div>
              <ul className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                {withdrawals.map(w => (
                  <li key={w.withdrawal_id} className="border-2 border-black rounded-lg p-3 flex items-center gap-3"
                      data-testid={`wd-row-${w.withdrawal_id}`}>
                    <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
                         style={{ background: w.status === "COMPLETED" ? "#2CFF05" : "#2D2D2D",
                                  color: w.status === "COMPLETED" ? "#000" : "#fff" }}>
                      {w.status === "COMPLETED" ? <CheckCircle2 size={18} /> : <Clock size={18} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-display font-black text-lg">₹ {fmt(w.amount)}</p>
                      <p className="font-mono text-[10px] text-[#2D2D2D] tracking-[0.1em]">{fmtDate(w.created_at)}</p>
                      <p className="font-mono text-[9px] text-[#2D2D2D] truncate">{w.razorpay_payout_id}</p>
                    </div>
                    <span className="oc-chip flex-shrink-0"
                          style={{ background: w.status === "COMPLETED" ? "#000" : "#BF00FF",
                                   color: w.status === "COMPLETED" ? "#2CFF05" : "#fff" }}>
                      {w.status}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
