import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { AppLayout } from "@/components/layout/AppLayout";
import Landing from "@/pages/Landing";
import AuthCallback from "@/pages/AuthCallback";
import DashboardRouter from "@/pages/DashboardRouter";
import CampaignsRouter from "@/pages/CampaignsRouter";
import CampaignDetail from "@/pages/CampaignDetail";
import CampaignSubmissions from "@/pages/CampaignSubmissions";
import CreateCampaign from "@/pages/CreateCampaign";
import Leaderboard from "@/pages/Leaderboard";
import Resources from "@/pages/Resources";
import Profile, { PublicProfile } from "@/pages/Profile";
import ContactUs from "@/pages/ContactUs";
import AdminDashboard from "@/pages/AdminDashboard";
import Talent from "@/pages/Talent";
import Earnings from "@/pages/Earnings";
import CreatorApply from "@/pages/CreatorApply";
import SocialVerification from "@/pages/SocialVerification";
import "@/App.css";

const Protected = ({ children, role, state }) => {
  const { user, loading } = useAuth();
  if (loading) return <p className="font-mono text-sm p-10">LOADING…</p>;
  if (!user) return <Navigate to="/" replace state={state} />;
  // No role redirect; new users default to EDITOR
  if (role && user.role !== role && user.role !== "ADMIN") return <Navigate to="/app/dashboard" replace />;
  return children;
};

function Router() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/u/:username" element={<PublicProfile />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
  {/* Onboarding route removed */}
      <Route path="/creator-apply" element={<CreatorApply />} />
      
      {/* Public App Routes */}
      <Route path="/app/campaigns"     element={<AppLayout><CampaignsRouter /></AppLayout>} />
      <Route path="/app/campaigns/:id" element={<AppLayout><CampaignDetail /></AppLayout>} />
      <Route path="/app/campaigns/:id/submissions" element={<AppLayout><CampaignSubmissions /></AppLayout>} />
      <Route path="/app/leaderboard"   element={<AppLayout><Leaderboard /></AppLayout>} />

      {/* Protected App Routes */}
      <Route path="/app/dashboard"     element={<Protected state={{ fromDashboard: true }}><AppLayout><DashboardRouter /></AppLayout></Protected>} />
      <Route path="/app/campaigns/new" element={<Protected role="CREATOR"><AppLayout><CreateCampaign /></AppLayout></Protected>} />
      <Route path="/app/resources"     element={<Protected><AppLayout><Resources /></AppLayout></Protected>} />
      <Route path="/app/talent"        element={<Protected role="CREATOR"><AppLayout><Talent /></AppLayout></Protected>} />
      <Route path="/app/earnings"      element={<Protected role="EDITOR"><AppLayout><Earnings /></AppLayout></Protected>} />
      <Route path="/app/profile"       element={<Protected><AppLayout><Profile /></AppLayout></Protected>} />
      <Route path="/app/contact"       element={<Protected><AppLayout><ContactUs /></AppLayout></Protected>} />
      <Route path="/app/social-verification" element={<Protected><AppLayout><SocialVerification /></AppLayout></Protected>} />
      <Route path="/admin" element={<Navigate to="/app/admin" replace />} />
      <Route path="/app/admin" element={<Protected role="ADMIN"><AppLayout><AdminDashboard /></AppLayout></Protected>} />
      
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}



export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Router />
      </AuthProvider>
    </BrowserRouter>
  );
}


