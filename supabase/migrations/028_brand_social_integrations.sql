-- 028_brand_social_integrations.sql
-- Social publishing integrations via Postiz (self-hosted or cloud).
BEGIN;

-- Isolated schema for Postiz self-hosted (optional — only needed if running
-- the Docker satellite). Safe to run even if Postiz is in cloud mode.
CREATE SCHEMA IF NOT EXISTS postiz;

-- brand_social_integrations stores opaque Postiz integration IDs per platform.
-- No OAuth tokens, no secrets — just references to Postiz channels.
CREATE TABLE IF NOT EXISTS public.brand_social_integrations (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id              uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  platform              text NOT NULL CHECK (platform IN (
                            'linkedin','twitter','x','instagram','facebook',
                            'tiktok','youtube','reddit','pinterest',
                            'threads','bluesky','mastodon','discord','slack'
                          )),
  postiz_integration_id text NOT NULL,
  postiz_channel_name   text,
  is_active             boolean NOT NULL DEFAULT true,
  metadata              jsonb NOT NULL DEFAULT '{}',
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brand_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_brand_social_int_brand
  ON public.brand_social_integrations (brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_social_int_active
  ON public.brand_social_integrations (brand_id, is_active);

ALTER TABLE public.brand_social_integrations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS brand_social_int_select ON public.brand_social_integrations;
CREATE POLICY brand_social_int_select ON public.brand_social_integrations
  FOR SELECT USING (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS brand_social_int_insert ON public.brand_social_integrations;
CREATE POLICY brand_social_int_insert ON public.brand_social_integrations
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS brand_social_int_update ON public.brand_social_integrations;
CREATE POLICY brand_social_int_update ON public.brand_social_integrations
  FOR UPDATE USING (public.user_has_brand(brand_id))
               WITH CHECK (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS brand_social_int_delete ON public.brand_social_integrations;
CREATE POLICY brand_social_int_delete ON public.brand_social_integrations
  FOR DELETE USING (public.user_has_brand(brand_id));

-- Touch updated_at trigger
CREATE OR REPLACE FUNCTION public.touch_brand_social_integrations_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_brand_social_integrations_touch
  ON public.brand_social_integrations;
CREATE TRIGGER trg_brand_social_integrations_touch
  BEFORE UPDATE ON public.brand_social_integrations
  FOR EACH ROW EXECUTE FUNCTION public.touch_brand_social_integrations_updated_at();

COMMIT;
