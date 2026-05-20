-- Migration 040: Heygen per-brand quota tracking.
-- Heygen API key stored in brand_integrations (provider='heygen', key_name='api_key').
-- Monthly minutes usage tracked here.

BEGIN;

CREATE TABLE IF NOT EXISTS heygen_usage (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id    uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  year_month  text NOT NULL,          -- e.g. '2025-01'
  minutes_used numeric NOT NULL DEFAULT 0,
  updated_at  timestamptz DEFAULT now(),

  CONSTRAINT uq_heygen_usage_brand_month UNIQUE (brand_id, year_month)
);

CREATE INDEX IF NOT EXISTS idx_heygen_usage_brand ON heygen_usage(brand_id, year_month);

ALTER TABLE heygen_usage ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS heygen_usage_brand ON heygen_usage;
CREATE POLICY heygen_usage_brand ON heygen_usage
  FOR ALL USING (public.user_has_brand(brand_id));

-- Add heygen_avatar_id to videos for talking-head type reference
ALTER TABLE videos ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'hyperframes'
  CHECK (kind IN ('hyperframes', 'heygen'));
ALTER TABLE videos ADD COLUMN IF NOT EXISTS heygen_video_id text;

COMMIT;
