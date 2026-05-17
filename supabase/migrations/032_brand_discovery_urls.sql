-- Migration 032: Add discovery_urls field to brands table
-- Stores the URLs used in brand auto-discovery so they can be shown in the UI
-- and re-discovery can reference the same sources.

ALTER TABLE public.brands
  ADD COLUMN IF NOT EXISTS discovery_urls text[] DEFAULT '{}';

COMMENT ON COLUMN public.brands.discovery_urls IS
  'URLs and social profile links used in the last brand auto-discovery run.';
