import React, { useState } from "react";
import { submitCreatorApplication } from "@/lib/api";

export default function CreatorApply() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    youtube: "",
    instagram: "",
    tiktok: "",
    twitter: "",
    linkedin: "",
    website: "",
    content_type: "",
    how_heard_about_us: ""
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const login = () => {
    const redirectUrl = window.location.origin + "/auth/callback";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await submitCreatorApplication(form);
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to submit application");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-6" data-testid="creator-apply-success">
        <div className="max-w-md w-full text-center">
          <h1 className="font-display text-4xl font-black mb-4">Application submitted successfully.</h1>
          <p className="text-gray-400 mb-8">Our team will review your profile and contact you if approved.</p>
          <a href="/" className="oc-btn oc-btn-secondary inline-block" data-testid="return-home-btn">Return Home</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white py-12 px-6" data-testid="creator-apply-page">
      <div className="max-w-xl mx-auto">
        <a href="/" className="font-mono text-xs tracking-[0.2em] text-[#2D2D2D] hover:text-[#2CFF05] mb-8 inline-block" data-testid="back-to-home">
          ← BACK TO HOME
        </a>
        <h1 className="font-display text-4xl md:text-5xl font-black mb-2">Apply as Creator</h1>
        <p className="text-gray-400 mb-6">Join the merit-based bounty marketplace and start sourcing the best clips for your content.</p>
        
        <p className="mb-8 font-mono text-sm">
          <button onClick={login} className="text-[#2CFF05] hover:underline" data-testid="already-creator-signin">Already an approved creator? Sign in</button>
        </p>

        {error && <div className="bg-red-500/20 border border-red-500 text-red-200 p-3 mb-6 text-sm">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono tracking-widest text-gray-400 mb-2">FULL NAME *</label>
            <input
  required
  type="text"
  className="oc-input w-full"
  style={{
    color: "black",
    backgroundColor: "white",
    WebkitTextFillColor: "black"
  }}
  value={form.name} onChange={e => setForm({...form, name: e.target.value})} data-testid="apply-name" />
          </div>
          <div>
            <label className="block text-xs font-mono tracking-widest text-gray-400 mb-2">EMAIL ADDRESS *</label>
            <input required type="email" className="oc-input w-full"style={{
  color: "black",
  backgroundColor: "white",
  WebkitTextFillColor: "black"
}} value={form.email} onChange={e => setForm({...form, email: e.target.value})} data-testid="apply-email" />
          </div>
          <div>
            <label className="block text-xs font-mono tracking-widest text-gray-400 mb-2">CONTENT TYPE / NICHE *</label>
            <input required type="text" className="oc-input w-full" placeholder="e.g. Gaming, Podcasts, IRL" value={form.content_type} onChange={e => setForm({...form, content_type: e.target.value})} data-testid="apply-content-type" />
          </div>
          
          <div className="pt-4 border-t border-[#2D2D2D]">
            <label className="block text-xs font-mono tracking-widest text-gray-400 mb-4">SOCIAL LINKS (Provide at least one)</label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input type="url" className="oc-input w-full" placeholder="YouTube URL" value={form.youtube} onChange={e => setForm({...form, youtube: e.target.value})} data-testid="apply-youtube" />
              <input type="url" className="oc-input w-full" placeholder="Instagram URL" value={form.instagram} onChange={e => setForm({...form, instagram: e.target.value})} data-testid="apply-instagram" />
              <input type="url" className="oc-input w-full" placeholder="TikTok URL" value={form.tiktok} onChange={e => setForm({...form, tiktok: e.target.value})} data-testid="apply-tiktok" />
              <input type="url" className="oc-input w-full" placeholder="Twitter/X URL" value={form.twitter} onChange={e => setForm({...form, twitter: e.target.value})} data-testid="apply-twitter" />
              <input type="url" className="oc-input w-full" placeholder="LinkedIn URL" value={form.linkedin} onChange={e => setForm({...form, linkedin: e.target.value})} data-testid="apply-linkedin" />
              <input type="url" className="oc-input w-full" placeholder="Personal Website" value={form.website} onChange={e => setForm({...form, website: e.target.value})} data-testid="apply-website" />
            </div>
          </div>

          <div className="pt-4 border-t border-[#2D2D2D]">
            <label className="block text-xs font-mono tracking-widest text-gray-400 mb-2">HOW DID YOU HEAR ABOUT US?</label>
            <input type="text" className="oc-input w-full" value={form.how_heard_about_us} onChange={e => setForm({...form, how_heard_about_us: e.target.value})} data-testid="apply-how-heard" />
          </div>

          <div className="pt-4">
            <button type="submit" disabled={loading} className="oc-btn oc-btn-primary w-full justify-center" data-testid="apply-submit">
              {loading ? "SUBMITTING..." : "SUBMIT APPLICATION"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
