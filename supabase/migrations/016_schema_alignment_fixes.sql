-- ============================================================================
-- Migration 016: Schema alignment fixes
--
-- Fixes three mismatches between DB schema and application code:
--
-- 1. brands.use_context7 — boolean flag for Context7 MCP fact-checking
--    augmentation, queried in god_system.py but never added to schema.
--
-- 2. content_performance VIEW — humanizer.py queries this table to find
--    top-performing content for voice calibration. The underlying data lives
--    in content_drafts + social_metrics. A VIEW makes the query work without
--    changing Python code.
--
-- 3. (No DB change needed for #3 — pipeline_health.py uses 'pending_review'
--    which maps to 'scored' in the item_status enum; fixed in Python code.)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Fix #1: brands.use_context7
-- Context7 MCP augmentation flag per brand.
-- Defaults FALSE — opt-in feature, no existing behaviour changes.
-- ----------------------------------------------------------------------------
ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS use_context7 BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN public.brands.use_context7 IS
  'When TRUE, the GOD Fact-Checker agent augments prompts with Context7 MCP '
  'to fetch up-to-date documentation/facts for the content being reviewed.';


-- ----------------------------------------------------------------------------
-- Fix #2: content_performance VIEW
-- Synthesises published drafts + social engagement into the shape that
-- humanizer.py expects: (brand_id, title, body, platform, engagement_score).
--
-- Engagement score formula (weighted):
--   shares  × 3  (highest intent signal)
--   comments × 2
--   likes   × 1
--   clicks  × 1
--   saves   × 2
--   impressions × 0.01  (reach, low weight)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.content_performance AS
SELECT
  cd.id,
  cd.brand_id,
  cd.title,
  cd.body,
  cd.platform,
  ROUND(
    COALESCE(sm.shares,   0) * 3.0  +
    COALESCE(sm.comments, 0) * 2.0  +
    COALESCE(sm.likes,    0) * 1.0  +
    COALESCE(sm.clicks,   0) * 1.0  +
    COALESCE(sm.saves,    0) * 2.0  +
    COALESCE(sm.impressions, 0) * 0.01
  , 2) AS engagement_score
FROM public.content_drafts cd
JOIN public.social_metrics sm ON sm.draft_id = cd.id
WHERE cd.status = 'published'
  AND cd.title  IS NOT NULL
  AND cd.body   IS NOT NULL;

COMMENT ON VIEW public.content_performance IS
  'Aggregated engagement view used by the Humanizer agent for voice calibration. '
  'Joins published content_drafts with social_metrics; engagement_score is a '
  'weighted composite of shares, comments, likes, clicks, saves, impressions.';

-- Grant read access to authenticated role (same as tables)
GRANT SELECT ON public.content_performance TO authenticated;
