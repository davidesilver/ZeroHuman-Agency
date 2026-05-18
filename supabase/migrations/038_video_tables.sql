-- Migration 038: video_templates and videos tables for HyperFrames rendering pipeline.

BEGIN;

-- ----------------------------------------------------------------------------
-- 8.1 video_templates — reusable HyperFrames composition specs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS video_templates (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id     uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name         text NOT NULL,
  slug         text NOT NULL,
  description  text,
  composition_path text NOT NULL,   -- relative path to HyperFrames composition dir
  props_schema jsonb NOT NULL DEFAULT '{}',  -- JSON Schema for allowed render variables
  thumbnail_url text,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now(),

  CONSTRAINT uq_video_templates_brand_slug UNIQUE (brand_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_video_templates_brand ON video_templates(brand_id);

-- System-level templates (brand_id IS NULL) visible to all brands
-- We allow NULL brand_id for global/system templates.
ALTER TABLE video_templates ALTER COLUMN brand_id DROP NOT NULL;

-- ----------------------------------------------------------------------------
-- 8.2 videos — render jobs and output artefacts
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS videos (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  template_id     uuid REFERENCES video_templates(id) ON DELETE SET NULL,
  title           text NOT NULL,
  status          text NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','rendering','completed','failed')),
  render_props    jsonb NOT NULL DEFAULT '{}',  -- actual variable values used
  output_url      text,         -- Supabase Storage signed URL (set when completed)
  storage_path    text,         -- raw storage path for re-signing
  duration_secs   numeric,
  error           text,
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_videos_brand_status    ON videos(brand_id, status);
CREATE INDEX IF NOT EXISTS idx_videos_brand_created   ON videos(brand_id, created_at DESC);

-- updated_at trigger
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_video_templates_updated_at'
  ) THEN
    CREATE TRIGGER trg_video_templates_updated_at
      BEFORE UPDATE ON video_templates
      FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_videos_updated_at'
  ) THEN
    CREATE TRIGGER trg_videos_updated_at
      BEFORE UPDATE ON videos
      FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
  END IF;
END $$;

-- ----------------------------------------------------------------------------
-- RLS
-- ----------------------------------------------------------------------------
ALTER TABLE video_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;

-- video_templates: brand-scoped or system (brand_id IS NULL)
DROP POLICY IF EXISTS video_templates_brand_select ON video_templates;
CREATE POLICY video_templates_brand_select ON video_templates
  FOR SELECT USING (
    brand_id IS NULL OR public.user_has_brand(brand_id)
  );

DROP POLICY IF EXISTS video_templates_brand_write ON video_templates;
CREATE POLICY video_templates_brand_write ON video_templates
  FOR ALL USING (brand_id IS NOT NULL AND public.user_has_brand(brand_id));

-- videos: full per-brand isolation
DROP POLICY IF EXISTS videos_brand_all ON videos;
CREATE POLICY videos_brand_all ON videos
  FOR ALL USING (public.user_has_brand(brand_id));

-- ----------------------------------------------------------------------------
-- Seed global weekly-recap template (brand_id = NULL → system template)
-- ----------------------------------------------------------------------------
INSERT INTO video_templates (brand_id, name, slug, description, composition_path, props_schema)
VALUES (
  NULL,
  'Weekly Recap',
  'weekly-recap',
  'Animated weekly analytics summary with brand metrics, content highlights, and engagement stats.',
  'compositions/weekly-recap',
  '{
    "type": "object",
    "required": ["brand_name", "week_start"],
    "properties": {
      "brand_name":        {"type": "string",  "description": "Brand display name"},
      "week_start":        {"type": "string",  "description": "ISO date e.g. 2025-01-06"},
      "total_posts":       {"type": "integer", "default": 0},
      "total_reach":       {"type": "integer", "default": 0},
      "total_engagement":  {"type": "integer", "default": 0},
      "top_post_title":    {"type": "string",  "default": ""},
      "top_post_metric":   {"type": "string",  "default": ""},
      "accent_color":      {"type": "string",  "default": "#6366f1"},
      "logo_url":          {"type": "string",  "default": ""}
    }
  }'::jsonb
)
ON CONFLICT (brand_id, slug) DO NOTHING;

COMMIT;
