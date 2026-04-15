-- ============================================================================
-- AI Content Engine - Performance Optimization
-- Migration: 010_performance_optimization.sql
-- Purpose: Add strategic indexes for dashboard performance and feedback loop efficiency
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Feedback Loop Optimizations
-- ----------------------------------------------------------------------------

-- Speed up score updates by research_item_id
CREATE INDEX IF NOT EXISTS idx_scores_research_item 
  ON scores(research_item_id);

-- Speed up engagement summary queries
CREATE INDEX IF NOT EXISTS idx_social_metrics_draft_platform
  ON social_metrics(draft_id, platform);

-- ----------------------------------------------------------------------------
-- 2. Dashboard & Listing Optimizations
-- ----------------------------------------------------------------------------

-- Speed up filtering drafts by publication date
CREATE INDEX IF NOT EXISTS idx_content_drafts_published_at
  ON content_drafts(published_at DESC)
  WHERE status = 'published';

-- Speed up keyword/title searches in research items
-- (Using gin_trgm_ops if pg_trgm extension is available, or standard B-tree for exact/prefix)
CREATE INDEX IF NOT EXISTS idx_research_items_title_prefix
  ON research_items(title text_pattern_ops);

-- Speed up newsletter listing by brand
CREATE INDEX IF NOT EXISTS idx_newsletters_brand_status_date
  ON newsletters(brand_id, status, scheduled_at DESC);

-- ----------------------------------------------------------------------------
-- 3. Maintenance Optimizations
-- ----------------------------------------------------------------------------

-- Index for log cleanup and auditing
CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp_brin
  ON audit_trail USING brin(timestamp);

COMMENT ON INDEX idx_audit_trail_timestamp_brin IS
  'BRIN index for efficient range queries and cleanup on large audit logs.';
