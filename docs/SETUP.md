# Setup Guide

This guide gets you from zero to a running local stack. Every section is marked **required** or **optional** so you can start minimal and add capabilities as needed.

---

## Prerequisites

**Local tools**

| Tool | Version | Install |
|---|---|---|
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| Python | 3.14+ | [python.org](https://python.org) |
| uv | any | `pip install uv` or `brew install uv` |
| Supabase CLI | any | `brew install supabase/tap/supabase` |

**External services — required**

- A [Supabase](https://supabase.com) project (free tier works)
- At least one LLM provider API key (Anthropic or OpenRouter)

**External services — optional**

| Service | Purpose |
|---|---|
| Search API (e.g. Serper) | Web research retriever |
| YouTube Data API | YouTube trend retriever |
| Resend | Newsletter email delivery |
| Replicate / OpenAI / OpenRouter / Anthropic | Image generation backends |
| Postiz (self-hosted or cloud) | Social publishing and scheduling |
| Firecrawl | Premium content extraction (falls back to trafilatura without it) |
| Telegram bot | Alert channel for pipeline events |

---

## 1. Clone and install

```bash
git clone <repo-url>
cd ai-automation

# Frontend
npm install

# Backend
cd python && uv sync && cd ..
```

---

## 2. Environment variables

```bash
cp .env.example .env.local
```

Edit `.env.local`. At minimum you need these to start:

```bash
# --- Supabase (get from your project dashboard) ---
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# --- Backend location ---
PYTHON_BACKEND_URL=http://localhost:8000

# --- LLM (at least one) ---
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=

# --- Security ---
SCHEDULER_SECRET=    # generate with: openssl rand -hex 32
ALLOWED_ORIGINS=http://localhost:3000
```

Everything else is optional and can be added later. See [`.env.example`](../.env.example) for the full reference with descriptions.

---

## 3. Database

Link the Supabase CLI to your project, then push all migrations:

```bash
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

This applies all 29 migrations in [`supabase/migrations/`](../supabase/migrations/), which creates:

- Tenant tables: `brands`, `users`, `brand_members`
- Content pipeline: `research_items`, `scores`, `content_drafts`, `newsletters`
- Agent system: `agent_configs`, `agent_skills`
- Observability: `api_costs`, `pipeline_health`, `llm_fallback_log`
- Enums, SQL helper functions, RLS policies, and views

If you see an error like `relation does not exist`, make sure you are pushing from a clean database. Run `supabase migration list` to verify all migrations are applied.

---

## 4. Create your first brand

After applying migrations, create a brand (tenant) record. You can do this in the Supabase SQL editor or via the dashboard after setup.

**Option A — SQL editor:**

```sql
-- Create the brand
INSERT INTO public.brands (name, slug, topics, tone_of_voice, scoring_weights)
VALUES (
  'My Brand',
  'my-brand',
  ARRAY['topic one', 'topic two'],
  '{"style": "clear", "audience": "professionals"}'::jsonb,
  '{"applicability": 1, "credibility": 1, "alignment": 1, "trend_prediction": 1}'::jsonb
);

-- Link your auth user to the brand (replace both UUIDs)
INSERT INTO public.users (id, brand_id, email, role)
VALUES (
  '<your-supabase-auth-user-id>',
  '<brand-id-from-above>',
  'you@example.com',
  'owner'
);
```

**Option B — Dashboard UI:** Sign in first, then use **Settings → Brands → Add brand**. The function `create_brand_with_owner()` handles both inserts atomically.

---

## 5. Start the services

Open two terminals:

```bash
# Terminal 1 — Backend
cd python
uv run uvicorn src.content_engine.main:app --reload --port 8000

# Terminal 2 — Frontend
npm run dev
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Backend docs | http://localhost:8000/docs |

---

## 6. Smoke tests

```bash
# Backend liveness
curl http://localhost:8000/health

# Backend + database readiness
curl http://localhost:8000/health/db

# Frontend API (requires running Next.js)
curl http://localhost:3000/api/system/health
```

All should return `{"success": true, ...}`.

Then in the dashboard:

1. Sign in
2. Confirm the brand selector shows your brand
3. Go to **Research** and trigger a research run (or add a manual URL)

---

## 7. Optional: Social publishing (Postiz)

Skip this section if you don't need social publishing. There are two modes.

### Mode A — Self-hosted (Docker)

Run Postiz locally alongside the Content Engine. Gives you full control and no SaaS fees.

**Requirements:** Docker and Docker Compose; OAuth app credentials for each platform you want to connect.

```bash
# 1. Copy and edit the Postiz env file
cp postiz/.env.postiz.example postiz/.env.postiz
# Fill in your OAuth app credentials (LinkedIn, X/Twitter, Meta, etc.)

# 2. Start the Postiz stack
docker compose -f docker-compose.postiz.yaml up -d
```

Services started:

| Service | Port | Purpose |
|---|---|---|
| Postiz UI | 4200 | Admin interface (register, connect accounts) |
| Postiz API | 3001 | REST API used by Content Engine |
| Temporal UI | 8233 | Workflow monitoring (localhost only) |

```bash
# 3. Add to .env.local
POSTIZ_MODE=self_hosted
POSTIZ_API_URL=http://localhost:3001
POSTIZ_API_KEY=<key-from-postiz-ui>
```

Then open `http://localhost:4200`, register your admin account, go to **Settings → API** to generate an API key.

### Mode B — Cloud / Managed instance

Use the hosted [Postiz Cloud](https://postiz.com) or any managed Postiz deployment. No Docker needed.

1. Sign up at [postiz.com](https://postiz.com) (or deploy Postiz to a VPS yourself)
2. Generate an API key in **Settings → API**
3. Add to `.env.local`:

```bash
POSTIZ_MODE=cloud
POSTIZ_API_URL=https://api.postiz.com    # or your self-managed domain
POSTIZ_API_KEY=<your-api-key>
```

### Connecting social accounts (both modes)

1. Open the Postiz UI (local: `http://localhost:4200`, cloud: your domain)
2. Go to **Integrations → Add** and complete the OAuth flow for each platform
3. Copy the **Integration ID** shown in the integrations list
4. In the Content Engine dashboard, go to **Settings → Social Connections** and paste each ID

The Content Engine never stores OAuth tokens — only the opaque integration ID. Postiz owns the credentials and handles rate limiting, retries, and scheduling.

For full details see [`docs/POSTIZ_SATELLITE.md`](POSTIZ_SATELLITE.md).

---

## 8. Optional: Image generation

Set in `.env.local`:

```bash
DEFAULT_IMAGE_BACKEND=mock  # no cost, returns placeholder
# or: replicate | openai | openrouter | anthropic | pillo
DEFAULT_IMAGE_MODEL=        # backend-specific model string
```

Use `mock` during development to avoid image API costs.

**Backend-specific model strings:**

| Backend | Example model |
|---|---|
| `replicate` | `black-forest-labs/flux-schnell` |
| `openai` | `dall-e-3` |
| `openrouter` | `openai/dall-e-3` |
| `anthropic` | *(not currently supported for images)* |
| `pillo` | `carousel-v1` |

Per-brand overrides are set in **Settings → Brand Context → Image Generation**.

---

## 9. Optional: Other API integrations

All of these can be added to `.env.local` at any time. The platform degrades gracefully when they are absent.

### Research

| Key | Service | Get it at | Purpose |
|---|---|---|---|
| `SERPER_API_KEY` | [Serper](https://serper.dev) | serper.dev → API Keys | Google Search results for the research pipeline |
| `YOUTUBE_API_KEY` | [Google Cloud](https://console.cloud.google.com) | Enable YouTube Data API v3 → Credentials | YouTube trend retriever |
| `FIRECRAWL_API_KEY` | [Firecrawl](https://firecrawl.dev) | firecrawl.dev → Dashboard | Premium web scraping (falls back to `trafilatura` if absent) |

### Email / Newsletter

| Key | Service | Get it at | Purpose |
|---|---|---|---|
| `RESEND_API_KEY` | [Resend](https://resend.com) | resend.com → API Keys | Transactional email for newsletter sends |
| `NEWSLETTER_FROM_EMAIL` | — | Your verified sending domain | `From:` address on outbound newsletters |
| `NEWSLETTER_FROM_NAME` | — | Freeform string | Display name on outbound newsletters |

> Resend requires a verified sending domain. Follow [their domain setup guide](https://resend.com/docs/dashboard/domains/introduction) before sending.

### LLM providers

| Key | Service | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | [Anthropic](https://console.anthropic.com) | Preferred — used for Claude models |
| `OPENROUTER_API_KEY` | [OpenRouter](https://openrouter.ai) | Fallback; also enables 100+ third-party models |

At least one must be set. If both are set, Anthropic is tried first and OpenRouter is the automatic fallback. Fallback events are logged in `llm_fallback_log`.

### Alerts

| Key | How to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Create a bot with [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_CHAT_ID` | Send a message to your bot, then get the chat ID from [@userinfobot](https://t.me/userinfobot) |

When both are set, the backend sends alerts for pipeline errors and daily summaries.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 Unauthorized` from backend | Missing or expired session token | Sign out and sign back in; verify `NEXT_PUBLIC_SUPABASE_*` values |
| `403 User has no associated brand` | Missing row in `public.users` | Insert the user-to-brand mapping (see step 4) |
| `Could not find function ... in schema cache` | Migrations not applied | Run `supabase db push` and hard-reload the dashboard |
| Scheduler endpoints return `503` | `PYTHON_BACKEND_URL` wrong or backend not running | Check both services are running |
| CORS errors in browser | `ALLOWED_ORIGINS` missing the frontend URL | Add `http://localhost:3000` to `ALLOWED_ORIGINS` |
| `type "vector" does not exist` | pgvector not in search_path | This is fixed in migration 001; ensure you are on the latest code before pushing |
| Backend cannot connect to Supabase | Missing URL or keys in Python env | The Python backend reads from `../.env.local` relative to `python/`; verify the path |
