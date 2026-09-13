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
export const adminSetCampaignStatus = (id, status) => api.post(`/admin/campaigns/${id}/status`, { status }).then(r => r.data);
export const adminVerifyFunding = (id) => api.post(`/admin/campaigns/${id}/verify-funding`).then(r => r.data);
export const adminStartSettlement = (id) => api.post(`/admin/campaigns/${id}/start-settlement`).then(r => r.data);
export const adminPayEditor = (partId, payment_reference) => api.post(`/admin/participations/${partId}/pay`, { payment_reference }).then(r => r.data);
export const adminGetPendingCampaigns = () => api.get("/admin/pending-campaigns").then(r => r.data);
export const adminApprovalDecision = (id, decision) => api.post(`/admin/campaigns/${id}/approval-decision`, { decision }).then(r => r.data);
export const saveBankDetails = (data) => api.post("/profile/bank-details", data).then(r => r.data);
export const getEarnings = () => api.get("/earnings").then(r => r.data);
export const joinCampaign = (id, youtube_channel) => api.post(`/campaigns/${id}/join`, { youtube_channel }).then(r => r.data);
export const submitShort = (id, short_url) => api.post(`/campaigns/${id}/submit-short`, { short_url }).then(r => r.data);

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

// Wallet and Admin
export const cashout = (amount) => api.post("/wallet/cashout", { amount }).then(r => r.data);
export const getWithdrawals = () => api.get("/wallet/withdrawals").then(r => r.data);
export const adminGetOverview = () => api.get("/admin/overview").then(r => r.data);
export const adminGetCreators = () => api.get("/admin/creators").then(r => r.data);
export const adminGetEditors = () => api.get("/admin/editors").then(r => r.data);
export const adminSuspendUser = (userId) => api.post(`/admin/users/${userId}/suspend`).then(r => r.data);
export const adminListWithdrawalRequests = (status) => api.get("/admin/withdrawal-requests", { params: { status } }).then(r => r.data);
export const adminSetWithdrawalStatus = (requestId, status) => api.post(`/admin/withdrawal-requests/${requestId}/status`, { status }).then(r => r.data);
export const adminListAllCampaigns = (status) => api.get("/admin/campaigns", { params: { status } }).then(r => r.data);


