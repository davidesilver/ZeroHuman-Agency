-- ============================================================================
-- Migration: 014_add_manual_retriever_and_skill_description.sql
-- Description:
--   1. Adds 'manual' value to retriever_type enum so research_items accepts
--      manually submitted URLs (see src/app/api/content/from-url/route.ts).
--   2. Adds description column to agent_skills — the /settings/agenti UI
--      collects and displays it, but the original schema (005) omitted it.
-- ============================================================================

-- Fix #4: enum retriever_type must include 'manual'
ALTER TYPE retriever_type ADD VALUE IF NOT EXISTS 'manual';

-- Fix #5: agent_skills needs a description column for the settings UI
ALTER TABLE agent_skills
  ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '';
