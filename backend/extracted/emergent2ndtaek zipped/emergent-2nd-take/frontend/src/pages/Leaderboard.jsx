import React, { useEffect, useState } from "react";
import { lbLifetime, lbMonthly } from "@/lib/api";
import { Trophy } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const fmt = (n) => Intl.NumberFormat("en-US").format(Math.round(n || 0));

export default function Leaderboard() {
  const { user } = useAuth();
  const [tab, setTab] = useState("LIFETIME");
  const [rows, setRows] = useState([]);

  useEffect(() => {
    (tab === "LIFETIME" ? lbLifetime() : lbMonthly()).then(setRows);
  }, [tab]);

  const top3 = rows.slice(0, 3);
  const rest = rows.slice(3);

  return (
    <div data-testid="leaderboard-page">
      <header className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <div>
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">LEADERBOARD</p>
          <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Who's climbing fastest.</h1>
        </div>
      </header>

      <div className="flex gap-2 mb-8">
        {["LIFETIME", "MONTHLY"].map(t => (
          <button key={t} onClick={() => setTab(t)} className={`oc-tab ${tab === t ? (t === "LIFETIME" ? "green active" : "purple active") : ""}`}
            data-testid={`lb-tab-${t}`}>{t}</button>
        ))}
      </div>

      {rows.length === 0 ? (
        <div className="oc-card text-center py-16">
          <Trophy size={36} className="mx-auto mb-3" />
          <p className="font-mono text-xs tracking-[0.2em]">NO RANKINGS YET</p>
        </div>
      ) : (
        <>
          {top3.length > 0 && (
            <div className="grid md:grid-cols-3 gap-5 mb-8">
              {top3.map((r, i) => {
                const palette = [{ bg: "#2CFF05", fg: "#000" }, { bg: "#BF00FF", fg: "#fff" }, { bg: "#2D2D2D", fg: "#fff" }][i];
                const pts = tab === "LIFETIME" ? r.lifetime_points : r.monthly_points;
                return (
                  <div key={r.editor.user_id} className="oc-card oc-card-offset" style={{ background: palette.bg, color: palette.fg }}
                    data-testid={`podium-${i + 1}`}>
                    <p className="font-display font-black text-5xl">#{r.rank}</p>
                    <div className="mt-4 flex items-center gap-3">
                      <img src={r.editor.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${r.editor.name}`} className="w-12 h-12 rounded-full border-2 border-black" alt="" />
                      <div className="min-w-0">
                        <p className="font-bold truncate">{r.editor.name}</p>
                        <p className="font-mono text-[10px] opacity-80 truncate">@{r.editor.username}</p>
                      </div>
                    </div>
                    <p className="font-display font-black text-3xl mt-4">{fmt(pts)} pts</p>
                  </div>
                );
              })}
            </div>
          )}
          <ol className="space-y-2">
            {rest.map(r => {
              const pts = tab === "LIFETIME" ? r.lifetime_points : r.monthly_points;
              const isMe = r.editor?.user_id === user?.user_id;
              return (
                <li key={r.editor.user_id} className="flex items-center gap-4 p-3 rounded-lg border-2 border-black"
                  style={{ background: isMe ? "#000" : "#fff", color: isMe ? "#2CFF05" : "#000" }} data-testid={`lb-${r.rank}`}>
                  <span className="font-display font-black text-2xl w-12">#{r.rank}</span>
                  <img src={r.editor.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${r.editor.name}`} className="w-9 h-9 rounded-full border-2 border-black" alt="" />
                  <div className="flex-1 min-w-0">
                    <p className="font-bold truncate">{r.editor.name} {isMe && <span className="font-mono text-[10px]">(YOU)</span>}</p>
                  </div>
                  <p className="font-display font-black text-lg">{fmt(pts)} pts</p>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </div>
  );
}
