# Autonomous Content Engine 🚀

> **Build once. Adapt forever.**
> A production-ready, white-label Multi-Agent Platform capable of managing and scaling autonomous content operations for multiple brands from a single deployment.

This repository serves as the definitive architecture for an autonomous, AI-driven content generation engine. Built on a fully decoupled Next.js 15 frontend and FastAPI Python backend, it integrates direct web scraping, AI workflows (via Anthropic/OpenAI), and semantic optimization. 

---

## 🎯 Architecture & Empty Box Principle

The platform acts as a "**White-Label Empty Box**". You can deploy it once and manage an infinite number of independent brands. 

This means the engine pipeline stays identical; the topic, tone, sources, scoring criteria, and output format belong to the vertical configuration injected at runtime.

- **Frontend**: Next.js 15, React 19, Tailwind CSS v4.
- **Backend**: FastAPI (Python 3.10+), LangChain, Anthropic + OpenRouter SDKs.
- **Database**: Supabase (PostgreSQL 15+) with `pgvector` for semantic duplication and **Row Level Security (RLS)** ensuring strict tenant isolation.
- **Agent Orchestration**: Sequential and competitive AI pipelines with structured XML prompts.

---

## 🔄 How the Pipeline Works

A full autonomous cycle — from raw signals to published content — runs daily with zero manual intervention.

```text
07:00 AM ──► RESEARCH PHASE
             Research agent queries all configured sources:
             RSS feeds, web search, YouTube, newsletters.
             Each item is stored with URL, title, summary, source type.
             ▼
08:00 AM ──► DEDUPLICATION
             URL-based exact dedup + semantic similarity check (pgvector).
             Filtered against historical items.
             ▼
08:30 AM ──► SCORING PHASE
             Scoring agent evaluates each item against your rubric:
             Relevance · Novelty · Trend strength · Audience fit · Risk
             Only items above your threshold proceed.
             ▼
10:00 AM ──► WRITING PHASE
             Writer agent generates content for approved items.
             Generated in platform-specific formats (LinkedIn, Newsletter, Blog).
             ▼
11:00 AM ──► GOD MODE REVIEW (Optional)
             Multi-agent review panel runs on high-stakes content:
             Advocate → FactCheck → Creative → Synthesis
             Final content score determines auto-approve or human-flag.
             ▼
12:00 PM ──► PUBLISH PHASE
             Approved content published to configured channels.
             ▼
CONTINUOUS ► FEEDBACK LOOP
             Engagement metrics flow back into scoring.
             High-performing topics get boosted in future scoring rounds.
```

---

## 🤖 The Multi-Agent Ecosystem

The entire orchestration does not rely on a single LLM pass. Every step is guided by dedicated "Identities" loaded dynamically from the Database `agent_configs` based on the targeted brand. 

- **Research Agent**: Collect raw intelligence from the world without bias.
- **Scoring Agent**: Use a lightweight model to cost-effectively filter noises and score signals.
- **Writer Agent**: Transform approved items into platform-ready content applying strictly the Brand Guidelines.
- **Editor Agent**: Quality gate before publish. Detects hallucinations, brand safety violations, and formatting errors.
- **GOD Mode Panel**: A multi-agent review system meant for high-stakes content. 
  - *Advocate*: Builds the case FOR the content.
  - *FactCheck*: Challenges every factual claim.
  - *Creative*: Suggests improvements to angle framing and hook structure.
  - *Synthesis*: Integrates all the feedback into the definitive cut.

> Read more in the [**Agents Ecosystem Guide**](./docs/AGENTS.md) and in the [**Architecture Overview**](./docs/ARCHITECTURE.md).

---

## 🚀 Quick Start (Local Development)

### 1. Database Setup
Ensure you have the Supabase CLI installed, or use the Supabase web console to run the SQL migrations located in `supabase/migrations/` sequentially. The engine comes with a pre-configured `005_agent_system.sql` to immediately seed the default 7 agents.

### 2. Frontend Launch
```bash
# Install Node dependencies
npm install

# Setup your local environment file
cp .env.example .env.local

# Run the Next.js dev server (default port 3000)
npm run dev
```

### 3. Backend Launch
```bash
# Navigate to the Python directory
cd python

# Install Python requirements
pip install -r requirements.txt

# Start the FastAPI engine (default port 8000)
uvicorn src.content_engine.main:app --reload
```

---

## 📖 Extended Documentation

| Guide | Description |
|---|---|
| [**Brand Onboarding**](./docs/ONBOARDING.md) | How to add a new Brand tenant, configure RLS, and generate its JWT. |
| [**System Architecture**](./docs/ARCHITECTURE.md) | Deep dive into the backend services and decoupled Next.js flow. |
| [**Deployment Guide**](./docs/DEPLOYMENT.md) | Step-by-step instructions for deploying to Vercel and Railway/Render. |
| [**Agents System**](./docs/AGENTS.md) | Deep dive into the GOD Panel and the A/B Writing Lab interactions. |

---

## 🛡 Security & Cost Optimization

- **Zero Hardcoded IDs**: Brands are loaded dynamically via Request JWTs directly extracted from the HTTP middleware.
- **Service Rate Limiting**: The backend leverages an IP-based persistent sliding-window throttle (stored in PostgreSQL).
- **Cost Reduction**: A two-stage scoring model structure significantly cuts LLM tokens by using fast, cheap models (like Claude Haiku) for pre-filtering 80% of the noise, reserving premium models (Claude Opus/Sonnet) exclusively for the GOD Mode or the writing phase.

![Open Source](https://img.shields.io/badge/Status-Production_Ready-success)
