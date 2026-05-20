-- 043_brand_llm_config.sql
-- Per-brand LLM preference configuration.
-- Allows each brand to choose a preferred LLM provider instead of relying on
-- the system-level env var fallback chain.
--
-- The BYOK keys themselves live in brand_integrations (provider='{provider_id}', key_name='api_key').
-- This table stores the routing preference: which provider to call first.
BEGIN;

CREATE TABLE IF NOT EXISTS public.brand_llm_config (
  brand_id           uuid  PRIMARY KEY REFERENCES public.brands(id) ON DELETE CASCADE,
  preferred_provider text,          -- e.g. 'anthropic', 'openai', 'groq'
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.brand_llm_config IS
  'Per-brand LLM routing preferences. BYOK keys are in brand_integrations.';
COMMENT ON COLUMN public.brand_llm_config.preferred_provider IS
  'Provider ID from PROVIDER_CATALOG. Null = use system cascade.';

ALTER TABLE public.brand_llm_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS brand_llm_config_select ON public.brand_llm_config;
CREATE POLICY brand_llm_config_select ON public.brand_llm_config
  FOR SELECT USING (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS brand_llm_config_insert ON public.brand_llm_config;
CREATE POLICY brand_llm_config_insert ON public.brand_llm_config
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS brand_llm_config_update ON public.brand_llm_config;
CREATE POLICY brand_llm_config_update ON public.brand_llm_config
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS brand_llm_config_delete ON public.brand_llm_config;
CREATE POLICY brand_llm_config_delete ON public.brand_llm_config
  FOR DELETE USING (public.user_has_brand(brand_id));

CREATE OR REPLACE FUNCTION public.touch_brand_llm_config_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END $$;

DROP TRIGGER IF EXISTS trg_brand_llm_config_touch ON public.brand_llm_config;
CREATE TRIGGER trg_brand_llm_config_touch
  BEFORE UPDATE ON public.brand_llm_config
  FOR EACH ROW EXECUTE FUNCTION public.touch_brand_llm_config_updated_at();

COMMIT;
