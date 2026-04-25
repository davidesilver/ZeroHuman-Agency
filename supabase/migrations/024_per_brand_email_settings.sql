-- Migration 024 — per-brand email sender (from_email, from_name)
--
-- Rationale: user-facing requirement — different brands need different
-- "From:" identities on newsletters.  Previously these were only global
-- env vars (FROM_EMAIL / FROM_NAME) which breaks multi-brand.
--
-- Fallback order at send-time:
--   1. brands.from_email / from_name (per-brand, authoritative if set)
--   2. FROM_EMAIL / FROM_NAME env vars (global default)
--
-- Social credentials (LinkedIn/Twitter/Instagram/TikTok tokens) are NOT
-- added here — encrypted credential storage needs a dedicated design
-- (separate vault table + pgcrypto or external KMS).  Tracked as future
-- work in the upgrade plan.

ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS from_email text,
  ADD COLUMN IF NOT EXISTS from_name  text;

COMMENT ON COLUMN public.brands.from_email IS
  'Per-brand newsletter sender address. NULL = use FROM_EMAIL env var.';
COMMENT ON COLUMN public.brands.from_name IS
  'Per-brand newsletter sender display name. NULL = use FROM_NAME env var.';
