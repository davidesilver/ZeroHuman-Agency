# Autonomous Content Operations Platform

This repository contains a multi-tenant content operations platform with:

- a `Next.js 16` application for authentication, dashboard pages, and first-party API routes
- a `FastAPI` backend for research, scoring, content generation, review, scheduling, and agent orchestration
- a `Supabase` database used for auth, storage, Row Level Security, and operational data

The codebase already supports research ingestion, scoring, draft generation, multi-agent review, humanization, writing-lab experiments, newsletter delivery, social scheduling, feedback collection, and health/cost monitoring. The documentation in this repository is now organized around what is actually implemented, not around aspirational architecture.

## Scope

Use this project if you need a white-label content workflow where each tenant has:

- isolated data scoped by `brand_id`
- configurable sources, tone, scoring weights, and social accounts
- authenticated dashboard access
- a research-to-draft pipeline
- optional review layers such as GOD mode and humanizer
- scheduling, analytics, and operational visibility

## Stack

| Layer | Technology | Notes |
| --- | --- | --- |
| Frontend | `Next.js 16`, `React 19`, `TypeScript`, `Tailwind CSS 4` | App Router app in [`src`](/Users/claw/Progetti/ai-automation/src) |
| Backend | `FastAPI`, `Python`, `uvicorn` | Service code in [`python/src/content_engine`](/Users/claw/Progetti/ai-automation/python/src/content_engine) |
| Database/Auth | `Supabase` / PostgreSQL | Schema, RLS, views, and functions in [`supabase/migrations`](/Users/claw/Progetti/ai-automation/supabase/migrations) |
| Scheduling | CI/cron caller + protected backend endpoints | See [`docs/DEPLOYMENT.md`](/Users/claw/Progetti/ai-automation/docs/DEPLOYMENT.md) |

## What Is Implemented

- Tenant-aware auth via Supabase session + backend JWT validation
- Research runs and research items
- Manual URL ingestion into the research pipeline
- Score computation and approval/rejection workflow
- Draft generation, adaptation, GOD mode review, and humanization
- Writing-lab sessions with round voting
- Newsletter preview and send
- Social publish and social schedule endpoints
- Feedback loop, metrics ingestion, fallback monitoring, and agent health dashboards
- Agent configuration and agent skills CRUD

## Documentation Map

- [Setup Guide](/Users/claw/Progetti/ai-automation/docs/SETUP.md): local setup, environment variables, database bootstrap, smoke tests
- [Architecture](/Users/claw/Progetti/ai-automation/docs/ARCHITECTURE.md): service boundaries, request flow, auth, scheduling, and directory map
- [API Guide](/Users/claw/Progetti/ai-automation/docs/API.md): route inventory, auth model, request examples, known gaps
- [Tenant Onboarding](/Users/claw/Progetti/ai-automation/docs/ONBOARDING.md): how to create a new tenant safely
- [Database Schema](/Users/claw/Progetti/ai-automation/docs/database/SCHEMA.md): tables, enums, views, and migration strategy
- [Deployment](/Users/claw/Progetti/ai-automation/docs/DEPLOYMENT.md): production topology and required environment variables
- [Agents](/Users/claw/Progetti/ai-automation/docs/AGENTS.md): dynamic agent configuration model

## Quick Start

1. Create a Supabase project and apply the migrations in [`supabase/migrations`](/Users/claw/Progetti/ai-automation/supabase/migrations).
2. Copy [`.env.example`](/Users/claw/Progetti/ai-automation/.env.example) to `.env.local` and fill every required value.
3. Install frontend dependencies and start the Next.js app:

```bash
npm install
npm run dev
```

4. Install backend dependencies from [`python/pyproject.toml`](/Users/claw/Progetti/ai-automation/python/pyproject.toml) and start FastAPI:

```bash
cd python
uv sync
uv run uvicorn src.content_engine.main:app --reload --port 8000
```

5. Follow the tenant bootstrap steps in [`docs/ONBOARDING.md`](/Users/claw/Progetti/ai-automation/docs/ONBOARDING.md).

## Repository Notes

- The public documentation intentionally ignores repository areas that are only useful for local tooling or meta-development.
- The authoritative contract for data is the migration set plus [`src/lib/types/database.types.ts`](/Users/claw/Progetti/ai-automation/src/lib/types/database.types.ts).
- The authoritative contract for backend behavior is [`python/src/content_engine/api/routes.py`](/Users/claw/Progetti/ai-automation/python/src/content_engine/api/routes.py) and [`python/src/content_engine/api/routes_agents.py`](/Users/claw/Progetti/ai-automation/python/src/content_engine/api/routes_agents.py).
