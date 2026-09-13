-- Migration to fix withdrawals schema
-- Add payment_reference column if missing
ALTER TABLE public.withdrawals
ADD COLUMN IF NOT EXISTS payment_reference TEXT;

-- Drop existing CHECK constraint on status (if any)
DO $$
BEGIN
    ALTER TABLE public.withdrawals DROP CONSTRAINT IF EXISTS withdrawals_status_check;
EXCEPTION WHEN others THEN NULL; END $$;

-- Recreate CHECK constraint to allow PAID
ALTER TABLE public.withdrawals
ADD CONSTRAINT withdrawals_status_check
CHECK (status IN ('PENDING', 'PAID', 'REJECTED'));
