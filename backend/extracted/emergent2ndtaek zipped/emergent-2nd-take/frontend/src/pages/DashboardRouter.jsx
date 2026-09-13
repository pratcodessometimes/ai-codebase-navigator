import React from "react";
import { useAuth } from "@/contexts/AuthContext";
import EditorDashboard from "@/pages/Dashboard";
import CreatorDashboard from "@/pages/CreatorDashboard";

export default function DashboardRouter() {
  const { user } = useAuth();
  if (user?.role === "CREATOR") return <CreatorDashboard />;
  return <EditorDashboard />;
}
