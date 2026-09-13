import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { authSession } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Logo } from "@/components/Logo";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser, refresh } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const hash = window.location.hash || "";
    const m = hash.match(/session_id=([^&]+)/);
    if (!m) { navigate("/"); return; }
    const sid = m[1];
    (async () => {
      try {
          const user = await authSession(sid);
          setUser(user);
          console.log('AuthCallback: user fetched', user);
          // clear hash
          window.history.replaceState({}, "", window.location.pathname);
          await refresh();
          // Navigate to dashboard (new users default to EDITOR)
          navigate('/app/dashboard');
      } catch (e) {
        console.error(e);
        navigate("/");
      }
    })();
  }, [navigate, setUser, refresh]);

  return (
    <div className="min-h-screen bg-black flex items-center justify-center" data-testid="auth-callback">
      <div className="text-center">
        <Logo size={64} />
        <p className="mt-6 font-mono text-xs tracking-[0.3em] text-[#2CFF05] oc-pulse">SIGNING YOU IN…</p>
      </div>
    </div>
  );
}
