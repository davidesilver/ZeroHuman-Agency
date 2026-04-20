# Architecture

## System Overview

The project is split into three runtime layers:

1. `Next.js` serves the authenticated web application and exposes first-party route handlers.
2. `FastAPI` executes research, scoring, generation, scheduling, review, and agent logic.
3. `Supabase` stores tenant data, application users, auth sessions, and operational telemetry.

This is not a microservices platform with many independently deployed services. It is a two-application system around one shared database.

## Runtime Responsibilities

### Frontend: [`src`](/Users/claw/Progetti/ai-automation/src)

Responsibilities:

- login and session handling
- dashboard pages
- server-side route handlers under `src/app/api`
- direct reads and writes for simple tenant-scoped operations
- request forwarding to FastAPI for orchestration-heavy workflows

Important detail:

- some routes read Supabase directly, for example brands, dashboard stats, drafts, and writing-lab listing
- some routes proxy to FastAPI through [`src/lib/api-helpers.ts`](/Users/claw/Progetti/ai-automation/src/lib/api-helpers.ts)

### Backend: [`python/src/content_engine`](/Users/claw/Progetti/ai-automation/python/src/content_engine)

Responsibilities:

- research retrievers
- scoring pipeline
- content generation
- GOD mode review
- humanizer
- social publishing and scheduling
- newsletter preview/send
- feedback loop
- LLM fallback monitoring
- scheduler endpoints
- agent config and skills CRUD

FastAPI entrypoint:

- [`python/src/content_engine/main.py`](/Users/claw/Progetti/ai-automation/python/src/content_engine/main.py)

Primary route modules:

- [`python/src/content_engine/api/routes.py`](/Users/claw/Progetti/ai-automation/python/src/content_engine/api/routes.py)
- [`python/src/content_engine/api/routes_agents.py`](/Users/claw/Progetti/ai-automation/python/src/content_engine/api/routes_agents.py)

### Database: [`supabase/migrations`](/Users/claw/Progetti/ai-automation/supabase/migrations)

Responsibilities:

- tenant records in `brands`
- user-to-tenant mapping in `users`
- research, scoring, drafts, newsletters, analytics, observability, and agent metadata
- enum types, helper functions, and read views
- Row Level Security across tenant-scoped tables

## Request Flow

### Authenticated Browser To FastAPI

1. User signs in through Supabase from the Next.js app.
2. A Next.js route handler calls `proxyToBackend`.
3. The current Supabase access token is forwarded as `Authorization: Bearer <token>`.
4. FastAPI middleware validates the JWT and resolves the caller's `brand_id`.
5. Route handlers operate against a user-scoped or service-scoped Supabase client.

Relevant files:

- [`src/lib/supabase/auth-helpers.ts`](/Users/claw/Progetti/ai-automation/src/lib/supabase/auth-helpers.ts)
- [`src/lib/api-helpers.ts`](/Users/claw/Progetti/ai-automation/src/lib/api-helpers.ts)
- [`python/src/content_engine/api/auth_middleware.py`](/Users/claw/Progetti/ai-automation/python/src/content_engine/api/auth_middleware.py)

### Scheduler Flow

1. An external scheduler or CI runner calls a protected backend endpoint.
2. The request includes `X-Scheduler-Secret`.
3. FastAPI authorizes the request without a user JWT.
4. The backend runs the job for the configured `SCHEDULER_BRAND_ID`.

Repository example:

- [`.github/workflows/daily-pipeline.yml`](/Users/claw/Progetti/ai-automation/.github/workflows/daily-pipeline.yml)

## Multi-Tenant Isolation

Tenant isolation is implemented in two layers:

- application layer: frontend helpers and backend middleware resolve `brand_id` from the authenticated user
- database layer: Supabase RLS policies constrain access to tenant rows

This means a correct setup requires all three of these to exist:

- a Supabase auth user
- a matching row in `public.users`
- an existing `public.brands` record

## Security Controls Already Present

- JWT verification on non-public backend routes
- RLS on core tables
- scheduler secret for cron-style execution
- persistent backend rate limiting
- CORS allowlist from `ALLOWED_ORIGINS`
- request correlation via `X-Request-ID`

## Data Flow Summary

Typical happy path:

1. create or discover research items
2. score them
3. generate drafts
4. optionally run GOD mode and humanizer
5. publish or schedule drafts
6. collect metrics and feed them back into scoring

Supporting tables store:

- costs
- health/heartbeat data
- fallback incidents
- writing-lab rounds
- newsletter candidate composition

## Directory Map

| Path | Purpose |
| --- | --- |
| [`src/app`](/Users/claw/Progetti/ai-automation/src/app) | pages and Next route handlers |
| [`src/components`](/Users/claw/Progetti/ai-automation/src/components) | UI building blocks |
| [`src/lib`](/Users/claw/Progetti/ai-automation/src/lib) | auth, Supabase, helpers, types |
| [`python/src/content_engine/agents`](/Users/claw/Progetti/ai-automation/python/src/content_engine/agents) | agent implementations |
| [`python/src/content_engine/orchestrator`](/Users/claw/Progetti/ai-automation/python/src/content_engine/orchestrator) | research and generation orchestration |
| [`python/src/content_engine/services`](/Users/claw/Progetti/ai-automation/python/src/content_engine/services) | publishing, newsletter, analytics, scheduler, monitoring |
| [`python/src/content_engine/utils`](/Users/claw/Progetti/ai-automation/python/src/content_engine/utils) | infrastructure helpers |
| [`supabase/migrations`](/Users/claw/Progetti/ai-automation/supabase/migrations) | schema and policy source of truth |
