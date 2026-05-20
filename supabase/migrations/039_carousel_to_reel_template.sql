-- Migration 039: seed carousel-to-reel system video template.

BEGIN;

INSERT INTO video_templates (brand_id, name, slug, description, composition_path, props_schema)
VALUES (
  NULL,
  'Carousel → Reel',
  'carousel-to-reel',
  'Converts an image carousel into an animated vertical reel. Supports slide, fade, and zoom transitions.',
  'compositions/carousel-to-reel',
  '{
    "type": "object",
    "required": ["slide_urls", "brand_name"],
    "properties": {
      "slide_urls":         {"type": "string",  "description": "JSON array of image URLs"},
      "brand_name":         {"type": "string",  "description": "Brand display name"},
      "duration_per_slide": {"type": "number",  "description": "Seconds per slide (default 2.5)", "default": 2.5},
      "transition_type":    {"type": "string",  "description": "slide | fade | zoom",             "default": "slide"},
      "accent_color":       {"type": "string",  "description": "Hex accent color",                "default": "#6366f1"},
      "caption":            {"type": "string",  "description": "Optional caption overlay",         "default": ""}
    }
  }'::jsonb
)
ON CONFLICT (brand_id, slug) DO NOTHING;

COMMIT;
