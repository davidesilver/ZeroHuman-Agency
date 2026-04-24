-- ============================================================================
-- AI Content Engine - Semantic Deduplication
-- Migration: 002_semantic_dedup.sql
-- Description: Adds SQL function for semantic dedup + audit_trail table
-- ============================================================================

SET search_path = public, extensions;

-- ----------------------------------------------------------------------------
-- 1. Semantic similarity search function
-- ----------------------------------------------------------------------------

-- Find research items semantically similar to a given embedding
CREATE OR REPLACE FUNCTION find_semantic_duplicates(
  p_brand_id   uuid,
  p_embedding  vector(1536),
  p_threshold  float DEFAULT 0.85,
  p_limit      int DEFAULT 5
)
RETURNS TABLE (
  id          uuid,
  title       text,
  url         text,
  similarity  float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    ri.id,
    ri.title,
    ri.url,
    1 - (ri.embedding <=> p_embedding) AS similarity
  FROM research_items ri
  WHERE ri.brand_id = p_brand_id
    AND ri.embedding IS NOT NULL
    AND (1 - (ri.embedding <=> p_embedding)) >= p_threshold
  ORDER BY ri.embedding <=> p_embedding
  LIMIT p_limit;
$$;

COMMENT ON FUNCTION find_semantic_duplicates IS
  'Find research items within a brand that are semantically similar to a given embedding. Uses cosine similarity.';


-- Batch update: mark items as semantic duplicates of an earlier item
CREATE OR REPLACE FUNCTION mark_semantic_duplicates(
  p_brand_id   uuid,
  p_threshold  float DEFAULT 0.85
)
RETURNS int
LANGUAGE plpgsql
AS $$
DECLARE
  archived_count int := 0;
  item RECORD;
  dup RECORD;
BEGIN
  -- For each item with an embedding, check if it's a near-duplicate of an earlier item
  FOR item IN
    SELECT ri.id, ri.embedding, ri.created_at
    FROM research_items ri
    WHERE ri.brand_id = p_brand_id
      AND ri.embedding IS NOT NULL
      AND ri.status = 'new'
    ORDER BY ri.created_at ASC
  LOOP
    -- Check if any earlier item is semantically similar
    SELECT INTO dup ri2.id
    FROM research_items ri2
    WHERE ri2.brand_id = p_brand_id
      AND ri2.embedding IS NOT NULL
      AND ri2.id != item.id
      AND ri2.created_at < item.created_at
      AND (1 - (ri2.embedding <=> item.embedding)) >= p_threshold
    LIMIT 1;

    IF FOUND THEN
      UPDATE research_items
      SET status = 'archived',
          metadata = jsonb_set(
            COALESCE(metadata, '{}'),
            '{semantic_duplicate_of}',
            to_jsonb(dup.id::text)
          )
      WHERE id = item.id;
      archived_count := archived_count + 1;
    END IF;
  END LOOP;

  RETURN archived_count;
END;
$$;

COMMENT ON FUNCTION mark_semantic_duplicates IS
  'Batch process: archive research items that are semantic duplicates of earlier items.';


-- ----------------------------------------------------------------------------
-- 2. Audit trail table
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS audit_trail (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id    uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  draft_id    text,
  action      text NOT NULL,
  platform    text DEFAULT '',
  status      text NOT NULL DEFAULT 'success',
  details     jsonb DEFAULT '{}',
  error       text,
  timestamp   timestamptz DEFAULT now()
);

COMMENT ON TABLE audit_trail IS 'Immutable log of publish operations for debugging and compliance.';

CREATE INDEX IF NOT EXISTS idx_audit_trail_brand_action
  ON audit_trail(brand_id, action, timestamp DESC);

-- RLS
ALTER TABLE audit_trail ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "audit_trail_select" ON audit_trail;
CREATE POLICY "audit_trail_select" ON audit_trail
  FOR SELECT USING (brand_id = auth_user_brand_id());

DROP POLICY IF EXISTS "audit_trail_insert" ON audit_trail;
CREATE POLICY "audit_trail_insert" ON audit_trail
  FOR INSERT WITH CHECK (
    brand_id = auth_user_brand_id()
    AND auth_user_role() IN ('owner', 'editor')
  );
