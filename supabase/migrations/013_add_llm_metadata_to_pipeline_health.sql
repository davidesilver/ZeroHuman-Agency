-- Add LLM metadata fields to pipeline_health table for Synergy Sync
-- This migration adds fields to track which LLM models and engines are being used

-- Add new columns for LLM metadata tracking
ALTER TABLE pipeline_health
ADD COLUMN IF NOT EXISTS current_model TEXT,
ADD COLUMN IF NOT EXISTS fallback_model TEXT,
ADD COLUMN IF NOT EXISTS engine TEXT NOT NULL DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS last_latency_ms INTEGER,
ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ;

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_pipeline_health_brand_status
ON pipeline_health(brand_id, status, last_seen DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_health_engine
ON pipeline_health(engine, last_seen DESC);

-- Add comments for documentation
COMMENT ON COLUMN pipeline_health.current_model IS 'The LLM model currently being used by this agent (e.g., claude-3-5-haiku-20241022)';
COMMENT ON COLUMN pipeline_health.fallback_model IS 'The fallback model if current model fails (NULL if no fallback)';
COMMENT ON COLUMN pipeline_health.engine IS 'The LLM engine being used: anthropic or openrouter';
COMMENT ON COLUMN pipeline_health.last_latency_ms IS 'Most recent LLM call latency in milliseconds';
COMMENT ON COLUMN pipeline_health.last_seen IS 'Timestamp of most recent heartbeat from this agent';

-- Update existing records to have default values
UPDATE pipeline_health
SET
    engine = 'unknown',
    last_seen = COALESCE(last_heartbeat, now())
WHERE engine IS NULL OR last_seen IS NULL;
