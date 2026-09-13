-- Table for verified social accounts
CREATE TABLE IF NOT EXISTS public.social_accounts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    account_name TEXT NOT NULL,
    account_handle TEXT NOT NULL,
    avatar_url TEXT,
    verified BOOLEAN NOT NULL DEFAULT TRUE,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (platform, account_id)
);

-- Table for temporary verification attempts/codes
CREATE TABLE IF NOT EXISTS public.social_verifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    verification_code TEXT NOT NULL,
    channel_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
