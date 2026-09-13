import React, { useEffect, useState } from "react";
import { getEarnings, saveBankDetails } from "@/lib/api";
import { Wallet as WalletIcon, ArrowUpRight, Receipt, CheckCircle2, AlertCircle } from "lucide-react";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));
const fmtDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" }) +
         " · " + d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
};

export default function Earnings() {
  const [data, setData] = useState(null);
  const [bankForm, setBankForm] = useState({
    payout_method: "UPI",
    upi_id: "",
    bank_name: "",
    bank_account_number: "",
    bank_account_name: "",
    bank_ifsc: "",
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const load = async () => {
    try {
      const res = await getEarnings();
      setData(res);
      if (res) {
        setBankForm({
          payout_method: res.payout_method || "UPI",
          upi_id: res.upi_id || "",
          bank_name: res.bank_name || "",
          bank_account_number: res.bank_account_number || "",
          bank_account_name: res.bank_account_name || "",
          bank_ifsc: res.bank_ifsc || "",
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSaveBank = async (e) => {
    e.preventDefault();
    
    // Validation
    if (bankForm.payout_method === "UPI") {
      if (!bankForm.upi_id || !bankForm.upi_id.trim()) {
        setMessage({ err: true, text: "UPI cannot be blank." });
        return;
      }
    } else {
      if (!bankForm.bank_name || !bankForm.bank_name.trim()) {
        setMessage({ err: true, text: "Bank name is required." });
        return;
      }
      if (!bankForm.bank_account_name || !bankForm.bank_account_name.trim()) {
        setMessage({ err: true, text: "Account holder name is required." });
        return;
      }
      if (!bankForm.bank_account_number || !bankForm.bank_account_number.trim()) {
        setMessage({ err: true, text: "Account number cannot be blank." });
        return;
      }
      if (!bankForm.bank_ifsc || !bankForm.bank_ifsc.trim()) {
        setMessage({ err: true, text: "IFSC cannot be blank." });
        return;
      }
    }

    setSaving(true);
    setMessage(null);
    try {
      await saveBankDetails(bankForm);
      const successText = bankForm.payout_method === "UPI" ? "UPI details saved" : "Bank details saved";
      setMessage({ err: false, text: successText });
      await load();
    } catch (err) {
      setMessage({ err: true, text: err.response?.data?.detail || "Failed to save payout details." });
    } finally {
      setSaving(false);
    }
  };

  if (!data) return <p className="font-mono text-sm oc-pulse p-6">LOADING EARNINGS…</p>;

  return (
    <div data-testid="earnings-page" className="p-6 max-w-7xl mx-auto">
      <header className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <div>
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">MY FINANCES</p>
          <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Earnings dashboard.</h1>
        </div>
      </header>

      <div className="grid md:grid-cols-3 gap-6 mb-8">
        <div className="oc-card oc-card-offset" style={{ background: "#2CFF05", color: "#000", borderColor: "#000" }} data-testid="stat-paid-earnings">
          <CheckCircle2 size={18} />
          <p className="font-mono text-[10px] tracking-[0.25em] mt-3 opacity-80">PAID EARNINGS</p>
          <p className="font-display text-3xl font-black mt-1.5">₹ {fmt(data.paid_earnings)}</p>
        </div>

        <div className="oc-card oc-card-offset" style={{ background: "#BF00FF", color: "#fff", borderColor: "#000" }} data-testid="stat-pending-earnings">
          <AlertCircle size={18} />
          <p className="font-mono text-[10px] tracking-[0.25em] mt-3 opacity-80">PENDING SETTLEMENT</p>
          <p className="font-display text-3xl font-black mt-1.5">₹ {fmt(data.pending_earnings)}</p>
        </div>

        <div className="oc-card oc-card-offset" style={{ background: "#fff", color: "#000", borderColor: "#000" }} data-testid="stat-campaigns-joined">
          <WalletIcon size={18} />
          <p className="font-mono text-[10px] tracking-[0.25em] mt-3 opacity-80">TOTAL CAMPAIGNS</p>
          <p className="font-display text-3xl font-black mt-1.5">{data.history?.length || 0}</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 oc-card" data-testid="earnings-history">
          <h2 className="font-display text-2xl font-black mb-4">Payout history</h2>
          {(!data.history || data.history.length === 0) ? (
            <div className="text-center py-12 border-2 border-dashed border-[#2D2D2D] rounded-lg" data-testid="no-earnings-message">
              <Receipt size={32} className="mx-auto text-[#2D2D2D]" />
              <p className="font-display text-lg font-black mt-3">No earnings yet.</p>
              <p className="text-sm text-[#2D2D2D] mt-1">Join campaigns and submit clips to start earning.</p>
            </div>
          ) : (
            <ul className="space-y-3">
              {data.history.map((tx) => {
                const isPaid = tx.payout_status === "PAID";
                return (
                  <li key={tx.participation_id} className="border-2 border-black rounded-lg p-4 flex flex-wrap items-center justify-between gap-4" data-testid={`payout-item-${tx.participation_id}`}>
                    <div className="flex-1 min-w-[200px]">
                      <p className="font-display font-black text-lg leading-tight">{tx.campaign_title}</p>
                      <p className="font-mono text-[10px] text-[#2D2D2D] mt-1">Pool: ₹{fmt(tx.bounty_pool)}</p>
                      {tx.payment_reference && (
                        <p className="font-mono text-[10px] text-[#BF00FF] mt-0.5">UTR: {tx.payment_reference}</p>
                      )}
                      {tx.paid_at && (
                        <p className="font-mono text-[9px] text-[#2D2D2D] mt-0.5">{fmtDate(tx.paid_at)}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="font-display font-black text-xl">₹{fmt(tx.payout_amount)}</p>
                      <span
                        className="oc-chip mt-1 inline-block"
                        style={{
                          background: isPaid ? "#2CFF05" : "#BF00FF",
                          color: isPaid ? "#000" : "#fff",
                        }}
                      >
                        {tx.payout_status}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="oc-card" data-testid="bank-details-card">
          <h2 className="font-display text-2xl font-black mb-1">Payout details</h2>
          <p className="text-xs text-[#2D2D2D] mb-4">Payouts are manually wired directly upon campaign completion.</p>

          <form onSubmit={handleSaveBank} className="space-y-4 text-sm">
            <div>
              <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D] block mb-1">PAYOUT METHOD</span>
              <div className="flex gap-6 mb-2">
                <label className="flex items-center gap-2 cursor-pointer font-bold">
                  <input
                    type="radio"
                    name="payout_method"
                    value="UPI"
                    checked={bankForm.payout_method === "UPI"}
                    onChange={(e) => setBankForm({ ...bankForm, payout_method: e.target.value })}
                    className="w-4 h-4"
                    data-testid="payout-method-upi"
                  />
                  <span>UPI</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer font-bold">
                  <input
                    type="radio"
                    name="payout_method"
                    value="BANK"
                    checked={bankForm.payout_method === "BANK"}
                    onChange={(e) => setBankForm({ ...bankForm, payout_method: e.target.value })}
                    className="w-4 h-4"
                    data-testid="payout-method-bank"
                  />
                  <span>Bank Transfer</span>
                </label>
              </div>
            </div>

            {bankForm.payout_method === "UPI" ? (
              <>
                <p className="text-xs text-[#BF00FF] font-mono mb-2" data-testid="upi-helper-text">
                  💡 UPI is recommended for faster payouts.
                </p>
                <label className="block">
                  <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">UPI ID</span>
                  <input
                    type="text"
                    value={bankForm.upi_id}
                    onChange={(e) => setBankForm({ ...bankForm, upi_id: e.target.value })}
                    placeholder="e.g. editor@upi"
                    className="w-full mt-1 p-3 border-2 border-black rounded-lg font-bold font-mono"
                    data-testid="upi-id-input"
                  />
                </label>
              </>
            ) : (
              <>
                <label className="block">
                  <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">BANK NAME</span>
                  <input
                    type="text"
                    value={bankForm.bank_name}
                    onChange={(e) => setBankForm({ ...bankForm, bank_name: e.target.value })}
                    placeholder="e.g. HDFC Bank"
                    className="w-full mt-1 p-3 border-2 border-black rounded-lg font-bold"
                    data-testid="bank-name-input"
                  />
                </label>

                <label className="block">
                  <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">ACCOUNT HOLDER NAME</span>
                  <input
                    type="text"
                    value={bankForm.bank_account_name}
                    onChange={(e) => setBankForm({ ...bankForm, bank_account_name: e.target.value })}
                    placeholder="Name as in bank record"
                    className="w-full mt-1 p-3 border-2 border-black rounded-lg font-bold"
                    data-testid="bank-account-name-input"
                  />
                </label>

                <label className="block">
                  <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">ACCOUNT NUMBER</span>
                  <input
                    type="text"
                    value={bankForm.bank_account_number}
                    onChange={(e) => setBankForm({ ...bankForm, bank_account_number: e.target.value })}
                    placeholder="Account number"
                    className="w-full mt-1 p-3 border-2 border-black rounded-lg font-bold font-mono"
                    data-testid="bank-account-number-input"
                  />
                </label>

                <label className="block">
                  <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">IFSC CODE</span>
                  <input
                    type="text"
                    value={bankForm.bank_ifsc}
                    onChange={(e) => setBankForm({ ...bankForm, bank_ifsc: e.target.value })}
                    placeholder="IFSC code"
                    className="w-full mt-1 p-3 border-2 border-black rounded-lg font-bold font-mono"
                    data-testid="bank-ifsc-input"
                  />
                </label>
              </>
            )}

            <button type="submit" disabled={saving} className="oc-btn oc-btn-primary w-full" data-testid="save-bank-btn">
              {saving ? "Saving…" : "Save payout details"}
            </button>

            {message && (
              <p
                className={`font-mono text-[11px] tracking-[0.1em] mt-2 ${
                  message.err ? "text-[#BF00FF]" : "text-[#2CFF05] bg-black p-2 rounded text-center"
                }`}
                data-testid="bank-msg"
              >
                {message.text}
              </p>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
