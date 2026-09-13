import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { setRole } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Logo } from "@/components/Logo";
import { Scissors, Megaphone } from "lucide-react";

export default function Onboarding() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(null);

  const pick = async (role) => {
    setLoading(role);
    try {
      const u = await setRole(role);
      setUser(u);
      navigate("/app/dashboard");
    } finally { setLoading(null); }
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-6" data-testid="onboarding">
      <div className="max-w-4xl w-full">
        <Logo size={48} />
        <h1 className="font-display text-4xl md:text-5xl font-black mt-8">Who are you on Outclip?</h1>
        <p className="text-gray-400 mt-3 max-w-xl">Pick the role that matches what you'll do most. You can change this later in settings.</p>
        <div className="mt-10 grid md:grid-cols-2 gap-6">
          <button onClick={() => pick("EDITOR")} disabled={loading}
            data-testid="role-editor-btn"
            className="oc-card text-left" style={{ background: "#2CFF05", color: "#000" }}>
            <Scissors size={36} />
            <h2 className="font-display text-3xl font-black mt-4">I'm an Editor</h2>
            <p className="text-sm mt-2">Hunt bounties, submit clips, climb leaderboards, get paid by performance.</p>
            <p className="font-mono text-xs mt-6 tracking-[0.2em]">{loading === "EDITOR" ? "PICKING…" : "PICK EDITOR →"}</p>
          </button>
          <button onClick={() => pick("CREATOR")} disabled={loading}
            data-testid="role-creator-btn"
            className="oc-card text-left" style={{ background: "#BF00FF", color: "#fff" }}>
            <Megaphone size={36} />
            <h2 className="font-display text-3xl font-black mt-4">I'm a Creator</h2>
            <p className="text-sm mt-2">Post campaigns, fund escrow, source high-quality clips from a global editor pool.</p>
            <p className="font-mono text-xs mt-6 tracking-[0.2em]">{loading === "CREATOR" ? "PICKING…" : "PICK CREATOR →"}</p>
          </button>
        </div>
      </div>
    </div>
  );
}
