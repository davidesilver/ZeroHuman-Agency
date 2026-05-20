-- Migration 037: add 'deep_research' to retriever_type enum
-- Allows research_items created from deep_research_jobs to be properly typed.

BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_enum
    WHERE enumlabel = 'deep_research'
      AND enumtypid = 'retriever_type'::regtype
  ) THEN
    ALTER TYPE retriever_type ADD VALUE 'deep_research';
  END IF;
END $$;

COMMIT;
