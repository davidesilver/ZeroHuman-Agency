-- Migration 034 — add layout_type to newsletters
--
-- Phase 2: React Email template system. The LLM selects a layout
-- during generation (digest | single_story | announcement).

ALTER TABLE public.newsletters
  ADD COLUMN IF NOT EXISTS layout_type text
    CHECK (layout_type IN ('digest', 'single_story', 'announcement'));

COMMENT ON COLUMN public.newsletters.layout_type IS
  'React Email layout chosen by LLM: digest | single_story | announcement';
