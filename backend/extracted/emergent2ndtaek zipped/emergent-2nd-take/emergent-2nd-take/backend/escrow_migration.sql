-- Database Migration: Outclipped MVP Escrow Funding System

-- 1. Update Campaigns Table
ALTER TABLE public.campaigns ADD COLUMN IF NOT EXISTS escrow_funded BOOLEAN DEFAULT FALSE;
ALTER TABLE public.campaigns ADD COLUMN IF NOT EXISTS funding_status TEXT DEFAULT 'UNFUNDED';
ALTER TABLE public.campaigns ADD COLUMN IF NOT EXISTS funding_reference TEXT DEFAULT NULL;

-- 2. Update Participations Table
ALTER TABLE public.participations ADD COLUMN IF NOT EXISTS payout_amount NUMERIC DEFAULT 0.00;
ALTER TABLE public.participations ADD COLUMN IF NOT EXISTS payout_status TEXT DEFAULT 'NONE';
ALTER TABLE public.participations ADD COLUMN IF NOT EXISTS payment_reference TEXT DEFAULT NULL;
ALTER TABLE public.participations ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ DEFAULT NULL;

-- 3. Update Users Table (Explicit Columns for Bank Details)
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS bank_name TEXT DEFAULT NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS bank_account_number TEXT DEFAULT NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS bank_account_name TEXT DEFAULT NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS bank_ifsc TEXT DEFAULT NULL;

-- 4. Create Settlement Logs Table
CREATE TABLE IF NOT EXISTS public.settlement_logs (
    settlement_id TEXT PRIMARY KEY,
    campaign_id TEXT REFERENCES public.campaigns(campaign_id) ON DELETE RESTRICT,
    total_ocv NUMERIC NOT NULL,
    bounty_pool NUMERIC NOT NULL,
    net_pool NUMERIC NOT NULL,
    platform_fee NUMERIC NOT NULL,
    payouts JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    settled_by TEXT REFERENCES public.users(user_id) ON DELETE SET NULL
);

-- 5. UPI and Bank Payout Option Support
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS payout_method TEXT DEFAULT 'UPI';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS upi_id TEXT DEFAULT NULL;

-- Backfill legacy payout_upi values to upi_id
UPDATE public.users 
SET upi_id = payout_upi 
WHERE upi_id IS NULL AND payout_upi IS NOT NULL;

