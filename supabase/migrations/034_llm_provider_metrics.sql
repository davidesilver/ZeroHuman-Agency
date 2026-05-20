-- 034_llm_provider_metrics.sql
-- Per-brand LLM call telemetry for provider cost/latency comparison.
-- Capability expansion PRD Phase 4 (LLM provider abstraction):
--   Records every LLM call so we can compare OpenRouter vs OpenClaw (Phase 14)
--   and track cost-per-1k-tokens and latency by provider and model.
BEGIN;

CREATE TABLE IF NOT EXISTS public.llm_provider_metrics (
  id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id          uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  provider          text        NOT NULL,          -- 'openrouter' | 'openclaw' | 'anthropic'
  model             text        NOT NULL,          -- e.g. 'google/gemma-4-150b:free'
  task_type         text,                          -- e.g. 'creative', 'reasoning', 'scoring'
  prompt_tokens     integer     NOT NULL DEFAULT 0,
  completion_tokens integer     NOT NULL DEFAULT 0,
  latency_ms        integer,
  cost_usd          numeric(12,8),
  is_fallback       boolean     NOT NULL DEFAULT false,
  error             text,                          -- NULL on success, error message on failure
  ts                timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.llm_provider_metrics IS
  'Per-call LLM telemetry. Used for cost/latency comparison across providers.';

-- Hot query: aggregate stats per brand+provider+model for the metrics dashboard
CREATE INDEX IF NOT EXISTS idx_llm_metrics_brand_ts
  ON public.llm_provider_metrics (brand_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_llm_metrics_brand_provider
  ON public.llm_provider_metrics (brand_id, provider, ts DESC);

ALTER TABLE public.llm_provider_metrics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS llm_metrics_select ON public.llm_provider_metrics;
CREATE POLICY llm_metrics_select ON public.llm_provider_metrics
  FOR SELECT USING (public.user_has_brand(brand_id));

-- Insert-only from service role (background jobs write, users only read)
DROP POLICY IF EXISTS llm_metrics_insert ON public.llm_provider_metrics;
CREATE POLICY llm_metrics_insert ON public.llm_provider_metrics
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));

COMMIT;
