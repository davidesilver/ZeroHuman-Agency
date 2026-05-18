-- 030_audit_indexes_and_search_path.sql
-- P10 audit follow-up (2026-04-25):
--   1. Harden bootstrap SECURITY DEFINER helpers from migration 001 with an
--      explicit search_path so they cannot be hijacked by a malicious schema
--      placed earlier on a caller's search_path (CVE-2018-1058 class).
--   2. Add the indexes flagged by the DB audit as missing on hot query paths.
--
-- All statements are idempotent (CREATE OR REPLACE FUNCTION / IF NOT EXISTS)
-- so this migration is safe to re-apply.
BEGIN;

SET search_path TO public, extensions;

-- ============================================================================
-- 1. SECURITY DEFINER hardening
-- ============================================================================
-- Migration 017 already replaced auth_user_brand_id() with a SECURITY INVOKER
-- variant; this re-asserts it for safety on databases where 017 may be
-- re-applied or a future migration toggles SECURITY DEFINER again.
CREATE OR REPLACE FUNCTION public.auth_user_brand_id()
RETURNS uuid
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public, pg_temp AS $$
  SELECT brand_id
  FROM   public.brand_members
  WHERE  user_id = auth.uid()
  ORDER  BY created_at ASC
  LIMIT  1
$$;

-- auth_user_role() was never updated since migration 001 and was the only
-- SECURITY DEFINER helper still missing search_path.  Lock it down here.
CREATE OR REPLACE FUNCTION public.auth_user_role()
RETURNS user_role
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp AS $$
  SELECT role FROM public.users WHERE id = auth.uid()
$$;

-- ============================================================================
-- 2. Missing indexes (P1 from audit)
-- ============================================================================
-- Discovery dashboard: list latest items per brand.
CREATE INDEX IF NOT EXISTS idx_research_items_brand_created_desc
  ON research_items(brand_id, created_at DESC);

-- Memory TTL sweep: cron deletes expired semantic rows per brand.
CREATE INDEX IF NOT EXISTS idx_memory_semantic_brand_expires
  ON memory_semantic(brand_id, expires_at DESC)
  WHERE expires_at IS NOT NULL;

-- Memory hot KV lookup by (brand, key).
CREATE INDEX IF NOT EXISTS idx_memory_hot_brand_key
  ON memory_hot(brand_id, key);

-- Draft version chain traversal (parent_draft_id self-ref).
CREATE INDEX IF NOT EXISTS idx_content_drafts_parent_id
  ON content_drafts(parent_draft_id)
  WHERE parent_draft_id IS NOT NULL;

-- Cost dashboard: latest spend per (brand, agent).
CREATE INDEX IF NOT EXISTS idx_api_costs_brand_agent_created
  ON api_costs(brand_id, agent_name, created_at DESC);

-- Pipeline health: latest event per (brand, agent).
CREATE INDEX IF NOT EXISTS idx_pipeline_health_brand_agent_latest
  ON pipeline_health(brand_id, agent_name, created_at DESC);

-- ============================================================================
-- 3. Aggregate RPC for /api/research/stats
-- ============================================================================
-- Replaces a Python-side loop over every research_item row (P0 N+1 from audit)
-- with a single GROUP BY executed in Postgres.  Returns a JSON object with
-- counts keyed by status plus a `total`.  RLS is enforced because the function
-- runs as SECURITY INVOKER under the caller's session.
CREATE OR REPLACE FUNCTION public.research_items_status_counts(p_brand_id uuid)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public, pg_temp AS $$
  WITH base AS (
    SELECT status, count(*)::bigint AS n
    FROM   public.research_items
    WHERE  brand_id = p_brand_id
    GROUP  BY status
  ), totals AS (
    SELECT coalesce(sum(n), 0)::bigint AS total FROM base
  )
  SELECT jsonb_build_object(
    'total',    (SELECT total FROM totals),
    'new',      coalesce((SELECT n FROM base WHERE status = 'new'),      0),
    'scored',   coalesce((SELECT n FROM base WHERE status = 'scored'),   0),
    'approved', coalesce((SELECT n FROM base WHERE status = 'approved'), 0),
    'rejected', coalesce((SELECT n FROM base WHERE status = 'rejected'), 0),
    'archived', coalesce((SELECT n FROM base WHERE status = 'archived'), 0)
  )
$$;

GRANT EXECUTE ON FUNCTION public.research_items_status_counts(uuid)
  TO anon, authenticated, service_role;

COMMIT;
