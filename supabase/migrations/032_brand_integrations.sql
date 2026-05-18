-- 032_brand_integrations.sql
-- Per-brand encrypted API keys / secrets vault.
-- Capability expansion PRD Phase 0 (foundation):
--   Replaces the previous pattern of storing API keys as global env vars.
--   Each brand can have its own Brevo key, Heygen key, OpenClaw key, etc.
--
-- Encryption:
--   Application layer uses Python cryptography.fernet (symmetric AES-128-CBC).
--   The Fernet key lives in BRAND_SECRETS_ENCRYPTION_KEY env var.
--   The DB stores only the ciphertext — the DB server never sees plaintext.
--
-- Access pattern:
--   SELECT encrypted_value FROM brand_integrations
--     WHERE brand_id=$1 AND provider=$2 AND key_name=$3
--   Python: get_brand_secret(brand_id, provider, key_name) → str
--   Python: set_brand_secret(brand_id, provider, key_name, value)
BEGIN;

CREATE TABLE IF NOT EXISTS public.brand_integrations (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  provider        text        NOT NULL,
  key_name        text        NOT NULL,
  encrypted_value text        NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brand_id, provider, key_name)
);

COMMENT ON TABLE public.brand_integrations IS
  'Per-brand encrypted API secrets. Encryption handled at app layer (Fernet). DB stores ciphertext only.';
COMMENT ON COLUMN public.brand_integrations.provider IS
  'Service name, e.g. brevo, heygen, openclaw, scrapling.';
COMMENT ON COLUMN public.brand_integrations.key_name IS
  'Key within the provider, e.g. api_key, webhook_secret.';
COMMENT ON COLUMN public.brand_integrations.encrypted_value IS
  'Fernet-encrypted ciphertext. Decrypt via get_brand_secret() in Python.';

CREATE INDEX IF NOT EXISTS idx_brand_integrations_brand
  ON public.brand_integrations (brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_integrations_lookup
  ON public.brand_integrations (brand_id, provider, key_name);

ALTER TABLE public.brand_integrations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS brand_integrations_select ON public.brand_integrations;
CREATE POLICY brand_integrations_select ON public.brand_integrations
  FOR SELECT USING (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS brand_integrations_insert ON public.brand_integrations;
CREATE POLICY brand_integrations_insert ON public.brand_integrations
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS brand_integrations_update ON public.brand_integrations;
CREATE POLICY brand_integrations_update ON public.brand_integrations
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS brand_integrations_delete ON public.brand_integrations;
CREATE POLICY brand_integrations_delete ON public.brand_integrations
  FOR DELETE USING (public.user_has_brand(brand_id));

-- Touch updated_at on change
CREATE OR REPLACE FUNCTION public.touch_brand_integrations_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END $$;

DROP TRIGGER IF EXISTS trg_brand_integrations_touch ON public.brand_integrations;
CREATE TRIGGER trg_brand_integrations_touch
  BEFORE UPDATE ON public.brand_integrations
  FOR EACH ROW EXECUTE FUNCTION public.touch_brand_integrations_updated_at();

COMMIT;
