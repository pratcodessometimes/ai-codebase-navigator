import React from "react";

export default function Resources() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6" data-testid="resources-page">
      <h1 className="font-display text-4xl md:text-5xl font-black text-center mb-4">Resources are on the way.</h1>
      <p className="text-lg text-center max-w-2xl mb-8">
        We're building creator guides, editing tutorials, growth strategies, and platform insights to help you succeed.
        Check back soon for polished, launch‑ready content.
      </p>
      <div className="oc-card w-full max-w-md p-6 text-center">
        <h2 className="font-display text-2xl font-bold mb-2">Coming Soon</h2>
        <p className="text-sm text-[#2D2D2D]">Stay tuned – exciting resources are on their way!</p>
      </div>
    </div>
  );
}
