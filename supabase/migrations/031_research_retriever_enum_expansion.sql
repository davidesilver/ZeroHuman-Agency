-- Migration 031: Add duckduckgo and tavily to retriever_type enum
-- These support the free research fallback cascade (Phase 2 fast-setup).
-- Safe to run on existing data: no existing rows use these values.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_enum
    WHERE enumlabel = 'duckduckgo'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'retriever_type')
  ) THEN
    ALTER TYPE public.retriever_type ADD VALUE 'duckduckgo';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_enum
    WHERE enumlabel = 'tavily'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'retriever_type')
  ) THEN
    ALTER TYPE public.retriever_type ADD VALUE 'tavily';
  END IF;
END
$$;
