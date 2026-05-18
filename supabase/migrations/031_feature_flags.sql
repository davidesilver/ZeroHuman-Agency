-- 031_feature_flags.sql
-- Per-brand feature flags table.
-- Capability expansion PRD Phase 0 (foundation):
--   All new capabilities (video, email-marketing, deep-research, etc.) are
--   default-OFF and gated per-brand through this table.
--
-- Access pattern:
--   SELECT value FROM feature_flags WHERE brand_id = $1 AND key = $2
--   UPSERT for set/unset (Python: set_feature_flag / TS: setFeatureFlag)
BEGIN;

CREATE TABLE IF NOT EXISTS public.feature_flags (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id   uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  key        text        NOT NULL,
  value      boolean     NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brand_id, key)
);

COMMENT ON TABLE public.feature_flags IS
  'Per-brand boolean feature flags. All capability-expansion features start as OFF (false).';
COMMENT ON COLUMN public.feature_flags.key IS
  'Flag name, e.g. video_enabled, email_marketing_enabled, deep_research_enabled.';

CREATE INDEX IF NOT EXISTS idx_feature_flags_brand_key
  ON public.feature_flags (brand_id, key);

ALTER TABLE public.feature_flags ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS feature_flags_select ON public.feature_flags;
CREATE POLICY feature_flags_select ON public.feature_flags
  FOR SELECT USING (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS feature_flags_insert ON public.feature_flags;
CREATE POLICY feature_flags_insert ON public.feature_flags
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS feature_flags_update ON public.feature_flags;
CREATE POLICY feature_flags_update ON public.feature_flags
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS feature_flags_delete ON public.feature_flags;
CREATE POLICY feature_flags_delete ON public.feature_flags
  FOR DELETE USING (public.user_has_brand(brand_id));

-- Touch updated_at on change
CREATE OR REPLACE FUNCTION public.touch_feature_flags_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END $$;

DROP TRIGGER IF EXISTS trg_feature_flags_touch ON public.feature_flags;
CREATE TRIGGER trg_feature_flags_touch
  BEFORE UPDATE ON public.feature_flags
  FOR EACH ROW EXECUTE FUNCTION public.touch_feature_flags_updated_at();

COMMIT;
