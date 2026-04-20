# Database Schema

This document is a map of the current schema implemented by the migration files in [`supabase/migrations`](/Users/claw/Progetti/ai-automation/supabase/migrations).

The migration set is the source of truth. Generated TypeScript types in [`src/lib/types/database.types.ts`](/Users/claw/Progetti/ai-automation/src/lib/types/database.types.ts) are the fastest way to inspect the live contract from application code.

## Migration Overview

Current migration sequence:

1. `001_initial_schema.sql`
2. `002_semantic_dedup.sql`
3. `004_rate_limit_table.sql`
4. `005_agent_system.sql`
5. `006_brand_scoring_enhancements.sql`
6. `007_anti_hype_gate_columns.sql`
7. `008_feedback_loop_cron.sql`
8. `009_feedback_loop_cron_jobs.sql`
9. `010_performance_optimization.sql`
10. `011_humanizer_control.sql`
11. `012_llm_fallback_monitoring.sql`
12. `013_add_llm_metadata_to_pipeline_health.sql`
13. `014_add_manual_retriever_and_skill_description.sql`

## Core Tenant Tables

| Table | Purpose |
| --- | --- |
| `brands` | tenant configuration, voice, sources, scoring, social, humanizer settings |
| `users` | maps auth users to `brand_id` and role |
| `agent_configs` | tenant-specific agent identities |
| `agent_skills` | tenant-specific skills attached to agents |
| `agent_config_versions` | historical versions of agent configs |

Important `brands` fields:

- `name`
- `slug`
- `topics`
- `tone_of_voice`
- `scoring_weights`
- `rss_sources`
- `social_accounts`
- `use_humanizer`
- `humanizer_channels`
- `humanizer_model_override`
- `founder_principles`
- `gold_examples`
- `discard_examples`

## Content Pipeline Tables

| Table | Purpose |
| --- | --- |
| `research_runs` | one research execution |
| `research_items` | discovered URLs and source metadata |
| `scores` | scoring output per research item |
| `content_drafts` | generated or edited content items |
| `god_mode_reviews` | multi-agent review output |
| `newsletters` | newsletter editions |
| `newsletter_candidates` | draft-to-newsletter slot selection |
| `writing_lab_sessions` | experimental writing sessions |
| `writing_lab_rounds` | champion/challenger rounds |

## Operations And Analytics Tables

| Table | Purpose |
| --- | --- |
| `api_costs` | token and cost accounting |
| `pipeline_health` | agent heartbeat and health |
| `feedback` | manual and system feedback |
| `social_metrics` | engagement metrics |
| `feedback_loop_audit` | feedback-loop run audit |
| `rate_limit_counters` | persistent rate limiting |
| `audit_trail` | pipeline audit entries |
| `humanizer_performance` | humanizer effectiveness data |
| `llm_fallback_log` | fallback incidents and emergency events |
| `campaigns` | campaign planning |
| `calendar_events` | content calendar |
| `revenue_deals` | commercial tracking |

## Views And SQL Functions

Views present in the schema:

- `v_content_pipeline`
- `v_daily_costs`
- `v_newsletter_performance`
- `v_daily_fallback_stats`

Key SQL functions:

- `auth_user_brand_id()`
- `auth_user_role()`
- `update_updated_at_column()`
- `find_semantic_duplicates(...)`
- `mark_semantic_duplicates(...)`
- `get_draft_engagement_summary(...)`

## Enums

Important enums currently used by the application:

| Enum | Values |
| --- | --- |
| `user_role` | `owner`, `editor`, `viewer` |
| `run_status` | `running`, `completed`, `failed` |
| `source_type` | `rss`, `search`, `youtube`, `scrape` |
| `retriever_type` | `semantic`, `practitioner`, `trusted_source`, `keyword`, `trend`, `manual` |
| `item_status` | `new`, `scored`, `approved`, `rejected`, `archived` |
| `content_type` | `post`, `blog`, `newsletter_section`, `carousel`, `video_script`, `thread` |
| `platform` | `linkedin`, `instagram`, `facebook`, `x`, `tiktok`, `blog`, `newsletter` |
| `draft_status` | `draft`, `in_review`, `god_mode`, `approved`, `scheduled`, `published`, `archived` |
| `newsletter_status` | `draft`, `in_review`, `approved`, `scheduled`, `sent` |
| `health_status` | `healthy`, `degraded`, `down` |

## Row Level Security

RLS is enabled on the tenant-scoped tables created in the migration set, including:

- `brands`
- `users`
- `research_runs`
- `research_items`
- `scores`
- `content_drafts`
- `god_mode_reviews`
- `newsletters`
- `newsletter_candidates`
- `campaigns`
- `calendar_events`
- `api_costs`
- `writing_lab_sessions`
- `writing_lab_rounds`
- `revenue_deals`
- `pipeline_health`
- `feedback`
- `audit_trail`
- `rate_limit_counters`
- `social_metrics`
- `feedback_loop_audit`
- `humanizer_performance`
- `llm_fallback_log`

## Rebuild Strategy

To recreate the project database from zero:

1. create the target Supabase project
2. run the migration set in order with `supabase db push`
3. verify generated tables and enums against [`src/lib/types/database.types.ts`](/Users/claw/Progetti/ai-automation/src/lib/types/database.types.ts)
4. create at least one `brands` row and one mapped `users` row

If the documentation and the generated types ever disagree, trust the migrations first and then regenerate types.
