-- 044_setup_progress.sql
-- Per-brand wizard completion tracking.
-- Replaces localStorage-only persistence with server-side state
-- so setup resumes after browser clears or across devices.
BEGIN;

CREATE TABLE IF NOT EXISTS public.setup_progress (
  brand_id      uuid        PRIMARY KEY REFERENCES public.brands(id) ON DELETE CASCADE,
  completed     jsonb       NOT NULL DEFAULT '{}'::jsonb,
  -- e.g. {"infrastructure": true, "llm": true, "brand": true, "voice": false}
  wizard_state  jsonb       NOT NULL DEFAULT '{}'::jsonb,
  -- transient wizard state (current step index, partial form data)
  dismissed     boolean     NOT NULL DEFAULT false,
  -- user dismissed the "Getting Started" banner
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.setup_progress IS
  'Per-brand setup wizard completion state. dismissed=true hides the Getting Started banner.';
COMMENT ON COLUMN public.setup_progress.completed IS
  'JSON map of step_id -> boolean. True = step completed or explicitly skipped.';
COMMENT ON COLUMN public.setup_progress.wizard_state IS
  'Transient wizard form state for resuming mid-wizard.';

ALTER TABLE public.setup_progress ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS setup_progress_all ON public.setup_progress;
CREATE POLICY setup_progress_all ON public.setup_progress
  USING (public.user_has_brand(brand_id))
  WITH CHECK (public.user_has_brand(brand_id));

CREATE OR REPLACE FUNCTION public.touch_setup_progress_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END $$;

DROP TRIGGER IF EXISTS trg_setup_progress_touch ON public.setup_progress;
CREATE TRIGGER trg_setup_progress_touch
  BEFORE UPDATE ON public.setup_progress
  FOR EACH ROW EXECUTE FUNCTION public.touch_setup_progress_updated_at();

COMMIT;
