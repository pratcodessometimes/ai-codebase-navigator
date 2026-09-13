import React from "react";
import { useAuth } from "@/contexts/AuthContext";
import EditorCampaigns from "@/pages/Campaigns";
import CreatorCampaigns from "@/pages/CreatorCampaigns";

export default function CampaignsRouter() {
  const { user } = useAuth();
  if (user?.role === "CREATOR") return <CreatorCampaigns />;
  return <EditorCampaigns />;
}
