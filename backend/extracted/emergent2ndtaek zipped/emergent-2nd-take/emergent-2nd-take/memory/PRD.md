# Outclip – PRD & Progress

## Original Problem Statement
Build Outclip — a merit-based bounty marketplace for short-form video editors. Creators post campaigns with bounty pools; editors compete by submitting clips; reward is distributed by transparent points formula (Views × Retention × Engagement × Hit Multiplier).
Color scheme is strict: #000000, #2CFF05, #BF00FF, #2D2D2D (and white). Reference dashboard UI provided for visual balance.

## Adapted Stack (vs TRD)
- Frontend: React 19 + React Router + Tailwind + shadcn (instead of Next.js)
- Backend: FastAPI + Motor/MongoDB (instead of tRPC + Prisma + Postgres)
- Auth: Emergent Google OAuth (instead of Clerk)
- File Storage: Emergent Object Storage (instead of Cloudflare R2)
- Payments: MOCKED escrow + payouts (Razorpay deferred)
- Source videos: Google Drive link field
- Analytics: Manual entry + YouTube Data API v3 auto-fetch (when YOUTUBE_API_KEY set)
- Email/Resend: deferred (in-app only)

## User Personas
- Editor (16-28 yo, TikTok/YT/Reels native) → earn from clips
- Creator (YouTuber/streamer) → source clips affordably
- Admin → deferred for MVP+

## Built (Feb 2026)
- Auth: Google OAuth landing, AuthCallback, Onboarding (role pick), `/api/auth/{session,me,logout,set-role,profile}`
- Dashboard: role-aware (Editor stats + chart + active campaigns; Creator stats + my campaigns + top editors)
- Campaigns: list with filters/sort (status, content, sort_by, mine), detail w/ tabs (Overview/Clips/Leaderboard), 4-step creation wizard (Details → Budget → Source Drive links → Review), Publish (mock escrow), Cancel, Approve payout (mock distribution)
- Clips: Submit modal with YouTube auto-fetch (views/engagement), screenshot upload to Object Storage, full points engine
- Leaderboards: Campaign / Lifetime / Monthly with podium top-3 (green/purple/dark)
- Resources: 8-card static library
- Profile + Settings (username, bio, UPI, public earnings toggle)
- Layout: Black sidebar w/ Duolingo-style nav, white content, brutalist Swiss cards w/ offset shadows
- Fonts: Unbounded (display) + IBM Plex Sans + JetBrains Mono
- Points engine: full retention/engagement/hit multiplier tables per PRD
- Recompute hooks update participation ranks + lifetime points on every clip

## Deferred / Backlog
- P0: Real Razorpay integration (currently mocked)
- P0: Editor rating signal for creators
- P1: Real-time leaderboard refresh (WebSocket) — currently on page load
- P1: TikTok / Instagram API analytics auto-fetch
- P1: Resend email notifications
- P1: Admin verification queue for screenshots
- P2: Dispute resolution flow
- P2: Creator preferences / style guides per campaign
