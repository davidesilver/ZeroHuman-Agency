# Content #4 — Multi-Tenancy Architecture

## Blog version (technical deep dive)

---
title: "Multi-tenant AI content ops: how we isolated 50+ tables for agency-grade brand separation"
slug: multi-tenant-architecture
date: 2026-05-20
author: Davide Silvestri
tags: [architecture, multi-tenancy, supabase, rls, agencies, build-in-public]
---

If you run a content agency, you manage multiple brands. Each brand has its own voice, its own topics, its own API keys, its own audience. Most AI content tools handle this with "workspaces" — separate accounts that share nothing.

That model breaks at scale. You can't see all your brands in one dashboard. You can't share a pipeline configuration across brands. You can't run reports across your portfolio.

ZeroHuman takes a different approach: true multi-tenancy at the database level.

### Row-Level Security everywhere

Every table in the system — and there are 50+ of them — has a `brand_id` column and a Supabase RLS (Row-Level Security) policy. When a user queries `research_items`, they only see items for brands they have access to. This isn't application-level filtering that a bug could bypass. It's enforced by PostgreSQL itself.

The pattern is consistent across the entire schema:

```sql
CREATE POLICY brand_isolation ON research_items
  FOR ALL USING (public.user_has_brand(brand_id));
```

One function, `user_has_brand()`, checks the `brand_members` table. If you're not a member of that brand, the row doesn't exist for you.

### Per-brand encrypted credentials

Agencies connect different API keys per client — one brand uses OpenAI, another uses Anthropic, one client has their own Brevo account. ZeroHuman stores these in `brand_integrations` with encrypted values. The encryption key is per-brand, derived from the brand's ID and a server-side secret.

This means:
- Brand A's Brevo API key can't be accessed by Brand B's users
- If someone exports the database, encrypted values are useless without the server secret
- Each brand can be configured independently without affecting others

### What gets isolated

Everything:
- Research items and scores
- Content drafts and reviews
- Social publishing connections
- Newsletter subscribers and campaigns
- Memory (hot, semantic, archive)
- Feature flags
- Agent configurations and skills
- Calendar events
- Cost tracking
- Competitor snapshots

### Brand switching in the UI

The dashboard has a brand switcher in the sidebar. When you switch brands, the entire context changes — the data you see, the sources configured, the social accounts connected. It's not a filter on top of shared data; it's a complete context switch enforced at every layer.

### Why this matters for agencies

1. **Client data isolation** — you can guarantee to clients that their data never touches another client's data. This isn't a promise in your ToS; it's a database constraint.

2. **Independent configuration** — one client might want aggressive content scoring, another might want conservative. One might publish to LinkedIn only, another to all platforms. Each brand is fully independent.

3. **Single pane of glass** — despite full isolation, you manage everything from one dashboard. One login, one instance, one deployment.

4. **Cost tracking per brand** — every LLM call is tagged with `brand_id`, so you can see exactly how much each client costs.

### The trade-off

True multi-tenancy is more complex to build than workspace-based separation. Every new table needs RLS policies. Every new API route needs to respect brand context. Every migration needs to add `brand_id` columns.

But it's the correct foundation for a platform that agencies can trust with client data.

ZeroHuman is MIT open-source. The entire schema is in `supabase/migrations/`.

https://github.com/davidesilver/ZeroHuman-Agency

---

## LinkedIn version

Most AI content tools handle multiple brands with "workspaces" — separate accounts that share nothing.

That breaks at scale. You can't see all brands in one dashboard. Can't share pipeline config. Can't report across your portfolio.

ZeroHuman uses true database-level multi-tenancy:

→ 50+ tables, every one with `brand_id` + Row-Level Security
→ PostgreSQL enforces isolation — not application code that a bug could bypass
→ Per-brand encrypted API credentials (OpenAI for Brand A, Anthropic for Brand B)
→ Independent config: scoring weights, sources, social accounts, feature flags
→ Single dashboard, one login, complete context switch per brand

What gets isolated? Everything:
- Research items and scores
- Content drafts and reviews
- Social connections
- Newsletter subscribers
- Memory system
- Agent configurations
- Cost tracking

Why it matters for agencies:
1. Client data isolation is a database constraint, not a ToS promise
2. Each client can be configured completely independently
3. You manage everything from one instance
4. Cost tracking per brand — know exactly what each client costs

The trade-off: every new table needs RLS policies, every migration adds brand_id. More complex to build. But it's the correct foundation for client-grade data separation.

MIT open-source. Full schema in supabase/migrations/.
https://github.com/davidesilver/ZeroHuman-Agency

#MultiTenancy #Supabase #OpenSource #AgencyLife #BuildInPublic
