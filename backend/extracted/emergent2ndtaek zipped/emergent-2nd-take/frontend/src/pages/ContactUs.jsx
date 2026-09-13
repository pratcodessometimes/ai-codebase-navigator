import React, { useState } from "react";
import { Twitter, Instagram, MessageCircle, Mail, Globe, ExternalLink, Send } from "lucide-react";

// Outclip official contact channels
const SOCIALS = [
  { Icon: Twitter,        label: "Twitter / X", handle: "@outclip",       href: "https://twitter.com/outclip" },
  { Icon: Instagram,      label: "Instagram",   handle: "@outclip",       href: "https://instagram.com/outclip" },
  { Icon: MessageCircle,  label: "Discord",     handle: "Join the server",href: "https://discord.gg/outclip" },
  { Icon: Mail,           label: "Email",       handle: "hello@outclip.io",href:"mailto:hello@outclip.io" },
  { Icon: Globe,          label: "Website",     handle: "outclip.io",     href: "https://outclip.io" },
];

export default function ContactUs() {
  const [form, setForm] = useState({ subject: "", message: "" });
  const [sent, setSent] = useState(false);

  const send = () => {
    if (!form.subject || !form.message) return;
    const body = encodeURIComponent(form.message + "\n\n— sent from Outclip Contact form");
    const subject = encodeURIComponent(form.subject);
    window.location.href = `mailto:hello@outclip.io?subject=${subject}&body=${body}`;
    setSent(true);
    setTimeout(() => setSent(false), 3000);
  };

  return (
    <div data-testid="contact-page">
      <header className="mb-8">
        <p className="font-mono text-xs tracking-[0.3em] text-[#2D2D2D]">CONTACT US</p>
        <h1 className="font-display text-4xl md:text-5xl font-black mt-1">We're listening.</h1>
        <p className="text-[#2D2D2D] mt-3 max-w-2xl">
          Hit us up on any of the channels below or shoot us a message. We typically reply within 24 hours on weekdays.
        </p>
      </header>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* socials list */}
        <section className="lg:col-span-3" data-testid="contact-socials">
          <h2 className="font-display text-2xl font-black mb-4">Official channels</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {SOCIALS.map(({ Icon, label, handle, href }) => (
              <a key={label} href={href} target="_blank" rel="noreferrer"
                 className="oc-card group flex items-center gap-4 hover:bg-[#2CFF05] hover:border-black transition-colors"
                 data-testid={`contact-${label.toLowerCase().replace(/[^a-z]/g, "")}`}>
                <div className="w-12 h-12 rounded-full bg-black text-[#2CFF05] flex items-center justify-center flex-shrink-0 group-hover:bg-white group-hover:text-black transition-colors">
                  <Icon size={22} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-display font-black text-lg leading-tight">{label}</p>
                  <p className="font-mono text-xs text-[#2D2D2D] truncate group-hover:text-black">{handle}</p>
                </div>
                <ExternalLink size={16} className="opacity-50 group-hover:opacity-100" />
              </a>
            ))}
          </div>
        </section>

        {/* quick message form */}
        <section className="lg:col-span-2" data-testid="contact-form">
          <h2 className="font-display text-2xl font-black mb-4">Drop a message</h2>
          <div className="oc-card space-y-4">
            <label className="block">
              <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">SUBJECT</span>
              <input value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })}
                     placeholder="What's this about?"
                     className="w-full mt-1 p-3 border-2 border-black rounded-lg" data-testid="contact-subject" />
            </label>
            <label className="block">
              <span className="font-mono text-[10px] tracking-[0.2em] text-[#2D2D2D]">MESSAGE</span>
              <textarea rows={6} value={form.message} onChange={e => setForm({ ...form, message: e.target.value })}
                        placeholder="Tell us more…"
                        className="w-full mt-1 p-3 border-2 border-black rounded-lg" data-testid="contact-message" />
            </label>
            <button onClick={send} disabled={!form.subject || !form.message}
                    className="oc-btn oc-btn-primary w-full" data-testid="contact-send">
              <Send size={16}/> {sent ? "Opened your email…" : "Send via email"}
            </button>
            <p className="font-mono text-[10px] tracking-[0.15em] text-[#2D2D2D] text-center">
              OPENS YOUR DEFAULT EMAIL APP → HELLO@OUTCLIP.IO
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
