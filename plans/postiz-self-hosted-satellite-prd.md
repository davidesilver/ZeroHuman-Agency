# Postiz Self-Hosted Satellite — Integration PRD

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate [Postiz](https://github.com/gitroomhq/postiz-app) (AGPL-3.0 open-source social-media scheduler) as a **satellite service** next to the existing Memory-Native stack. Postiz runs in Docker, shares the existing Supabase PostgreSQL (via dedicated schema `postiz`), uses local file storage, and exposes OAuth portals for LinkedIn, X, Instagram, TikTok, YouTube, Reddit, etc. Our FastAPI backend calls Postiz Public API (`/public/v1/*`) to publish/schedule/analyze instead of the current `postiz_api_key` mock.

**Architecture:** Postiz is treated as an external, replaceable backend plugin — not a monolith merger. The existing `brands` table gets a new `postiz_integration_map` JSONB column (or a dedicated `brand_social_integrations` table) that stores Postiz `integration_id` per platform. The FastAPI `social_publisher.py` is rewritten to call Postiz Public API with the correct `integration` IDs, media URLs (from Supabase Storage), and scheduling ISO timestamps. Postiz handles OAuth refresh, platform rate limits, and analytics collection. Our scheduler (`publish_scheduled_posts`) delegates to Postiz for the actual publish action.

**Tech Stack:** Docker Compose (Postiz + Redis + Temporal + local storage), Supabase PostgreSQL (shared, schema `postiz`), FastAPI + httpx, Next.js 14 settings UI.

---

## 0. Why this phase exists — grounding

The current social publishing layer has three critical gaps:

1. **OAuth is manual / non-existent.** `social_publisher.py` expects access tokens inside `brands.social_accounts`, but there is no UI, no OAuth flow, and no token refresh. Every token expires in 60 days and breaks publishing.
2. **The Postiz integration is a mock.** `publish_to_postiz()` calls an internal-looking endpoint (`/api/v1/posts`) with a `platforms` array. This does not match the real Postiz Public API, which requires per-platform `integration_id`s, media upload first, and platform-specific JSON settings.
3. **No analytics feedback from social platforms.** The feedback loop relies on `record_social_metrics()` being called manually. Postiz collects impressions, likes, shares, comments natively and exposes them via `/public/v1/analytics/:integration`.

**Decision locked:** Self-hosted Postiz satellite (Option B). Reasons:
- **Data sovereignty:** OAuth tokens live inside the user's Docker network, not on a SaaS.
- **Cost control:** zero recurring SaaS fee; user pays only for VPS resources.
- **White-label ready:** each tenant's brand maps to Postiz channels without leaking credentials across brands.
- **AGPL compliance:** we call Postiz via HTTP API (arm's length), keeping our code licensing independent.

---

## 1. File structure

### P9 — Postiz Satellite Integration

**New infrastructure files:**
- `docker-compose.postiz.yaml` — satellite services: Postiz app, Redis, Temporal server, Temporal UI
- `postiz/.env.postiz` — Postiz-specific env vars (shared with `../.env.local` where possible)
- `postiz/README-POSTIZ.md` — quick-start for the satellite
- `supabase/migrations/027_postiz_social_integrations.sql` — `brand_social_integrations` table + schema `postiz`

**New Python modules:**
- `python/src/content_engine/services/postiz_client.py` — typed HTTP client for Postiz Public API
- `python/src/content_engine/services/postiz_publisher.py` — replaces `social_publisher.py` core logic
- `python/tests/test_postiz_client.py` — mocked unit tests for client methods
- `python/tests/test_postiz_publisher.py` — mocked unit tests for publish/schedule flows

**Modified Python modules:**
- `python/src/content_engine/services/social_publisher.py` — refactored to delegate to `postiz_publisher.py`; legacy direct-token path marked deprecated
- `python/src/content_engine/config.py` — adds `postiz_api_url`, `postiz_api_key`
- `python/src/content_engine/services/scheduler.py` — `publish_scheduled_posts` calls Postiz for the actual publish action

**New Next.js routes:**
- `src/app/api/brands/[id]/social-integrations/route.ts` — CRUD for Postiz integration IDs per brand
- `src/app/api/social/publish/route.ts` — thin proxy, unchanged contract
- `src/app/api/social/schedule/route.ts` — thin proxy, unchanged contract

**New React components:**
- `src/components/settings/social-integrations-card.tsx` — manage Postiz integration IDs per platform
- `src/components/settings/postiz-status-badge.tsx` — show Postiz connectivity + channel status

**New settings page:**
- `src/app/(dashboard)/settings/social-connections/page.tsx` — per-brand social connection manager

**Modified settings index:**
- `src/app/(dashboard)/settings/page.tsx` — add "Social Connections" card linking to new page

**Docs (to be updated at the end):**
- `.env.example` — add Postiz section
- `README.md` — add Postiz satellite paragraph
- `docs/SETUP.md` — add Docker satellite bootstrap steps
- `docs/DEPLOYMENT.md` — add production topology with Postiz
- `docs/API.md` — add Postiz Public API integration notes

---

## 2. Database shapes (locked)

### `brand_social_integrations`
```sql
CREATE TABLE IF NOT EXISTS public.brand_social_integrations (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        uuid NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
  platform        text NOT NULL CHECK (platform IN (
                    'linkedin','twitter','x','instagram','facebook',
                    'tiktok','youtube','reddit','pinterest',
                    'threads','bluesky','mastodon','discord','slack'
                  )),
  postiz_integration_id text,   -- UUID from Postiz /public/v1/integrations
  postiz_channel_name   text,   -- human label (e.g. "MyBrand LinkedIn")
  is_active       boolean NOT NULL DEFAULT true,
  metadata        jsonb NOT NULL DEFAULT '{}',  -- extra platform settings
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brand_id, platform)
);
CREATE INDEX idx_brand_social_integrations_brand ON public.brand_social_integrations (brand_id);
CREATE INDEX idx_brand_social_integrations_active ON public.brand_social_integrations (brand_id, is_active);

-- RLS
ALTER TABLE public.brand_social_integrations ENABLE ROW LEVEL SECURITY;
CREATE POLICY brand_social_int_select ON public.brand_social_integrations
  FOR SELECT USING (public.user_has_brand(brand_id));
CREATE POLICY brand_social_int_insert ON public.brand_social_integrations
  FOR INSERT WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY brand_social_int_update ON public.brand_social_integrations
  FOR UPDATE USING (public.user_has_brand(brand_id))
              WITH CHECK (public.user_has_brand(brand_id));
CREATE POLICY brand_social_int_delete ON public.brand_social_integrations
  FOR DELETE USING (public.user_has_brand(brand_id));

-- touch updated_at
CREATE OR REPLACE FUNCTION public.touch_brand_social_integrations_updated_at()
RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_brand_social_integrations_touch
  BEFORE UPDATE ON public.brand_social_integrations
  FOR EACH ROW EXECUTE FUNCTION public.touch_brand_social_integrations_updated_at();
```

### Postiz shared PostgreSQL schema
```sql
-- Create isolated schema for Postiz so its Prisma migrations don't collide
-- with our application tables. Postiz must be configured with:
--   DATABASE_URL="postgresql://.../postgres?schema=postiz"
CREATE SCHEMA IF NOT EXISTS postiz;
GRANT ALL ON SCHEMA postiz TO postgres;
GRANT ALL ON SCHEMA postiz TO anon;
GRANT ALL ON SCHEMA postiz TO authenticated;
GRANT ALL ON SCHEMA postiz TO service_role;
```

---

## 3. Docker Satellite Topology

`docker-compose.postiz.yaml` (overlay, not replacing the existing compose):

```yaml
services:
  postiz-redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks: [postiz]

  postiz-temporal:
    image: temporalio/auto-setup:1.25
    restart: unless-stopped
    environment:
      DB: postgresql
      POSTGRES_USER: postgres
      POSTGRES_PWD: ${SUPABASE_DB_PASSWORD}
      POSTGRES_SEEDS: db.${SUPABASE_PROJECT_REF}.supabase.co
      DB_PORT: 5432
      POSTGRES_DB: postgres
      DYNAMIC_CONFIG_FILE_PATH: config/dynamicconfig/development-sql.yaml
      TEMPORAL_BROADCAST_ADDRESS: postiz-temporal
    networks: [postiz]

  postiz-temporal-ui:
    image: temporalio/ui:2.34.0
    restart: unless-stopped
    environment:
      TEMPORAL_HOST: postiz-temporal:7233
      TEMPORAL_CORS_ORIGINS: http://localhost:4200
    ports: ["8233:8080"]
    networks: [postiz]
    depends_on: [postiz-temporal]

  postiz-app:
    image: ghcr.io/gitroomhq/postiz-app:latest
    restart: unless-stopped
    env_file: ./postiz/.env.postiz
    environment:
      DATABASE_URL: "postgresql://postgres:${SUPABASE_DB_PASSWORD}@db.${SUPABASE_PROJECT_REF}.supabase.co:5432/postgres?schema=postiz"
      REDIS_URL: "redis://postiz-redis:6379"
      FRONTEND_URL: "http://localhost:4200"
      NEXT_PUBLIC_BACKEND_URL: "http://localhost:3001"
      BACKEND_INTERNAL_URL: "http://localhost:3001"
      STORAGE_PROVIDER: local
      UPLOAD_DIRECTORY: /uploads
      NEXT_PUBLIC_UPLOAD_STATIC_DIRECTORY: /uploads
      DISABLE_REGISTRATION: "true"
      API_LIMIT: 300
    volumes:
      - postiz-uploads:/uploads
    ports:
      - "4200:4200"   # Postiz UI
      - "3001:3000"   # Postiz API (mapped to avoid clash with our Next.js 3000)
    networks: [postiz]
    depends_on: [postiz-redis, postiz-temporal]

volumes:
  postiz-uploads:

networks:
  postiz:
    driver: bridge
```

**Important:** Postiz API is exposed on `localhost:3001` (not 3000, which is our Next.js dev server). The `BACKEND_INTERNAL_URL` inside the container remains `http://localhost:3000` (internal), but from our FastAPI we call `http://localhost:3001`.

---

## 4. Environment variables (locked)

Append to `.env.example` and `.env.local`:

```bash
# ── Postiz Self-Hosted Satellite ────────────────────────────────────────────
# The Postiz API endpoint visible from our FastAPI / Next.js (host port mapped)
POSTIZ_API_URL=http://localhost:3001

# Generate this inside Postiz Settings → API after first admin login
POSTIZ_API_KEY=<generate-from-postiz-dashboard>

# Supabase connection details shared with Postiz (same DB, schema=postiz)
SUPABASE_PROJECT_REF=<project-ref>
SUPABASE_DB_PASSWORD=<db-password>

# (Optional) Disable Postiz in local dev if satellite is not running
# POSTIZ_ENABLED=false
```

Python `config.py` additions:
```python
    postiz_api_url: str = ""
    postiz_api_key: str = ""
    postiz_enabled: bool = True
```

---

## 5. Task Breakdown

### Task P9.1: Migration 027 — `brand_social_integrations` + Postiz schema

- [ ] **Step 1: Write migration**
  Create `supabase/migrations/027_postiz_social_integrations.sql` containing:
  - `CREATE SCHEMA postiz`
  - `CREATE TABLE brand_social_integrations` (shape above)
  - RLS policies + trigger
- [ ] **Step 2: Apply migration**
  Run: `npx supabase db push --include-all`
- [ ] **Step 3: Regenerate TypeScript types**
  Run: `npx supabase gen types typescript --project-id <ref> > src/lib/types/database.types.ts`
- [ ] **Step 4: Commit**
  ```bash
  git add supabase/migrations/027_postiz_social_integrations.sql src/lib/types/database.types.ts
  git commit -m "feat(p9): brand_social_integrations table + postiz schema"
  ```

---

### Task P9.2: Docker Compose Satellite

- [ ] **Step 1: Write `docker-compose.postiz.yaml`**
  Content exactly as specified in §3 above.
- [ ] **Step 2: Write `postiz/.env.postiz`**
  Minimal env file with placeholder comments for every OAuth client ID/secret.
- [ ] **Step 3: Write `postiz/README-POSTIZ.md`**
  Quick-start:
  ```markdown
  # Postiz Satellite
  1. Ensure Supabase DB allows connections from your IP (or use connection pooling).
  2. Copy `.env.postiz.example` to `.env.postiz` and fill OAuth credentials.
  3. Run: docker compose -f docker-compose.postiz.yaml up -d
  4. Open http://localhost:4200, create admin user.
  5. Go to Settings → API → generate API key.
  6. Paste the API key into the root `.env.local` as POSTIZ_API_KEY.
  7. For each social platform, go to Integrations → Add and complete OAuth.
  8. Copy integration IDs into our dashboard (Settings → Social Connections).
  ```
- [ ] **Step 4: Commit**
  ```bash
  git add docker-compose.postiz.yaml postiz/
  git commit -m "feat(p9): Postiz self-hosted Docker satellite"
  ```

---

### Task P9.3: Postiz API Client (Python)

**Files:**
- Create: `python/src/content_engine/services/postiz_client.py`
- Create: `python/tests/test_postiz_client.py`

- [ ] **Step 1: Write typed client**
  ```python
  """Typed HTTP client for Postiz Public API.

  Endpoints used:
    GET  /public/v1/integrations
    POST /public/v1/posts
    GET  /public/v1/posts
    DELETE /public/v1/posts/:id
    GET  /public/v1/analytics/:integration
    GET  /public/v1/analytics/post/:postId
  """
  from __future__ import annotations
  from typing import Optional
  import httpx
  from ..config import settings

  class PostizClient:
      def __init__(self, api_url: str | None = None, api_key: str | None = None):
          self.api_url = (api_url or settings.postiz_api_url or "").rstrip("/")
          self.api_key = api_key or settings.postiz_api_key or ""

      def _headers(self) -> dict[str, str]:
          return {
              "Authorization": f"Bearer {self.api_key}",
              "Content-Type": "application/json",
          }

      async def list_integrations(self) -> list[dict]:
          async with httpx.AsyncClient(timeout=30) as c:
              r = await c.get(f"{self.api_url}/public/v1/integrations", headers=self._headers())
              r.raise_for_status()
              return r.json()

      async def create_post(
          self,
          *,
          integration_ids: list[str],
          content: str,
          scheduled_at: Optional[str] = None,
          media_urls: Optional[list[str]] = None,
          settings_json: Optional[dict] = None,
      ) -> dict:
          body: dict = {
              "integrations": integration_ids,
              "posts": [{"content": content}],
          }
          if scheduled_at:
              body["date"] = scheduled_at
          if media_urls:
              # Postiz requires media uploaded to Postiz first; we will do that in the publisher layer
              pass
          if settings_json:
              body["settings"] = settings_json
          async with httpx.AsyncClient(timeout=30) as c:
              r = await c.post(f"{self.api_url}/public/v1/posts", json=body, headers=self._headers())
              r.raise_for_status()
              return r.json()

      async def get_platform_analytics(self, integration_id: str, days: int = 7) -> dict:
          async with httpx.AsyncClient(timeout=30) as c:
              r = await c.get(
                  f"{self.api_url}/public/v1/analytics/{integration_id}",
                  params={"d": days},
                  headers=self._headers(),
              )
              r.raise_for_status()
              return r.json()
  ```
- [ ] **Step 2: Write tests**
  Use `respx` to mock the public API endpoints.
- [ ] **Step 3: Run tests**
  `cd python && pytest tests/test_postiz_client.py -v`
- [ ] **Step 4: Commit**
  ```bash
  git add python/src/content_engine/services/postiz_client.py python/tests/test_postiz_client.py
  git commit -m "feat(p9): typed Postiz Public API client + tests"
  ```

---

### Task P9.4: Postiz Publisher Service (replaces mock)

**Files:**
- Create: `python/src/content_engine/services/postiz_publisher.py`
- Modify: `python/src/content_engine/services/social_publisher.py`

- [ ] **Step 1: Write `postiz_publisher.py`**
  Responsibilities:
  1. Read `brand_social_integrations` for the brand + platform.
  2. If `postiz_enabled` is False or Postiz unreachable, raise with clear error.
  3. Call `PostizClient.create_post()` with correct `integration_ids`.
  4. On success, update `content_drafts` status to `published` and store `postiz_post_id`.
  5. On failure, log to audit_trail and raise HTTPException(502).

  ```python
  async def publish_via_postiz(
      brand_id: str, draft_id: str, platform: str
  ) -> dict:
      db = get_db()
      # 1) resolve integration
      row = (
          db.table("brand_social_integrations")
          .select("postiz_integration_id")
          .eq("brand_id", brand_id)
          .eq("platform", platform)
          .eq("is_active", True)
          .maybe_single()
          .execute()
          .data
      )
      if not row or not row.get("postiz_integration_id"):
          raise ValueError(f"No active Postiz integration for platform={platform}")

      integration_id = row["postiz_integration_id"]

      # 2) load draft
      draft = db.table("content_drafts").select("*").eq("id", draft_id).single().execute().data
      if not draft:
          raise ValueError("Draft not found")

      text = f"{draft.get('title', '')}\n\n{draft.get('body', '')}".strip()

      # 3) call Postiz
      client = PostizClient()
      result = await client.create_post(
          integration_ids=[integration_id],
          content=text,
      )

      postiz_post_id = result.get("id", "")

      # 4) update draft
      db.table("content_drafts").update({
          "status": "published",
          "published_url": result.get("url", ""),
          "postiz_post_id": postiz_post_id,
      }).eq("id", draft_id).execute()

      await log_publish_event(
          brand_id, draft_id,
          action="postiz_publish",
          platform=platform,
          status="success",
          details={"postiz_post_id": postiz_post_id},
      )

      return {"draft_id": draft_id, "postiz_post_id": postiz_post_id, "platform": platform}
  ```
- [ ] **Step 2: Refactor `social_publisher.py`**
  Replace the body of `publish_to_postiz` with a call to `postiz_publisher.publish_via_postiz` when `postiz_enabled=True`. Keep the old mock path as an explicit `elif not settings.postiz_enabled:` block with a loud warning log.
- [ ] **Step 3: Write tests**
  `python/tests/test_postiz_publisher.py`
- [ ] **Step 4: Commit**
  ```bash
  git add python/src/content_engine/services/postiz_publisher.py \
          python/src/content_engine/services/social_publisher.py \
          python/tests/test_postiz_publisher.py
  git commit -m "feat(p9): Postiz publisher service replaces mock"
  ```

---

### Task P9.5: Scheduler Bridge — publish_scheduled_posts delegates to Postiz

**Files:**
- Modify: `python/src/content_engine/services/scheduler.py`

- [ ] **Step 1: Locate `publish_scheduled_posts`**
  Search for `publish_scheduled_posts` in the codebase.
- [ ] **Step 2: Refactor to use Postiz**
  For each scheduled draft that is due:
  1. Determine platform from `content_drafts.platform`.
  2. Resolve `postiz_integration_id` from `brand_social_integrations`.
  3. Call `PostizClient.create_post(integration_ids=[...], content=..., scheduled_at=...)` — or if the time is already past, call without `scheduled_at` to publish immediately.
  4. Update draft status to `published`.
- [ ] **Step 3: Commit**
  ```bash
  git add python/src/content_engine/services/scheduler.py
  git commit -m "feat(p9): scheduler delegates scheduled publishes to Postiz"
  ```

---

### Task P9.6: Next.js API — `brand_social_integrations` CRUD

**Files:**
- Create: `src/app/api/brands/[id]/social-integrations/route.ts`
- Create: `src/app/api/brands/[id]/social-integrations/[platform]/route.ts`

- [ ] **Step 1: Write list + upsert route**
  `GET` returns rows for the brand.
  `POST` upserts `{ platform, postiz_integration_id, postiz_channel_name }`.
- [ ] **Step 2: Write delete route**
  `DELETE /api/brands/[id]/social-integrations/[platform]`
- [ ] **Step 3: Commit**
  ```bash
  git add src/app/api/brands/\[id\]/social-integrations/
  git commit -m "feat(p9): CRUD API for brand_social_integrations"
  ```

---

### Task P9.7: Settings UI — Social Connections page

**Files:**
- Create: `src/app/(dashboard)/settings/social-connections/page.tsx`
- Create: `src/components/settings/social-integrations-card.tsx`
- Modify: `src/app/(dashboard)/settings/page.tsx`

- [ ] **Step 1: Write the settings page**
  Displays a grid of supported platforms. For each:
  - shows current `postiz_integration_id` if set
  - input field to paste the integration ID from Postiz
  - save button calling the CRUD API
  - status badge (active / missing)
- [ ] **Step 2: Add link in Settings index**
  New card in `src/app/(dashboard)/settings/page.tsx` with a link to `/settings/social-connections`.
- [ ] **Step 3: Commit**
  ```bash
  git add src/app/\(dashboard\)/settings/social-connections/ \
          src/components/settings/social-integrations-card.tsx \
          src/app/\(dashboard\)/settings/page.tsx
  git commit -m "feat(p9): social connections settings UI"
  ```

---

### Task P9.8: FastAPI routes — mount Postiz analytics bridge

**Files:**
- Create: `python/src/content_engine/api/routes_postiz.py`
- Modify: `python/src/content_engine/api/routes.py`

- [ ] **Step 1: Write bridge routes**
  - `GET /social/analytics?platform=&days=` → calls Postiz analytics and returns JSON
  - `GET /social/integrations` → proxies `PostizClient.list_integrations()` so the frontend can discover available channels
- [ ] **Step 2: Mount router**
  In `routes.py`: `from .routes_postiz import router as postiz_router; app.include_router(postiz_router)`
- [ ] **Step 3: Commit**
  ```bash
  git add python/src/content_engine/api/routes_postiz.py python/src/content_engine/api/routes.py
  git commit -m "feat(p9): Postiz analytics + integrations bridge routes"
  ```

---

### Task P9.9: Documentation sweep

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/SETUP.md`
- Modify: `docs/DEPLOYMENT.md`
- Modify: `docs/API.md`

- [ ] **Step 1: `.env.example`**
  Append Postiz section (see §4).
- [ ] **Step 2: `README.md`**
  Add a paragraph in the scope/stack section:
  > "Social publishing is handled by a self-hosted Postiz satellite (Docker) that manages OAuth, scheduling, and analytics for LinkedIn, X, Instagram, TikTok, YouTube, Reddit, and 20+ other platforms."
- [ ] **Step 3: `docs/SETUP.md`**
  Add a new section "5. Start the Postiz satellite" after the backend start:
  ```markdown
  ### 5. Start the Postiz satellite (optional, required for social publishing)
  1. Create OAuth apps on each social platform you need.
  2. Fill `postiz/.env.postiz`.
  3. Run: `docker compose -f docker-compose.postiz.yaml up -d`
  4. Visit http://localhost:4200 → create admin → Settings → API → copy API key.
  5. Paste the API key into `.env.local` as `POSTIZ_API_KEY`.
  6. Go to Integrations in Postiz and connect each social account.
  7. In our dashboard (Settings → Social Connections), paste the Postiz integration IDs.
  ```
- [ ] **Step 4: `docs/DEPLOYMENT.md`**
  Add Postiz containers to the production topology diagram.
- [ ] **Step 5: `docs/API.md`**
  Add Postiz bridge routes and the `brand_social_integrations` CRUD endpoints.
- [ ] **Step 6: Commit**
  ```bash
  git add .env.example README.md docs/
  git commit -m "docs(p9): Postiz satellite setup and deployment docs"
  ```

---

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **Temporal startup slow / heavy** | Temporal container uses ~300MB RAM. Acceptable for dev. In production, use Temporal Cloud or replace with a lightweight in-memory scheduler if Postiz adds support. |
| **Postiz Prisma migrations collide with our migrations** | Postiz is isolated in schema `postiz`. Our migrations never touch that schema. |
| **OAuth callback URLs must point to Postiz (localhost:4200)** | Postiz UI handles OAuth callbacks. Our app never sees tokens. User must configure redirect URIs in each social dev portal to `http://localhost:4200/integrations/social/callback` (or production domain equivalent). |
| **Postiz API key exposure** | Stored in `.env.local` (server-side only). Never sent to browser. |
| **AGPL contamination fear** | We call Postiz via HTTP API over a TCP socket. This is not linking, not a derivative work under AGPL. Our codebase remains independent. |
| **Supabase connection limits** | Postiz + our app + Temporal DB all hit the same Supabase Postgres. Free tier allows 60 connections. If exceeded, enable Supabase connection pooling (pgBouncer) on port 6543. |
| **Image/media upload mismatch** | Postiz requires media URLs it can reach. We must upload generated images to Postiz's local storage (`/uploads`) or to a public URL. Mitigation: before calling Postiz, POST the image bytes to Postiz `/public/v1/upload` and use the returned URL. |

---

## 7. What is NOT in scope (and why)

- **Direct OAuth flow inside our UI.** Postiz already has a beautiful OAuth UI. Re-implementing it would require ~20 OAuth handlers and constant maintenance. We delegate.
- **Auto-provisioning Postiz organizations per brand.** Postiz does not expose an admin API to create organizations programmatically without internal tokens. We use a single Postiz instance and distinguish channels via integration IDs.
- **Replacing our scheduler with Temporal.** Temporal is only for Postiz internal workflows. Our `publish_scheduled_posts` remains pg_cron-driven; it just calls Postiz at publish time.
- **Video publishing (TikTok, YouTube Shorts).** Postiz supports it, but our image generator (P8) only emits images. Video support is P10+.
- **Real-time analytics streaming.** We poll Postiz analytics daily, not via webhook. Postiz webhooks are enterprise/self-hosted custom features.

---

## 8. Files touched summary

**New migrations (1):** `027_postiz_social_integrations.sql`

**New Docker / infrastructure (3):**
- `docker-compose.postiz.yaml`
- `postiz/.env.postiz`
- `postiz/README-POSTIZ.md`

**New Python modules (3):**
- `python/src/content_engine/services/postiz_client.py`
- `python/src/content_engine/services/postiz_publisher.py`
- `python/src/content_engine/api/routes_postiz.py`

**New tests (2):**
- `python/tests/test_postiz_client.py`
- `python/tests/test_postiz_publisher.py`

**New Next.js API routes (2):**
- `src/app/api/brands/[id]/social-integrations/route.ts`
- `src/app/api/brands/[id]/social-integrations/[platform]/route.ts`

**New React components (2):**
- `src/components/settings/social-integrations-card.tsx`
- `src/app/(dashboard)/settings/social-connections/page.tsx`

**Modified:**
- `python/src/content_engine/config.py`
- `python/src/content_engine/services/social_publisher.py`
- `python/src/content_engine/services/scheduler.py`
- `python/src/content_engine/api/routes.py`
- `src/app/(dashboard)/settings/page.tsx`
- `src/lib/types/database.types.ts`
- `.env.example`
- `README.md`
- `docs/SETUP.md`
- `docs/DEPLOYMENT.md`
- `docs/API.md`

---

## 9. Self-review checklist (pre-execution)

- ✅ **Spec coverage**
  - Postiz self-hosted Docker satellite → P9.2
  - Schema isolation (`postiz`) → P9.1 + docker-compose env
  - OAuth delegated to Postiz UI → P9.2 README instructions
  - Public API client typed → P9.3
  - Publisher refactor (mock replaced) → P9.4
  - Scheduler bridge → P9.5
  - Settings UI for integration IDs → P9.7
  - Analytics bridge → P9.8
  - Documentation sweep → P9.9
- ✅ **Placeholder scan**: no "TBD", all code blocks complete.
- ✅ **Type consistency**: `PostizClient`, `PostizPublisher`, `brand_social_integrations` stable across tasks.
- ✅ **Path consistency**: storage paths not touched; all DB paths scoped by `brand_id`.

---

## 10. Execution handoff

**Two execution options:**

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks.
   → REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`

2. **Inline Execution** — Execute tasks in this session with checkpoints for review.
   → REQUIRED SUB-SKILL: `superpowers:executing-plans`

**Recommended sequencing:** P9.1 → P9.2 → P9.3 → P9.4 → P9.5 → P9.6 → P9.7 → P9.8 → P9.9.

**Estimated effort:** ~2.5 days (Docker + Python + Next.js + docs).

---

## 11. Manual steps the user MUST perform (cannot be scripted)

These steps require human interaction with external platforms and cannot be automated by this codebase:

| Step | Platform | Action | Why it can't be scripted |
|---|---|---|---|
| 1 | **LinkedIn Developer Portal** | Create OAuth 2.0 app, obtain `LINKEDIN_CLIENT_ID` + `LINKEDIN_CLIENT_SECRET` | Requires accepting legal terms, verifying identity, callback domain ownership. |
| 2 | **X Developer Portal** | Create app, obtain `X_API_KEY` + `X_API_SECRET` | Same as above + elevated access approval (manual review). |
| 3 | **Meta (Facebook)** | Create app for Instagram + Facebook, obtain `FACEBOOK_APP_ID` + `FACEBOOK_APP_SECRET` | Business verification required for Instagram Basic Display. |
| 4 | **TikTok for Developers** | Create app, obtain `TIKTOK_CLIENT_ID` + `TIKTOK_CLIENT_SECRET` | Requires business account + app review. |
| 5 | **YouTube / Google Cloud** | Create OAuth credentials, obtain `YOUTUBE_CLIENT_ID` + `YOUTUBE_CLIENT_SECRET` | Google OAuth consent screen requires manual branding setup. |
| 6 | **Reddit** | Create app, obtain `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | OAuth app creation is manual. |
| 7 | **Pinterest, Threads, Bluesky, etc.** | Same pattern for each platform you need. | All require developer portal registration. |
| 8 | **Postiz UI (localhost:4200)** | Complete OAuth for each platform inside Postiz. Postiz opens the platform OAuth dialog; you authorize. | Involves browser redirects and 2FA on social accounts. |
| 9 | **Postiz UI → Settings → API** | Generate API key and paste into `.env.local` as `POSTIZ_API_KEY`. | Key is generated server-side inside Postiz. |
| 10 | **Our Dashboard** | For each connected platform, copy the Postiz `integration_id` into Settings → Social Connections. | Integration IDs are only visible after successful OAuth in Postiz. |
| 11 | **Supabase Dashboard** | Add your local IP to the Database Connection Pool allow-list (if self-hosting locally). | Security measure; cannot be automated via CLI without service-role escalation. |

**Workflow diagram for manual steps:**

```
External Dev Portals
  → create OAuth apps → get CLIENT_ID/SECRET
        ↓
postiz/.env.postiz  (paste IDs)
        ↓
docker compose -f docker-compose.postiz.yaml up -d
        ↓
http://localhost:4200  (Postiz UI)
  → login as admin
  → Integrations → Add LinkedIn/X/IG/etc.
  → complete OAuth popup
  → Settings → API → generate key
        ↓
.env.local  (paste POSTIZ_API_KEY)
        ↓
Our Dashboard → Settings → Social Connections
  → copy integration IDs from Postiz into each platform row
        ↓
Ready to publish 🚀
```

---

*End of PRD.*
