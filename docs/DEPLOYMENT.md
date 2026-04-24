# Deployment

## Production topology

Three components to deploy:

```
┌──────────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│   Next.js Frontend   │    │   FastAPI Backend     │    │    Supabase     │
│   (Node.js host)     │───▶│   (container host)    │───▶│  (managed PG)   │
│   Port 3000/443      │    │   Port 8000           │    │  + Storage      │
└──────────────────────┘    └──────────────────────┘    └─────────────────┘
                                      │
                             Optional │
                      ┌───────────────▼────────────┐
                      │   Postiz Satellite          │
                      │   (Docker, same host or VPS)│
                      │   Port 3001 (API)           │
                      └────────────────────────────┘
```

The backend must **not** be publicly exposed — only the frontend should be able to reach it. Configure your network so port 8000 is private.

---

## Environment variables

### Frontend host

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
PYTHON_BACKEND_URL=https://your-backend-internal-url:8000
NEXT_PUBLIC_APP_URL=https://your-frontend-domain.com
```

### Backend host

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Security
ALLOWED_ORIGINS=https://your-frontend-domain.com
SCHEDULER_SECRET=<openssl rand -hex 32>
SCHEDULER_BRAND_ID=            # UUID of the brand to run scheduled jobs for
                               # leave empty to fan out to all active brands

# LLM providers (at least one)
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=

# Research
SERPER_API_KEY=
YOUTUBE_API_KEY=
FIRECRAWL_API_KEY=             # optional

# Newsletter
RESEND_API_KEY=
NEWSLETTER_FROM_EMAIL=
NEWSLETTER_FROM_NAME=

# Image generation
DEFAULT_IMAGE_BACKEND=mock     # change to replicate / openai / etc.
DEFAULT_IMAGE_MODEL=
REPLICATE_API_TOKEN=

# Social publishing
POSTIZ_MODE=disabled           # self_hosted | cloud | disabled
POSTIZ_API_URL=
POSTIZ_API_KEY=

# Alerting (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## Start commands

### Backend

```bash
cd python
uv sync --frozen
uv run uvicorn src.content_engine.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2
```

For production, run behind a process manager (systemd, supervisord, or a container runtime). The app is stateless between requests except for in-memory caches (JWT cache, agent loader TTL cache) — these are per-process and reset on restart.

### Frontend

```bash
npm ci
npm run build
npm run start
```

Or deploy to a Node.js-compatible platform (Vercel, Fly.io, Railway, etc.) with the environment variables set.

---

## Database migrations

On every deployment, before starting the application:

```bash
supabase link --project-ref <project-ref>
supabase db push
```

The migration set is the release artifact. Never modify production schema manually.

To verify applied migrations:

```sql
SELECT version FROM supabase_migrations.schema_migrations ORDER BY version;
```

---

## Scheduler setup

The platform needs three periodic jobs:

| Job | Endpoint | Suggested frequency |
|---|---|---|
| Daily research pipeline | `POST /api/scheduler/daily-pipeline` | Once per day |
| Publish scheduled posts | `POST /api/scheduler/publish-scheduled` | Every 15–30 min |
| Pull social metrics | `POST /api/analytics/pull-metrics` | Once per day |

Every call must include:

```http
X-Scheduler-Secret: <your-scheduler-secret>
```

**GitHub Actions example:**

```yaml
# .github/workflows/daily-pipeline.yml
name: Daily pipeline
on:
  schedule:
    - cron: '0 6 * * *'   # 06:00 UTC daily
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger research
        run: |
          curl -X POST ${{ secrets.BACKEND_URL }}/api/scheduler/daily-pipeline \
            -H "X-Scheduler-Secret: ${{ secrets.SCHEDULER_SECRET }}"
```

**Cron (server-side):**

```bash
# Publish scheduled posts every 15 minutes
*/15 * * * * curl -s -X POST https://your-backend/api/scheduler/publish-scheduled \
  -H "X-Scheduler-Secret: YOUR_SECRET"
```

---

## Health checks

Configure your load balancer or uptime monitor to hit:

```
GET /health        → {"status": "ok"}                 (liveness)
GET /health/db     → {"status": "ok", "latency_ms": N} (readiness)
```

---

## Deployment checklist

- [ ] Database migrations applied (`supabase db push`)
- [ ] All required environment variables set on both frontend and backend
- [ ] Backend not publicly exposed (only frontend can reach it)
- [ ] `ALLOWED_ORIGINS` set to exact frontend domain (no trailing slash, no wildcards)
- [ ] `SCHEDULER_SECRET` is a strong random value (32+ hex chars)
- [ ] `SUPABASE_SERVICE_ROLE_KEY` only on backend, never in frontend env
- [ ] Scheduler jobs configured and tested
- [ ] `/health` and `/health/db` return 200
- [ ] At least one brand and one user created
- [ ] End-to-end smoke: sign in → research → draft → (optionally) publish
- [ ] Postiz satellite running and connected (if social publishing needed)

---

## Rotating secrets

**Supabase keys:** After rotating in the Supabase dashboard, update env on both hosts and invalidate the backend JWT cache:

```bash
curl -X POST https://your-backend/api/auth/cache-invalidate \
  -H "X-Scheduler-Secret: <scheduler-secret>"
```

**Scheduler secret:** Update `SCHEDULER_SECRET` on the backend and in every cron/CI caller simultaneously. There is no grace period — old secrets are rejected immediately.
