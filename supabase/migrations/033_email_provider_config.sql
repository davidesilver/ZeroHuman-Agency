-- Migration 033 — per-brand email provider configuration
--
-- Stores which email provider each brand uses (Brevo, Mailchimp, Resend)
-- along with delivery credentials and A/B test defaults.
--
-- API keys are stored encrypted via pgcrypto (symmetric AES-256-CBC).
-- The encryption key comes from SUPABASE_SERVICE_ROLE_KEY-derived secret;
-- at read-time the Python backend decrypts before passing to SDKs.
-- For simplicity in v1, we store the raw key and rely on RLS to restrict access.
-- Encrypted storage is tracked as a hardening task.
--
-- Fallback precedence at send-time:
--   1. email_provider_config for the brand (this table)
--   2. Resend via RESEND_API_KEY env var (global default)

CREATE TABLE IF NOT EXISTS public.email_provider_config (
  brand_id        uuid        PRIMARY KEY REFERENCES public.brands(id) ON DELETE CASCADE,
  provider        text        NOT NULL DEFAULT 'resend'
                              CHECK (provider IN ('brevo', 'mailchimp', 'resend')),
  api_key         text        NOT NULL DEFAULT '',
  sender_name     text        NOT NULL DEFAULT '',
  sender_email    text        NOT NULL DEFAULT '',
  list_id         text        NOT NULL DEFAULT '',
  webhook_secret  text        NOT NULL DEFAULT '',
  ab_split_pct    int         NOT NULL DEFAULT 20
                              CHECK (ab_split_pct BETWEEN 5 AND 50),
  ab_wait_hours   int         NOT NULL DEFAULT 4
                              CHECK (ab_wait_hours BETWEEN 1 AND 168),
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.email_provider_config IS
  'Per-brand email provider credentials and A/B test settings.';
COMMENT ON COLUMN public.email_provider_config.provider IS
  'Email delivery provider: brevo | mailchimp | resend';
COMMENT ON COLUMN public.email_provider_config.list_id IS
  'Provider-side subscriber list/audience ID to send campaigns to.';
COMMENT ON COLUMN public.email_provider_config.ab_split_pct IS
  'Percentage of list used for A/B test (each variant gets half). 5-50.';
COMMENT ON COLUMN public.email_provider_config.ab_wait_hours IS
  'Hours to wait before picking A/B winner. 1-168 (max 7 days).';

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION public.set_email_provider_config_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_email_provider_config_updated_at
  BEFORE UPDATE ON public.email_provider_config
  FOR EACH ROW EXECUTE FUNCTION public.set_email_provider_config_updated_at();

-- RLS: users can only read/write their own brand's config
ALTER TABLE public.email_provider_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "brand members can read email_provider_config"
  ON public.email_provider_config FOR SELECT
  USING (
    brand_id IN (
      SELECT brand_id FROM public.brand_members
      WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "brand members can upsert email_provider_config"
  ON public.email_provider_config FOR INSERT
  WITH CHECK (
    brand_id IN (
      SELECT brand_id FROM public.brand_members
      WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "brand members can update email_provider_config"
  ON public.email_provider_config FOR UPDATE
  USING (
    brand_id IN (
      SELECT brand_id FROM public.brand_members
      WHERE user_id = auth.uid()
    )
  );
