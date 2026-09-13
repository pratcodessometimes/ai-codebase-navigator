import React, { useEffect, useState } from "react";
import { listResources } from "@/lib/api";
import { BookOpen, Clock } from "lucide-react";

const palette = ["#2CFF05", "#BF00FF", "#2D2D2D"];

export default function Resources() {
  const [items, setItems] = useState([]);
  useEffect(() => { listResources().then(setItems); }, []);
  return (
    <div data-testid="resources-page">
      <header className="mb-8">
        <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">RESOURCES</p>
        <h1 className="font-display text-4xl md:text-5xl font-black mt-1">Improve your craft. Earn more.</h1>
      </header>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
        {items.map((r, i) => {
          const c = palette[i % 3];
          const fg = c === "#2CFF05" ? "#000" : "#fff";
          return (
            <div key={r.id} className="oc-card hover:translate-y-[-2px] transition-transform" data-testid={`res-${r.id}`}>
              <div className="oc-chip mb-3" style={{ background: c, color: fg }}>{r.category}</div>
              <BookOpen size={22} />
              <h3 className="font-display text-xl font-black mt-3 leading-tight">{r.title}</h3>
              <p className="text-sm mt-2 text-[#2D2D2D]">{r.summary}</p>
              <div className="mt-5 pt-4 border-t-2 border-black flex items-center justify-between">
                <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D] flex items-center gap-1"><Clock size={11}/> {r.read_minutes} MIN</span>
                <span className="oc-chip" style={{ background: "#000", color: "#2CFF05" }}>{r.tag}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
