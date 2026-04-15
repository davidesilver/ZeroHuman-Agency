-- ============================================================================
-- AI Content Engine - Anti-Hype Gate Examples
-- Migration: 007_anti_hype_gate_columns.sql
-- Purpose: Add gold/discard examples for few-shot anti-hype learning
-- ============================================================================

-- Add gold_examples and discard_examples columns to brands table
ALTER TABLE brands
  ADD COLUMN IF NOT EXISTS gold_examples text[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS discard_examples text[] DEFAULT '{}';

-- Add comments for documentation
COMMENT ON COLUMN brands.gold_examples IS
  'Examples of GOOD content that passes anti-hype gate. Used for few-shot learning.';

COMMENT ON COLUMN brands.discard_examples IS
  'Examples of HYPE content that should be blocked. Used for few-shot learning.';

-- Note: Brands can be updated individually with their examples:
--   UPDATE brands
--   SET gold_examples = ARRAY['Post con dati concreti e case study', 'Tutorial pratico step-by-step'],
--       discard_examples = ARRAY['Affermazioni generiche senza dati', 'Contenuto puramente promozionale']
--   WHERE slug = 'example-brand';
