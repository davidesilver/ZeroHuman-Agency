# Autonomous Content Engine 🚀

> A production-ready, white-label Multi-Agent Platform capable of managing and scaling autonomous content operations for multiple brands from a single deployment.

This repository serves as the definitive architecture for an autonomous, AI-driven content generation engine. Built on a fully decoupled Next.js 15 frontend and FastAPI Python backend, it integrates direct web scraping, AI workflows (via LangChain/Anthropic/OpenAI), and semantic optimization. 

The entire system is designed around **Row Level Security (RLS)** in Supabase to enforce multi-tenant isolation out-of-the-box. 

---

## 🎯 Architecture Overview

The platform acts as a "White-Label Empty Box". You can deploy it once and manage an infinite number of independent brands. Thanks to JWT-based RLS on the database tier, no agent or user can cross boundaries or contaminate another brand's proprietary tone of voice.

### Core Stack
- **Frontend**: Next.js 15, React 19, Tailwind CSS v4, Base UI (Unstyled components).
- **Backend**: FastAPI (Python 3.10+), LangChain, Anthropic + OpenRouter SDKs.
- **Database**: Supabase (PostgreSQL 15+) with `pgvector` for semantic duplication and RLS.
- **Agent Orchestration**: Sequential and competitive AI pipelines (Writing Lab) acting as multi-persona nodes.

---

## 📖 White-Label Documentation

Everything you need to configure and scale this engine for your own business is detailed in our documentation:

| Guide | Description |
|---|---|
| [**System Architecture**](./docs/ARCHITECTURE.md) | Deep dive into the backend services and decoupled Next.js flow. |
| [**Brand Onboarding**](./docs/ONBOARDING.md) | How to add a new Brand tenant, configure RLS, and generate its JWT. |
| [**Deployment Guide**](./docs/DEPLOYMENT.md) | Step-by-step instructions for deploying to Vercel and Railway/Render. |
| [**Agents Ecosystem**](./docs/AGENTS.md) | How the `agent_loader`, System Prompts, and GOD Mode work. |

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Node.js `20+` & `npm`
- Python `3.10+` & `pip`
- A Supabase Project (for DB & Authentication)

### 1. Database Setup
Ensure you have the Supabase CLI installed, or use the Supersbase web console to run the SQL migrations located in `supabase/migrations/` sequentially.

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

## 🛡 Security & Extensibility

This project comes hardened by default:
- **Zero Hardcoded IDs**: Brands are loaded dynamically via Request JWTs.
- **Service Rate Limiting**: The backend leverages an IP-based persistent sliding-window throttle.
- **Agent Skill Composition**: Agent roles and fallback instructions are managed via SQL (`agent_configs` table).

---

![Open Source](https://img.shields.io/badge/Status-Production_Ready-success)
