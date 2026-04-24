# Social Publishing — Postiz Satellite

The platform delegates all social publishing to [Postiz](https://github.com/gitroomhq/postiz-app), an open-source social scheduling tool. This keeps platform OAuth tokens out of the Content Engine database and lets Postiz handle rate limiting, retries, and multi-platform dispatch.

**AGPL boundary:** Postiz runs as a separate process, connected only via HTTP API. No Postiz source code lives in this repository.

---

## Modes

| Mode | `POSTIZ_MODE` | When to use |
|---|---|---|
| Disabled | `disabled` | Default. Social features hidden in dashboard. |
| Self-hosted | `self_hosted` | Full control, no SaaS fees, local OAuth flows |
| Cloud | `cloud` | Managed Postiz instance or VPS deployment |

---

## Self-hosted setup

### Prerequisites

- Docker and Docker Compose
- OAuth credentials for each platform you want to connect (LinkedIn app, X/Twitter app, Meta app, etc.)

### 1. Configure Postiz environment

```bash
cp postiz/.env.postiz.example postiz/.env.postiz
```

Edit `postiz/.env.postiz` and fill in your OAuth app credentials and database connection.

### 2. Start the Postiz stack

```bash
docker compose -f docker-compose.postiz.yaml up -d
```

This starts:

| Service | Port | Purpose |
|---|---|---|
| `postiz-app` | 4200 (UI) · 3001 (API) | Core Postiz application |
| `postiz-redis` | internal | Job queue and cache |
| `postiz-temporal` | internal | Workflow orchestration |
| `postiz-temporal-ui` | 8233 | Temporal monitoring (localhost only) |

### 3. Create admin user and API key

1. Open `http://localhost:4200`
2. Register your admin account
3. Go to **Settings → API** → generate an API key

### 4. Connect social accounts

1. In Postiz, go to **Integrations → Add**
2. Complete the OAuth flow for each platform
3. Once connected, copy the **Integration ID** for each platform (visible in the Postiz integrations list)

### 5. Configure Content Engine

Add to `.env.local`:

```bash
POSTIZ_MODE=self_hosted
POSTIZ_API_URL=http://localhost:3001
POSTIZ_API_KEY=<api-key-from-step-3>
```

### 6. Link integrations to the brand

1. In the Content Engine dashboard, go to **Settings → Social Connections**
2. Paste the integration ID for each platform
3. These are stored in `brand_social_integrations` in the database

---

## Cloud setup

The process is identical except:

```bash
POSTIZ_MODE=cloud
POSTIZ_API_URL=https://your-postiz-domain.com
POSTIZ_API_KEY=<your-api-key>
```

Complete OAuth and paste integration IDs the same way.

---

## How publishing works

```
User clicks "Publish" in dashboard
  ↓
Content Engine backend resolves integration IDs
  from brand_social_integrations for the selected platforms
  ↓
POST /public/v1/posts → Postiz API
  {integration_ids: [...], content: "...", media_urls: [...]}
  Idempotency-Key: publish:<draft_id>    ← prevents duplicates on retry
  ↓
Postiz dispatches to each platform with its own rate limiting and retry logic
  ↓
Content Engine updates draft status → "published"
  stores postiz_post_ids in content_drafts.metadata
```

**Scheduling:** same flow but `scheduled_at` is passed to Postiz. Postiz owns the schedule — Content Engine does not need to poll or re-trigger.

**Retry safety:** the `Idempotency-Key` header ensures that if the publish call is retried (due to timeout or network error), Postiz will not create a duplicate post.

---

## Analytics sync

After posts are published, the platform pulls engagement metrics back via the Postiz analytics API. This is triggered by the `POST /api/analytics/pull-metrics` scheduler endpoint.

Metrics are stored in `social_metrics` and feed back into the scoring engine to influence future content prioritization.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| "Postiz disabled" error | `POSTIZ_MODE=disabled` | Set mode and restart backend |
| 503 from Postiz | Container not running | `docker compose -f docker-compose.postiz.yaml ps` |
| "No active integration for platform X" | Missing integration ID | Paste ID in Settings → Social Connections |
| Post appears blank or duplicated | Retry without idempotency key | Check `postiz_post_ids` in draft metadata; should only post once |
| OAuth expired | Platform token rotation | Re-connect OAuth in Postiz UI |
| Analytics not updating | `pull-metrics` job not scheduled | Set up scheduler cron (see DEPLOYMENT.md) |

---

## File reference

| File | Purpose |
|---|---|
| `docker-compose.postiz.yaml` | Self-hosted Postiz stack |
| `postiz/.env.postiz.example` | OAuth and DB configuration template |
| `python/src/content_engine/services/postiz_client.py` | Typed HTTP client with retry and idempotency |
| `python/src/content_engine/services/postiz_publisher.py` | Publish and schedule logic with SSRF-safe media URL validation |
| `python/src/content_engine/services/postiz_analytics.py` | Metrics pull from Postiz |
| `python/src/content_engine/api/routes_postiz.py` | FastAPI bridge routes |
| `src/app/(dashboard)/settings/social-connections/page.tsx` | Integration ID management UI |
| `supabase/migrations/028_brand_social_integrations.sql` | `brand_social_integrations` table and RLS |
