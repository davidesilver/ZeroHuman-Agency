-- 033_brevo_foundation.sql
-- Email marketing foundation: per-brand Brevo contacts mirror.
-- Capability expansion PRD Phase 3 (Brevo foundation):
--   Stores a local mirror of Brevo contacts per brand.
--   Brevo is the marketing automation layer; Resend stays for transactional email.
--
-- Brevo API key stored in brand_integrations (provider='brevo', key_name='api_key').
-- Feature gate: feature_flags.key = 'email_marketing_enabled' must be true.
BEGIN;

-- Local mirror of Brevo contacts per brand
CREATE TABLE IF NOT EXISTS public.brevo_contacts (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  brevo_id      bigint,
  email         text        NOT NULL,
  first_name    text,
  last_name     text,
  attributes    jsonb       NOT NULL DEFAULT '{}',
  list_ids      integer[]   NOT NULL DEFAULT '{}',
  is_blocklisted boolean    NOT NULL DEFAULT false,
  synced_at     timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brand_id, email)
);

COMMENT ON TABLE public.brevo_contacts IS
  'Local mirror of Brevo contacts. brevo_id is the remote contact ID; NULL until first sync.';
COMMENT ON COLUMN public.brevo_contacts.list_ids IS
  'Brevo list IDs this contact belongs to (mirrors remote state after sync).';

CREATE INDEX IF NOT EXISTS idx_brevo_contacts_brand
  ON public.brevo_contacts (brand_id);
CREATE INDEX IF NOT EXISTS idx_brevo_contacts_email
  ON public.brevo_contacts (brand_id, email);
CREATE INDEX IF NOT EXISTS idx_brevo_contacts_synced
  ON public.brevo_contacts (brand_id, synced_at);

ALTER TABLE public.brevo_contacts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS brevo_contacts_select ON public.brevo_contacts;
CREATE POLICY brevo_contacts_select ON public.brevo_contacts
  FOR SELECT USING (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS brevo_contacts_insert ON public.brevo_contacts;
CREATE POLICY brevo_contacts_insert ON public.brevo_contacts
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS brevo_contacts_update ON public.brevo_contacts;
CREATE POLICY brevo_contacts_update ON public.brevo_contacts
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS brevo_contacts_delete ON public.brevo_contacts;
CREATE POLICY brevo_contacts_delete ON public.brevo_contacts
  FOR DELETE USING (public.user_has_brand(brand_id));

CREATE OR REPLACE FUNCTION public.touch_brevo_contacts_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END $$;

DROP TRIGGER IF EXISTS trg_brevo_contacts_touch ON public.brevo_contacts;
CREATE TRIGGER trg_brevo_contacts_touch
  BEFORE UPDATE ON public.brevo_contacts
  FOR EACH ROW EXECUTE FUNCTION public.touch_brevo_contacts_updated_at();

COMMIT;
