import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, Trophy, Megaphone, BookOpen, User, Settings, LogOut, MessageCircle,
         Menu, X, Wallet as WalletIcon, Users as UsersIcon, ShieldCheck } from "lucide-react";
import { Logo } from "@/components/Logo";
import { useAuth } from "@/contexts/AuthContext";

const editorNav = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard, tid: "nav-dashboard" },
  { to: "/app/campaigns", label: "Campaigns", icon: Megaphone, tid: "nav-campaigns" },
  { to: "/app/leaderboard", label: "Leaderboard", icon: Trophy, tid: "nav-leaderboard" },
  { to: "/app/resources", label: "Resources", icon: BookOpen, tid: "nav-resources" },
  { to: "/app/social-verification", label: "Social Verification", icon: ShieldCheck, tid: "nav-social-verification" },
  { to: "/app/profile", label: "Profile", icon: User, tid: "nav-profile" },
];

const creatorNav = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard, tid: "nav-dashboard" },
  { to: "/app/campaigns", label: "Campaigns", icon: Megaphone, tid: "nav-campaigns" },
  { to: "/app/talent", label: "Talent", icon: UsersIcon, tid: "nav-talent" },
  { to: "/app/wallet", label: "Wallet", icon: WalletIcon, tid: "nav-wallet" },
  { to: "/app/profile", label: "Profile", icon: User, tid: "nav-profile" },
];

const guestNav = [
  { to: "/app/campaigns", label: "Campaigns", icon: Megaphone, tid: "nav-campaigns" },
  { to: "/app/leaderboard", label: "Leaderboard", icon: Trophy, tid: "nav-leaderboard" },
  { action: "login", label: "Edit Profile", icon: User, tid: "nav-profile" },
];

export const Sidebar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const isEditor = user?.role === "EDITOR";
  const navItems = !user ? guestNav : (isEditor ? editorNav : creatorNav);

  const close = () => setOpen(false);

  return (
    <>
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 bg-black border-b-2 border-[#2D2D2D] flex items-center justify-between px-4 py-3"
           data-testid="mobile-topbar">
        <button onClick={() => navigate("/app/dashboard")} data-testid="mobile-logo"><Logo size={28} /></button>
        <button onClick={() => setOpen(true)} className="text-white p-2" data-testid="hamburger-btn"><Menu size={26} /></button>
      </div>
      <div className="md:hidden h-[58px]" aria-hidden />

      {open && <div className="md:hidden fixed inset-0 bg-black/70 z-40" onClick={close} data-testid="sidebar-overlay" />}

      <aside className={`bg-black text-white flex flex-col flex-shrink-0
                         fixed md:sticky top-0 left-0 z-50 w-72 md:w-64 h-screen
                         transition-transform duration-300
                         ${open ? "translate-x-0" : "-translate-x-full"} md:translate-x-0`}
             data-testid="sidebar">
        <div className="px-6 pt-7 pb-5 border-b border-[#2D2D2D] flex items-center justify-between flex-shrink-0">
          <button onClick={() => { navigate("/app/dashboard"); close(); }} data-testid="sidebar-logo">
            <Logo size={36} />
          </button>
          <button onClick={close} className="md:hidden text-white p-1" data-testid="sidebar-close"><X size={22} /></button>
        </div>
        <p className="px-6 font-mono text-[10px] tracking-[0.25em] text-gray-400 mt-3 flex-shrink-0">OUTPERFORM · CLIMB · EARN</p>
        <nav className="flex-1 px-3 py-5 space-y-1 overflow-y-auto">
          {navItems.map(({ to, label, icon: Icon, tid, action }) => {
            if (action === "login") {
              return (
                <button key={label} onClick={() => window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(window.location.origin + "/auth/callback")}`} className="oc-sidebar-link w-full text-left" data-testid={tid}>
                  <Icon size={18} strokeWidth={2.4} />
                  <span>{label}</span>
                </button>
              );
            }
            return (
              <NavLink key={to} to={to} end onClick={close} data-testid={tid}
                className={({ isActive }) => `oc-sidebar-link ${isActive ? "active" : ""}`}>
                <Icon size={18} strokeWidth={2.4} />
                <span>{label}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="px-3 pb-5 space-y-1 border-t border-[#2D2D2D] pt-4 flex-shrink-0">
          {user && (
            <NavLink to="/app/contact" onClick={close} data-testid="nav-contact"
              className={({ isActive }) => `oc-sidebar-link ${isActive ? "active" : ""}`}>
              <MessageCircle size={18} strokeWidth={2.4} /><span>Contact Us</span>
            </NavLink>
          )}
          {user && !isEditor && (
            <NavLink to="/app/settings" onClick={close} data-testid="nav-settings"
              className={({ isActive }) => `oc-sidebar-link ${isActive ? "active" : ""}`}>
              <Settings size={18} strokeWidth={2.4} /><span>Settings</span>
            </NavLink>
          )}
          {user ? (
            <button onClick={logout} className="oc-sidebar-link w-full text-left" data-testid="nav-logout">
              <LogOut size={18} strokeWidth={2.4} /><span>Log out</span>
            </button>
          ) : (
            <button onClick={() => window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(window.location.origin + "/auth/callback")}`} className="oc-sidebar-link w-full text-left" data-testid="nav-login">
              <User size={18} strokeWidth={2.4} /><span>Sign in</span>
            </button>
          )}
          {user && (
            <div className="mt-4 px-3 py-2 flex items-center gap-3 rounded-xl bg-[#2D2D2D]" data-testid="sidebar-user">
              <img src={user.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${user.name}`}
                   className="w-9 h-9 rounded-full border-2 border-[#2CFF05]" alt="" />
              <div className="min-w-0">
                <p className="text-sm font-semibold truncate">{user.name}</p>
                <p className="text-[10px] font-mono uppercase tracking-wider text-[#2CFF05]">{user.role || "NEW"}</p>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
