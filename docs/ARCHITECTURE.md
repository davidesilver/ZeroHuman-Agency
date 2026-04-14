# System Architecture

The Autonomous Content Engine is built upon a hybrid decoupled architecture, separating the high-performance Next.js 15 frontend from the Python-based AI orchestration backend.

## 🏗 High-Level Overview

![Architecture Blueprint](https://img.shields.io/badge/Architecture-Decoupled_Microservices-blue)

1. **Next.js 15 App Router (Frontend)**: Serves the static content, client dashboard, and handles user authentication securely. Communicates with Supabase directly for standard UI fetching and talks to the Python backend to trigger background AI tasks.
2. **FastAPI (Python Backend)**: The heart of the Content Engine. Contains all the LangChain integrations, autonomous agents, semantic deduplication, and scheduler logic.
3. **Supabase (Database + Auth)**: The source of truth. Manages Row Level Security (RLS) ensuring strict tenant isolation. 

## 🔐 Multi-Tenant Security (Row Level Security)

This is a **White-Label Box**. It doesn't rely on hardcoded tenant IDs (`brand_id`). 

Instead, tenant isolation is guaranteed at the Postgres Level via Supabase **Row Level Security (RLS)**.
- Every API endpoint is protected by a JWT validator middleware (`_get_brand_id(request)`).
- The resolved JWT limits the `supabase-py` client connection explicitly to that user's brand.
- Attempting to query `db.table("content_drafts")` automatically filters out any data belonging to other tenants.

## 🧠 Brains & Memory

- **Vector Database**: We use `pgvector` stored directly in Supabase. The `research_items` table contains a 1536-dimensional `embedding` column powered by OpenAI (`text-embedding-3-small`). 
- **Semantic Deduplication**: Before a new research item is fed to the LLMs, a cosine distance check runs against historical embeddings, throwing out duplicate news dynamically.

## ⚡ Agent Loop

The content generation isn't a single LLM call; it's an orchestration pipeline.
1. The **Context Manager** fetches the required data.
2. The **Agent Loader** resolves the specific brand's `writer` / `editor` identities from the database.
3. The prompt is injected with contextual limits (Brand rules, Tone of Voice).
4. For critical pieces, the **GOD System** acts as an internal feedback loop (Advocate/Creative/Factcheck) before letting human intervention happen.
