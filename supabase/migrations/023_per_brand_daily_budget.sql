-- Migration 023: per-brand daily cost budget
--
-- Adds `daily_budget_usd` to brands.
--   NULL  = unlimited (no cap enforced)
--   > 0   = daily spend limit in USD; Python cost_tracker aborts the pipeline
--           when the brand's spend for the current UTC day exceeds this value.
--
-- The global DAILY_COST_CAP_USD env var remains as a system-wide hard ceiling
-- across all brands.  Per-brand budget is an additional per-tenant limit.

ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS daily_budget_usd numeric(10, 4) DEFAULT NULL;

COMMENT ON COLUMN public.brands.daily_budget_usd IS
  'Optional per-brand daily spend cap in USD. NULL = unlimited. '
  'Enforced by Python cost_tracker.check_daily_cost_cap(). '
  'The global DAILY_COST_CAP_USD env var is a separate system-wide ceiling.';
