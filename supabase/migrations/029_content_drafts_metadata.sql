-- 029_content_drafts_metadata.sql
-- Add metadata jsonb column to content_drafts.
-- Used by postiz_publisher.py to persist postiz_post_ids per platform so
-- postiz_analytics.py can pull Postiz metrics for published/scheduled posts.
BEGIN;

SET search_path TO public, extensions;

ALTER TABLE content_drafts
  ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}';

COMMENT ON COLUMN content_drafts.metadata IS
  'Opaque metadata bag. Holds postiz_post_ids (platform -> Postiz post ID) '
  'and scheduled_platforms used by the social publishing pipeline.';

COMMIT;
