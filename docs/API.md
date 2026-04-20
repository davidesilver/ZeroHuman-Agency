# API Guide

This project exposes two API layers:

- `Next.js route handlers` under [`src/app/api`](/Users/claw/Progetti/ai-automation/src/app/api), used by the browser and by simple integrations
- `FastAPI routes` under [`python/src/content_engine/api`](/Users/claw/Progetti/ai-automation/python/src/content_engine/api), used for orchestration and protected service logic

## Authentication Model

Browser and first-party consumers:

- authenticate with Supabase
- call the Next.js routes on the frontend host
- the frontend forwards the Supabase JWT to FastAPI when needed

Direct backend consumers:

- must send `Authorization: Bearer <supabase-access-token>`
- optional `X-Brand-ID` is validated against the token if present

Scheduler consumers:

- call protected endpoints with `X-Scheduler-Secret`
- do not use a user JWT
- require `SCHEDULER_BRAND_ID` on the backend side

## Response Shape

Most routes return one of these shapes:

```json
{ "success": true, "data": { "...": "..." } }
```

```json
{ "success": false, "error": { "message": "..." } }
```

## Frontend Route Inventory

These routes are available on the Next.js application host.

### Health And System

| Route | Method | Notes |
| --- | --- | --- |
| `/api/health` | `GET` | basic frontend liveness |
| `/api/system/health` | `GET` | reads `pipeline_health` and fallback logs |
| `/api/system/activity` | `GET` | aggregates research, drafts, newsletters |
| `/api/system/costs` | `GET` | reads cost data from Supabase |

### Tenant, Research, Drafts

| Route | Method | Notes |
| --- | --- | --- |
| `/api/brands` | `GET` | direct Supabase read |
| `/api/research/trigger` | `POST` | proxies to FastAPI |
| `/api/research/runs` | `GET` | proxies to FastAPI |
| `/api/research/items` | `GET` | direct Supabase read with auth |
| `/api/research/items/:id/status` | `PATCH` | proxies to FastAPI |
| `/api/research/stats` | `GET` | direct Supabase read |
| `/api/content/from-url` | `POST` | inserts a manual research item directly in Supabase |
| `/api/content/drafts` | `GET` | direct Supabase read |
| `/api/content/drafts/:id` | `GET`, `PATCH` | direct Supabase read/update |
| `/api/content/generate` | `POST` | proxies to FastAPI |
| `/api/content/drafts/:id/god-mode` | `POST` | proxies to FastAPI |

### Agents

| Route | Method | Notes |
| --- | --- | --- |
| `/api/v1/agent-configs` | `GET`, `POST` | mixed frontend auth + FastAPI proxy |
| `/api/v1/agent-configs/:id` | `PUT`, `DELETE` | proxies to FastAPI |
| `/api/v1/agent-skills` | `GET`, `POST` | mixed frontend auth + FastAPI proxy |
| `/api/v1/agent-skills/:id` | `PUT`, `DELETE` | proxies to FastAPI |

### Writing Lab, Newsletter, Social

| Route | Method | Notes |
| --- | --- | --- |
| `/api/writing-lab/sessions` | `GET`, `POST` | `GET` reads Supabase directly, `POST` proxies |
| `/api/writing-lab/sessions/:id` | `GET` | direct/read proxy hybrid depending route |
| `/api/writing-lab/sessions/:id/vote` | `POST` | proxies to FastAPI |
| `/api/newsletter` | `GET` | direct Supabase read |
| `/api/newsletter/:id` | `GET`, `PATCH` | direct Supabase read/update |
| `/api/newsletter/:id/preview` | `GET` | proxies to FastAPI |
| `/api/newsletter/send` | `POST` | proxies to FastAPI |
| `/api/social/publish/linkedin` | `POST` | proxies to FastAPI |
| `/api/social/publish/twitter` | `POST` | proxies to FastAPI |
| `/api/social/schedule` | `POST` | proxies to FastAPI |

### Scheduler And Analytics

| Route | Method | Notes |
| --- | --- | --- |
| `/api/analytics/metrics` | `POST` | proxies to FastAPI |
| `/api/analytics/feedback-loop` | `POST` | proxies to FastAPI |
| `/api/scheduler/daily-pipeline` | `POST` | proxies to FastAPI |
| `/api/scheduler/publish-scheduled` | `POST` | proxies to FastAPI |

## FastAPI Route Inventory

The backend lives at `PYTHON_BACKEND_URL`.

### Public

| Route | Method | Auth |
| --- | --- | --- |
| `/health` | `GET` | none |
| `/health/db` | `GET` | none |

### Research And Scoring

| Route | Method | Auth |
| --- | --- | --- |
| `/api/research/trigger` | `POST` | JWT |
| `/api/research/runs` | `GET` | JWT |
| `/api/research/items` | `GET` | JWT |
| `/api/research/items/{item_id}/status` | `PATCH` | JWT |
| `/api/research/stats` | `GET` | JWT |
| `/api/scoring/run` | `POST` | JWT |

### Draft Pipeline

| Route | Method | Auth |
| --- | --- | --- |
| `/api/content/generate` | `POST` | JWT |
| `/api/content/drafts` | `GET` | JWT |
| `/api/content/drafts/{draft_id}` | `PATCH` | JWT |
| `/api/content/drafts/{draft_id}/god-mode` | `POST` | JWT |
| `/api/content/drafts/{draft_id}/adapt` | `POST` | JWT |
| `/api/content/drafts/{draft_id}/humanize` | `POST` | JWT |

### Writing Lab, Newsletter, Social

| Route | Method | Auth |
| --- | --- | --- |
| `/api/writing-lab/sessions` | `GET`, `POST` | JWT |
| `/api/writing-lab/sessions/{session_id}` | `GET` | JWT |
| `/api/writing-lab/sessions/{session_id}/vote` | `POST` | JWT |
| `/api/newsletter/send` | `POST` | JWT |
| `/api/newsletter/{newsletter_id}/preview` | `GET` | JWT |
| `/api/social/publish` | `POST` | JWT |
| `/api/social/publish/linkedin` | `POST` | JWT |
| `/api/social/publish/twitter` | `POST` | JWT |
| `/api/social/schedule` | `POST` | JWT |

### Analytics, Scheduler, Ops

| Route | Method | Auth |
| --- | --- | --- |
| `/api/analytics/metrics` | `POST` | none in route handler |
| `/api/analytics/feedback-loop` | `POST` | JWT |
| `/api/analytics/pull-metrics` | `POST` | scheduler secret |
| `/api/scheduler/daily-pipeline` | `POST` | scheduler secret |
| `/api/scheduler/publish-scheduled` | `POST` | scheduler secret |
| `/api/auth/cache-invalidate` | `POST` | scheduler secret |
| `/api/llm/fallback-stats` | `GET` | no explicit JWT enforcement in route handler, but middleware applies |
| `/api/llm/fallback-log` | `GET` | JWT |
| `/api/llm/fallback-monitor/reset` | `POST` | scheduler secret |

### Agent CRUD

| Route | Method | Auth |
| --- | --- | --- |
| `/api/v1/agent-configs` | `GET`, `POST` | JWT |
| `/api/v1/agent-configs/{config_id}` | `GET`, `PUT`, `DELETE` | JWT |
| `/api/v1/agent-skills` | `GET`, `POST` | JWT |
| `/api/v1/agent-skills/{skill_id}` | `GET`, `PUT`, `DELETE` | JWT |

## Example Requests

Trigger research from an authenticated client:

```bash
curl -X POST http://localhost:8000/api/research/trigger \
  -H "Authorization: Bearer <supabase-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"retrievers":["semantic","trend"],"max_items_per_retriever":25}'
```

Generate a draft with GOD mode enabled:

```bash
curl -X POST http://localhost:8000/api/content/generate \
  -H "Authorization: Bearer <supabase-access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "research_item_id":"<research-item-uuid>",
    "platform":"linkedin",
    "content_type":"post",
    "run_god":true,
    "run_humanizer":false
  }'
```

Run the protected scheduler endpoint:

```bash
curl -X POST http://localhost:8000/api/scheduler/daily-pipeline \
  -H "X-Scheduler-Secret: <scheduler-secret>"
```

## Known Gaps

- The frontend exposes `POST /api/newsletter/generate`, but there is no matching FastAPI endpoint in [`python/src/content_engine/api/routes.py`](/Users/claw/Progetti/ai-automation/python/src/content_engine/api/routes.py). Treat it as incomplete.
- The API surface is intentionally hybrid: some Next.js routes query Supabase directly while others proxy to FastAPI. Integrators should not assume all `/api/*` routes behave the same way internally.
