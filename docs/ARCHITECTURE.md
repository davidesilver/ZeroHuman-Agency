# Architecture

## System overview

The platform is a two-application system around one shared database. It is not a microservices architecture — there are no service meshes, message queues, or inter-service discovery. Complexity is kept in the database layer (RLS, views, SQL functions) and in the Python orchestration layer.

```
┌─────────────────────────────────────────────────────────┐
│                     Browser / API Client                │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼────────────────────────────────┐
│                    Next.js (src/)                       │
│   App Router · Auth · Dashboard · API route handlers    │
│   Direct Supabase reads for simple tenant queries       │
│   proxyToBackend() for orchestration-heavy routes       │
└──────────┬────────────────────────────────┬─────────────┘
           │ Supabase JS SDK                │ HTTP + Bearer token
┌──────────▼───────────┐     ┌─────────────▼─────────────┐
│  Supabase / Postgres  │     │   FastAPI (python/)        │
│                       │     │                           │
│  Auth sessions        │◄────┤  JWT validation           │
│  Row Level Security   │     │  Research orchestration   │
│  pgvector embeddings  │     │  Scoring + generation     │
│  pg_cron jobs         │     │  Agent system             │
│  Storage (assets,     │     │  Email marketing (Brevo)  │
│    videos)            │     │  Video rendering          │
│  Edge functions       │     │  LLM provider hub         │
└──────────────────────┘     └──┬──────────┬─────────────┘
                                │          │ HTTP (optional)
              ┌─────────────────┘          │
              │ HTTP (optional)   ┌─────────▼─────────────┐
┌─────────────▼─────────┐        │   Postiz Satellite     │
│  local-deep-research  │        │  Social OAuth+schedule │
│  (Docker :5000)       │        │  (Docker or cloud)     │
│  Async research jobs  │        └───────────────────────┘
└───────────────────────┘
```

**Sidecars (optional Docker services)**

| Sidecar | Port | Purpose |
|---|---|---|
| `local-deep-research` | 5000 | Multi-source research jobs (async) |
| `Postiz` | 4000 | Social OAuth + publishing queue |

---

## Runtime responsibilities

### Frontend (`src/`)

- Authentication and session management via Supabase Auth
- Dashboard pages (research, content hub, writing lab, newsletter, social, analytics, settings)
- API route handlers that either:
  - Read/write Supabase directly (brands, drafts list, assets, memory, costs)
  - Proxy to FastAPI for heavy orchestration (research triggers, scoring, generation, publishing)

The proxy helper (`src/lib/api-helpers.ts`) forwards the Supabase session token to FastAPI as `Authorization: Bearer <token>`, generates a correlation ID (`X-Request-ID`), and propagates the active brand (`X-Brand-ID`).

### Backend (`python/src/content_engine/`)

- JWT validation and `brand_id` resolution for every authenticated request
- Research pipeline: parallel retrievers, deduplication, DB insertion
- Scoring engine with configurable per-brand weights
- Content generation: Writer → Editor pipeline
- Optional review layers: GOD mode (4-agent), Humanizer (2-pass)
- Cross-platform content adaptation
- Writing Lab session management
- Newsletter preview and delivery
- Social publishing via Postiz (publish now or schedule)
- Image generation across multiple backends
- **Email marketing (Phase 3–6):** Brevo contacts/lists sync, campaign create+schedule, webhook metrics ingestion, 3-template automation sequences (welcome/nurture/win-back)
- **LLM provider hub (Phase 4+14):** `LLMProvider` ABC, OpenRouter + OpenClaw providers, probabilistic A/B traffic split, per-call telemetry to `llm_provider_metrics`
- **Deep research (Phase 7–8):** async job queue wrapping `local-deep-research` sidecar; LLM-based idea extraction → `research_items`
- **Competitor monitoring (Phase 9):** Scrapling stealth scraper (httpx fallback) for competitor page snapshots
- **Video pipeline (Phase 10–12):** HyperFrames CLI subprocess for composition rendering; Heygen talking-head (quota-gated, per-brand); output to Supabase Storage
- **Brand secrets (Phase 0):** Fernet encryption at app layer; `brand_integrations` table stores only ciphertext
- Feedback loop: aggregate metrics → update scoring weights
- Scheduled jobs: daily research, publish queued posts
- Agent config and skills CRUD (reads from DB with 5-min TTL cache)
- Observability: cost tracking, pipeline health heartbeats, LLM fallback logs

### Database (`supabase/migrations/`)

- 42 migrations (001–042); migration files are the canonical schema source of truth
- Row Level Security on every tenant-scoped table — isolation enforced at DB layer
- `pgvector` for semantic deduplication and memory retrieval
- `pg_cron` for analytics sync jobs
- SQL helper functions: `auth_user_brand_id()`, `user_has_brand()`, `find_semantic_duplicates()`
- Views for common aggregations: `v_content_pipeline`, `v_daily_costs`

**New tables (migrations 031–042)**

| Table | Purpose |
|---|---|
| `feature_flags` | Per-brand boolean/numeric feature switches (default OFF) |
| `brand_integrations` | Per-brand encrypted API secrets vault (Fernet ciphertext) |
| `brevo_contacts` | Mirror of Brevo contact list for local querying |
| `llm_provider_metrics` | Per-call LLM telemetry (provider, latency, cost) |
| `deep_research_jobs` | Async job queue for local-deep-research sidecar |
| `competitor_snapshots` | Competitor page capture results (Scrapling / httpx) |
| `video_templates` | HyperFrames composition specs (system + per-brand) |
| `videos` | Render jobs and output artefacts (HyperFrames + Heygen) |
| `heygen_usage` | Per-brand monthly Heygen quota counter |
| `brevo_campaigns` | Brevo email campaign mirror + webhook metrics |
| `email_automations` | Multi-step Brevo automation sequences |

---

## Request flows

### Standard authenticated request

```
Browser → Next.js route handler
  → requireAuth() — validates Supabase session server-side
  → proxyToBackend(req, "/some/path")
    → reads session.access_token
    → sets Authorization: Bearer <token>
    → sets X-Request-ID: <uuid>
    → sets X-Brand-ID: <active brand cookie>
  → FastAPI JWTAuthMiddleware
    → validates JWT with Supabase anon key
    → resolves brand_id from token sub → public.users
    → populates request.state.brand_id
  → Route handler executes with scoped brand_id
  → Returns JSON response
```

### Scheduler request (no user session)

```
Cron system → POST /api/scheduler/daily-research
  → Next.js route handler → proxyToBackend with scheduler headers
  → FastAPI checks X-Scheduler-Secret header
  → Resolves brand_id from SCHEDULER_BRAND_ID env
    (or iterates all active brands if env not set)
  → Runs pipeline without a user JWT
```

---

## Multi-tenant isolation

Tenant isolation works at two independent layers. Both must be intact for security:

**Application layer:** the JWT middleware resolves `brand_id` from the authenticated user's record in `public.users`. Every route handler uses this resolved `brand_id` to scope queries.

**Database layer:** RLS policies enforce that a user can only SELECT, INSERT, UPDATE, or DELETE rows where `brand_id` matches their own. This holds even if the application layer has a bug.

A working tenant setup requires three things to exist:
1. A Supabase auth user (`auth.users`)
2. A row in `public.users` linking that auth user to a brand
3. A row in `public.brands` for the brand

---

## Feature flags

All new capabilities are gated by per-brand boolean flags in the `feature_flags` table (default OFF). The Python service reads flags via `services/feature_flags.py`; the frontend via `src/lib/feature-flags.ts`.

| Flag key | Capability gated |
|---|---|
| `video_enabled` | HyperFrames rendering + Heygen talking-head |
| `email_marketing_enabled` | Brevo contacts/campaigns/automations |
| `deep_research_enabled` | local-deep-research async jobs |
| `competitor_monitoring_enabled` | Scrapling competitor snapshots |

---

## Brand secrets

Third-party API keys (Brevo, Heygen, HyperFrames, OpenClaw) are stored encrypted in `brand_integrations`. Encryption uses **Fernet** (AES-128-CBC + HMAC-SHA256) from the Python `cryptography` library. The application-layer key is `BRAND_SECRETS_ENCRYPTION_KEY` (env var). The database stores only ciphertext; the plaintext never touches Supabase Storage or logs.

---

## Security controls

| Control | Implementation |
|---|---|
| JWT authentication | `JWTAuthMiddleware` validates every non-public backend route |
| Row Level Security | Enabled on all tenant-scoped tables; enforced at DB layer |
| Scheduler protection | `X-Scheduler-Secret` header required; constant-time comparison |
| Rate limiting | Persistent sliding-window counter in Supabase; fails open if DB unavailable |
| CORS | Explicit allowlist from `ALLOWED_ORIGINS`; no wildcards |
| SSRF protection | Media URLs validated against scheme allowlist + private-IP blocklist before forwarding to Postiz |
| Request correlation | `X-Request-ID` generated per request; forwarded to backend; included in responses |
| Secret masking | API keys masked in all log output (`***xxxx` pattern) |
| Brand secret encryption | Fernet at app layer; DB stores ciphertext only; key never logged or exposed via API |

---

## Content pipeline data flow

```
brands (config: topics, sources, tone, weights, gold_examples)
  ↓
research_runs (status: running → completed)
  ↓
research_items (status: new → scored → approved/rejected)
  ↓
scores (per-item score across all dimensions)
  ↓
content_drafts (status: draft → in_review → god_mode → approved → scheduled → published)
  ↓
god_mode_reviews (advocate · factcheck · creative · synthesis)
  ↓
newsletters / social platforms (via Postiz)
  ↓
social_metrics (impressions, engagement, clicks)
  ↓
feedback loop → scores updated → influences next research run
```

Supporting tables: `api_costs`, `pipeline_health`, `llm_fallback_log`, `audit_trail`, `writing_lab_sessions`, `brand_assets`, `memory_semantic`, `feature_flags`, `brand_integrations`, `brevo_contacts`, `brevo_campaigns`, `email_automations`, `llm_provider_metrics`, `deep_research_jobs`, `competitor_snapshots`, `video_templates`, `videos`, `heygen_usage`.

---

## Directory map

| Path | Purpose |
|---|---|
| `src/app/(dashboard)/` | Dashboard pages (App Router) |
| `src/app/(dashboard)/deep-research/` | Deep research job UI |
| `src/app/(dashboard)/competitor-watch/` | Competitor snapshot UI |
| `src/app/(dashboard)/video/` | Video generation and templates UI |
| `src/app/(dashboard)/settings/audience/` | Brevo email marketing settings |
| `src/app/api/` | Next.js API route handlers |
| `src/app/api/research/deep/` | Proxy → FastAPI deep research |
| `src/app/api/research/competitor/` | Proxy → FastAPI competitor monitor |
| `src/app/api/video/` | Proxy → FastAPI video rendering |
| `src/app/api/email-marketing/` | Proxy → FastAPI Brevo integration |
| `src/app/api/internal/brand-secrets/` | Proxy → FastAPI encrypted secrets CRUD |
| `src/app/api/llm/providers/` | Proxy → FastAPI LLM provider hub |
| `src/app/api/feature-flags/` | Proxy → FastAPI feature flag read/write |
| `src/components/` | Shared UI components |
| `src/lib/` | Supabase clients, auth helpers, types, API proxy |
| `src/lib/feature-flags.ts` | Client-side feature flag reader |
| `src/lib/brand-secrets.ts` | Secret existence check (no plaintext) |
| `python/src/content_engine/api/` | FastAPI routes and middleware |
| `python/src/content_engine/agents/` | Writer, Editor, GOD mode, Humanizer, Adapter |
| `python/src/content_engine/orchestrator/` | Research and content pipeline orchestration |
| `python/src/content_engine/retrievers/` | RSS, Search, YouTube, deep research, competitor spider |
| `python/src/content_engine/scoring/` | Scoring engine |
| `python/src/content_engine/services/` | Postiz, newsletter, scheduler, image gen, Brevo, brand secrets, feature flags, LLM hub |
| `python/src/content_engine/services/llm/` | LLMProvider ABC, OpenRouter, OpenClaw, registrar, telemetry |
| `python/src/content_engine/monitoring/` | Pipeline health and LLM fallback monitoring |
| `python/src/content_engine/utils/` | LLM client, cost tracker, rate limiter, SSRF guard, JSON parser |
| `python/src/content_engine/config/` | Pydantic settings (all from environment) |
| `supabase/migrations/` | Schema source of truth (001–042) |
| `supabase/functions/` | Supabase Edge Functions (analytics sync) |
| `agents/` | Installed community agent categories (from agency-agents) |
| `.vendor/agency-agents/` | Git submodule — msitarzewski/agency-agents |
| `scripts/install-agents.sh` | Agent category installer |
| `docs/` | Extended documentation |
