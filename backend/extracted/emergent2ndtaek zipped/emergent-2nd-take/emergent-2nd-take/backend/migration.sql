-- SQL migration to add OCV column to clips table
ALTER TABLE public.clips ADD COLUMN IF NOT EXISTS ocv NUMERIC DEFAULT NULL;
ALTER TABLE public.clips ADD COLUMN IF NOT EXISTS ocv_formula_version INT DEFAULT 1;

-- V1 manual payments: campaign states and editor wallet fields.
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS wallet_balance NUMERIC NOT NULL DEFAULT 0;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS total_earnings NUMERIC NOT NULL DEFAULT 0;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS total_withdrawn NUMERIC NOT NULL DEFAULT 0;

ALTER TABLE public.campaigns ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE public.campaigns ALTER COLUMN status SET DEFAULT 'DRAFT';

UPDATE public.campaigns SET status = 'ACTIVE' WHERE status IN ('OPEN', 'CLOSING_SOON');
UPDATE public.campaigns SET status = 'PENDING_PAYMENT' WHERE status = 'UNDER_REVIEW';

CREATE TABLE IF NOT EXISTS public.withdrawal_requests (
    request_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    amount NUMERIC NOT NULL CHECK (amount > 0),
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PAID', 'REJECTED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_user_id ON public.withdrawal_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_status ON public.withdrawal_requests(status);
