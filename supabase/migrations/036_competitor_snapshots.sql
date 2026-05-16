-- 036_competitor_snapshots.sql
-- Competitor monitoring via Scrapling spider (Phase 9).
-- Scrapling replaces/complements Firecrawl where stealth or Cloudflare bypass
-- is needed. Results are stored as periodic snapshots per monitored URL.
BEGIN;

CREATE TABLE IF NOT EXISTS public.competitor_snapshots (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id    uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  url         text        NOT NULL,
  title       text,
  content     text,                   -- extracted markdown/text content
  metadata    jsonb       NOT NULL DEFAULT '{}',
  status      text        NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending','running','completed','failed')),
  error       text,
  captured_at timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.competitor_snapshots IS
  'Periodic competitor page snapshots captured via Scrapling spider.';

CREATE INDEX IF NOT EXISTS idx_competitor_brand_url
  ON public.competitor_snapshots (brand_id, url, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_competitor_brand_recent
  ON public.competitor_snapshots (brand_id, created_at DESC);

ALTER TABLE public.competitor_snapshots ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS competitor_select ON public.competitor_snapshots;
CREATE POLICY competitor_select ON public.competitor_snapshots
  FOR SELECT USING (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS competitor_insert ON public.competitor_snapshots;
CREATE POLICY competitor_insert ON public.competitor_snapshots
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));

DROP POLICY IF EXISTS competitor_update ON public.competitor_snapshots;
CREATE POLICY competitor_update ON public.competitor_snapshots
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));

COMMIT;
