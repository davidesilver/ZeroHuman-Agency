# Memory-Native Upgrade Plan

**Status**: Draft 1 — awaiting user approval per phase
**Author**: Claude (Opus) + Davide
**Date**: 2026-04-21
**Grounding reports**:
- *Implementation Roadmap: Deploying Multi-Layered Memory Systems for AI Agents*
- *Technical Selection Framework: Enterprise Memory for Agentic AI*

---

## 0. Strategic Frame

The project today is a **stateless** pipeline: every LLM call re-injects context from scratch. The two reports above converge on a clear thesis — the durable differentiator is **memory infrastructure**, not model choice. Concretely:

> *"As models become interchangeable commodities, the agent's identity lives in its memory rather than its model weights."*

Translating to this project:

- Brand "identity" (tone, principles, examples) cannot live in a static JSON field that nobody edits. It must live in a **warm semantic store** that is populated by discovery, refined by use, and decays when stale.
- Writing-lab preferences, GOD-mode outcomes, and user feedback are **episodic signals** that today evaporate. They must feed back into retrieval ranking.
- Skill runbooks (`agent_skills`) are **procedural memory** already in the right shape but disconnected from feedback.
- Multi-brand is not "a feature" — it is a **tenant isolation boundary** that memory infra must respect from day one, or retrofit will be painful.

This plan is therefore **memory-first, features-second**. Features (newsletter generate, brand editor, retrievers) are built *on top of* the memory foundation. The ordering is deliberate.

---

## 1. Tech decisions (committed)

These are decided unless explicitly contested. Every alternative was considered; reasoning below.

| Decision | Choice | Why |
|---|---|---|
| **Memory storage engine** | Postgres + pgvector (Supabase) | Already installed, RLS already brand-scoped, zero new infra to operate, cost scales linearly with Supabase usage. |
| **Memory framework** | **Custom Python module** `content_engine/memory/` patterned on Mem0+Graphiti, **not** the Mem0/Zep SDK | Avoids second source of truth / vendor coupling. Can add Mem0 SDK later as thin compression layer if token savings become material. |
| **Extraction model** (consolidation) | Claude Haiku via OpenRouter | Report recommends small MoE (Llama 4 Scout). Haiku is the equivalent-cost Claude equivalent, already wired in `OPENROUTER_API_KEY`. |
| **Synthesis model** | Claude Sonnet (existing default) | No change. |
| **Temporal graph** | Inline via SQL columns (`asserted_at`, `expired_at`, `supersedes_id`) | Avoids Neo4j. Traversal done with recursive CTE when needed. Matches Graphiti semantics at a fraction of ops cost. |
| **TTL / decay** | `expires_at` column + nightly vacuum cron + refresh-on-read trigger | Direct translation of MaRS/FadeMem. Simple, auditable. |
| **Multi-brand model** | N:M via `brand_members` junction table + active-brand cookie | No user-facing account duplication. RLS rewrite is mechanical. |
| **Active-brand resolution** | Cookie `active_brand_id` + server-side middleware validates membership | Works for both Next.js and FastAPI. Survives refresh. |

### Explicitly rejected

- **Mem0 SDK as primary store** — adds framework lock-in, fights our RLS model, we want the architectural understanding that comes from building the layer ourselves.
- **Zep/Graphiti with Neo4j** — new DB to operate, too heavy for current scale. Revisit if we cross ~1M memories.
- **Cloudflare Agent Memory** — project is Vercel-native; adding Cloudflare Durable Objects for this alone is not justified.
- **LangMem** — useful primitive for procedural learning but requires buying into LangGraph; we can steal the pattern (auto-optimize prompts based on past performance) without the framework.

---

## 2. Memory architecture — the 5 stores

Mapped onto the taxonomy from *Technical Selection Framework §2*:

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1 — HOT (session, ephemeral)                              │
│   Table: memory_hot                                              │
│   TTL: session end or 24h whichever first                        │
│   Contents: current task scratchpad, intermediate tool results   │
└─────────────────────────────────────────────────────────────────┘
                          ↓ consolidation (async, 8-point verified)
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2 — WARM                                                  │
│                                                                 │
│  A. memory_semantic    (facts, rules, principles, examples)     │
│     → pgvector, brand_id scoped, TTL per importance tier        │
│                                                                 │
│  B. memory_episodic    (what happened when)                     │
│     → timestamped rows, brand_id scoped, TTL 90d default        │
│     → e.g. "Draft X was rejected by GOD mode for reason Y"      │
│                                                                 │
│  C. memory_procedural  (how to do things)                       │
│     → extends existing agent_skills, adds performance metrics   │
│     → auto-refines prompts based on success rate                │
└─────────────────────────────────────────────────────────────────┘
                          ↓ decay + compaction
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3 — COLD (archive, compliance)                            │
│   Table: memory_archive (partitioned monthly)                    │
│   Contents: serialized past sessions, expired facts, full drafts │
│   Retrieval: cold path only, not in active index                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Consolidation pipeline (8-point verifier)

Runs asynchronously via Python worker triggered by:
- End of writing-lab session
- After each successful content generation
- Nightly batch (`04:00 UTC`) sweeping hot → warm

Each candidate fact runs through the 8 checks from the report. Reject if any fail:

```
1. entity_identity   — maps to known actor UUID, or creates new with disambiguation
2. object_identity   — tracked item across sessions (draft_id, research_item_id)
3. location_context  — platform / channel grounded
4. temporal_accuracy — absolute ISO timestamps, no "yesterday"
5. org_context       — brand_id resolved
6. completeness      — not a fragment (≥ 20 chars, complete sentence)
7. relational        — has at least one edge to existing memory node OR is seed
8. inference_support — traceable back to source_id
```

A candidate that fails → moved to `memory_rejected` with reason (useful for pipeline debugging, not indexed).

### 2.2 Retrieval — temporal-weighted composite score

From *Implementation Roadmap §4*:

```python
score = (α * cosine_similarity)
      + (β * exp(-λ * age_days))
      + (γ * importance_tier)
      - (δ * conflict_penalty)
```

Defaults: α=0.6, β=0.25, γ=0.15, δ=0.3, λ=0.02 (half-life ~35 days).

### 2.3 Conflict resolution — Arbiter Agent

When a new fact contradicts an existing one (e.g., brand rule changes):
1. Do NOT delete the old fact.
2. Set `expired_at = now()` on old fact.
3. Insert new fact with `supersedes_id = old.id`.
4. Background LLM call generates a *temporal reflection summary* stored in `memory_episodic` describing the pivot.
5. Retrieval ranker picks up only un-expired facts by default; `supersedes_id` chain is traversable on demand for audit.

---

## 3. Schema (migration 017 + 018)

> **Migration 017**: multi-brand N:M (foundation for everything else)
> **Migration 018**: memory layer tables + RLS + helper functions

### 3.1 Migration 017 — multi-brand

```sql
-- brand_members: replaces the 1:1 users.brand_id relationship
CREATE TABLE IF NOT EXISTS public.brand_members (
  user_id    uuid NOT NULL REFERENCES auth.users(id)   ON DELETE CASCADE,
  brand_id   uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  role       public.user_role NOT NULL DEFAULT 'editor',
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, brand_id)
);

-- Backfill from users.brand_id
INSERT INTO public.brand_members (user_id, brand_id, role)
SELECT id, brand_id, role FROM public.users
ON CONFLICT DO NOTHING;

-- Helper: active brand for current session.
-- Reads cookie via a request-local GUC set by middleware.
CREATE OR REPLACE FUNCTION public.active_brand_id()
RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT COALESCE(
    NULLIF(current_setting('request.active_brand_id', true), '')::uuid,
    -- Fallback: first brand the user belongs to (deterministic: oldest membership)
    (SELECT brand_id FROM public.brand_members
      WHERE user_id = auth.uid()
      ORDER BY created_at ASC LIMIT 1)
  );
$$;

-- RLS rewrite (example for one table; applied to all brand-scoped tables)
DROP POLICY IF EXISTS "research_items_select" ON public.research_items;
CREATE POLICY "research_items_select" ON public.research_items
  FOR SELECT TO authenticated
  USING (brand_id IN (SELECT brand_id FROM public.brand_members WHERE user_id = auth.uid()));
-- (repeat pattern for all tables currently scoped by users.brand_id)

-- Deprecate users.brand_id: keep column for now, stop using it.
-- Drop in migration 020 after all code paths migrated.
COMMENT ON COLUMN public.users.brand_id IS
  'DEPRECATED as of migration 017. Use brand_members. Will be dropped in 020.';

-- Update create_brand_with_owner RPC (from migration 015)
-- to use brand_members instead of users.brand_id.
CREATE OR REPLACE FUNCTION public.create_brand_with_owner(
  p_name text, p_slug text, p_topics text[] DEFAULT '{}'
) RETURNS json ...
-- BODY: same as 015 but inserts into brand_members instead of users.
-- ALSO: removes the "user_already_has_brand" guard — now N:M allowed.
```

**Impact surface**:
- ~18 RLS policies to rewrite (mechanical find/replace).
- Python `auth_middleware.py`: resolve `brand_id` from `X-Active-Brand` header + membership check instead of from user row.
- Next.js `auth-helpers.ts` `requireAuth()`: returns `{ userId, activeBrandId, memberBrands: [...] }`.
- All RPC/routes that read `users.brand_id` directly → switch to `active_brand_id()` or middleware value.

### 3.2 Migration 018 — memory layer

```sql
-- ============================================================================
-- Importance tiers (drives TTL assignment)
-- ============================================================================
CREATE TYPE public.memory_tier AS ENUM (
  'core',       -- immutable brand facts, infinite TTL
  'persistent', -- ~1 year default
  'standard',   -- ~90 days
  'transient'   -- ~7 days
);

-- Map tier → interval
CREATE OR REPLACE FUNCTION public.memory_ttl(t public.memory_tier)
RETURNS interval LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE t
    WHEN 'core'       THEN NULL::interval       -- no expiry
    WHEN 'persistent' THEN interval '365 days'
    WHEN 'standard'   THEN interval '90 days'
    WHEN 'transient'  THEN interval '7 days'
  END
$$;

-- ============================================================================
-- memory_semantic — facts, rules, principles, examples (the "brand brain")
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.memory_semantic (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id       uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  kind           text NOT NULL,  -- 'tone_rule'|'principle'|'gold_example'|'discard_example'|'fact'
  statement      text NOT NULL,
  embedding      vector(1536),
  tier           public.memory_tier NOT NULL DEFAULT 'standard',
  importance     numeric(3,2) NOT NULL DEFAULT 0.50,  -- 0..1 from verifier
  source_kind    text,   -- 'discover-agent'|'user-edit'|'feedback-loop'
  source_id      uuid,   -- draft/research/session that produced this
  asserted_at    timestamptz NOT NULL DEFAULT now(),
  expires_at     timestamptz,            -- NULL for 'core' tier
  supersedes_id  uuid REFERENCES public.memory_semantic(id) ON DELETE SET NULL,
  last_retrieved timestamptz,            -- refresh-on-read
  retrieval_hits int NOT NULL DEFAULT 0,
  metadata       jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_memory_semantic_brand_kind ON public.memory_semantic(brand_id, kind);
CREATE INDEX idx_memory_semantic_embedding
  ON public.memory_semantic USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
CREATE INDEX idx_memory_semantic_active ON public.memory_semantic(brand_id)
  WHERE expires_at IS NULL OR expires_at > now();

-- ============================================================================
-- memory_episodic — what happened when (events, feedback, outcomes)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.memory_episodic (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id    uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  actor_id    uuid,   -- user_id if human, NULL if agent
  event_kind  text NOT NULL, -- 'draft_rejected'|'draft_approved'|'vote_cast'|'publish_success'|'metric_pulled'
  subject_kind text,         -- 'content_draft'|'research_item'|'newsletter'
  subject_id  uuid,
  summary     text NOT NULL,
  payload     jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz NOT NULL DEFAULT (now() + interval '90 days')
);
CREATE INDEX idx_memory_episodic_brand_time ON public.memory_episodic(brand_id, occurred_at DESC);
CREATE INDEX idx_memory_episodic_subject ON public.memory_episodic(subject_kind, subject_id);

-- ============================================================================
-- memory_hot — session scratchpad, short-lived
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.memory_hot (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id   uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  session_id text NOT NULL,     -- free-form, caller-supplied
  key        text NOT NULL,
  value      jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL DEFAULT (now() + interval '24 hours'),
  UNIQUE (brand_id, session_id, key)
);
CREATE INDEX idx_memory_hot_expiry ON public.memory_hot(expires_at);

-- memory_procedural is NOT a new table — we extend agent_skills.
ALTER TABLE public.agent_skills
  ADD COLUMN IF NOT EXISTS success_count   int NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS failure_count   int NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_optimized_at timestamptz,
  ADD COLUMN IF NOT EXISTS optimization_history jsonb NOT NULL DEFAULT '[]'::jsonb;

-- ============================================================================
-- memory_archive (cold, partitioned monthly)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.memory_archive (
  id          uuid NOT NULL DEFAULT gen_random_uuid(),
  brand_id    uuid NOT NULL,
  archived_at timestamptz NOT NULL DEFAULT now(),
  origin      text NOT NULL,  -- 'memory_semantic'|'memory_episodic'|'content_drafts'
  payload     jsonb NOT NULL,
  PRIMARY KEY (id, archived_at)
) PARTITION BY RANGE (archived_at);

-- Create first partition; cron job will create rolling partitions.
CREATE TABLE public.memory_archive_202604 PARTITION OF public.memory_archive
  FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- ============================================================================
-- RLS — scope by brand_members membership (same pattern as 017)
-- ============================================================================
ALTER TABLE public.memory_semantic  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_episodic  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_hot       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_archive   ENABLE ROW LEVEL SECURITY;

-- Policies: SELECT/INSERT/UPDATE/DELETE scoped to brand_members (repeat pattern)
-- ... (omitted for brevity; generated from template)

-- ============================================================================
-- Helper: record a retrieval hit (refresh-on-read)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.memory_touch(p_id uuid)
RETURNS void LANGUAGE sql AS $$
  UPDATE public.memory_semantic
    SET last_retrieved = now(),
        retrieval_hits = retrieval_hits + 1,
        expires_at = CASE
          WHEN tier = 'core' THEN NULL
          ELSE now() + public.memory_ttl(tier)
        END
    WHERE id = p_id;
$$;

-- ============================================================================
-- Helper: search warm semantic with temporal-weighted composite score
-- ============================================================================
CREATE OR REPLACE FUNCTION public.memory_search(
  p_brand_id uuid,
  p_query_embedding vector(1536),
  p_kind text DEFAULT NULL,
  p_limit int DEFAULT 10
) RETURNS TABLE (
  id uuid, statement text, kind text, tier public.memory_tier,
  similarity float, age_days float, score float
) LANGUAGE sql STABLE AS $$
  SELECT
    m.id, m.statement, m.kind, m.tier,
    1 - (m.embedding <=> p_query_embedding) AS similarity,
    EXTRACT(EPOCH FROM (now() - m.asserted_at)) / 86400 AS age_days,
    (0.60 * (1 - (m.embedding <=> p_query_embedding)))
    + (0.25 * exp(-0.02 * EXTRACT(EPOCH FROM (now() - m.asserted_at)) / 86400))
    + (0.15 * m.importance)
    AS score
  FROM public.memory_semantic m
  WHERE m.brand_id = p_brand_id
    AND (m.expires_at IS NULL OR m.expires_at > now())
    AND (p_kind IS NULL OR m.kind = p_kind)
    AND m.embedding IS NOT NULL
  ORDER BY score DESC
  LIMIT p_limit;
$$;
```

---

## 4. Python module — `content_engine/memory/`

New package structure:

```
python/src/content_engine/memory/
├── __init__.py              # public API: store, recall, forget, consolidate
├── stores/
│   ├── hot.py               # session KV operations
│   ├── semantic.py          # pgvector + temporal weighted search
│   ├── episodic.py          # event log
│   └── archive.py           # cold tier
├── consolidation/
│   ├── verifier.py          # 8-point check
│   ├── extractor.py         # Haiku-based fact extraction
│   ├── synthesizer.py       # Sonnet-based summary generation
│   └── worker.py            # async pipeline driver
├── decay.py                 # TTL expiry, refresh-on-read
├── arbiter.py               # conflict resolution + temporal reflection
└── retrieval.py             # unified recall() with temporal weighting
```

Public API (what every agent uses):

```python
from content_engine.memory import memory

# Store (synchronous, raw — not consolidated yet)
await memory.hot.put(brand_id, session_id, key, value)
await memory.episodic.log(brand_id, event_kind, summary, subject_id, payload)

# Recall (synchronous, fast)
facts = await memory.recall(brand_id, query="brand voice rules", kind="tone_rule", k=5)

# Explicit consolidation (background-safe)
await memory.consolidate.schedule(brand_id, session_id)

# Explicit forget (Arbiter-mediated)
await memory.arbiter.supersede(old_id, new_statement, reason)
```

---

## 5. Phased roadmap

### P0 — Crisis fixes (3 days)

Unblock current bugs *without* committing architectural direction. Ship these regardless of downstream phases.

| # | Task | File(s) |
|---|---|---|
| P0.1 | Fix `calendar_events` GET schema mismatch (`scheduled_at`→`scheduled_date`, `content_draft_id`→`draft_id`) | `src/app/api/calendar/events/route.ts` |
| P0.2 | Disable "Generate Newsletter" button with "Coming soon" tooltip; remove 500s from console | `src/app/(dashboard)/newsletter/page.tsx` |
| P0.3 | Implement `PATCH`/`DELETE /api/brands/[id]` + edit dialog in Brands page (for name/topics only, not tone/weights yet) | `src/app/api/brands/[id]/route.ts` (NEW), `src/app/(dashboard)/brands/page.tsx` |
| P0.4 | Regenerate TS types after migration 016 deploys | `src/lib/types/database.types.ts` |

**Gate**: zero 500s in browser console on dashboard load.

---

### P1 — Multi-brand N:M (5 days)

Must happen before memory layer. Memory layer assumes correct tenant isolation.

| # | Task | Artifact |
|---|---|---|
| P1.1 | Migration 017 — `brand_members` + backfill + `active_brand_id()` helper | `supabase/migrations/017_multi_brand_membership.sql` |
| P1.2 | Rewrite RLS policies on all brand-scoped tables to use `brand_members` | inside 017 |
| P1.3 | Update `create_brand_with_owner` RPC to use new junction, drop `user_already_has_brand` guard | inside 017 |
| P1.4 | Next.js `requireAuth()` returns `{ activeBrandId, memberBrands }`; reads `active_brand_id` cookie; validates membership | `src/lib/supabase/auth-helpers.ts` |
| P1.5 | Python `auth_middleware.py` resolves brand_id from `X-Active-Brand` header + membership query | `python/src/content_engine/api/auth_middleware.py` |
| P1.6 | Brand switcher component in dashboard header | `src/components/layout/brand-switcher.tsx` (NEW) |
| P1.7 | "Invite teammate" / "Add another brand" flow in `/settings` | `src/app/(dashboard)/settings/page.tsx` |
| P1.8 | Regenerate TS types | `database.types.ts` |

**Gate**: Davide can create a 2nd brand, switch between the two in the header, each brand's research/drafts/calendar are visibly isolated.

---

### P2 — Memory foundation (7 days)

The infrastructure that everything else builds on.

| # | Task | Artifact |
|---|---|---|
| P2.1 | Migration 018 — memory tables, RLS, helper functions | `supabase/migrations/018_memory_layer.sql` |
| P2.2 | Python `content_engine/memory/` package skeleton | see §4 |
| P2.3 | Implement `memory.hot` (KV), `memory.episodic.log`, `memory.semantic.store`, `memory.recall` | `memory/stores/*.py` |
| P2.4 | 8-point verifier — minimum viable version (5 of 8 checks, rest TODO with tests) | `memory/consolidation/verifier.py` |
| P2.5 | Haiku-based extractor — given transcript/source, returns candidate facts | `memory/consolidation/extractor.py` |
| P2.6 | Consolidation worker endpoint `POST /api/memory/consolidate` (scheduler-secret protected) | `routes.py` |
| P2.7 | pg_cron: nightly consolidation + TTL sweep + monthly archive partition creation | `supabase/migrations/018_memory_layer.sql` (end) |
| P2.8 | Arbiter: supersede + temporal reflection summary | `memory/arbiter.py` |
| P2.9 | Minimal Memory Inspector UI `/memory` — list brand facts, edit, delete, see episodic feed | `src/app/(dashboard)/memory/page.tsx` (NEW) |
| P2.10 | Wire existing research dedup (migration 002 `find_similar_research_items`) to log episodic event on duplicate | `scoring/*.py` |

**Gate**: For a test brand, `memory.recall("brand tone")` returns ranked results from `memory_semantic`; episodic log shows every draft/GOD/feedback event; TTL sweep empties transient entries older than 7 days.

---

### P3 — Brand context via memory (5 days)

Replaces the dead `tone_of_voice` JSON editor with memory-backed flow.

| # | Task | Artifact |
|---|---|---|
| P3.1 | `/settings/brand-context` page: list memory_semantic of kinds `tone_rule`, `principle`, `gold_example`, `discard_example` | `src/app/(dashboard)/settings/brand-context/page.tsx` (NEW) |
| P3.2 | Per-memory edit/delete/promote-tier | same |
| P3.3 | "Discover from sources" wizard: paste URLs / upload docs → spawn `brand-voice:discover-brand` agent → verifier → write to memory_semantic | `src/app/api/memory/discover/route.ts` (NEW, proxies to Python) |
| P3.4 | Python endpoint `POST /memory/discover` runs the brand-voice discover agent, pipes output through verifier | `routes.py` |
| P3.5 | Python endpoint `POST /memory/upload-source` accepts file, runs document-analysis agent | `routes.py` |
| P3.6 | Scoring pipeline (`scoring/*.py`) reads principles via `memory.recall(kind='principle')` instead of `brands.scoring_weights` JSON | `scoring/` |
| P3.7 | GOD mode reads `discard_example` and `gold_example` memories for few-shot context | `agents/god_system.py` |
| P3.8 | Humanizer reads `tone_rule` memories | `agents/humanizer.py` |
| P3.9 | Brand Context page shows "memory health" KPIs: count per tier, avg age, expiring soon | `brand-context/page.tsx` |

**Gate**: Davide points the wizard at `silvestripallets.com` + a Notion page, gets back 15-20 candidate tone rules + principles, reviews, approves. Running the scoring pipeline produces meaningfully different scores vs the defaults. Running GOD mode flags a test draft against one of the `discard_example` rules.

---

### P4 — Newsletter generate (5 days)

Now that memory is in place, generation can use brand voice properly.

| # | Task | Artifact |
|---|---|---|
| P4.1 | Python endpoint `POST /newsletter/generate` | `routes.py` + new `services/newsletter_generator.py` |
| P4.2 | Logic: fetch last 7 days of `research_items WHERE status='approved'` for active brand, group by topic, call Claude Sonnet with brand tone memories as system prompt, write editorial + section intros, save to `newsletters` | `newsletter_generator.py` |
| P4.3 | Log episodic event `newsletter_generated` with token usage + cost | `newsletter_generator.py` |
| P4.4 | Weekly cron: Monday 05:00 UTC `/scheduler/weekly-newsletter` (secret-protected, per brand) | migration 019 (new cron) |
| P4.5 | Newsletter page: re-enable button, remove "Coming soon", add progress indicator | `src/app/(dashboard)/newsletter/page.tsx` |
| P4.6 | Newsletter edit: allow editing sections before send | `src/app/(dashboard)/newsletter/[id]/page.tsx` (NEW) |
| P4.7 | Engagement note: Q2 decision confirmed — do NOT weight by historical engagement, since follower growth skews fairness. Purely topic/recency based. | doc in code comment |

**Gate**: Clicking "Generate Newsletter" on an active brand with ≥5 approved items in last 7 days produces a full draft newsletter in <60s, with editorial intro that references brand tone. Weekly cron fires and produces one without human action.

---

### P5 — Daily pipeline automation (3 days)

Ties scoring + draft generation to cron.

| # | Task | Artifact |
|---|---|---|
| P5.1 | Verify existing `/scheduler/daily-pipeline` endpoint covers scoring; extend if it doesn't include draft generation from scored-approved items | `routes.py` |
| P5.2 | Migration 019: add daily cron 06:00 for scoring, 07:00 for draft generation, per brand loop | `supabase/migrations/019_daily_pipeline_cron.sql` |
| P5.3 | Cost guardrails: hard cap per brand per day in `cost_tracker`, abort pipeline if exceeded, send Telegram alert | `utils/cost_tracker.py` |
| P5.4 | Pipeline Health dashboard reads memory_episodic for run history | `monitoring/pipeline_health.py` |

**Gate**: Leave the system overnight. Next morning: new research items scored, top-N auto-generated to drafts in `draft` status, pipeline health shows green, no cost overruns.

---

### P6 — Retrievers expansion (2 weeks)

Per Q5, all four retrievers. Staged by effort.

| # | Task | Artifact |
|---|---|---|
| P6.1 | **RSS** retriever — `feedparser`-based, uses `brands.research_sources` JSONB array of feed URLs | `retrievers/rss.py` |
| P6.2 | UI in `/settings/brand-context` to manage RSS feeds per brand | same page |
| P6.3 | **YouTube** retriever — YouTube Data API v3 (channel videos) + `youtube-transcript-api` for transcripts | `retrievers/youtube.py` |
| P6.4 | **X/Twitter** retriever — apify actor or paid X API; stash results as research_items with `retriever_type='x'` (new enum value via migration 020) | `retrievers/x.py` |
| P6.5 | **Gmail** retriever — Google OAuth2 + IMAP, filter by label "newsletters", parse Subject as title + body as content | `retrievers/gmail.py` |
| P6.6 | Migration 020: enum `retriever_type` adds `rss`, `youtube`, `x`, `gmail`; drop `users.brand_id` (now fully migrated to brand_members) | `020_retrievers_enum_expansion.sql` |
| P6.7 | Orchestrator `research_orchestrator.py` rotates through enabled retrievers per brand | `orchestrator/` |

**Gate**: Each retriever individually verified with 1 real source per brand. Overnight daily pipeline pulls from all 4 source types.

---

## 6. Risk register & guardrails

| Risk | Mitigation |
|---|---|
| Memory layer eats Supabase quota | pgvector with `ivfflat` lists=100 scales to ~10M rows on Small instance. Add alert at 5M. |
| LLM cost spike from consolidation | Haiku (not Sonnet) for extraction (~10× cheaper). Hard cap in `cost_tracker`. Telegram alert at 80% of daily brand budget. |
| 8-point verifier is slow and blocks hot path | Verification runs *async* only. Hot path never waits. |
| Arbiter generates conflicting summaries | Arbiter calls are idempotent on `(old_id, new_id)` pair. Manual override UI in memory inspector. |
| Multi-brand RLS rewrite leaks data across brands | Staged deployment: 017 applied in a Supabase branch first, verified with integration tests that User A cannot read Brand B's rows, then merged. |
| Dropping `users.brand_id` breaks legacy callers | 3-migration deprecation: 017 adds membership, 019 shifts all reads, 020 drops column. Each gated by grep-clean. |
| Memory drift — old brand rules persist forever | TTL + Arbiter + quarterly "memory hygiene" review surfaced in Memory Inspector UI. |
| Retriever credentials leak | All stored in `brands.social_accounts` JSONB (already RLS-protected); never sent to frontend (pattern C-03 already established). |
| No single developer understands the whole memory layer | This plan document + ADRs per phase + a `docs/memory/README.md` produced as deliverable of P2. |

---

## 7. Verification gates (summary)

Each phase is "done" when its gate passes:

- **P0 gate**: browser console = 0 unexpected 5xx on dashboard load.
- **P1 gate**: 2-brand manual test passes (see P1 description).
- **P2 gate**: memory recall + episodic log + TTL sweep all verifiable from SQL shell.
- **P3 gate**: discover wizard populates ≥15 memories; scoring/GOD/humanizer produce brand-distinct output.
- **P4 gate**: weekly cron fires and produces newsletter; manual click also works.
- **P5 gate**: overnight dry-run succeeds with cost < cap.
- **P6 gate**: all 4 retrievers active for at least 1 brand end-to-end.

---

## 8. Open questions

Things I still need to decide *with Davide* before starting a given phase:

1. **P1.6 Brand switcher placement** — top-right header dropdown (standard) or sidebar? Recommend: header dropdown (closer to user avatar, matches SaaS convention).
2. **P3.3 Discovery sources** — which platforms do we support in V1? Recommend: public URLs + PDF/DOCX upload. Notion/Drive/Gong come via MCP later.
3. **P4.7 Engagement weighting** — confirmed OFF per Q2. But we *do* track outcomes in episodic memory — should we expose "top-performed topics" as a signal to the user, while not feeding it back into scoring? Recommend: yes, read-only insight.
4. **P6 retriever order** — RSS first clearly. YouTube/X/Gmail — priority? Recommend: YouTube (highest signal for long-form brand voice), then Gmail (existing newsletter substrate), then X (highest operational friction).
5. **Backups/archive tier storage** — Supabase partitioned table or external blob (Supabase Storage / S3)? Recommend: Supabase partitions for V1; blob if we ever exceed 100GB.
6. **Mem0 SDK adoption timeline** — build custom for V1 (committed). Re-evaluate at end of P3: if our custom consolidation underperforms on token savings, add Mem0 as a compression layer in front of `memory.recall`.

---

## 9. What I need from Davide to start

For P0 (can start immediately): **nothing** — these are pure bug fixes, ~3 days.

For P1 (multi-brand): confirm the brand switcher placement (Q#1 above).

For P2 (memory): confirm we proceed with the Postgres-native path, no Mem0/Zep SDK in V1.

For P3 (brand context): list 2-3 source URLs/docs for Silvestri Pallets and the 2nd brand you want active, so discovery has real data to work with.

For P4+ (newsletter + automation): no blockers beyond P1-P3 landing.

---

## 10. Sequencing recap

```
Week 1:   P0 (3d) + start P1 (2d)
Week 2:   finish P1 (3d) + start P2 (2d)
Week 3:   finish P2 (5d)
Week 4:   P3 (5d)
Week 5:   P4 (5d)
Week 6:   P5 (3d) + start P6 RSS+YouTube (2d)
Week 7-8: P6 X + Gmail (2 weeks realistic with debug)
```

Total: **~7-8 weeks** of focused work to reach "memory-native, multi-brand, fully automated" state. P0-P3 (4 weeks) is the critical path to a working 2-brand memory-backed system; P4+ adds polish and breadth.

---

**Plan revision**: this document is versioned. Every decision made during execution that contradicts this plan requires an ADR entry appended to §1 with rationale.
