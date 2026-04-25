-- 025_brand_visual_assets.sql
-- Editable, long-term brand visual assets. Distinct from memory_semantic
-- (which is TTL-decaying and vector-indexed). These rows point at binary
-- files in the 'brand-assets' private bucket.

BEGIN;

CREATE TABLE IF NOT EXISTS public.brand_assets (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id      uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  kind          text NOT NULL CHECK (kind IN (
                  'logo_primary','logo_mono','logo_favicon',
                  'palette','font_specimen','design_system_pdf',
                  'example_newsletter','example_post','example_carousel',
                  'watermark','other'
                )),
  label         text,
  storage_path  text NOT NULL,
  mime_type     text NOT NULL,
  bytes         bigint NOT NULL,
  width_px      int,
  height_px     int,
  palette_hex   text[],
  metadata      jsonb NOT NULL DEFAULT '{}',
  uploaded_by   uuid REFERENCES auth.users(id),
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brand_assets_brand_kind
  ON public.brand_assets (brand_id, kind);

-- Only one primary logo per brand (enforced at app layer normally, but guardrail here)
CREATE UNIQUE INDEX IF NOT EXISTS uq_brand_assets_single_primary_logo
  ON public.brand_assets (brand_id)
  WHERE kind = 'logo_primary';

-- Same membership RLS pattern used elsewhere in this codebase (P1 helper).
ALTER TABLE public.brand_assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY brand_assets_select ON public.brand_assets
  FOR SELECT USING (public.user_has_brand(brand_id));
CREATE POLICY brand_assets_insert ON public.brand_assets
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY brand_assets_update ON public.brand_assets
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY brand_assets_delete ON public.brand_assets
  FOR DELETE USING (public.user_has_brand(brand_id));

-- Storage bucket (created idempotently; policies attached separately).
INSERT INTO storage.buckets (id, name, public)
  VALUES ('brand-assets','brand-assets', false)
  ON CONFLICT (id) DO NOTHING;

-- Storage policies — object path is '<brand_id>/<uuid>.<ext>', first segment scopes membership.
DROP POLICY IF EXISTS brand_assets_storage_read ON storage.objects;
CREATE POLICY brand_assets_storage_read ON storage.objects
   FOR SELECT USING (
     bucket_id = 'brand-assets'
     AND public.user_has_brand((split_part(name, '/', 1))::uuid)
   );
DROP POLICY IF EXISTS brand_assets_storage_write ON storage.objects;
CREATE POLICY brand_assets_storage_write ON storage.objects
   FOR INSERT WITH CHECK (
     bucket_id = 'brand-assets'
     AND public.user_has_brand((split_part(name, '/', 1))::uuid)
   );
DROP POLICY IF EXISTS brand_assets_storage_delete ON storage.objects;
CREATE POLICY brand_assets_storage_delete ON storage.objects
   FOR DELETE USING (
     bucket_id = 'brand-assets'
     AND public.user_has_brand((split_part(name, '/', 1))::uuid)
   );

-- keep updated_at fresh
CREATE OR REPLACE FUNCTION public.touch_brand_assets_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_brand_assets_touch ON public.brand_assets;
CREATE TRIGGER trg_brand_assets_touch
   BEFORE UPDATE ON public.brand_assets
   FOR EACH ROW EXECUTE FUNCTION public.touch_brand_assets_updated_at();

COMMIT;
