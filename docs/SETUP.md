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
| Resend | Transactional newsletter email |
| Replicate / OpenAI / OpenRouter / Anthropic | Image generation backends |
| Postiz (self-hosted or cloud) | Social publishing and scheduling |
| Firecrawl | Premium content extraction (falls back to trafilatura without it) |
| Telegram bot | Alert channel for pipeline events |
| Brevo | Email marketing: contacts, campaigns, automations |
| local-deep-research (Docker) | Multi-source async research jobs (port 5000) |
| HyperFrames | Motion graphics / video composition CLI |
| Heygen | AI talking-head video generation (API key via brand secrets) |
| OpenClaw | Alternative LLM provider for A/B traffic split |

---

## 1. Clone and install

```bash
git clone https://github.com/davidesilver/ZeroHuman-Agency.git
cd ZeroHuman-Agency

# Frontend
npm install

# Backend
cd python && uv sync && cd ..
```

---

## 2. Database setup

**Option A: Using individual migrations (recommended for production)**

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Link to your project
supabase link --project-ref YOUR_PROJECT_REF

# Apply all migrations (001-042)
supabase db push
```

**Option B: Using complete schema file (recommended for fresh setup)**

```bash
# Get your database connection string from Supabase dashboard
export DATABASE_URL="postgresql://user:password@host:port/database"

# Apply the complete schema
psql "$DATABASE_URL" -f supabase/schema_complete.sql
```

For detailed migration information, see [`docs/database/MIGRATIONS_LIST.md`](../docs/database/MIGRATIONS_LIST.md).

---

## 3. Environment variables

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

Run the consolidated schema against your Supabase project:

```bash
supabase link --project-ref YOUR_PROJECT_REF
psql "$DATABASE_URL" -f supabase/schema_complete.sql
```

The single `schema_complete.sql` file creates all tables, enums, functions, RLS policies, views, storage buckets, cron jobs, and seed data.

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

## 8. Optional: Per-brand credential vault

The credential vault lets each brand use its own API keys for research (Serper, Tavily), publishing (Postiz), and content enrichment (Firecrawl) without sharing a single global key.

Credentials are Fernet-encrypted before being stored in the database. Migration 033 creates the `brand_service_credentials` table and its RLS policies.

**1. Generate a Fernet encryption key:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add the output to `.env.local`:

```bash
BRAND_SECRETS_ENCRYPTION_KEY=<output-from-command-above>
```

**2. Ensure migration 033 is applied** (it runs automatically with `supabase db push`).

**3. Store credentials via the API:**

```bash
# Set brand-specific Serper key
curl -X PUT http://localhost:8000/api/brands/credentials/serper \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"credentials": {"api_key": "sk-serper-xxxx"}}'

# Supported services: serper · tavily · firecrawl · postiz · x_twitter · youtube · telegram
```

Vault credentials take priority over global `.env.local` values for the matching brand.

---

## 9. Optional: PrintingPress CLI binaries (token savings)

[PrintingPress](https://printingpress.dev) generates thin Go CLI wrappers around external APIs. When a CLI binary is present, the research pipeline and enrichment services use it instead of making raw API calls, reducing context-window usage by ~35× per tool call.

**Install the CLIs you need:**

```bash
# Core research tools
go install github.com/printingpress/serper@latest
go install github.com/printingpress/tavily@latest
go install github.com/printingpress/youtube@latest

# Content enrichment
go install github.com/printingpress/firecrawl@latest

# Social
go install github.com/printingpress/x-twitter@latest
```

Binaries land in `~/go/bin/`. The backend auto-detects them at startup; no configuration required. Each retriever falls back to direct HTTP if the binary is absent.

**Override the binary path per service** (useful for pinning a version):

```bash
PP_SERPER_BIN=/usr/local/bin/serper-v2
PP_TAVILY_BIN=/opt/bin/tavily
# PP_YOUTUBE_BIN, PP_FIRECRAWL_BIN, PP_X_TWITTER_BIN, PP_POSTIZ_BIN
```

---

## 10. Optional: Image generation

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

## 11. Optional: Other API integrations

All of these can be added to `.env.local` at any time. The platform degrades gracefully when they are absent.

### Research

| Key | Service | Get it at | Purpose |
|---|---|---|---|
| `SERPER_API_KEY` | [Serper](https://serper.dev) | serper.dev → API Keys | Google Search results for the research pipeline |
| `YOUTUBE_API_KEY` | [Google Cloud](https://console.cloud.google.com) | Enable YouTube Data API v3 → Credentials | YouTube trend retriever |
| `FIRECRAWL_API_KEY` | [Firecrawl](https://firecrawl.dev) | firecrawl.dev → Dashboard | Premium web scraping (falls back to `trafilatura` if absent) |
| `DEEP_RESEARCH_URL` | local-deep-research Docker | `http://localhost:5000` | Async multi-source research sidecar |

### Email marketing (Brevo)

Brevo API keys are stored **encrypted per brand** in `brand_integrations` — not as env vars. Set them via **Settings → Audience** in the dashboard. The following env var is only for the webhook secret:

| Key | Purpose |
|---|---|
| `BREVO_WEBHOOK_SECRET` | HMAC-SHA256 signature verification for Brevo webhooks |

### Email / Newsletter (Resend)

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
| `OPENCLAW_API_URL` | OpenClaw instance | `http://localhost:11434` for local; or remote endpoint |
| `OPENCLAW_DEFAULT_MODEL` | — | Default model name for OpenClaw provider |
| `OPENCLAW_TRAFFIC_SPLIT` | — | 0.0–1.0 fraction of calls routed to OpenClaw (default `0.0`) |

At least one of Anthropic or OpenRouter must be set. Fallback events are logged in `llm_fallback_log`. LLM telemetry is written to `llm_provider_metrics` regardless of which provider is used.

### Brand secrets encryption

```bash
# Generate a key (keep this secret — loss means encrypted data is unrecoverable)
BRAND_SECRETS_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

This key encrypts all per-brand API secrets (Brevo, Heygen, HyperFrames, OpenClaw) stored in `brand_integrations`. Must be the same across all backend instances.

### Video (HyperFrames + Heygen)

HyperFrames and Heygen API keys are stored per-brand in `brand_integrations` (encrypted). Set them via **Settings → Integrations** in the dashboard. The following env vars control the video pipeline globally:

| Key | Purpose | Default |
|---|---|---|
| `VIDEO_STORAGE_BUCKET` | Supabase Storage bucket for rendered videos | `videos` |
| `HYPERFRAMES_BIN` | Path to HyperFrames CLI binary | `hyperframes` (must be on PATH) |
| `HEYGEN_MONTHLY_QUOTA` | Per-brand monthly video generation cap | `10` |

### Alerts

| Key | How to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Create a bot with [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_CHAT_ID` | Send a message to your bot, then get the chat ID from [@userinfobot](https://t.me/userinfobot) |

When both are set, the backend sends alerts for pipeline errors and daily summaries.

---

## 10. Optional: local-deep-research sidecar

Run the research sidecar alongside the backend to enable async multi-source research jobs.

```bash
# Pull and start
docker pull ghcr.io/LearningCircuit/local-deep-research:latest
docker run -d -p 5000:5000 --name ldr ghcr.io/LearningCircuit/local-deep-research:latest

# Add to .env.local
DEEP_RESEARCH_URL=http://localhost:5000
```

Then enable the feature flag for each brand:

```sql
INSERT INTO feature_flags (brand_id, key, value)
VALUES ('<brand-id>', 'deep_research_enabled', true);
```

---

## 11. Optional: Agency agents

Install community agent collections from the bundled submodule:

```bash
# Install default categories (marketing, paid-media, design, sales, product)
bash scripts/install-agents.sh

# Install specific categories
bash scripts/install-agents.sh --categories marketing,sales

# Install all available categories
bash scripts/install-agents.sh --all
```

Agents are installed to `agents/`. See [`docs/AGENTS.md`](AGENTS.md) for the full catalogue and usage notes.

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
| `Feature not enabled for this brand` | Feature flag is OFF | Insert the flag via SQL or the feature-flags API endpoint |
| Deep research jobs stay `pending` | local-deep-research sidecar not running | Start the Docker container and verify `DEEP_RESEARCH_URL` |
| Brevo sync fails with `401` | Brevo API key not set or wrong | Set it via **Settings → Audience** → save API key |
| `BRAND_SECRETS_ENCRYPTION_KEY not configured` | Missing env var | Generate the key and add to `.env.local` (see section 9) |
| Video jobs stay `pending` | HyperFrames CLI not on PATH | Install HyperFrames and verify `hyperframes --version` works |
| `Scrapling not installed, using httpx fallback` | scrapling optional dep missing | `cd python && uv sync` (scrapling is in pyproject.toml) |
