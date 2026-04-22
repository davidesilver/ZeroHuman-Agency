-- Migration 020: Retriever enum expansion + research_sources column
-- Adds rss/youtube/gmail/x to retriever_type enum
-- Adds research_sources jsonb config column to brands
-- Drops users.brand_id (migrated to brand_members in 017)

-- ============================================================
-- 1. Add new values to retriever_type enum (idempotent)
-- ============================================================

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'rss' AND enumtypid = 'retriever_type'::regtype) THEN
    ALTER TYPE retriever_type ADD VALUE 'rss';
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'youtube' AND enumtypid = 'retriever_type'::regtype) THEN
    ALTER TYPE retriever_type ADD VALUE 'youtube';
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'gmail' AND enumtypid = 'retriever_type'::regtype) THEN
    ALTER TYPE retriever_type ADD VALUE 'gmail';
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'x' AND enumtypid = 'retriever_type'::regtype) THEN
    ALTER TYPE retriever_type ADD VALUE 'x';
  END IF;
END $$;

-- ============================================================
-- 2. Add research_sources jsonb column to brands (idempotent)
--    Schema:
--    {
--      "rss_feeds": [{"url": "...", "name": "..."}],
--      "youtube_channels": ["UCxxxx"],
--      "gmail_label": "newsletters",
--      "x_accounts": ["@handle"]
--    }
-- ============================================================

ALTER TABLE brands ADD COLUMN IF NOT EXISTS research_sources jsonb DEFAULT '{}';

COMMENT ON COLUMN brands.research_sources IS 'Per-brand retriever config: rss_feeds, youtube_channels, gmail_label, x_accounts';

-- ============================================================
-- 3. Add 'editorial' to slot_type enum (newsletter_candidates)
--    Required by newsletter_generator.py which inserts editorial
--    candidates that don't map to the original 3-slot structure.
-- ============================================================

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'editorial' AND enumtypid = 'slot_type'::regtype) THEN
    ALTER TYPE slot_type ADD VALUE 'editorial';
  END IF;
END $$;

-- ============================================================
-- 4. Drop users.brand_id (multi-brand now uses brand_members
--    table introduced in migration 017) — idempotent
-- ============================================================

ALTER TABLE users DROP COLUMN IF EXISTS brand_id;
