# Setup Guide

This guide is written for two goals:

- a developer must be able to recreate the project from zero
- a non-specialist integrator must understand which pieces are mandatory and which are optional

## 1. Prerequisites

Required on the local machine:

- `Node.js 20+`
- `npm`
- `Python 3.14+` because [`python/pyproject.toml`](/Users/claw/Progetti/ai-automation/python/pyproject.toml) declares `requires-python = ">=3.14"`
- `uv` for Python dependency management
- `Supabase CLI`

External services used by the codebase:

- Supabase project
- at least one LLM provider key
- optional research, email, social, and enrichment providers

## 2. Clone And Install

Frontend:

```bash
npm install
```

Backend:

```bash
cd python
uv sync
```

## 3. Environment Variables

Copy [`.env.example`](/Users/claw/Progetti/ai-automation/.env.example) to `.env.local` in the repository root:

```bash
cp .env.example .env.local
```

Minimum variables needed for a working local stack:

| Variable | Required | Used by |
| --- | --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | frontend + backend |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | frontend auth + backend JWT validation |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | backend privileged access |
| `PYTHON_BACKEND_URL` | Yes | Next.js proxy routes |
| `ALLOWED_ORIGINS` | Yes | backend CORS |
| `SCHEDULER_SECRET` | Recommended locally, required in production | protected scheduler endpoints |

Feature-specific variables:

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | primary LLM provider |
| `OPENROUTER_API_KEY` | alternative/fallback LLM provider |
| `SERPER_API_KEY` | search retriever |
| `YOUTUBE_API_KEY` | YouTube retriever |
| `RESEND_API_KEY` | newsletter delivery |
| `FIRECRAWL_API_KEY` | optional premium content extraction |
| `SCHEDULER_BRAND_ID` | required for scheduler endpoints that run without a user JWT |

Additional backend settings are defined in [`python/src/content_engine/config.py`](/Users/claw/Progetti/ai-automation/python/src/content_engine/config.py).

## 4. Provision The Database

Apply all migrations from [`supabase/migrations`](/Users/claw/Progetti/ai-automation/supabase/migrations):

```bash
supabase link --project-ref <your-project-ref>
supabase db push
```

This creates:

- core tables such as `brands`, `users`, `research_items`, `content_drafts`, `newsletters`
- agent tables such as `agent_configs` and `agent_skills`
- observability tables such as `api_costs`, `pipeline_health`, `llm_fallback_log`
- RLS policies, views, enum types, and helper SQL functions

## 5. Bootstrap The First Tenant

Create one tenant record in `brands`:

```sql
insert into public.brands (
  name,
  slug,
  topics,
  tone_of_voice,
  scoring_weights,
  rss_sources
) values (
  'Example Workspace',
  'example-workspace',
  array['topic-a', 'topic-b'],
  '{"style":"clear","audience":"operators"}'::jsonb,
  '{"applicability":1,"credibility":1,"alignment":1,"trend_prediction":1,"italy_relevance":1}'::jsonb,
  '[]'::jsonb
);
```

Create a Supabase auth user, then add the matching application user row:

```sql
insert into public.users (id, brand_id, email, role)
values (
  '<auth-user-uuid>',
  '<brand-uuid>',
  'owner@example.com',
  'owner'
);
```

The backend resolves `brand_id` from the authenticated user record. Without this row, the user can log in but cannot use the application.

## 6. Start The Services

Backend:

```bash
cd python
uv run uvicorn src.content_engine.main:app --reload --port 8000
```

Frontend:

```bash
npm run dev
```

Default local URLs:

- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`

## 7. Smoke Tests

Check liveness:

```bash
curl http://localhost:8000/health
curl http://localhost:3000/api/health
```

Check database readiness:

```bash
curl http://localhost:8000/health/db
```

Then:

1. open the login page
2. sign in with the tenant user you created
3. load the dashboard
4. trigger one research run or add one manual URL

## 8. Recommended First End-To-End Test

1. Add a research source in the `brands.rss_sources` field.
2. Trigger `POST /api/research/trigger`.
3. Run `POST /api/scoring/run`.
4. Generate content with `POST /api/content/generate`.
5. Optionally run GOD mode or humanizer on the produced draft.

## 9. Common Failure Modes

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `401 Unauthorized` from backend | missing forwarded Supabase session | sign in again and verify frontend env values |
| `403 User has no associated brand` | missing row in `public.users` | insert the user-brand mapping |
| scheduler endpoints fail with `503` | `SCHEDULER_BRAND_ID` missing | set it in `.env.local` |
| CORS errors | `ALLOWED_ORIGINS` wrong | include the frontend origin |
| backend cannot connect to Supabase | missing URL or keys | re-check `.env.local` |
