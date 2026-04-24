-- 026_image_generation_config.sql
BEGIN;

ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS image_model          text DEFAULT 'black-forest-labs/flux-schnell',
  ADD COLUMN IF NOT EXISTS image_style_preset   text DEFAULT 'editorial-minimal',
  ADD COLUMN IF NOT EXISTS image_prompt_template text,
  ADD COLUMN IF NOT EXISTS image_backend        text DEFAULT 'replicate'
    CHECK (image_backend IN ('replicate','openai','pillo','mock'));

CREATE TABLE IF NOT EXISTS public.image_generations (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  draft_id        uuid REFERENCES public.content_drafts(id) ON DELETE SET NULL,
  backend         text NOT NULL,
  model_id        text NOT NULL,
  prompt          text NOT NULL,
  negative_prompt text,
  seed            bigint,
  status          text NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','running','succeeded','failed')),
  storage_path    text,
  public_url      text,
  width_px        int,
  height_px       int,
  cost_usd        numeric(10,4),
  error           text,
  started_at      timestamptz,
  finished_at     timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_imggen_brand_draft
  ON public.image_generations (brand_id, draft_id);
CREATE INDEX IF NOT EXISTS idx_imggen_status_created
  ON public.image_generations (status, created_at DESC);

ALTER TABLE public.image_generations ENABLE ROW LEVEL SECURITY;
CREATE POLICY imggen_select ON public.image_generations
  FOR SELECT USING (public.user_has_brand(brand_id));
CREATE POLICY imggen_insert ON public.image_generations
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY imggen_update ON public.image_generations
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));

-- Dedicated bucket for generated images (separate from brand-assets so we
-- never mix human-uploaded originals with machine outputs).
INSERT INTO storage.buckets (id, name, public)
  VALUES ('generated-images','generated-images', false)
  ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS generated_images_read ON storage.objects;
CREATE POLICY generated_images_read ON storage.objects
  FOR SELECT USING (
    bucket_id = 'generated-images'
    AND public.user_has_brand((split_part(name, '/', 1))::uuid)
  );
DROP POLICY IF EXISTS generated_images_write ON storage.objects;
CREATE POLICY generated_images_write ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'generated-images'
    AND public.user_has_brand((split_part(name, '/', 1))::uuid)
  );

COMMIT;
