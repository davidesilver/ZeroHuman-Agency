-- 035_deep_research_jobs.sql
-- Deep research job queue (Phase 7).
-- local-deep-research runs as a Docker sidecar on port 5000.
-- Jobs are async: POST to start, poll GET /status/:id, fetch GET /results/:id.
BEGIN;

CREATE TABLE IF NOT EXISTS public.deep_research_jobs (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id    uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  topic       text        NOT NULL,
  depth       integer     NOT NULL DEFAULT 3 CHECK (depth BETWEEN 1 AND 5),
  status      text        NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending','running','completed','failed')),
  external_id text,                   -- job ID from local-deep-research API
  result      jsonb,                  -- structured results when completed
  sources     jsonb,                  -- list of sources used
  error       text,
  started_at  timestamptz,
  completed_at timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.deep_research_jobs IS
  'Async deep research jobs dispatched to local-deep-research Docker container (port 5000).';
COMMENT ON COLUMN public.deep_research_jobs.depth IS
  '1=shallow (fast), 5=deep (slow). Default 3. Per-brand cap enforced at app layer.';

CREATE INDEX IF NOT EXISTS idx_deep_research_brand_status
  ON public.deep_research_jobs (brand_id, status, created_at DESC);

ALTER TABLE public.deep_research_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS deep_research_select ON public.deep_research_jobs;
CREATE POLICY deep_research_select ON public.deep_research_jobs
  FOR SELECT USING (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS deep_research_insert ON public.deep_research_jobs;
CREATE POLICY deep_research_insert ON public.deep_research_jobs
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS deep_research_update ON public.deep_research_jobs;
CREATE POLICY deep_research_update ON public.deep_research_jobs
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));

CREATE OR REPLACE FUNCTION public.touch_deep_research_jobs_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END $$;

DROP TRIGGER IF EXISTS trg_deep_research_jobs_touch ON public.deep_research_jobs;
CREATE TRIGGER trg_deep_research_jobs_touch
  BEFORE UPDATE ON public.deep_research_jobs
  FOR EACH ROW EXECUTE FUNCTION public.touch_deep_research_jobs_updated_at();

COMMIT;
