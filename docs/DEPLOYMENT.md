# Deployment

## Production Topology

The project is designed for a split deployment:

- one Node-compatible host for the Next.js application
- one long-running Python host for the FastAPI backend
- one managed PostgreSQL/Supabase environment

This matches the codebase more accurately than a single all-in-one deployment.

## Required Environment Variables

### Frontend Host

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `PYTHON_BACKEND_URL`
- any other variables read by Next.js route handlers

### Backend Host

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ALLOWED_ORIGINS`
- `SCHEDULER_SECRET`
- `SCHEDULER_BRAND_ID` if scheduled jobs are enabled
- provider keys required by the features you plan to use

## Database Release Process

For every environment:

```bash
supabase link --project-ref <project-ref>
supabase db push
```

Do not document or maintain schema manually in production. The migration folder is the release artifact.

## Backend Start Command

Example:

```bash
cd python
uv sync
uv run uvicorn src.content_engine.main:app --host 0.0.0.0 --port 8000
```

## Frontend Start Command

Example:

```bash
npm install
npm run build
npm run start
```

## Scheduler

The repository already includes a CI-style scheduler example in [`.github/workflows/daily-pipeline.yml`](/Users/claw/Progetti/ai-automation/.github/workflows/daily-pipeline.yml).

Required protected endpoints:

- `POST /api/scheduler/daily-pipeline`
- `POST /api/scheduler/publish-scheduled`
- `POST /api/analytics/pull-metrics`
- `POST /api/auth/cache-invalidate`

Every scheduler caller must send:

- `X-Scheduler-Secret: <secret>`

## Deployment Checklist

1. apply database migrations
2. set all environment variables
3. deploy backend
4. deploy frontend with the backend URL
5. create at least one tenant and one mapped user
6. verify `/health` and `/health/db`
7. verify authenticated dashboard access
8. test one end-to-end content cycle

## Production Notes

- Keep `ALLOWED_ORIGINS` restrictive.
- Do not expose `SUPABASE_SERVICE_ROLE_KEY` to the frontend.
- If you rotate Supabase keys, invalidate the backend auth cache using the dedicated protected endpoint.
- Scheduler jobs depend on `SCHEDULER_BRAND_ID`; they are not multi-tenant fan-out jobs by default.
