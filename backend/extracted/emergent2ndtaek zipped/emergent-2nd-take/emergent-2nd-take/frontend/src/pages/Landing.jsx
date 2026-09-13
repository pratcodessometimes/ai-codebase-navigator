import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Logo } from "@/components/Logo";
import { ArrowRight, Coins, Sparkles, Megaphone, Twitter, Instagram, MessageCircle, Mail, Globe } from "lucide-react";
import { listCampaigns } from "@/lib/api";

// Dynamic live ticker: fetch up to 3 active campaigns from the backend

const SOCIALS = [
  { Icon: Twitter, label: "Twitter / X", href: "https://twitter.com" },
  { Icon: Instagram, label: "Instagram", href: "https://instagram.com" },
  { Icon: MessageCircle, label: "Discord", href: "https://discord.com" },
  { Icon: Mail, label: "Email", href: "mailto:hello@outclip.io" },
  { Icon: Globe, label: "Website", href: "#" },
];

export default function Landing() {
  const location = useLocation();
  const navigate = useNavigate();
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const login = () => {
    const redirectUrl = window.location.origin + "/auth/callback";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const [liveCampaigns, setLiveCampaigns] = useState([]);

useEffect(() => {
  // Fetch active campaigns (status = ACTIVE)
  listCampaigns({ status: "ACTIVE" }).then((data) => {
    // Ensure we have an array
    const campaigns = Array.isArray(data) ? data : [];
    setLiveCampaigns(campaigns);
  });
}, []);

// Build ticker items based on the number of active campaigns
const ticker = (() => {
  const count = liveCampaigns.length;
  if (count === 0) {
    return [{ name: "Campaigns launching soon.", bounty: 0 }];
  }
  if (count === 1) {
    return [
      { name: liveCampaigns[0].title, bounty: liveCampaigns[0].bounty_pool },
      { name: "More campaigns coming soon.", bounty: 0 },
      { name: "More campaigns coming soon.", bounty: 0 },
    ];
  }
  if (count === 2) {
    return [
      { name: liveCampaigns[0].title, bounty: liveCampaigns[0].bounty_pool },
      { name: liveCampaigns[1].title, bounty: liveCampaigns[1].bounty_pool },
      { name: "More campaigns coming soon.", bounty: 0 },
    ];
  }
  // 3 or more
  return liveCampaigns.slice(0, 3).map(c => ({ name: c.title, bounty: c.bounty_pool }));
})();

  return (
    <div className="min-h-screen bg-black text-white overflow-x-hidden" data-testid="landing-page">
      {location.state?.fromDashboard && (
        <div className="bg-[#BF00FF] text-white font-mono text-xs tracking-[0.1em] text-center py-2 px-4 uppercase" data-testid="dashboard-cta">
          Sign in to access your dashboard
        </div>
      )}
      {/* nav */}
      <header className="max-w-7xl mx-auto px-6 md:px-10 py-6 flex items-center justify-between">
        <Logo size={40} />
        <button onClick={login} className="oc-btn oc-btn-primary" data-testid="header-login-btn">
          Sign in with Google <ArrowRight size={16} />
        </button>
      </header>

      {/* hero */}
      <section className="max-w-7xl mx-auto px-6 md:px-10 pt-14 pb-10">
        <div className="max-w-4xl">
          <span className="oc-chip" style={{ background: "#2CFF05", color: "#000" }}>MERIT-BASED · NO GATEKEEPERS</span>
          <h1 className="font-display font-black text-5xl sm:text-6xl lg:text-7xl mt-6 leading-[0.95]">
            Outperform.<br/>
            <span className="text-[#2CFF05]">Climb.</span><br/>
            <span className="text-[#BF00FF]">Earn.</span>
          </h1>
          <p className="mt-6 text-lg text-gray-300 max-w-xl">
            The first bounty marketplace for short-form video editors where pay is a pure
            function of performance. Views × Retention × Engagement × Hit Multiplier.
            That's it.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button onClick={() => navigate("/app/campaigns")} className="oc-btn oc-btn-primary" data-testid="hero-login-btn">
              Start earning <ArrowRight size={16} />
            </button>
            <button onClick={() => navigate("/creator-apply")} className="oc-btn oc-btn-secondary" data-testid="hero-creator-btn">
              Create Campaign
            </button>
          </div>
        </div>
      </section>

      {/* live ticker */}
      <section className="border-y-2 border-[#2D2D2D] bg-black" data-testid="live-ticker">
        <div className="flex items-stretch">
          <div className="flex items-center gap-2 px-5 py-4 bg-[#2CFF05] text-black font-mono text-xs tracking-[0.25em] flex-shrink-0 border-r-2 border-black z-10">
            <span className="oc-live-dot" />
            LIVE
          </div>
          <div className="flex-1 overflow-hidden relative">
            <div className="oc-ticker-track flex gap-8 py-4 px-6 whitespace-nowrap">
              {ticker.map((c, i) => (
                <span key={i} className="font-mono text-sm tracking-wider text-white" data-testid={`ticker-item-${i}`}>
                  {c.name} <span className="text-[#2CFF05] font-bold">${c.bounty.toLocaleString()}</span>
                  <span className="text-[#2D2D2D] ml-8">|</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* how */}
      <section className="bg-white text-black py-20" data-testid="how-section">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">HOW IT WORKS</p>
          <h2 className="font-display text-4xl md:text-5xl font-black mt-3">A formula, not an opinion.</h2>
          <div className="mt-12 grid md:grid-cols-3 gap-6">
            {[
              { icon: Megaphone, color: "#2CFF05", title: "Creators post a bounty", body: "Set a pool, drop source video links from Drive, pick guidelines. Escrow funds instantly." },
              { icon: Sparkles, color: "#BF00FF", title: "Editors compete", body: "Submit unlimited clips. Every view, retention point and engagement % gets weighed and scored." },
              { icon: Coins, color: "#2D2D2D", title: "Pool splits by performance", body: "Reward = your OCV ÷ campaign OCV × pool. Hit a million? +50% multiplier on top." },
            ].map((s, i) => (
              <div key={i} className="oc-card" style={{ background: s.color, color: s.color === "#2D2D2D" ? "#fff" : (s.color === "#2CFF05" ? "#000" : "#fff") }}>
                <s.icon size={28} />
                <h3 className="font-display text-2xl font-black mt-4">{s.title}</h3>
                <p className="text-sm mt-2 opacity-90">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* footer cta */}
      <section className="bg-black py-24 text-center">
        <h2 className="font-display text-4xl md:text-6xl font-black px-6">
          Start <span className="text-[#2CFF05]">Outclipping</span> Today
        </h2>
        <p className="text-gray-400 mt-4 max-w-xl mx-auto">No favouritism. No gatekeepers. Just throughput.</p>
        <button onClick={login} className="oc-btn oc-btn-primary mt-8" data-testid="footer-login-btn">
          Get in <ArrowRight size={16} />
        </button>
      </section>

      {/* socials */}
      <section className="bg-black pt-16 pb-12 border-t-2 border-[#2D2D2D]" data-testid="socials-section">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">FOLLOW · CONNECT · BUILD</p>
          <h3 className="font-display text-3xl md:text-4xl font-black mt-3 text-white">Stay in the loop.</h3>
          <div className="mt-8 grid grid-cols-2 md:grid-cols-5 gap-4">
            {SOCIALS.map(({ Icon, label, href }) => (
              <a key={label} href={href} target="_blank" rel="noreferrer"
                 className="oc-card border-2 border-[#2D2D2D] hover:border-[#2CFF05] transition-colors group bg-black"
                 data-testid={`social-${label.toLowerCase().replace(/[^a-z]/g, "")}`}>
                <Icon size={24} className="text-[#2CFF05] group-hover:scale-110 transition-transform" />
                <p className="font-mono text-xs tracking-[0.15em] text-white mt-3">{label.toUpperCase()}</p>
              </a>
            ))}
          </div>
          <p className="text-xs text-gray-600 mt-14 font-mono">© OUTCLIPPED · OUTPERFORM. CLIMB. EARN.</p>
        </div>
      </section>

      <style>{`
        @keyframes oc-ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        .oc-ticker-track { animation: oc-ticker 38s linear infinite; width: max-content; }
        @keyframes oc-blink { 0%,100%{opacity:1} 50%{opacity:.25} }
        .oc-live-dot { width:10px; height:10px; border-radius:50%; background:#FF0033; animation: oc-blink 1s ease-in-out infinite; box-shadow: 0 0 8px #FF0033; }
      `}</style>
    </div>
  );
}
