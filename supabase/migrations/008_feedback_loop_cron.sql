-- ============================================================================
-- AI Content Engine - Feedback Loop Cron Infrastructure
-- Migration: 008_feedback_loop_cron.sql
-- Purpose: Tables and functions for daily feedback loop cron jobs
-- ============================================================================

-- Ensure pg_cron setup is consistent
CREATE EXTENSION IF NOT EXISTS pg_cron;
GRANT USAGE ON SCHEMA cron TO postgres;

-- ----------------------------------------------------------------------------
-- 1. Social Metrics Tracking
-- ----------------------------------------------------------------------------

DROP TABLE IF EXISTS social_metrics CASCADE;

CREATE TABLE IF NOT EXISTS social_metrics (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  draft_id            UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
  platform             TEXT NOT NULL,
  impressions          INTEGER NOT NULL DEFAULT 0,
  clicks              INTEGER NOT NULL DEFAULT 0,
  likes               INTEGER NOT NULL DEFAULT 0,
  shares              INTEGER NOT NULL DEFAULT 0,
  comments            INTEGER NOT NULL DEFAULT 0,
  saves               INTEGER NOT NULL DEFAULT 0,
  recorded_at         TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(draft_id, platform)
);

COMMENT ON TABLE social_metrics IS
'Stores engagement metrics for published social media posts. One row per platform per draft.';

COMMENT ON COLUMN social_metrics.recorded_at IS
'When these metrics were recorded from the platform API.';

-- ----------------------------------------------------------------------------
-- 2. Feedback Loop Audit Log
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS feedback_loop_audit (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id            UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  previous_bonus      NUMERIC NOT NULL,
  new_bonus           NUMERIC NOT NULL,
  metrics_used        INTEGER NOT NULL,
  score_delta         NUMERIC GENERATED ALWAYS AS (new_bonus - previous_bonus) STORED,
  executed_at         TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE feedback_loop_audit IS
'Audit trail of all feedback bonus calculations for transparency and debugging.';

COMMENT ON COLUMN feedback_loop_audit.score_delta IS
'Automatically calculated delta between new and previous bonus scores.';

-- ----------------------------------------------------------------------------
-- 3. Indexes
-- ----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_social_metrics_draft ON social_metrics(draft_id);
CREATE INDEX IF NOT EXISTS idx_social_metrics_recorded ON social_metrics(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_loop_audit_brand ON feedback_loop_audit(brand_id);
CREATE INDEX IF NOT EXISTS idx_feedback_loop_audit_executed ON feedback_loop_audit(executed_at DESC);

-- ----------------------------------------------------------------------------
-- 4. RLS Policies (system-level, no user restrictions)
-- ----------------------------------------------------------------------------

-- Social metrics: read-only for brand members
ALTER TABLE social_metrics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "social_metrics_select" ON social_metrics;
CREATE POLICY "social_metrics_select" ON social_metrics
  FOR SELECT USING (
    draft_id IN (
      SELECT id FROM content_drafts
      WHERE brand_id = auth_user_brand_id()
    )
  );

-- Feedback audit: read-only for brand members
ALTER TABLE feedback_loop_audit ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "feedback_loop_audit_select" ON feedback_loop_audit;
CREATE POLICY "feedback_loop_audit_select" ON feedback_loop_audit
  FOR SELECT USING (brand_id = auth_user_brand_id());

-- ----------------------------------------------------------------------------
-- 5. Helper Functions
-- ----------------------------------------------------------------------------

-- Function: Get engagement metrics for a draft across all platforms
CREATE OR REPLACE FUNCTION get_draft_engagement_summary(draft_uuid UUID)
RETURNS TABLE (
  total_impressions INTEGER,
  total_likes INTEGER,
  total_shares INTEGER,
  total_comments INTEGER,
  total_saves INTEGER,
  platforms_count INTEGER,
  first_recorded_at TIMESTAMPTZ,
  last_recorded_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    COALESCE(SUM(impressions), 0) AS total_impressions,
    COALESCE(SUM(likes), 0) AS total_likes,
    COALESCE(SUM(shares), 0) AS total_shares,
    COALESCE(SUM(comments), 0) AS total_comments,
    COALESCE(SUM(saves), 0) AS total_saves,
    COUNT(*) AS platforms_count,
    MIN(recorded_at) AS first_recorded_at,
    MAX(recorded_at) AS last_recorded_at
  FROM social_metrics
  WHERE draft_id = draft_uuid;
END;
$$;

COMMENT ON FUNCTION get_draft_engagement_summary IS
'Aggregates engagement metrics across all platforms for a single draft.';

-- ----------------------------------------------------------------------------
-- 6. Initial Seeding for Testing
-- ----------------------------------------------------------------------------

-- Note: In production, this table is populated by the Postiz Analytics Puller
-- via pull_daily_metrics() function in postiz_analytics.py

-- Example metrics for a test brand (replace UUID with actual brand_id)
-- INSERT INTO social_metrics (draft_id, platform, impressions, likes, shares, comments, saves)
-- SELECT
--   cd.id,
--   'linkedin',
--   1500,
--   45,
--   12,
--   8,
--   0
-- FROM content_drafts cd
-- JOIN brands b ON cd.brand_id = b.id
-- WHERE b.name = 'Test Brand'
-- LIMIT 1;
