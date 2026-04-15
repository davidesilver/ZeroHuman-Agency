-- ============================================================================
-- AI Content Engine - Humanizer Control
-- Migration: 011_humanizer_control.sql
-- Description: Granular control for Humanizer agent per brand and channel
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Add humanizer control columns to brands table
-- ----------------------------------------------------------------------------

ALTER TABLE brands
ADD COLUMN IF NOT EXISTS use_humanizer BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS humanizer_channels TEXT[] DEFAULT ARRAY['linkedin', 'blog'],
ADD COLUMN IF NOT EXISTS humanizer_model_override TEXT;  -- Optional: force specific model

COMMENT ON COLUMN brands.use_humanizer IS 'Enable/disable Humanizer agent for this brand. If FALSE, humanization is skipped in the pipeline.';
COMMENT ON COLUMN brands.humanizer_channels IS 'Platforms/channels where Humanizer should be applied. E.g., ARRAY[linkedin, blog] means humanize LinkedIn and blog content but not docs or Instagram.';
COMMENT ON COLUMN brands.humanizer_model_override IS 'Optional explicit model to use for Humanizer (bypasses default routing). E.g., "anthropic/claude-3-5-haiku-20241022" or "google/gemma-4-150b:free". If NULL, uses default capability-based routing.';

-- ----------------------------------------------------------------------------
-- 2. Create humanizer_performance tracking table (for feedback loop)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS humanizer_performance (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id            UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
    brand_id            UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    ai_patterns_found   INTEGER NOT NULL DEFAULT 0,
    remaining_ai_tells  INTEGER NOT NULL DEFAULT 0,
    engagement_score    DECIMAL(5,2),
    platform            TEXT NOT NULL,
    model_used          TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE humanizer_performance IS 'Tracks Humanizer effectiveness. Correlates AI pattern detection with actual engagement to determine if humanization improves performance.';

-- Indexes for performance queries
CREATE INDEX IF NOT EXISTS idx_humanizer_brand ON humanizer_performance(brand_id);
CREATE INDEX IF NOT EXISTS idx_humanizer_draft ON humanizer_performance(draft_id);
CREATE INDEX IF NOT EXISTS idx_humanizer_score ON humanizer_performance(engagement_score DESC);
CREATE INDEX IF NOT EXISTS idx_humanizer_platform ON humanizer_performance(platform);

-- RLS Policies (brand isolation)
ALTER TABLE humanizer_performance ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "humanizer_perf_select" ON humanizer_performance;
CREATE POLICY "humanizer_perf_select" ON humanizer_performance
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "humanizer_perf_insert" ON humanizer_performance;
CREATE POLICY "humanizer_perf_insert" ON humanizer_performance
  FOR INSERT WITH CHECK (brand_id = auth_user_brand_id());

-- ----------------------------------------------------------------------------
-- 3. Add gold_examples support to tone_of_voice
-- ----------------------------------------------------------------------------
-- This is already supported since tone_of_voice is JSONB. No migration needed.
-- Example structure for brands.tone_of_voice.gold_examples:
-- {
--   "gold_examples": [
--     {
--       "title": "Best performing post about X",
--       "content": "This is the content...",
--       "notes": "Why this works well for our brand..."
--     },
--     {
--       "title": "Another great example",
--       "content": "More content...",
--       "notes": "Notes about style..."
--     }
--   ]
-- }

-- ----------------------------------------------------------------------------
-- 4. Enable Humanizer for existing brands (optional - set to FALSE by default)
-- ----------------------------------------------------------------------------

-- Uncomment to enable for specific brands:
-- UPDATE brands SET use_humanizer = TRUE WHERE slug = 'your-brand-slug';

-- ----------------------------------------------------------------------------
-- 5. Example queries for feedback loop analysis
-- ----------------------------------------------------------------------------

-- -- Do humanized posts perform better?
-- SELECT
--     AVG(engagement_score) as avg_score,
--     COUNT(*) as post_count,
--     CASE WHEN ai_patterns_found > 5 THEN 'Many AI patterns' ELSE 'Few AI patterns' END as pattern_category
-- FROM humanizer_performance
-- GROUP BY (ai_patterns_found > 5)
-- ORDER BY avg_score DESC;

-- -- Which platforms benefit most from humanization?
-- SELECT
--     platform,
--     AVG(engagement_score) as avg_engagement,
--     AVG(ai_patterns_found) as avg_patterns_removed,
--     COUNT(*) as post_count
-- FROM humanizer_performance
-- WHERE engagement_score IS NOT NULL
-- GROUP BY platform
-- ORDER BY avg_engagement DESC;

-- -- Correlation between patterns found and engagement
-- SELECT
--     ai_patterns_found,
--     AVG(engagement_score) as avg_engagement,
--     STDDEV(engagement_score) as score_variance
-- FROM humanizer_performance
-- WHERE engagement_score IS NOT NULL
-- GROUP BY ai_patterns_found
-- ORDER BY avg_engagement DESC;

-- -- Is the model override worth it?
-- SELECT
--     model_used,
--     AVG(engagement_score) as avg_engagement,
--     AVG(ai_patterns_found) as avg_patterns_removed,
--     COUNT(*) as post_count
-- FROM humanizer_performance
-- WHERE engagement_score IS NOT NULL
-- GROUP BY model_used
-- ORDER BY avg_engagement DESC;
