import React, { useEffect, useState } from "react";
import { creatorWalletSummary, walletTransactions, addFunds } from "@/lib/api";
import { Plus, Wallet as WalletIcon, ArrowDownLeft, ArrowUpRight, RefreshCw, Receipt } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));
const fmtDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" }) +
         " · " + d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
};

const TX_META = {
  TOP_UP:           { Icon: ArrowDownLeft, color: "#2CFF05", label: "Top-up" },
  REFUND:           { Icon: ArrowDownLeft, color: "#2CFF05", label: "Refund" },
  CAMPAIGN_FUNDING: { Icon: ArrowUpRight,  color: "#BF00FF", label: "Campaign funding" },
  PAYOUT:           { Icon: ArrowUpRight,  color: "#BF00FF", label: "Editor payout" },
  PLATFORM_FEE:     { Icon: ArrowUpRight,  color: "#2D2D2D", label: "Platform fee" },
  PENALTY:          { Icon: ArrowUpRight,  color: "#2D2D2D", label: "Early-close penalty" },
};

export default function CreatorWallet() {
  const { refresh } = useAuth();
  const [summary, setSummary] = useState(null);
  const [txs, setTxs] = useState([]);
  const [filter, setFilter] = useState("ALL");
  const [showAdd, setShowAdd] = useState(false);

  const load = () => Promise.all([creatorWalletSummary().then(setSummary), walletTransactions().then(setTxs)]);
  useEffect(() => { load(); }, []);

  const filtered = filter === "ALL" ? txs : txs.filter(t => t.type === filter);

  if (!summary) return <p className="font-mono text-sm oc-pulse">LOADING…</p>;

  return (
    <div data-testid="creator-wallet-page">
      <header className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <div>
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">WALLET</p>
          <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Financial control.</h1>
        </div>
        <button onClick={() => setShowAdd(true)} className="oc-btn oc-btn-primary" data-testid="add-funds-btn">
          <Plus size={16}/> Add Funds
        </button>
      </header>

      <div className="grid md:grid-cols-4 gap-4 mb-8">
        <BigStat color="#2CFF05" fg="#000" label="WALLET BALANCE" value={`₹ ${fmt(summary.balance)}`} icon={WalletIcon} tid="stat-balance" />
        <BigStat color="#BF00FF" fg="#fff" label="CAMPAIGN SPEND" value={`₹ ${fmt(summary.total_spend)}`} icon={ArrowUpRight} tid="stat-spend" />
        <BigStat color="#2D2D2D" fg="#fff" label="IN ESCROW" value={`₹ ${fmt(summary.in_escrow)}`} icon={RefreshCw} tid="stat-escrow" />
        <BigStat color="#fff"    fg="#000" label="PENDING PAYOUTS" value={`₹ ${fmt(summary.pending_payouts)}`} icon={Receipt} tid="stat-pending" />
      </div>

      <div className="oc-card" data-testid="tx-history">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 className="font-display text-2xl font-black">Transaction history</h2>
          <div className="flex flex-wrap gap-2">
            {["ALL", "TOP_UP", "CAMPAIGN_FUNDING", "PAYOUT", "REFUND", "PLATFORM_FEE"].map(f => (
              <button key={f} onClick={() => setFilter(f)}
                      className={`oc-tab text-xs ${filter === f ? "active" : ""}`}
                      data-testid={`tx-filter-${f}`}>
                {f.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>
        {filtered.length === 0 ? (
          <div className="text-center py-12">
            <Receipt size={32} className="mx-auto text-[#2D2D2D]" />
            <p className="font-mono text-[10px] tracking-[0.25em] text-[#2D2D2D] mt-3">NO TRANSACTIONS YET</p>
          </div>
        ) : (
          <ul className="space-y-2">
            {filtered.map(tx => {
              const meta = TX_META[tx.type] || { Icon: Receipt, color: "#000", label: tx.type };
              const positive = tx.amount > 0;
              return (
                <li key={tx.tx_id} className="border-2 border-black rounded-lg p-3 flex items-center gap-3" data-testid={`tx-${tx.tx_id}`}>
                  <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                       style={{ background: meta.color, color: meta.color === "#2CFF05" ? "#000" : "#fff" }}>
                    <meta.Icon size={16} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-display font-black text-sm leading-tight">{meta.label}</p>
                    <p className="font-mono text-[10px] text-[#2D2D2D] truncate">{tx.description}</p>
                    <p className="font-mono text-[9px] text-[#2D2D2D] mt-0.5">{fmtDate(tx.created_at)}</p>
                  </div>
                  <p className="font-display font-black text-lg flex-shrink-0"
                     style={{ color: positive ? "#2CFF05" : "#000" }}>
                    {positive ? "+" : ""}₹{fmt(Math.abs(tx.amount))}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {showAdd && <AddFundsModal onClose={() => setShowAdd(false)} onDone={async () => { setShowAdd(false); await load(); await refresh(); }} />}
    </div>
  );
}

const BigStat = ({ color, fg, label, value, icon: Icon, tid }) => (
  <div className="oc-card oc-card-offset" style={{ background: color, color: fg, borderColor: "#000" }} data-testid={tid}>
    <Icon size={18} />
    <p className="font-mono text-[10px] tracking-[0.25em] mt-3 opacity-80">{label}</p>
    <p className="font-display text-3xl font-black mt-1.5">{value}</p>
  </div>
);

const AddFundsModal = ({ onClose, onDone }) => {
  const [amount, setAmount] = useState(5000);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!amount || amount <= 0) return;
    setBusy(true);
    try { await addFunds(Number(amount)); onDone(); }
    catch (e) { alert(e.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" data-testid="add-funds-modal">
      <div className="oc-card bg-white w-full max-w-md">
        <h2 className="font-display text-2xl font-black">Add funds to wallet</h2>
        <p className="text-sm text-[#2D2D2D] mt-2">Mock top-up — credits your balance instantly. Real Razorpay ships when keys are configured.</p>
        <label className="block mt-5">
          <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">AMOUNT (₹)</span>
          <input type="number" value={amount} onChange={e => setAmount(e.target.value)}
                 className="w-full mt-1 p-3 border-2 border-black rounded-lg font-display text-2xl font-black"
                 data-testid="add-amount" autoFocus />
        </label>
        <div className="flex flex-wrap gap-2 mt-3">
          {[1000, 5000, 10000, 25000, 50000].map(v => (
            <button key={v} onClick={() => setAmount(v)} className="oc-tab text-xs" data-testid={`preset-${v}`}>
              ₹{fmt(v)}
            </button>
          ))}
        </div>
        <div className="mt-6 flex gap-3 justify-end">
          <button onClick={onClose} className="oc-btn oc-btn-ghost" data-testid="add-cancel">Cancel</button>
          <button onClick={submit} disabled={busy || !amount} className="oc-btn oc-btn-primary" data-testid="add-confirm">
            {busy ? "Adding…" : `Add ₹${fmt(amount || 0)}`}
          </button>
        </div>
      </div>
    </div>
  );
};
