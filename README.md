# Content Engine

**An autonomous, multi-tenant AI content operations platform that transforms how teams create, manage, and publish content across multiple channels.**

Content Engine combines intelligent web research, AI-powered content generation, multi-agent review systems, and automated publishing into a unified platform. Perfect for content teams, marketing agencies, and businesses that need to scale their content production while maintaining quality and brand consistency.

```
Topics + Sources → Research → Scoring → Draft → Review → Publish
                                                 ↑
                                       Metrics feedback loop
```

**Perfect for:**
- Marketing teams managing multiple brands
- Content agencies scaling client deliverables  
- Businesses automating their content marketing
- Creators maintaining consistency across platforms
- Teams needing AI-powered content research and generation

---

## What it does

| Capability | Description |
|---|---|
| **Research** | Pulls from RSS feeds, search APIs, and video platforms in parallel; deduplicates by URL and semantic similarity |
| **Scoring** | Rates each item across configurable dimensions (relevance, credibility, trend signal, alignment with your voice) |
| **Content generation** | Produces platform-native drafts (LinkedIn, X, Instagram, newsletter, blog) with a Writer → Editor pipeline |
| **Multi-agent review** | Optional four-agent GOD mode: critic, fact-checker, creative enhancer, synthesis verdict |
| **Humanizer** | Strips AI-isms and re-applies your brand voice using your own gold examples and top performers |
| **Writing Lab** | Challenger/champion rounds for experimental content iteration |
| **Newsletter** | Compose from approved drafts, preview, and send via transactional email |
| **Social publishing** | Publish now or schedule via a self-hosted or cloud social publishing satellite |
| **Image generation** | Generate images per draft using any compatible image backend |
| **Feedback loop** | Social metrics flow back into scoring weights — high-performing content influences future research |
| **Observability** | Cost tracking, agent heartbeats, LLM fallback logs, pipeline health dashboard |

Everything is **multi-tenant**: each brand has isolated data, its own sources, tone of voice, scoring weights, and agent configuration.

---

## How it works

```
┌─────────────────────────────────────────────────────────┐
│                     Browser / API Client                │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼────────────────────────────────┐
│                    Next.js Frontend                     │
│   Dashboard · Auth · Direct DB reads · Proxy to API     │
└──────────┬────────────────────────────────┬─────────────┘
           │ Supabase SDK                   │ HTTP proxy
┌──────────▼───────────┐     ┌─────────────▼─────────────┐
│   Supabase / Postgres │     │    FastAPI Backend         │
│   Auth · RLS · Storage│     │  Research · Scoring       │
│   Migrations 001-029  │     │  Generation · Agents      │
│   pgvector · pg_cron  │     │  Scheduler · Analytics    │
└──────────────────────┘     └─────────────┬─────────────┘
                                            │ HTTP (optional)
                              ┌─────────────▼─────────────┐
                              │   Postiz Satellite         │
                              │  Social publishing & OAuth │
                              │  (self-hosted via Docker)  │
                              └───────────────────────────┘
```

The frontend handles authentication, the dashboard UI, and direct database reads. Heavy orchestration (research, scoring, generation, scheduling) runs in the FastAPI backend. The database enforces tenant isolation at the row level — no tenant can read another tenant's data even if the application layer has a bug.

---

## Usage modes

### Minimal — content drafting only
You can run the platform without any social publishing or image generation. Connect one LLM provider, set up Supabase, and use it purely as a research-to-draft pipeline. The social and image sections of the dashboard will be inactive.

### Standard — full content pipeline
Add a search API key for web research, configure sources per brand, enable the feedback loop. Drafts flow through Writer → Editor → GOD mode → Humanizer → approval.

### Full — publish and schedule
Connect a social publishing satellite (self-hosted Docker or cloud). The platform handles OAuth delegation and scheduling. Metrics flow back to influence scoring.

### Multi-tenant / agency
Create multiple brands, each with its own sources, tone, agents, scoring weights, and social accounts. A single deployment serves all tenants with strict data isolation.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4 |
| Backend | Python, FastAPI, uvicorn |
| Database | PostgreSQL via Supabase (auth, RLS, storage, vector search) |
| Social publishing | Postiz (self-hosted Docker or cloud — optional) |
| Package management | npm (frontend), uv (Python backend) |

---

## Quick start

### Prerequisites

- Node.js 20+
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`pip install uv` or `brew install uv`)
- A Supabase project (free tier works)
- At least one LLM provider API key

### 1 — Database

Create a Supabase project, then apply the migrations:

```bash
# Install Supabase CLI if you don't have it
brew install supabase/tap/supabase   # or: npm i -g supabase

# Link to your project (get the ref from your Supabase dashboard)
supabase link --project-ref YOUR_PROJECT_REF

# Apply all migrations (001-030)
supabase db push

# Or use the complete schema file for fresh setup
psql "$DATABASE_URL" -f supabase/schema_complete.sql
```

### 2 — Environment

```bash
cp .env.example .env.local
```

Open `.env.local` and fill in the required values (marked `# required`). See the [full variable reference](#environment-variables) below.

### 3 — Frontend

```bash
npm install
npm run dev
# → http://localhost:3000
```

### 4 — Backend

```bash
cd python
uv sync
uv run uvicorn src.content_engine.main:app --reload --port 8000
# → http://localhost:8000
```

### 5 — First brand

1. Open [http://localhost:3000](http://localhost:3000) and sign up with your email.
2. Go to **Settings → Brands → Add brand** and fill in your name, topics, and RSS sources.
3. Go to **Research** and click **Run research** to pull your first batch of items.
4. Score items, approve the ones you like, then generate your first draft.

That's it. You're in the pipeline.

---

## Environment variables

### Required

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Backend location (frontend proxies heavy ops here)
PYTHON_BACKEND_URL=http://localhost:8000

# At least one LLM provider
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=          # used as fallback or primary (many free models available)

# Scheduler security (generate with: openssl rand -hex 32)
SCHEDULER_SECRET=
```

### Research (add what you need)

```bash
SERPER_API_KEY=              # web search
YOUTUBE_API_KEY=             # YouTube trends
FIRECRAWL_API_KEY=           # premium content extraction (optional; falls back to trafilatura)
```

### Publishing and delivery

```bash
RESEND_API_KEY=              # newsletter send
POSTIZ_MODE=disabled         # disabled | self_hosted | cloud
POSTIZ_API_URL=              # required if POSTIZ_MODE != disabled
POSTIZ_API_KEY=              # required if POSTIZ_MODE != disabled
```

### Image generation (pick one or leave as mock)

```bash
DEFAULT_IMAGE_BACKEND=mock   # mock | replicate | openai | openrouter | anthropic | pillo
DEFAULT_IMAGE_MODEL=         # backend-specific model identifier
REPLICATE_API_TOKEN=
```

### Operations

```bash
ALLOWED_ORIGINS=http://localhost:3000   # comma-separated, no trailing slash
NEWSLETTER_FROM_EMAIL=hello@yourdomain.com
NEWSLETTER_FROM_NAME=Your Newsletter
TELEGRAM_BOT_TOKEN=          # optional: alert channel
TELEGRAM_CHAT_ID=
```

Full reference with descriptions: [`.env.example`](.env.example)

---

## Architecture overview

### Research pipeline

Each research run fans out across all configured retrievers in parallel. Items are deduplicated first by normalized URL, then by semantic similarity using vector embeddings. Only novel items reach the scoring phase.

```
Brand config (topics, sources)
        ↓
┌───────────────────────────┐
│  Retrievers (parallel)    │
│  RSS · Search · YouTube   │
│  Manual URL ingestion     │
└───────────────────────────┘
        ↓ deduplicate (URL + vectors)
research_items (status: new)
        ↓
Scoring agent → scores table
        ↓
content_drafts (status: draft)
```

### Content generation

The Writer agent produces an initial draft using brand tone, principles, and gold examples. The Editor agent refines it. Each step reads agent identity and skills from the database — you can customize prompts per brand without touching code.

```
research_item → Writer → Editor → draft
                                    ↓
                     ┌──────────────┴──────────────┐
                     │        (optional)            │
                  GOD mode                     Humanizer
                  4-agent review               voice calibration
                  critic · factcheck           remove AI patterns
                  creative · synthesis         double-pass refinement
                     └──────────────┬──────────────┘
                                    ↓
                              approved draft
                                    ↓
                    Publish now · Schedule · Newsletter
```

### Agent configuration

Every agent in the system (writer, editor, GOD mode advocates, humanizer) loads its identity and skills from the database at runtime. This means you can:

- Give each brand a different writer persona
- Attach specialized skills (e.g., "always end with a question", "use data-driven openings")
- Update behavior without redeploys

The system falls back to hardcoded defaults if no database configuration exists, so it works out of the box.

### Multi-tenancy

Every table that holds operational data has a `brand_id` foreign key. Row Level Security policies are enforced at the database layer — the application cannot accidentally serve one tenant's data to another. The backend JWT middleware extracts `brand_id` from the session token and attaches it to every request.

---

## Project structure

```
/
├── src/                          # Next.js frontend (App Router)
│   ├── app/
│   │   ├── (auth)/               # Login page
│   │   ├── (dashboard)/          # All dashboard pages
│   │   │   ├── page.tsx          # Home / overview
│   │   │   ├── content-hub/      # Draft listing and editor
│   │   │   ├── ricerca/          # Research runs and item management
│   │   │   ├── newsletter/       # Newsletter composition
│   │   │   ├── social/           # Social publishing
│   │   │   ├── writing-lab/      # Experimental writing sessions
│   │   │   ├── metriche/         # Analytics
│   │   │   ├── settings/         # Brand settings, agents, social connections
│   │   │   └── ...
│   │   └── api/                  # Next.js route handlers
│   │       ├── brands/           # Brand CRUD + assets
│   │       ├── content/          # Drafts, generation (proxy)
│   │       ├── research/         # Research trigger + items
│   │       ├── social/           # Publish + schedule (proxy)
│   │       ├── images/           # Image generation (proxy)
│   │       ├── newsletter/       # Send + preview (proxy)
│   │       └── system/           # Health, costs, config
│   ├── components/               # Shared UI components
│   └── lib/                      # Supabase clients, types, helpers
│
├── python/src/content_engine/    # FastAPI backend
│   ├── api/
│   │   ├── routes.py             # Core routes (research, scoring, generation)
│   │   ├── routes_agents.py      # Agent config/skills CRUD
│   │   ├── routes_images.py      # Image generation
│   │   └── routes_postiz.py      # Social publishing bridge
│   ├── agents/                   # Writer, Editor, GOD mode, Humanizer, Adapter
│   ├── orchestrator/             # Research and content pipeline orchestration
│   ├── retrievers/               # RSS, Search, YouTube retrievers
│   ├── scoring/                  # Scoring engine
│   ├── services/                 # Newsletter, Postiz, image backends, scheduler
│   ├── monitoring/               # Pipeline health and fallback monitoring
│   ├── utils/                    # LLM client, cost tracker, rate limiter, SSRF guard
│   └── config/settings.py        # Pydantic settings (all from env)
│
├── supabase/
│   ├── migrations/               # 001–029: canonical schema source of truth
│   └── functions/                # Edge functions (analytics sync)
│
├── docker-compose.postiz.yaml    # Optional social publishing satellite
└── docs/                         # Extended documentation
```

---

## Social publishing (Postiz satellite)

By default `POSTIZ_MODE=disabled` and social features are hidden. To enable:

**Self-hosted (recommended for full control)**

```bash
# Start the Postiz stack
docker compose -f docker-compose.postiz.yaml up -d

# Set in .env.local
POSTIZ_MODE=self_hosted
POSTIZ_API_URL=http://localhost:3001
POSTIZ_API_KEY=your-postiz-api-key
```

Connect your social accounts in the Postiz UI at `http://localhost:4200`, then paste the integration IDs into **Settings → Social Connections** in the Content Engine dashboard.

**Cloud — Postiz.com managed service**

1. Sign up at [postiz.com](https://postiz.com) (free tier supports 3 channels)
2. Go to **Settings → API** → generate an API key
3. Set in `.env.local`:

```bash
POSTIZ_MODE=cloud
POSTIZ_API_URL=https://api.postiz.com
POSTIZ_API_KEY=<your-postiz-api-key>
```

**Cloud — self-managed Postiz on a VPS**

Deploy Postiz via its own Docker Compose on any VPS (Hetzner, DigitalOcean, fly.io…), then:

```bash
POSTIZ_MODE=cloud
POSTIZ_API_URL=https://postiz.yourdomain.com
POSTIZ_API_KEY=<your-postiz-api-key>
```

Postiz handles all platform OAuth, rate limiting, and post retry logic. Content Engine stores only opaque integration IDs — no social platform tokens are held in the Content Engine database.

---

## Image generation

Configure per brand in **Settings → Image Generation**. Available backends:

| Backend | Key needed | Example model |
|---|---|---|
| `mock` | — | `mock-v1` — free placeholder, good for development |
| `replicate` | `REPLICATE_API_TOKEN` | `black-forest-labs/flux-schnell` |
| `openai` | `OPENAI_API_KEY` | `dall-e-3` |
| `openrouter` | `OPENROUTER_API_KEY` | `openai/dall-e-3` |
| `anthropic` | `ANTHROPIC_API_KEY` | model string from Anthropic docs |
| `pillo` | `PILLO_API_KEY` | `carousel-v1` — carousel specialist |

Set `DEFAULT_IMAGE_BACKEND=mock` to disable image costs during development. Each brand can override the default in **Settings → Image Generation**.

---

## Deployment

The platform runs as three services: the Next.js frontend, the FastAPI backend, and Supabase (managed). In production:

- Deploy the frontend to any Node.js host (Vercel, Fly.io, Railway, etc.)
- Deploy the backend to any container host; expose port 8000 only to the frontend's network
- Set `SCHEDULER_SECRET` and configure your cron system to call `/api/scheduler/daily-research` and `/api/scheduler/publish-scheduled` on a schedule

Detailed production checklist: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

---

## Extending the system

### Add a retriever

Create a class in `python/src/content_engine/retrievers/` that implements the `BaseRetriever` interface, then register it in the orchestrator. The base class handles deduplication and DB insertion.

### Add an agent

Add an entry to `agent_configs` in the database with a new `agent_key`. The agent loader will pick it up. Attach skills via `agent_skills` without touching code.

### Add an image backend

Implement the backend class in `python/src/content_engine/services/image_backends/` following the existing pattern, then register it in the image generator's backend registry.

### Add a platform

Add the platform to the `platform` enum in a new migration, add platform-specific formatting rules to the adapter agent, and add the platform's UI entry in the social settings page.

---

## Documentation

| Document | What's inside |
|---|---|
| [`docs/SETUP.md`](docs/SETUP.md) | Prerequisites, local setup, environment variables, smoke tests |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Service boundaries, request flow, auth, security controls |
| [`docs/AGENTS.md`](docs/AGENTS.md) | Agent configuration model, skills system, resolution logic |
| [`docs/API.md`](docs/API.md) | Route inventory, auth model, request/response shapes |
| [`docs/ONBOARDING.md`](docs/ONBOARDING.md) | How to create and configure a new tenant |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Production topology, environment variables, scheduling |
| [`docs/POSTIZ_SATELLITE.md`](docs/POSTIZ_SATELLITE.md) | Social publishing setup, self-hosted vs cloud |
| [`docs/database/SCHEMA.md`](docs/database/SCHEMA.md) | Full schema reference, migrations, RLS policies |

---

## Security notes

- All backend routes require a valid JWT from the Supabase session (except public health probes)
- Scheduler endpoints are protected by a separate secret (`SCHEDULER_SECRET`)
- Row Level Security is enabled on every tenant-scoped table — isolation is enforced at the database layer
- Media URLs passed to external services are validated against an SSRF blocklist (no private IPs, no non-HTTPS schemes)
- CORS is configured with an explicit allowlist (`ALLOWED_ORIGINS`) — no wildcards
- API keys and secrets are masked in all log output

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Apply migrations locally: `supabase db push`
4. Make your changes, add tests where applicable
5. Ensure the build passes: `npm run lint && npm run build`
6. Ensure backend tests pass: `cd python && uv run pytest`
7. Open a pull request with a clear description of what changed and why

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**What this means for you:**
- ✅ **Commercial Use**: You can use this code to build products, services, or businesses
- ✅ **Modification**: You can modify the code to fit your needs
- ✅ **Distribution**: You can distribute your modified versions
- ✅ **Private Use**: You can use it privately without sharing your changes
- ✅ **Sublicensing**: You can incorporate it into larger projects with different licenses

**Only requirement**: Keep the license and copyright notice in any distributed copies.

This license is ideal for:
- Building commercial SaaS products
- Creating agency solutions for clients
- Developing internal tools for your company
- Starting a content automation business
