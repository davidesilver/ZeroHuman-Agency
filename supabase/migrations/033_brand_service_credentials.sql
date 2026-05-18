-- 033_brand_service_credentials.sql
-- Per-brand API credentials for external services (Postiz, Serper, Tavily, etc.)
-- Credentials are encrypted at the application layer (Fernet) before being stored.
-- This table holds opaque ciphertext — the DB never sees plaintext keys.
BEGIN;

CREATE TABLE IF NOT EXISTS public.brand_service_credentials (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  service_name    text        NOT NULL,    -- e.g. 'postiz', 'serper', 'tavily', 'resend'
  encrypted_creds text        NOT NULL,    -- Fernet ciphertext (base64) of JSON credentials
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brand_id, service_name)
);

CREATE INDEX IF NOT EXISTS idx_bsc_brand
  ON public.brand_service_credentials (brand_id);

-- RLS: a brand member can only see credentials for their own brand
ALTER TABLE public.brand_service_credentials ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS bsc_select ON public.brand_service_credentials;
CREATE POLICY bsc_select ON public.brand_service_credentials
  FOR SELECT USING (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS bsc_insert ON public.brand_service_credentials;
CREATE POLICY bsc_insert ON public.brand_service_credentials
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS bsc_update ON public.brand_service_credentials;
CREATE POLICY bsc_update ON public.brand_service_credentials
  FOR UPDATE USING (public.user_has_brand(brand_id))
               WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS bsc_delete ON public.brand_service_credentials;
CREATE POLICY bsc_delete ON public.brand_service_credentials
  FOR DELETE USING (public.user_has_brand(brand_id));

-- Touch updated_at trigger
CREATE OR REPLACE FUNCTION public.touch_bsc_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_bsc_touch ON public.brand_service_credentials;
CREATE TRIGGER trg_bsc_touch
  BEFORE UPDATE ON public.brand_service_credentials
  FOR EACH ROW EXECUTE FUNCTION public.touch_bsc_updated_at();

COMMENT ON TABLE public.brand_service_credentials IS
  'Per-brand credentials for external services. Values are Fernet-encrypted; '
  'never stored or logged in plaintext. Key: BRAND_SECRETS_ENCRYPTION_KEY env var.';

COMMIT;
