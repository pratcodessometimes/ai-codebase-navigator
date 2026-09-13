import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// Auth
export const authMe = () => api.get("/auth/me").then(r => r.data);
export const authSession = (session_id) => api.post("/auth/session", { session_id }).then(r => r.data);
export const authLogout = () => api.post("/auth/logout").then(r => r.data);
export const setRole = (role) => api.post("/auth/set-role", { role }).then(r => r.data);
export const updateProfile = (data) => api.put("/auth/profile", data).then(r => r.data);

// Dashboard
export const getDashboard = () => api.get("/dashboard").then(r => r.data);

// Campaigns
export const listCampaigns = (params = {}) => api.get("/campaigns", { params }).then(r => r.data);
export const getCampaign = (id) => api.get(`/campaigns/${id}`).then(r => r.data);
export const createCampaign = (data) => api.post("/campaigns", data).then(r => r.data);
export const publishCampaign = (id) => api.post(`/campaigns/${id}/publish`).then(r => r.data);
export const cancelCampaign = (id) => api.post(`/campaigns/${id}/cancel`).then(r => r.data);
export const approvePayout = (id) => api.post(`/campaigns/${id}/approve-payout`).then(r => r.data);
export const joinCampaign = (id, youtube_channel) => api.post(`/campaigns/${id}/join`, { youtube_channel }).then(r => r.data);
export const submitShort = (id, short_url) => api.post(`/campaigns/${id}/submit-short`, { short_url }).then(r => r.data);
export const deleteSubmission = (campaignId, clipId) => api.delete(`/campaigns/${campaignId}/submit-short/${clipId}`).then(r => r.data);

// Clips
export const submitClip = (data) => api.post("/clips", data).then(r => r.data);
export const listClips = (params) => api.get("/clips", { params }).then(r => r.data);
export const ytFetch = (clip_url) => api.post("/youtube/fetch", { clip_url }).then(r => r.data);

// Leaderboard
export const lbCampaign = (id) => api.get(`/leaderboard/campaign/${id}`).then(r => r.data);
export const lbLifetime = () => api.get("/leaderboard/lifetime").then(r => r.data);
export const lbMonthly = () => api.get("/leaderboard/monthly").then(r => r.data);

// Resources / profile
export const listResources = () => api.get("/resources").then(r => r.data);
export const getUser = (id) => api.get(`/users/${id}`).then(r => r.data);
export const getMyFullProfile = () => api.get("/profile/me/full").then(r => r.data);
export const getProfileByUsername = (u) => api.get(`/profile/by-username/${u}`).then(r => r.data);
export const addFeaturedClip = (data) => api.post("/profile/featured-clips", data).then(r => r.data);
export const removeFeaturedClip = (clipId) => api.delete(`/profile/featured-clips/${clipId}`).then(r => r.data);

// Creator Application
export const submitCreatorApplication = (data) => api.post("/creator/apply", data).then(r => r.data);

// Upload
export const uploadFile = (file) => {
  const fd = new FormData(); fd.append("file", file);
  return api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
};

// Wallet
export const cashout = (amount) => api.post("/wallet/cashout", { amount }).then(r => r.data);
export const listWithdrawals = () => api.get("/wallet/withdrawals").then(r => r.data);
export const addFunds = (amount) => api.post("/wallet/add-funds", { amount }).then(r => r.data);
export const walletTransactions = () => api.get("/wallet/transactions").then(r => r.data);
export const creatorWalletSummary = () => api.get("/wallet/creator-summary").then(r => r.data);

// Creator
export const creatorDashboard = () => api.get("/dashboard/creator").then(r => r.data);
export const cloneCampaign = (id) => api.post(`/campaigns/${id}/clone`).then(r => r.data);

// Talent
export const listTalent = (params = {}) => api.get("/talent", { params }).then(r => r.data);

// Social Verification
export const getVerifiedChannels = () => api.get("/social/verified-channels").then(r => r.data);
export const startYoutubeVerification = (youtube_channel) => api.post("/social/start-youtube-verification", { youtube_channel }).then(r => r.data);
export const verifyYoutube = (youtube_channel) => api.post("/social/verify-youtube", { youtube_channel }).then(r => r.data);
export const removeVerifiedChannel = (channelId) => api.delete(`/social/verified-channels/${channelId}`).then(r => r.data);
export const getVerificationStatus = () => api.get("/social/verification-status").then(r => r.data);

