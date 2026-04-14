-- Migration: 006_brand_scoring_enhancements.sql
-- Purpose: Add standalone columns for founder_principles and feedback_bonus
-- Created: 2026-04-14

-- Add founder_principles as standalone text array (not buried in JSONB)
ALTER TABLE brands
  ADD COLUMN IF NOT EXISTS founder_principles text[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS feedback_bonus numeric DEFAULT 5.0;

-- Add comments for clarity
COMMENT ON COLUMN brands.founder_principles IS 'Editorial principles that guide content curation (e.g., "No fluff", "Actionable on Monday morning").';
COMMENT ON COLUMN brands.feedback_bonus IS 'Dynamic adjustment to final score based on historical engagement data (0-10 scale).';

-- Note: scoring_weights JSONB remains for weight configuration, not principles
-- Migration data: existing brands will get empty founder_principles and default 5.0 feedback_bonus
-- Brands can be updated individually with their principles:
--   UPDATE brands SET founder_principles = ARRAY['No fluff', 'Actionable on Monday morning'] WHERE slug = 'example';
