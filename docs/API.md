# API Guide

The platform exposes two API surfaces:

- **Next.js route handlers** (`src/app/api/`) — used by the browser and simple integrations; mix of direct Supabase reads and FastAPI proxies
- **FastAPI routes** (`python/src/content_engine/api/`) — orchestration-heavy logic; always requires auth

All responses use a consistent envelope:

```json
{ "success": true, "data": { ... } }
{ "success": false, "error": { "message": "..." } }
```

---

## Authentication

### Browser / first-party clients

Authenticate via Supabase, then call Next.js routes. The frontend forwards the Supabase JWT to FastAPI automatically via `proxyToBackend()`.

### Direct FastAPI access

```http
Authorization: Bearer <supabase-access-token>
Content-Type: application/json
X-Brand-ID: <brand-uuid>   # optional; validated against token if present
```

### Scheduler / cron callers

Protected endpoints only — no user JWT required:

```http
X-Scheduler-Secret: <your-scheduler-secret>
```

---

## Next.js route inventory

### System and health

| Route | Method | Source |
|---|---|---|
| `/api/system/health` | GET | Supabase |
| `/api/system/activity` | GET | Supabase |
| `/api/system/costs` | GET | Supabase |
| `/api/system/config` | GET | Env (no secrets exposed) |

### Brands and assets

| Route | Method | Source |
|---|---|---|
| `/api/brands` | GET | Supabase |
| `/api/brands/:id` | GET, PATCH | Supabase |
| `/api/brands/:id/assets` | GET, POST | Supabase |
| `/api/brands/:id/assets/:assetId` | GET, PATCH, DELETE | Supabase |
| `/api/brands/:id/assets/:assetId/preview` | GET | Supabase Storage |
| `/api/brands/:id/assets/upload-url` | GET | Supabase (signed URL) |

### Research

| Route | Method | Source |
|---|---|---|
| `/api/research/trigger` | POST | → FastAPI |
| `/api/research/runs` | GET | → FastAPI |
| `/api/research/items` | GET | Supabase |
| `/api/research/items/:id/status` | PATCH | → FastAPI |
| `/api/research/stats` | GET | Supabase |
| `/api/content/from-url` | POST | Supabase (manual URL insert) |

### Content and drafts

| Route | Method | Source |
|---|---|---|
| `/api/content/drafts` | GET | Supabase |
| `/api/content/drafts/:id` | GET, PATCH | Supabase |
| `/api/content/generate` | POST | → FastAPI |
| `/api/content/drafts/:id/god-mode` | POST | → FastAPI |

### Writing Lab

| Route | Method | Source |
|---|---|---|
| `/api/writing-lab/sessions` | GET, POST | GET: Supabase · POST: → FastAPI |
| `/api/writing-lab/sessions/:id` | GET | Supabase |
| `/api/writing-lab/sessions/:id/vote` | POST | → FastAPI |

### Newsletter

| Route | Method | Source |
|---|---|---|
| `/api/newsletter` | GET | Supabase |
| `/api/newsletter/:id` | GET, PATCH | Supabase |
| `/api/newsletter/:id/preview` | GET | → FastAPI |
| `/api/newsletter/send` | POST | → FastAPI |

### Social publishing

| Route | Method | Source |
|---|---|---|
| `/api/social/publish` | POST | → FastAPI |
| `/api/social/publish/linkedin` | POST | → FastAPI |
| `/api/social/publish/twitter` | POST | → FastAPI |
| `/api/social/schedule` | POST | → FastAPI |
| `/api/social/health` | GET | → FastAPI |
| `/api/social/integrations` | GET | → FastAPI |
| `/api/social/integrations/mine` | GET | → FastAPI |
| `/api/social/integrations/mine/:platform` | GET | → FastAPI |
| `/api/social/analytics` | GET | → FastAPI |

### Image generation

| Route | Method | Source |
|---|---|---|
| `/api/images/generate` | POST | → FastAPI |
| `/api/images/carousel` | POST | → FastAPI |
| `/api/images/jobs/:id` | GET | → FastAPI |
| `/api/images/stats` | GET | → FastAPI |

### Memory

| Route | Method | Source |
|---|---|---|
| `/api/memory/facts` | GET, POST | Supabase (`memory_semantic`) |
| `/api/memory/facts/:id` | GET, PATCH, DELETE | Supabase |
| `/api/memory/episodic` | GET | Supabase (view) |
| `/api/memory/consolidate` | POST | → FastAPI |
| `/api/memory/discover` | POST | → FastAPI |
| `/api/memory/upload` | POST | → FastAPI |

### Agents

| Route | Method | Source |
|---|---|---|
| `/api/v1/agent-configs` | GET, POST | GET: Supabase · POST: → FastAPI |
| `/api/v1/agent-configs/:id` | GET, PUT, DELETE | → FastAPI |
| `/api/v1/agent-skills` | GET, POST | GET: Supabase · POST: → FastAPI |
| `/api/v1/agent-skills/:id` | GET, PUT, DELETE | → FastAPI |

### Scheduler and analytics

| Route | Method | Source |
|---|---|---|
| `/api/scheduler/daily-pipeline` | POST | → FastAPI |
| `/api/scheduler/publish-scheduled` | POST | → FastAPI |
| `/api/analytics/metrics` | POST | → FastAPI |
| `/api/analytics/feedback-loop` | POST | → FastAPI |
| `/api/scoring/run` | POST | → FastAPI |

---

## FastAPI route inventory

Base URL: `PYTHON_BACKEND_URL` (default: `http://localhost:8000`)

### Public (no auth)

| Route | Method |
|---|---|
| `/health` | GET |
| `/health/db` | GET |

### Research and scoring

| Route | Method | Auth |
|---|---|---|
| `/api/research/trigger` | POST | JWT |
| `/api/research/runs` | GET | JWT |
| `/api/research/items` | GET | JWT |
| `/api/research/items/{item_id}/status` | PATCH | JWT |
| `/api/research/stats` | GET | JWT |
| `/api/scoring/run` | POST | JWT |

### Content generation

| Route | Method | Auth |
|---|---|---|
| `/api/content/generate` | POST | JWT |
| `/api/content/drafts` | GET | JWT |
| `/api/content/drafts/{id}` | PATCH | JWT |
| `/api/content/drafts/{id}/god-mode` | POST | JWT |
| `/api/content/drafts/{id}/adapt` | POST | JWT |
| `/api/content/drafts/{id}/humanize` | POST | JWT |

### Writing Lab and Newsletter

| Route | Method | Auth |
|---|---|---|
| `/api/writing-lab/sessions` | GET, POST | JWT |
| `/api/writing-lab/sessions/{id}` | GET | JWT |
| `/api/writing-lab/sessions/{id}/vote` | POST | JWT |
| `/api/newsletter/send` | POST | JWT |
| `/api/newsletter/{id}/preview` | GET | JWT |

### Social publishing

| Route | Method | Auth |
|---|---|---|
| `/api/social/publish` | POST | JWT |
| `/api/social/publish/linkedin` | POST | JWT |
| `/api/social/publish/twitter` | POST | JWT |
| `/api/social/schedule` | POST | JWT |
| `/api/social/health` | GET | JWT |
| `/api/social/integrations` | GET | JWT |
| `/api/social/integrations/mine` | GET | JWT |
| `/api/social/analytics` | GET | JWT |

### Image generation

| Route | Method | Auth |
|---|---|---|
| `/images/generate` | POST | JWT |
| `/images/carousel` | POST | JWT |
| `/images/jobs/{id}` | GET | JWT |
| `/images/stats` | GET | JWT |

### Agent CRUD

| Route | Method | Auth |
|---|---|---|
| `/api/v1/agent-configs` | GET, POST | JWT |
| `/api/v1/agent-configs/{id}` | GET, PUT, DELETE | JWT |
| `/api/v1/agent-skills` | GET, POST | JWT |
| `/api/v1/agent-skills/{id}` | GET, PUT, DELETE | JWT |

### Analytics and feedback loop

| Route | Method | Auth |
|---|---|---|
| `/api/analytics/metrics` | POST | JWT |
| `/api/analytics/feedback-loop` | POST | JWT |
| `/api/analytics/pull-metrics` | POST | Scheduler secret |
| `/api/llm/fallback-stats` | GET | JWT |
| `/api/llm/fallback-log` | GET | JWT |
| `/api/llm/fallback-monitor/reset` | POST | Scheduler secret |

### Scheduler (protected endpoints)

| Route | Method | Auth |
|---|---|---|
| `/api/scheduler/daily-pipeline` | POST | Scheduler secret |
| `/api/scheduler/publish-scheduled` | POST | Scheduler secret |
| `/api/auth/cache-invalidate` | POST | Scheduler secret |

---

## Example requests

**Trigger a research run:**

```bash
curl -X POST http://localhost:8000/api/research/trigger \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"retrievers": ["semantic", "rss", "trend"], "max_items_per_retriever": 25}'
```

**Generate a draft with GOD mode:**

```bash
curl -X POST http://localhost:8000/api/content/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "research_item_id": "<uuid>",
    "platform": "linkedin",
    "content_type": "post",
    "run_god": true,
    "run_humanizer": false
  }'
```

**Publish to a social platform:**

```bash
curl -X POST http://localhost:8000/api/social/publish \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "draft_id": "<uuid>",
    "platforms": ["linkedin", "twitter"]
  }'
```

**Generate an image for a draft:**

```bash
curl -X POST http://localhost:8000/images/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "draft_id": "<uuid>",
    "width": 1024,
    "height": 1024
  }'
```

**Call a scheduler endpoint:**

```bash
curl -X POST http://localhost:8000/api/scheduler/daily-pipeline \
  -H "X-Scheduler-Secret: <scheduler-secret>"
```
