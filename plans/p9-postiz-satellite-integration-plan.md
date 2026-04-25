# Plan: P9 — Postiz Social Publishing Integration (Dual-Mode)

> Source PRD: `plans/postiz-self-hosted-satellite-prd.md`

## Architectural decisions

- **Dual-mode**: Postiz can be `self_hosted` (Docker Compose), `cloud` (SaaS/managed), or `disabled`.
  Both modes use the same HTTP Public API (`/public/v1/*`). Only the base URL differs.
- **AGPL boundary**: Zero Postiz code in the monorepo. Communication only via HTTP API.
- **Auth pattern**: OAuth remains on Postiz UI. Our app stores only `postiz_integration_id`
  (opaque string) per platform per brand. No tokens, no secrets.
- **Cross-posting**: Postiz natively supports multi-platform publishing. Our payload includes
  `integration_ids: [...]` and Postiz handles parallel dispatch.
- **Scheduling source-of-truth**: Our `content_drafts.scheduled_at` is the calendar view and
  scheduler trigger. Postiz is the execution engine. Daily scheduler fan-out on expired drafts.
- **Failure model**: If Postiz is down, drafts remain `scheduled` and retry on next scheduler run.
  No auto-fallback to native APIs.
- **Deployment**: Docker Compose overlay (`docker-compose.postiz.yaml`) for self-hosted local dev.
  For cloud, no extra infrastructure needed.

---

## Phase 1: "Dual-Mode Foundation"

**User stories**: Configure Postiz mode, verify health, have typed API client

### What to build
Schema, configuration, and client layer that works identically for self-hosted and cloud.

### Acceptance criteria
- [x] Migration `028_brand_social_integrations.sql` with `postiz` schema (optional), table, RLS, indices
- [x] `config.py` expanded with `postiz_mode`, `postiz_api_url`, `postiz_api_key`
- [x] `.env.example` with dual-mode documentation and examples
- [x] `postiz_client.py` typed HTTP client for all Public API endpoints
- [x] `postiz_publisher.py` replaces mock with real publish/schedule logic, supports both modes
- [x] `social_publisher.py` refactored to re-export from `postiz_publisher`
- [x] `scheduler.py` delegates `publish_scheduled_posts` to Postiz
- [x] `docker-compose.postiz.yaml` with Redis, Temporal, Postiz app
- [x] `postiz/.env.postiz.example` with all OAuth placeholders
- [x] `routes_postiz.py` bridge routes (health, integrations, analytics, mine CRUD)
- [x] `main.py` mounts `routes_postiz` with `/api` prefix
- [x] `docs/POSTIZ_SATELLITE.md` with dual-mode quick-start and troubleshooting

---

## Phase 2: "First Connection"

**User stories**: Connect a brand to LinkedIn via Postiz, see connection status

### What to build
UI and APIs to store Postiz integration IDs per platform, per brand.

### Acceptance criteria
- [x] `GET /api/social/integrations/mine` — list brand integrations
- [x] `POST /api/social/integrations/mine` — upsert integration
- [x] `DELETE /api/social/integrations/mine/:platform` — disconnect
- [x] Next.js proxy routes for the CRUD above
- [x] Settings page `/settings/social-connections`:
  - Cards per platform (13 supported)
  - Input "Postiz Integration ID" + channel name
  - Toggle active/inactive
  - Save / update / delete
  - Health status banner (ok / disabled / error)
- [x] Settings index page links to Social Connections and Image Generation
- [x] `GET /api/social/health` endpoint showing mode and connectivity

---

## Phase 3: "First Real Post"

**User stories**: Write a draft, press "Publish now", see the post on Postiz (cross-platform)

### What to build
Replace the mock publisher with real Postiz API calls. Add publish UI to draft views.

### Acceptance criteria
- [x] `postiz_publisher.publish_now()` calls Postiz `POST /public/v1/posts`
- [x] `content_drafts` updated with `status=published`, `published_at`, `published_url`, `metadata.postiz_post_ids`
- [x] `POST /api/social/publish` generic proxy (legacy per-platform routes still work)
- [x] `PublishButton` component with multi-platform selector (loads active integrations)
- [x] `DraftDetail` includes `PublishButton` alongside `GenerateVisualButton`
- [x] `DraftCard` shows first media preview and links to detail
- [x] Error handling: Postiz errors surfaced as toast, draft stays in `approved`

---

## Phase 4: "Scheduled Publishing"

**User stories**: Schedule a post for tomorrow, see Postiz execute it

### What to build
Connect the existing scheduler to Postiz instead of no-op.

### Acceptance criteria
- [x] `scheduler.py` `publish_scheduled_posts()` queries drafts past `scheduled_at`
- [x] For each draft, calls `postiz_publisher.publish_scheduled_via_postiz()`
- [x] If draft already has `postiz_post_ids` (scheduled on Postiz), marks as published locally
- [x] Otherwise publishes immediately via `publish_now`
- [x] `ScheduleRequest` supports optional `platforms` array
- [x] Drafts scheduled without platforms fallback to `draft.platform`
- [x] Errors logged, draft stays `scheduled` for retry on next run

---

## Phase 5: "Analytics Loop"

**User stories**: See engagement metrics of published posts, improve future drafts

### What to build
Close the feedback cycle: published posts → metrics → content engine memory.

### Acceptance criteria
- [x] `postiz_analytics.py` refactored to use `PostizClient`
- [x] Reads `metadata.postiz_post_ids` dict (platform → postiz_id)
- [x] `GET /api/social/analytics?integration_id=&days=` proxy route
- [x] Engagement score computation with platform normalization and temporal decay
- [x] `update_feedback_bonus()` saves to `brands.feedback_bonus` and `memory_events`
- [x] `run_daily_analytics_cycle()` iterates all brands, pulls metrics, updates scores
- [x] Daily scheduler workflow (`publish_scheduled_posts`) includes analytics pull

---

## Appendix: Platform Support Matrix

| Platform   | Postiz Support | Our Phase |
|------------|----------------|-----------|
| LinkedIn   | Yes            | Phase 2   |
| X/Twitter  | Yes            | Phase 2   |
| Instagram  | Yes            | Phase 2   |
| TikTok     | Yes            | Phase 2   |
| YouTube    | Yes            | Phase 2   |
| Threads    | Yes            | Phase 2   |
| Bluesky    | Yes            | Phase 2   |
| Pinterest  | Yes            | Phase 2   |
| Reddit     | Yes            | Phase 2   |
| Facebook   | Yes            | Phase 2   |
| Mastodon   | Yes            | Phase 2   |
| Discord    | Yes            | Phase 2   |
| Slack      | Yes            | Phase 2   |

All platforms are treated uniformly via the `integration_ids` array in the Postiz API payload.
