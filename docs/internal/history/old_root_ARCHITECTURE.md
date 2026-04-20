# Content Engine — Architecture Document

> End-to-end architecture map requested in Perplexity analysis.
> Last updated: 2026-04-15

---

## System Overview

The Content Engine is a **multi-brand AI content pipeline** that automates research, scoring, writing, review, and publishing of content across platforms.

```text
┌──────────────────────── Frontend (Next.js) ─────────────────────────┐
│  src/app/(dashboard)/                                                │
│  ├── page.tsx          — KPIs, pipeline status, agent health         │
│  ├── ricerca/          — Research runs viewer                        │
│  ├── content-hub/      — Draft management                           │
│  ├── writing-lab/      — Champion/challenger writing sessions        │
│  ├── newsletter/       — Newsletter composer + preview               │
│  ├── calendario/       — Content calendar                            │
│  ├── metriche/         — Analytics metrics                           │
│  ├── costi-api/        — API cost tracking                           │
│  ├── revenue/          — Revenue tracking                            │
│  └── blog/             — Blog management                             │
│                                                                      │
│  src/app/api/          — Next.js API routes (proxy to Python)        │
└─────────────────────────────┬────────────────────────────────────────┘
                              │ HTTP (localhost:3000 → localhost:8000)
┌─────────────────────────────▼────────────────────────────────────────┐
│  Backend (Python FastAPI)   python/src/content_engine/               │
│  ├── main.py           — App entry, CORS, rate limiting              │
│  ├── config.py         — Settings from .env.local                    │
│  ├── api/routes.py     — All REST endpoints                          │
│  ├── orchestrator/     — Research + content orchestration             │
│  ├── retrievers/       — RSS, Serper, YouTube data sources            │
│  ├── scoring/          — 6-parameter LLM scoring engine               │
│  ├── agents/           — Writer, Editor, Adapter, GOD System          │
│  ├── services/         — Scheduler, feedback loop, newsletter, social │
│  └── utils/            — Cost tracker, rate limiter                    │
└─────────────────────────────┬────────────────────────────────────────┘
                              │ Supabase SDK (REST + Realtime)
┌─────────────────────────────▼────────────────────────────────────────┐
│  Database (Supabase/PostgreSQL)                                       │
│  Tables: brands, research_runs, research_items, scores,               │
│          content_drafts, god_mode_reviews, newsletters,                │
│          calendar_events, social_metrics, feedback, api_costs,         │
│          writing_lab_sessions, writing_lab_rounds, audit_trail,        │
│          agent_configs, agent_skills, feedback_loop_audit              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Flow (End-to-End)

```text
1. RESEARCH          2. SCORING           3. WRITING           4. REVIEW
╔═══════════════╗   ╔═══════════════╗   ╔═══════════════╗   ╔═══════════════╗
║ 5 Retrievers  ║──▶║ 6-param LLM   ║──▶║ Writer Agent  ║──▶║ GOD System    ║
║ (parallel)    ║   ║ scoring       ║   ║ + Editor      ║   ║ (4 agents)    ║
║               ║   ║               ║   ║ + Adapter     ║   ║               ║
╚═══════════════╝   ╚═══════════════╝   ╚═══════════════╝   ╚═══════════════╝
       │                   │                   │                   │
   Dedup URL          Auto-approve         Brand voice         Advocate
   Save to DB         Auto-reject          Tone rules          FactCheck
                      feedback_bonus       Platform rules      Creative
                                                               Synthesis
                                                                   │
                                                                   ▼
                    5. PUBLISH               6. FEEDBACK
                 ╔═══════════════╗       ╔═══════════════╗
                 ║ Social Post   ║──────▶║ Engagement    ║
                 ║ Newsletter    ║       ║ feedback_bonus║
                 ║ Schedule      ║       ║ update        ║
                 ╚═══════════════╝       ╚═══════════════╝
```

---

## Component Details

### Retrievers (`orchestrator/research.py` + `retrievers/`)

| Retriever | Source | Module |
| :--- | :--- | :--- |
| `TRUSTED_SOURCE` | RSS feeds | `retrievers/rss.py` |
| `SEMANTIC` | Serper semantic search | `retrievers/serper.py` |
| `KEYWORD` | Serper keyword search | `retrievers/serper.py` |
| `PRACTITIONER` | Serper practitioner search | `retrievers/serper.py` |
| `TREND` | YouTube trending | `retrievers/youtube.py` |

**Execution**: All run in parallel via `asyncio.gather()` with `return_exceptions=True`.
**Dedup**: URL-based normalization (strips UTM params, www prefix, trailing slashes).
**Semantic Dedup**: Implemented via pgvector and `find_semantic_duplicates` SQL function (Migration 002).

### Scoring Engine (`scoring/engine.py`)

**6 parameters with weights:**

| Parameter | Weight | Purpose |
| :--- | :--- | :--- |
| `applicability` | 25% | Actionability — can reader apply Monday? |
| `credibility` | 20% | Source/author reliability, citations |
| `alignment` | 25% | Brand topics + founder principles |
| `trend_prediction` | 15% | Emerging trend relevance at 6 months |
| `italy_relevance` | 10% | Italian market applicability |
| `feedback_bonus` | 5% | Historical engagement performance |

**Auto-decisioning**: Score ≥ 8.0 → `approved`, Score ≤ 3.0 → `rejected`.

### Content Agents (`agents/`)

| Agent | File | Purpose | LLM |
| :--- | :--- | :--- | :--- |
| Writer | `writer.py` | Generates content from research items | Sonnet |
| Editor | `editor.py` | Refines writer output | Sonnet |
| Adapter | `adapter.py` | Platform-specific formatting (LinkedIn, TikTok, etc.) | Sonnet |
| GOD System | `god_system.py` | 4-agent review pipeline | Sonnet + Opus |
| Writing Lab | `writing_lab.py` | Champion/challenger A/B writing | Sonnet |

### GOD System Pipeline (`agents/god_system.py`)

```text
Draft → [Advocate] → [FactCheck] → [Creative] → [Synthesis] → Updated Draft
           │              │              │              │
           │         uses advocate   uses advocate   uses all
           │         feedback        + factcheck     feedback
           │                         feedback
           ▼              ▼              ▼              ▼
       Weaknesses     Claim status   Hook ideas     Final version
       Strengths      Reliability    Engagement     Pass/Revise/Reject
```

**Error handling**: Each step has try/except. On failure → status `god_mode_failed` with error info.
**Cost tracking**: Each agent call tracked to `api_costs` table.

### Services (`services/`)

| Service | File | Status |
| :--- | :--- | :--- |
| Scheduler | `scheduler.py` | ✅ Pipeline ready, needs external cron trigger |
| Feedback Loop | `feedback_loop.py` | ✅ Functional, synchronized with DB schema |
| Newsletter | `newsletter_delivery.py` | ✅ Integrated with **Resend** ESP |
| Social Publisher | `social_publisher.py` | ✅ LinkedIn UGC API implemented, needs OAuth token |

---

## API Surface (`api/routes.py`)

All routes prefixed with `/api/`. Brand ID currently hardcoded (single-brand mode).

| Method | Route | Rate Limit | Cost Level |
| :--- | :--- | :--- | :--- |
| POST | `/research/trigger` | 3/min | 💰💰💰 (5 retrievers + API calls) |
| GET | `/research/runs` | — | Free |
| GET | `/research/items` | — | Free |
| PATCH | `/research/items/{id}/status` | — | Free |
| GET | `/research/stats` | — | Free |
| POST | `/scoring/run` | 5/min | 💰💰 (LLM per item) |
| POST | `/content/generate` | 5/min | 💰💰 (Writer LLM) |
| POST | `/content/drafts/{id}/god-mode` | 3/min | 💰💰💰 (4 LLM calls) |
| POST | `/content/drafts/{id}/adapt` | — | 💰 (Adapter LLM) |
| GET | `/content/drafts` | — | Free |
| PATCH | `/content/drafts/{id}` | — | Free |
| POST | `/writing-lab/sessions` | — | 💰💰 |
| POST | `/writing-lab/sessions/{id}/vote` | — | 💰💰 |
| POST | `/newsletter/send` | 2/min | 💰 (Resend) |
| POST | `/social/publish/linkedin` | 3/min | Free (LinkedIn API) |
| POST | `/social/schedule` | — | Free |
| POST | `/analytics/metrics` | — | Free |
| POST | `/analytics/feedback-loop` | — | Free |
| POST | `/scheduler/daily-pipeline` | 1/5min | 💰💰💰 (full pipeline) |
| POST | `/scheduler/publish-scheduled` | — | Free |

---

## Data Flow & State Machine

### Research Item Lifecycle

```text
new → scored → approved → (draft created) → published
                 └──→ rejected
                 └──→ archived
```

### Content Draft Lifecycle

```text
draft → in_review → approved → scheduled → published
                       │
                  god_mode → approved (pass)
                           → in_review (needs_revision)
                           → god_mode_failed (error)
```

---

## Configuration (`config.py`)

All settings loaded from `../.env.local`:

| Variable | Purpose | Required |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | DB admin access | ✅ |
| `ANTHROPIC_API_KEY` | Claude API (primary) | One of these |
| `OPENROUTER_API_KEY` | OpenRouter API (fallback) | One of these |
| `SERPER_API_KEY` | Web search | For research |
| `YOUTUBE_API_KEY` | YouTube data | For research |
| `RESEND_API_KEY` | Email delivery | For newsletter |

---

## Boundaries

| Concern | Owner | Notes |
| :--- | :--- | :--- |
| UI rendering | Next.js (`src/`) | React components, ShadCN UI |
| API routing | Next.js API routes → FastAPI | Proxy pattern |
| Business logic | Python (`python/src/`) | All orchestration, agents, scoring |
| Data persistence | Supabase (PostgreSQL) | Via Supabase SDK |
| LLM calls | Python → Anthropic/OpenRouter | With cost tracking |
| Email delivery | Python → Resend | ESP integration |
| Social posting | Python → LinkedIn API | OAuth flow needed |
| Cron scheduling | External (Railway/Render) | Calls `/api/scheduler/daily-pipeline` |

---

## Known Limitations & TODOs

1. **Multi-brand**: Core infrastructure supports brand_id isolation, but needs further vetting for enterprise scaling.
2. **Semantic dedup**: Implemented in 002_semantic_dedup.sql.
3. **Test suite**: E2E test suite implemented in `python/tests/test_agent_system_e2e.py`.
4. **Social platforms**: Only LinkedIn implemented (Instagram, TikTok, Twitter missing).
5. **GOD Mode sequential**: 4 agents run in series (dependency chain prevents full parallelization).
6. **No webhook notifications**: No Slack/Telegram alerts on pipeline events.
