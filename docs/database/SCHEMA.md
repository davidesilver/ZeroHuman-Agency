# Database Schema

The migration files in [`supabase/migrations/`](../../supabase/migrations/) are the canonical source of truth. This document is a navigational map — when in doubt, read the migration SQL.

The generated TypeScript types in [`src/lib/types/database.types.ts`](../../src/lib/types/database.types.ts) are the fastest way to inspect the live contract from application code.

To regenerate types after a schema change:

```bash
supabase gen types typescript --linked > src/lib/types/database.types.ts
```

---

## Migration sequence

| # | File | What it adds |
|---|---|---|
| 001 | `initial_schema.sql` | Core tables: brands, users, research pipeline, content drafts, writing lab, campaigns, calendar, api_costs |
| 002 | `semantic_dedup.sql` | `find_semantic_duplicates()` function; `audit_trail` table |
| 004 | `rate_limit_table.sql` | `rate_limit_counters` persistent rate limiter |
| 005 | `agent_system.sql` | `agent_configs`, `agent_skills`, `agent_config_versions` |
| 006 | `brand_scoring_enhancements.sql` | `brands.scoring_weights`, `brands.topics` columns |
| 007 | `anti_hype_gate_columns.sql` | Anti-hype scoring gate columns on `scores` |
| 008 | `feedback_loop_cron.sql` | `social_metrics`, `feedback_loop_audit`; cron job setup |
| 009 | `feedback_loop_cron_jobs.sql` | Additional cron job registrations |
| 010 | `performance_optimization.sql` | Composite indexes on hot query paths |
| 011 | `humanizer_control.sql` | `brands.use_humanizer`, `brands.humanizer_channels`; `humanizer_performance` |
| 012 | `llm_fallback_monitoring.sql` | `llm_fallback_log`; fallback incident tracking |
| 013 | `add_llm_metadata_to_pipeline_health.sql` | LLM metadata columns on `pipeline_health` |
| 014 | `add_manual_retriever_and_skill_description.sql` | Manual retriever support; skill description column |
| 015 | `brand_self_service_onboarding.sql` | `create_brand_with_owner()` RPC function |
| 016 | `schema_alignment_fixes.sql` | View `content_performance`; `brands.use_context7` flag |
| 017 | `multi_brand_membership.sql` | `brand_members` (N:M); `user_has_brand()` helper; redefines `auth_user_brand_id()` |
| 018 | `memory_layer.sql` | `memory_hot`, `memory_semantic` (pgvector), `memory_events`, `memory_archive` |
| 019 | `weekly_newsletter_cron.sql` | Weekly newsletter automation cron job |
| 020 | `retrievers_enum_expansion.sql` | `retriever_type` enum expanded; `brands.research_sources` |
| 021 | `runtime_contract_stabilization.sql` | Function stabilization; re-creates `create_brand_with_owner()` |
| 022 | `brands_delete_policy.sql` | RLS DELETE policy for `brands` |
| 023 | `per_brand_daily_budget.sql` | `brands.daily_budget_usd` |
| 024 | `per_brand_email_settings.sql` | `brands.from_email`, `brands.from_name` |
| 025 | `brand_visual_assets.sql` | `brand_assets`; `brand-assets` Storage bucket + RLS |
| 026 | `image_generation_config.sql` | `image_generations` job log; `brands.image_*` config columns |
| 027 | `image_backend_providers.sql` | Expands `image_backend` constraint to include `openrouter`, `anthropic` |
| 028 | `brand_social_integrations.sql` | `brand_social_integrations`; Postiz integration ID storage |
| 029 | `content_drafts_metadata.sql` | `content_drafts.metadata` jsonb column (stores `postiz_post_ids`) |
| 030 | `audit_indexes_and_search_path.sql` | SECURITY DEFINER hardening (explicit `search_path`); missing indexes on hot paths |
| 031 | `feature_flags.sql` | `feature_flags` per-brand capability gating table |
| 031 | `research_retriever_enum_expansion.sql` | `retriever_type` expanded with `duckduckgo`, `tavily` |
| 032 | `brand_integrations.sql` | `brand_integrations` encrypted key vault (Fernet) |
| 032 | `brand_discovery_urls.sql` | `brands.discovery_urls` column |
| 033 | `brand_service_credentials.sql` | `brand_service_credentials` per-service credential vault |
| 033 | `brevo_foundation.sql` | `brevo_contacts` table |
| 033 | `email_provider_config.sql` | Per-brand email provider config |
| 034 | `llm_provider_metrics.sql` | `llm_provider_metrics` per-call LLM telemetry |
| 034 | `newsletter_layout_type.sql` | `newsletters.layout_type` column |
| 035 | `deep_research_jobs.sql` | `deep_research_jobs` async job queue |
| 035 | `newsletter_subject_variants.sql` | `newsletters.subject_variant_a/b` columns |
| 036 | `competitor_snapshots.sql` | `competitor_snapshots` table |
| 036 | `newsletter_ab_and_events.sql` | `newsletters.ab_winner`, `newsletter_events` table |
| 037 | `deep_research_retriever_type.sql` | `retriever_type` += `deep_research` |
| 037 | `notification_events.sql` | `notification_events` pipeline event table |
| 038 | `video_tables.sql` | `video_templates`, `videos` tables |
| 039 | `carousel_to_reel_template.sql` | Seeds carousel-to-reel system template |
| 040 | `heygen_quota.sql` | `heygen_usage` table; `videos.kind`, `videos.heygen_video_id` |
| 041 | `brevo_campaigns.sql` | `brevo_campaigns` email campaign tracking table |
| 042 | `email_automations.sql` | `email_automations` multi-step workflow table |

> Migration 003 was never created — it was consolidated into 005 during the initial schema review. The gap is intentional. Some migration numbers (031–037) have multiple files due to parallel feature development; all apply in alphabetical order within each number.

---

## Tables by domain

### Tenant and identity

| Table | Purpose |
|---|---|
| `brands` | One row per tenant. Holds all brand configuration: name, slug, topics, tone, scoring weights, sources, agent settings, image config, budget |
| `users` | Legacy single-brand user mapping (`user_id → brand_id`). Still read for backward-compat |
| `brand_members` | Current N:M membership table. One row per user-brand pair with role |
| `agent_configs` | Per-brand agent identities (system prompts) |
| `agent_skills` | Per-brand modular skill instructions attached to agents |
| `agent_config_versions` | Audit history of agent config updates |

### Research pipeline

| Table | Purpose |
|---|---|
| `research_runs` | One record per research execution. Tracks status and timing |
| `research_items` | Individual URLs/items discovered by retrievers. Contains summary, source metadata, embedding, status |
| `scores` | Scoring output per research item (applicability, credibility, alignment, trend_prediction, weighted_score) |

### Content

| Table | Purpose |
|---|---|
| `content_drafts` | Generated or edited drafts. Contains title, body, platform, content_type, status, media_urls, metadata |
| `god_mode_reviews` | 4-agent review output per draft (advocate, factcheck, creative, synthesis verdict) |
| `writing_lab_sessions` | Experimental writing sessions for A/B iterations |
| `writing_lab_rounds` | Individual rounds within a session (champion vs. challenger) |

### Newsletter

| Table | Purpose |
|---|---|
| `newsletters` | Newsletter editions with status lifecycle |
| `newsletter_candidates` | Draft-to-newsletter slot selection |

### Social and images

| Table | Purpose |
|---|---|
| `brand_social_integrations` | Postiz integration IDs per platform per brand |
| `social_metrics` | Engagement metrics imported from social platforms |
| `brand_assets` | Binary asset metadata (logos, palettes, design PDFs). Files stored in `brand-assets` bucket |
| `image_generations` | Image generation job log (backend, model, status, cost, storage path) |

### Memory

| Table | Purpose |
|---|---|
| `memory_hot` | Ephemeral session KV store. TTL: 24 hours |
| `memory_semantic` | Long-term semantic memory with pgvector embeddings. TTL-tiered (core: infinite, persistent: 365d, standard: 90d) |
| `memory_events` | Supplementary event log for memory graph |
| `memory_archive` | Cold storage for expired memory. Partitioned by month |

### Feature flags and secrets

| Table | Purpose |
|---|---|
| `feature_flags` | Per-brand feature flags. New capabilities are default-OFF and gated here |
| `brand_integrations` | Per-brand encrypted API keys (Fernet AES-128-CBC). Stores ciphertext only |
| `brand_service_credentials` | Per-service credential vault (Fernet-encrypted). Keyed by `(brand_id, service_name)` |

### Email marketing

| Table | Purpose |
|---|---|
| `brevo_contacts` | Local mirror of Brevo contacts per brand |
| `brevo_campaigns` | Brevo email campaigns with status lifecycle and engagement metrics |
| `email_automations` | Multi-step Brevo workflow definitions (welcome, nurture, win-back) |
| `newsletter_events` | ESP webhook events per newsletter (delivered, opened, clicked, bounced, unsubscribed) |

### Research extensions

| Table | Purpose |
|---|---|
| `deep_research_jobs` | Async job queue for local-deep-research Docker sidecar (port 5000) |
| `competitor_snapshots` | Periodic competitor page snapshots captured via Scrapling spider |

### Video pipeline

| Table | Purpose |
|---|---|
| `video_templates` | Reusable HyperFrames composition specs. `brand_id IS NULL` = system-level template |
| `videos` | Render jobs and output artefacts. `kind`: `hyperframes` \| `heygen` |
| `heygen_usage` | Per-brand monthly Heygen minute-quota tracking |

### LLM telemetry

| Table | Purpose |
|---|---|
| `llm_provider_metrics` | Per-call LLM telemetry: provider, model, tokens, latency, cost, fallback flag |

### Notifications

| Table | Purpose |
|---|---|
| `notification_events` | System-level pipeline events for Telegram digest and dashboard activity feed |

### Operations and observability

| Table | Purpose |
|---|---|
| `api_costs` | Token counts and cost in USD per request, per agent, per model |
| `pipeline_health` | Agent heartbeat and health status (healthy, degraded, down) |
| `feedback` | Manual and system feedback on drafts |
| `feedback_loop_audit` | Audit log of feedback loop runs |
| `llm_fallback_log` | Records of primary → fallback model switches |
| `audit_trail` | Pipeline events and decisions |
| `humanizer_performance` | Effectiveness tracking for the humanizer |
| `rate_limit_counters` | Persistent sliding-window counters for rate limiting |
| `campaigns` | Campaign planning records |
| `calendar_events` | Content calendar entries |
| `revenue_deals` | Commercial tracking |

---

## Views

| View | Purpose |
|---|---|
| `v_content_pipeline` | Unified pipeline state across research, scoring, drafts |
| `v_daily_costs` | Aggregated cost by day and agent |
| `v_newsletter_performance` | Newsletter send and engagement metrics |
| `v_daily_fallback_stats` | Daily LLM fallback incident statistics |
| `content_performance` | Drafts joined with social metrics; weighted engagement score |
| `vw_memory_episodic` | UNION view: api_costs + audit_trail + feedback_loop_audit + writing_lab_rounds + memory_events |

---

## Key SQL functions

| Function | Purpose |
|---|---|
| `auth_user_brand_id()` | Returns the first brand_id for the current user (legacy single-brand) |
| `auth_user_role()` | Returns the current user's role |
| `user_has_brand(p_brand_id)` | Returns TRUE if the current user is a member of the given brand (multi-brand) |
| `create_brand_with_owner(name, slug, topics)` | Atomically creates brand + brand_members row |
| `update_updated_at_column()` | Trigger function: sets `updated_at = now()` |
| `find_semantic_duplicates(brand_id, embedding, threshold, limit)` | pgvector nearest-neighbor search |
| `mark_semantic_duplicates(...)` | Batch archives semantically duplicate research items |
| `get_draft_engagement_summary(draft_id)` | Aggregates social_metrics for a draft |

---

## Enums

| Enum | Values |
|---|---|
| `user_role` | `owner` · `editor` · `viewer` |
| `run_status` | `running` · `completed` · `failed` |
| `source_type` | `rss` · `search` · `youtube` · `scrape` |
| `retriever_type` | `semantic` · `practitioner` · `trusted_source` · `keyword` · `trend` · `manual` · `rss` · `youtube` · `gmail` · `x` |
| `item_status` | `new` · `scored` · `approved` · `rejected` · `archived` |
| `content_type` | `post` · `blog` · `newsletter_section` · `carousel` · `video_script` · `thread` |
| `platform` | `linkedin` · `instagram` · `facebook` · `x` · `tiktok` · `blog` · `newsletter` |
| `draft_status` | `draft` · `in_review` · `god_mode` · `approved` · `scheduled` · `published` · `archived` |
| `newsletter_status` | `draft` · `in_review` · `approved` · `scheduled` · `sent` |
| `health_status` | `healthy` · `degraded` · `down` |
| `memory_tier` | `core` · `persistent` · `standard` |

---

## Row Level Security

RLS is enabled on every tenant-scoped table. The policy pattern depends on the migration era:

**Pre-migration 017** (single-brand):
```sql
USING (brand_id = auth_user_brand_id())
```

**Migration 017 and later** (multi-brand):
```sql
USING (public.user_has_brand(brand_id))
```

The `brand_assets` Storage bucket also enforces RLS via `storage.objects` policies that check `user_has_brand(split_part(name, '/', 1)::uuid)` — the first path segment is always the brand ID.

---

## Rebuild from scratch

```bash
# 1. Create a Supabase project
# 2. Link the CLI
supabase link --project-ref <project-ref>

# 3. Apply all migrations
supabase db push

# 4. Verify
supabase migration list   # all 42 should show Local = Remote

# 5. Generate TypeScript types
supabase gen types typescript --linked > src/lib/types/database.types.ts
```

If types and this document disagree, the migrations are authoritative.
