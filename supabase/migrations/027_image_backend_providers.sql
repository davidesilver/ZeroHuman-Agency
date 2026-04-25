-- 027_image_backend_providers.sql
-- Expand allowed image backends to include OpenRouter and Anthropic,
-- matching the agent-provider configuration pattern.
BEGIN;

-- PostgreSQL auto-generates constraint names for inline CHECK constraints.
-- We drop any existing constraint on image_backend and recreate it with
-- the expanded allowed set.
ALTER TABLE public.brands
  DROP CONSTRAINT IF EXISTS brands_image_backend_check;

ALTER TABLE public.brands
  ADD CONSTRAINT brands_image_backend_check
  CHECK (image_backend IN ('replicate','openai','pillo','mock','openrouter','anthropic'));

-- Performance: daily cost aggregation and recent-job listing
CREATE INDEX IF NOT EXISTS idx_imggen_brand_created
  ON public.image_generations (brand_id, created_at DESC);

COMMIT;
