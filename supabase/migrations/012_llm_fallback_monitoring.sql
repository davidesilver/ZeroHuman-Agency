-- ============================================================================
-- AI Content Engine - LLM Fallback Monitoring
-- Migration: 012_llm_fallback_monitoring.sql
-- Description: Track LLM fallback attempts for monitoring and cost visibility
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Create llm_fallback_log table
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS llm_fallback_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id            UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    context             TEXT NOT NULL,          -- e.g., "humanizer_pass1", "god_synthesis"
    action              TEXT NOT NULL,          -- e.g., "initial_humanization", "synthesis"
    primary_model       TEXT NOT NULL,          -- Model that failed
    fallback_reason     TEXT NOT NULL,          -- Error message or reason
    is_emergency        BOOLEAN NOT NULL DEFAULT FALSE,  -- True if Anthropic API down
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE llm_fallback_log IS 'Tracks all LLM fallback attempts for monitoring and cost visibility. Critical for identifying provider outages and cost escalation.';
COMMENT ON COLUMN llm_fallback_log.is_emergency IS 'TRUE when Anthropic API fails and system falls back to OpenRouter (critical incident). FALSE for normal fallback chain (e.g., Gemma 4 → Haiku).';

-- Indexes for monitoring queries
CREATE INDEX IF NOT EXISTS idx_llm_fallback_brand ON llm_fallback_log(brand_id);
CREATE INDEX IF NOT EXISTS idx_llm_fallback_created_at ON llm_fallback_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_fallback_emergency ON llm_fallback_log(is_emergency, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_fallback_context ON llm_fallback_log(context, created_at DESC);

-- RLS Policies (brand isolation)
ALTER TABLE llm_fallback_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "llm_fallback_log_select" ON llm_fallback_log;
CREATE POLICY "llm_fallback_log_select" ON llm_fallback_log
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "llm_fallback_log_insert" ON llm_fallback_log;
CREATE POLICY "llm_fallback_log_insert" ON llm_fallback_log
  FOR INSERT WITH CHECK (brand_id = auth_user_brand_id());

-- ----------------------------------------------------------------------------
-- 2. Add fallback monitoring configuration to settings (optional - via env vars)
-- ----------------------------------------------------------------------------

-- No DB columns needed - configuration via environment variables:
-- FALLBACK_ALERT_THRESHOLD: Percentage of daily calls that can be fallbacks before alert (default: 10)
-- FALLBACK_DAILY_RESET: Time when daily counter resets (default: 00:00 UTC)

-- ----------------------------------------------------------------------------
-- 3. Create monitoring view for daily fallback stats
-- ----------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_daily_fallback_stats AS
SELECT
    DATE(created_at AT TIME ZONE 'UTC') as date,
    brand_id,
    context,
    COUNT(*) as total_fallbacks,
    COUNT(*) FILTER (WHERE is_emergency = TRUE) as emergency_fallbacks,
    COUNT(*) FILTER (WHERE is_emergency = FALSE) as normal_fallbacks,
    ARRAY_AGG(DISTINCT primary_model) as failed_models,
    MAX(created_at) as last_fallback_at
FROM llm_fallback_log
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at AT TIME ZONE 'UTC'), brand_id, context
ORDER BY date DESC, brand_id, context;

COMMENT ON VIEW v_daily_fallback_stats IS 'Daily fallback statistics for monitoring. Shows total, emergency, and normal fallbacks by brand and context.';

-- ----------------------------------------------------------------------------
-- 4. Example queries for monitoring
-- ----------------------------------------------------------------------------

-- -- Emergency fallbacks in the last 24 hours (critical incidents)
-- SELECT
--     brand_id,
--     context,
--     action,
--     primary_model,
--     fallback_reason,
--     created_at
-- FROM llm_fallback_log
-- WHERE is_emergency = TRUE
--   AND created_at >= NOW() - INTERVAL '24 hours'
-- ORDER BY created_at DESC;

-- -- Fallback frequency by brand (last 7 days)
-- SELECT
--     brand_id,
--     COUNT(*) as total_fallbacks,
--     COUNT(*) FILTER (WHERE is_emergency = TRUE) as emergency_count,
--     ROUND(100.0 * COUNT(*) FILTER (WHERE is_emergency = TRUE) / NULLIF(COUNT(*), 0), 2) as emergency_percentage
-- FROM llm_fallback_log
-- WHERE created_at >= NOW() - INTERVAL '7 days'
-- GROUP BY brand_id
-- ORDER BY total_fallbacks DESC;

-- -- Most common failing models
-- SELECT
--     primary_model,
--     COUNT(*) as failure_count,
--     COUNT(DISTINCT brand_id) as affected_brands,
--     STRING_AGG(DISTINCT context, ', ') as contexts
-- FROM llm_fallback_log
-- WHERE created_at >= NOW() - INTERVAL '7 days'
-- GROUP BY primary_model
-- ORDER BY failure_count DESC;

-- -- Daily fallback trends (last 30 days)
-- SELECT
--     date,
--     SUM(total_fallbacks) as daily_total,
--     SUM(emergency_fallbacks) as daily_emergency,
--     ROUND(100.0 * SUM(emergency_fallbacks) / NULLIF(SUM(total_fallbacks), 0), 2) as emergency_rate
-- FROM v_daily_fallback_stats
-- GROUP BY date
-- ORDER BY date DESC;
