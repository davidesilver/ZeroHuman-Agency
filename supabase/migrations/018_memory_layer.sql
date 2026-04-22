-- Make pgvector's `vector` type visible. Migration 001 installed it in the
-- `extensions` schema; we need it in search_path for this migration.
SET search_path TO public, extensions;

-- ============================================================================
-- Migration 018: Memory layer foundation
--
-- Implements the multi-layered memory architecture defined in the
-- memory-native upgrade plan (§2–§4):
--
--   HOT   memory_hot            — session KV, TTL 24h
--   WARM  memory_semantic       — facts/rules/examples, pgvector, TTL per tier
--   WARM  vw_memory_episodic    — VIEW (no data copy) over existing tables
--   WARM  memory_events         — supplementary events not captured elsewhere
--   COLD  memory_archive        — partitioned monthly, swept from hot/warm
--
-- Also extends agent_skills for procedural memory tracking (P2.3).
--
-- Retrieval scoring formula:
--   score = 0.60·cosine_similarity + 0.25·exp(-0.02·age_days) + 0.15·importance
--
-- TTL tiers:
--   core       — infinite (brand identity, permanent rules)
--   persistent — 365 days
--   standard   — 90 days
--   transient  — 7 days
--
-- Telegram alerts (P2.T, P3.T, P4.T) are Python-side hooks in:
--   memory/consolidation/worker.py  (P2.T)
--   routes.py POST /memory/discover (P3.T)
--   services/newsletter_generator.py (P4.T)
-- All reuse services/alerting.send_telegram_alert (already wired).
-- ============================================================================


-- ============================================================================
-- PART 1 — Enums and types
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'memory_tier') THEN
    CREATE TYPE public.memory_tier AS ENUM (
      'core',        -- permanent, never expires (brand identity, invariants)
      'persistent',  -- long-lived, expires 365d
      'standard',    -- normal, expires 90d
      'transient'    -- short-lived, expires 7d
    );
  END IF;
END;
$$;

-- TTL helper: returns the expiry interval for a given tier.
CREATE OR REPLACE FUNCTION public.memory_ttl(p_tier public.memory_tier)
RETURNS interval LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE p_tier
    WHEN 'core'       THEN NULL               -- NULL = no expiry
    WHEN 'persistent' THEN interval '365 days'
    WHEN 'standard'   THEN interval '90 days'
    WHEN 'transient'  THEN interval '7 days'
  END
$$;

COMMENT ON FUNCTION public.memory_ttl IS
  'Returns the TTL interval for a memory tier. core returns NULL (no expiry).';


-- ============================================================================
-- PART 2 — memory_hot: session scratchpad
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.memory_hot (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id     uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  session_id   text        NOT NULL,
  key          text        NOT NULL,
  value        jsonb       NOT NULL DEFAULT '{}',
  created_at   timestamptz NOT NULL DEFAULT now(),
  expires_at   timestamptz NOT NULL DEFAULT (now() + interval '24 hours'),
  UNIQUE (brand_id, session_id, key)
);

CREATE INDEX IF NOT EXISTS idx_memory_hot_brand_session
  ON public.memory_hot (brand_id, session_id);
CREATE INDEX IF NOT EXISTS idx_memory_hot_expires
  ON public.memory_hot (expires_at);

ALTER TABLE public.memory_hot ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "memory_hot_select" ON public.memory_hot;
CREATE POLICY "memory_hot_select" ON public.memory_hot
  FOR SELECT USING (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS "memory_hot_insert" ON public.memory_hot;
CREATE POLICY "memory_hot_insert" ON public.memory_hot
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS "memory_hot_update" ON public.memory_hot;
CREATE POLICY "memory_hot_update" ON public.memory_hot
  FOR UPDATE USING (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS "memory_hot_delete" ON public.memory_hot;
CREATE POLICY "memory_hot_delete" ON public.memory_hot
  FOR DELETE USING (public.user_has_brand(brand_id));

COMMENT ON TABLE public.memory_hot IS
  'Layer 1 — Hot memory: ephemeral session KV store.
   Rows expire after 24h. Swept by nightly pg_cron job.
   Schema: (brand_id, session_id, key) → value JSONB.';

GRANT SELECT, INSERT, UPDATE, DELETE ON public.memory_hot TO authenticated;


-- ============================================================================
-- PART 3 — memory_semantic: warm semantic store (pgvector)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.memory_semantic (
  id               uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id         uuid            NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,

  -- Content
  kind             text            NOT NULL,   -- 'tone_rule' | 'principle' | 'gold_example' | 'discard_example' | 'fact' | etc.
  statement        text            NOT NULL,
  embedding        vector(1536),               -- text-embedding-3-small, populated async

  -- Importance and tier
  tier             public.memory_tier NOT NULL DEFAULT 'standard',
  importance       numeric(3,2)    NOT NULL DEFAULT 0.50 CHECK (importance BETWEEN 0 AND 1),

  -- Provenance
  source_kind      text,           -- 'document' | 'discovery' | 'writing_lab' | 'manual' | 'api' | etc.
  source_id        uuid,           -- FK to source row (optional, varies by source_kind)

  -- Temporal graph (Graphiti-inspired)
  asserted_at      timestamptz     NOT NULL DEFAULT now(),
  expires_at       timestamptz,               -- NULL for core tier
  supersedes_id    uuid            REFERENCES public.memory_semantic(id) ON DELETE SET NULL,

  -- Retrieval tracking (refresh-on-read)
  last_retrieved   timestamptz,
  retrieval_hits   integer         NOT NULL DEFAULT 0,

  -- Metadata
  metadata         jsonb           NOT NULL DEFAULT '{}',
  created_at       timestamptz     NOT NULL DEFAULT now(),
  updated_at       timestamptz     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_semantic_brand_kind
  ON public.memory_semantic (brand_id, kind);
CREATE INDEX IF NOT EXISTS idx_memory_semantic_brand_tier
  ON public.memory_semantic (brand_id, tier);
CREATE INDEX IF NOT EXISTS idx_memory_semantic_expires
  ON public.memory_semantic (expires_at)
  WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memory_semantic_supersedes
  ON public.memory_semantic (supersedes_id)
  WHERE supersedes_id IS NOT NULL;

-- IVFFlat index for cosine similarity (requires pgvector extension already installed)
-- DO NOT create until table has >= 1000 rows; use sequential scan below that threshold.
-- This index is created as a placeholder — query planner will fall back to seq scan
-- until the row count justifies it.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE tablename = 'memory_semantic'
      AND indexname = 'idx_memory_semantic_embedding'
  ) THEN
    CREATE INDEX idx_memory_semantic_embedding
      ON public.memory_semantic USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 50);   -- 50 lists for small initial dataset
  END IF;
END;
$$;

-- updated_at trigger
CREATE OR REPLACE FUNCTION public.set_memory_semantic_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS memory_semantic_updated_at ON public.memory_semantic;
CREATE TRIGGER memory_semantic_updated_at
  BEFORE UPDATE ON public.memory_semantic
  FOR EACH ROW EXECUTE FUNCTION public.set_memory_semantic_updated_at();

ALTER TABLE public.memory_semantic ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "memory_semantic_select" ON public.memory_semantic;
CREATE POLICY "memory_semantic_select" ON public.memory_semantic
  FOR SELECT USING (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS "memory_semantic_insert" ON public.memory_semantic;
CREATE POLICY "memory_semantic_insert" ON public.memory_semantic
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS "memory_semantic_update" ON public.memory_semantic;
CREATE POLICY "memory_semantic_update" ON public.memory_semantic
  FOR UPDATE USING (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS "memory_semantic_delete" ON public.memory_semantic;
CREATE POLICY "memory_semantic_delete" ON public.memory_semantic
  FOR DELETE USING (public.user_has_brand(brand_id));

COMMENT ON TABLE public.memory_semantic IS
  'Layer 2A — Warm semantic store: facts, rules, principles, examples.
   Each row is an atomic statement about a brand, optionally embedded for similarity
   retrieval. Tier controls TTL (core=infinite, transient=7d).
   supersedes_id creates a temporal graph: old facts are kept but linked to their
   replacement (Arbiter pattern, no deletion of historical data).';

GRANT SELECT, INSERT, UPDATE, DELETE ON public.memory_semantic TO authenticated;


-- ============================================================================
-- PART 4 — memory_events: supplementary event log
-- ============================================================================
-- Only stores events NOT already captured by api_costs / audit_trail /
-- feedback_loop_audit / writing_lab_rounds. Those existing tables are unioned
-- into vw_memory_episodic below without duplicating data.

CREATE TABLE IF NOT EXISTS public.memory_events (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id     uuid        NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  event_kind   text        NOT NULL,   -- e.g. 'discovery_run', 'memory_archived', 'brand_context_import'
  subject_kind text,                   -- e.g. 'research_item', 'content_draft', 'memory_semantic'
  subject_id   uuid,
  summary      text        NOT NULL,
  payload      jsonb       NOT NULL DEFAULT '{}',
  occurred_at  timestamptz NOT NULL DEFAULT now(),
  expires_at   timestamptz          DEFAULT (now() + interval '90 days')
);

CREATE INDEX IF NOT EXISTS idx_memory_events_brand_kind
  ON public.memory_events (brand_id, event_kind, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_events_expires
  ON public.memory_events (expires_at)
  WHERE expires_at IS NOT NULL;

ALTER TABLE public.memory_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "memory_events_select" ON public.memory_events;
CREATE POLICY "memory_events_select" ON public.memory_events
  FOR SELECT USING (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS "memory_events_insert" ON public.memory_events;
CREATE POLICY "memory_events_insert" ON public.memory_events
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
DROP POLICY IF EXISTS "memory_events_delete" ON public.memory_events;
CREATE POLICY "memory_events_delete" ON public.memory_events
  FOR DELETE USING (public.user_has_brand(brand_id));

COMMENT ON TABLE public.memory_events IS
  'Supplementary event log for episodes not captured in existing tables.
   NOT a copy of api_costs/audit_trail/writing_lab_rounds — those are
   UNION-ed in vw_memory_episodic without duplication.';

GRANT SELECT, INSERT, DELETE ON public.memory_events TO authenticated;


-- ============================================================================
-- PART 5 — memory_archive: cold storage, partitioned by month
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.memory_archive (
  id            uuid        NOT NULL DEFAULT gen_random_uuid(),
  brand_id      uuid        NOT NULL,   -- no FK — brand may be deleted
  origin_table  text        NOT NULL,   -- 'memory_semantic' | 'memory_hot' | 'memory_events'
  origin_id     uuid        NOT NULL,
  payload       jsonb       NOT NULL,   -- full row snapshot at archival time
  archived_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id, archived_at)
) PARTITION BY RANGE (archived_at);

-- Bootstrap partition for current month (subsequent months created by cron)
DO $$
DECLARE
  v_start date := date_trunc('month', now())::date;
  v_end   date := (date_trunc('month', now()) + interval '1 month')::date;
  v_name  text := 'memory_archive_' || to_char(now(), 'YYYYMM');
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_class
    WHERE relname = v_name AND relkind = 'r'
  ) THEN
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS public.%I PARTITION OF public.memory_archive
       FOR VALUES FROM (%L) TO (%L)',
      v_name, v_start, v_end
    );
  END IF;
END;
$$;

COMMENT ON TABLE public.memory_archive IS
  'Layer 3 — Cold archive: serialized snapshots of expired/superseded memory rows.
   Partitioned by archived_at (monthly). No RLS — only accessible server-side.
   Retrieval via direct SQL query from admin/scheduler context only.';


-- ============================================================================
-- PART 6 — vw_memory_episodic: unified episodic view (zero data duplication)
-- ============================================================================
-- Unions 5 existing sources + memory_events into a single feed.
-- Python code reads one view and gets retroactive history from all sources.

CREATE OR REPLACE VIEW public.vw_memory_episodic AS

-- 1. LLM calls from api_costs
SELECT
  'llm_call'::text                           AS event_kind,
  brand_id,
  agent_name                                 AS subject_kind,
  NULL::uuid                                 AS subject_id,
  format('%s %s | tokens=%s cost=$%s',
    agent_name, operation,
    COALESCE(tokens_input, 0) + COALESCE(tokens_output, 0),
    ROUND(COALESCE(cost_usd, 0)::numeric, 4)
  )                                          AS summary,
  jsonb_build_object(
    'model',      model,
    'latency_ms', latency_ms,
    'tokens_in',  tokens_input,
    'tokens_out', tokens_output,
    'cost_usd',   cost_usd
  )                                          AS payload,
  created_at                                 AS occurred_at
FROM public.api_costs

UNION ALL

-- 2. Publish / status changes from audit_trail
--    audit_trail.draft_id is TEXT (not UUID), so we cast carefully.
SELECT
  action::text                               AS event_kind,
  brand_id,
  'content_draft'::text                      AS subject_kind,
  -- Safe text→uuid cast: if the value doesn't look like a UUID, use NULL
  CASE
    WHEN draft_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    THEN draft_id::uuid
    ELSE NULL::uuid
  END                                        AS subject_id,
  format('%s → %s on %s', action, status, platform) AS summary,
  jsonb_build_object(
    'draft_id', draft_id
  ) || COALESCE(details, '{}')               AS payload,
  timestamp                                  AS occurred_at
FROM public.audit_trail
WHERE draft_id IS NOT NULL

UNION ALL

-- 3. Feedback loop scoring adjustments
SELECT
  'feedback_bonus'::text                     AS event_kind,
  brand_id,
  'scores'::text                             AS subject_kind,
  NULL::uuid                                 AS subject_id,
  format('bonus %s → %s (Δ%s)',
    previous_bonus, new_bonus, score_delta)  AS summary,
  jsonb_build_object(
    'previous_bonus', previous_bonus,
    'new_bonus',      new_bonus,
    'score_delta',    score_delta,
    'metrics_used',   metrics_used
  )                                          AS payload,
  executed_at                                AS occurred_at
FROM public.feedback_loop_audit

UNION ALL

-- 4. Writing lab votes (closes the feedback downstream gap)
SELECT
  'writing_lab_vote'::text                   AS event_kind,
  wls.brand_id,
  'writing_lab_session'::text                AS subject_kind,
  wls.id                                     AS subject_id,
  format('round %s winner: %s',
    wlr.round_number,
    COALESCE(wlr.winner::text, 'undecided'))  AS summary,
  jsonb_build_object(
    'round',    wlr.round_number,
    'winner',   wlr.winner::text,
    'feedback', wlr.user_feedback
  )                                          AS payload,
  wlr.created_at                             AS occurred_at
FROM public.writing_lab_rounds wlr
JOIN public.writing_lab_sessions wls ON wls.id = wlr.session_id

UNION ALL

-- 5. Custom events (discovery runs, memory operations, etc.)
SELECT
  event_kind,
  brand_id,
  subject_kind,
  subject_id,
  summary,
  payload,
  occurred_at
FROM public.memory_events
WHERE expires_at IS NULL OR expires_at > now();

COMMENT ON VIEW public.vw_memory_episodic IS
  'Unified episodic memory view. Zero data duplication — each branch reads from
   its source table via UNION ALL. Sources: api_costs, audit_trail,
   feedback_loop_audit, writing_lab_rounds, memory_events.
   Consumers: Pipeline Health dashboard, memory retrieval, Telegram alerts.';

GRANT SELECT ON public.vw_memory_episodic TO authenticated;


-- ============================================================================
-- PART 7 — SQL helper functions
-- ============================================================================

-- 7a. memory_touch: refresh-on-read — resets expiry + increments hit counter.
--     Called by memory.recall() in Python after each successful retrieval.
CREATE OR REPLACE FUNCTION public.memory_touch(p_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY INVOKER AS $$
DECLARE
  v_tier public.memory_tier;
  v_ttl  interval;
BEGIN
  SELECT tier INTO v_tier
  FROM public.memory_semantic
  WHERE id = p_id;

  IF NOT FOUND THEN RETURN; END IF;

  v_ttl := public.memory_ttl(v_tier);

  UPDATE public.memory_semantic
  SET
    retrieval_hits  = retrieval_hits + 1,
    last_retrieved  = now(),
    -- Refresh expiry only for non-core rows (core has NULL expires_at)
    expires_at      = CASE
                        WHEN v_ttl IS NULL THEN NULL
                        ELSE now() + v_ttl
                      END
  WHERE id = p_id;
END;
$$;

COMMENT ON FUNCTION public.memory_touch IS
  'Refresh-on-read: increments retrieval_hits and resets expires_at for a
   memory_semantic row. Mimics biological reinforcement — frequently-read
   memories decay slower.';


-- 7b. memory_search: temporal-weighted semantic retrieval.
--     score = 0.60·cosine + 0.25·exp(-0.02·age_days) + 0.15·importance
--     Caller must supply the query embedding as a vector string or cast.
--
--     Args:
--       p_brand_id  — brand scope (required)
--       p_embedding — query vector as text '0.1,0.2,...' (must cast to vector)
--       p_kind      — filter by kind (NULL = all kinds)
--       p_limit     — max results (default 10)
--
--     Returns rows ordered by composite score DESC.
CREATE OR REPLACE FUNCTION public.memory_search(
  p_brand_id  uuid,
  p_embedding vector(1536),
  p_kind      text    DEFAULT NULL,
  p_limit     integer DEFAULT 10
)
RETURNS TABLE (
  id          uuid,
  kind        text,
  statement   text,
  tier        public.memory_tier,
  importance  numeric,
  similarity  float,
  age_days    float,
  score       float
)
LANGUAGE sql STABLE SECURITY INVOKER AS $$
  SELECT
    ms.id,
    ms.kind,
    ms.statement,
    ms.tier,
    ms.importance,
    -- Cosine similarity (pgvector: 1 - <=> distance)
    ROUND((1 - (ms.embedding <=> p_embedding))::numeric, 4)::float AS similarity,
    ROUND(EXTRACT(EPOCH FROM (now() - ms.asserted_at)) / 86400.0, 1)::float AS age_days,
    -- Composite score: 60% cosine + 25% recency decay + 15% importance
    ROUND((
      0.60 * (1 - (ms.embedding <=> p_embedding)) +
      0.25 * EXP(-0.02 * EXTRACT(EPOCH FROM (now() - ms.asserted_at)) / 86400.0) +
      0.15 * ms.importance::float
    )::numeric, 4)::float                                            AS score
  FROM public.memory_semantic ms
  WHERE ms.brand_id = p_brand_id
    AND ms.embedding IS NOT NULL
    AND (ms.expires_at IS NULL OR ms.expires_at > now())
    AND (p_kind IS NULL OR ms.kind = p_kind)
  ORDER BY score DESC
  LIMIT p_limit
$$;

COMMENT ON FUNCTION public.memory_search IS
  'Temporal-weighted semantic search.
   score = 0.60·cosine_similarity + 0.25·exp(-0.02·age_days) + 0.15·importance.
   Only returns non-expired rows with a populated embedding.
   Call memory_touch(id) after reading results to refresh TTL.';


-- ============================================================================
-- PART 8 — Extend agent_skills for procedural memory
-- ============================================================================

ALTER TABLE public.agent_skills
  ADD COLUMN IF NOT EXISTS success_count       integer     NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS failure_count       integer     NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_optimized_at   timestamptz,
  ADD COLUMN IF NOT EXISTS optimization_history jsonb      NOT NULL DEFAULT '[]';

COMMENT ON COLUMN public.agent_skills.success_count IS
  'Number of successful invocations tracked since last reset. Used for procedural memory optimization.';
COMMENT ON COLUMN public.agent_skills.failure_count IS
  'Number of failed/rejected invocations. High ratio triggers prompt optimization.';
COMMENT ON COLUMN public.agent_skills.optimization_history IS
  'JSON array of past optimization events: [{date, reason, old_prompt_hash, new_prompt_hash}].';


-- ============================================================================
-- PART 9 — pg_cron jobs
-- ============================================================================
-- Idempotent: unschedule if exists, then re-schedule.

DO $$
BEGIN
  -- ── Nightly TTL sweep ─────────────────────────────────────────────────────
  -- Removes expired hot session keys, archives + deletes expired semantic
  -- rows, and purges expired memory_events. Runs 03:30 UTC every day.
  BEGIN PERFORM cron.unschedule('memory-ttl-sweep'); EXCEPTION WHEN OTHERS THEN NULL; END;
  PERFORM cron.schedule(
    'memory-ttl-sweep',
    '30 3 * * *',
    'DELETE FROM public.memory_hot WHERE expires_at < now();'
    '  INSERT INTO public.memory_archive (brand_id, origin_table, origin_id, payload)'
    '  SELECT brand_id, ''memory_semantic'', id, row_to_json(memory_semantic)::jsonb'
    '  FROM public.memory_semantic WHERE expires_at IS NOT NULL AND expires_at < now();'
    '  DELETE FROM public.memory_semantic WHERE expires_at IS NOT NULL AND expires_at < now();'
    '  DELETE FROM public.memory_events WHERE expires_at IS NOT NULL AND expires_at < now();'
  );

  -- ── Monthly archive partition creation ────────────────────────────────────
  -- Creates next month's partition on the 1st at 00:05 UTC.
  BEGIN PERFORM cron.unschedule('memory-archive-partition'); EXCEPTION WHEN OTHERS THEN NULL; END;
  PERFORM cron.schedule(
    'memory-archive-partition',
    '5 0 1 * *',
    $cmd$
      DO $inner$
      DECLARE
        v_start date := date_trunc('month', now() + interval '1 month')::date;
        v_end   date := date_trunc('month', now() + interval '2 months')::date;
        v_name  text := 'memory_archive_' || to_char(now() + interval '1 month', 'YYYYMM');
      BEGIN
        IF NOT EXISTS (
          SELECT 1 FROM pg_class WHERE relname = v_name AND relkind = 'r'
        ) THEN
          EXECUTE format(
            'CREATE TABLE IF NOT EXISTS public.%I PARTITION OF public.memory_archive
             FOR VALUES FROM (%L) TO (%L)',
            v_name, v_start, v_end
          );
        END IF;
      END;
      $inner$
    $cmd$
  );
END;
$$;
