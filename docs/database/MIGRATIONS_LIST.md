# Database Migrations - Complete List

This document lists all database migrations that build up the complete Content Engine schema.

## Migration Files

| # | File | Description | Date |
|---|------|-------------|------|
| 001 | `001_initial_schema.sql` | Core schema: brands, research items, scores, content drafts, generation logs | - |
| 002 | `002_semantic_dedup.sql` | Vector similarity function for content deduplication | - |
| 004 | `004_rate_limit_table.sql` | Rate limiting for API endpoints | - |
| 005 | `005_agent_system.sql` | Agent configuration and skills system | - |
| 006 | `006_brand_scoring_enhancements.sql` | Enhanced brand scoring with founder principles | - |
| 007 | `007_anti_hype_gate_columns.sql` | Anti-hype gate scoring mechanism | - |
| 008 | `008_feedback_loop_cron.sql` | Content performance tracking tables | - |
| 009 | `009_feedback_loop_cron_jobs.sql` | Cron job scheduling for feedback loops | - |
| 010 | `010_performance_optimization.sql` | Database indexes for performance | - |
| 011 | `011_humanizer_control.sql` | Humanizer settings and examples | - |
| 012 | `012_llm_fallback_monitoring.sql` | LLM provider fallback logging | - |
| 013 | `013_add_llm_metadata_to_pipeline_health.sql` | LLM metadata in generation logs | - |
| 014 | `014_add_manual_retriever_and_skill_description.sql` | Enhanced retriever and skill descriptions | - |
| 015 | `015_brand_self_service_onboarding.sql` | Brand topics and self-service features | - |
| 016 | `016_schema_alignment_fixes.sql` | Schema alignment and consistency fixes | - |
| 017 | `017_multi_brand_membership.sql` | Multi-brand user membership system | - |
| 018 | `018_memory_layer.sql` | Memory decay and retrieval system | - |
| 019 | `019_weekly_newsletter_cron.sql` | Weekly newsletter scheduling | - |
| 020 | `020_retrievers_enum_expansion.sql` | Expanded retriever types support | - |
| 021 | `021_runtime_contract_stabilization.sql` | Runtime contract management | - |
| 022 | `022_brands_delete_policy.sql` | Brand deletion and cascade policies | - |
| 023 | `023_per_brand_daily_budget.sql` | Per-brand daily budget tracking | - |
| 024 | `024_per_brand_email_settings.sql` | Brand-specific email configuration | - |
| 025 | `025_brand_visual_assets.sql` | Brand visual assets management | - |
| 026 | `026_image_generation_config.sql` | Image generation backend configuration | - |
| 027 | `027_image_backend_providers.sql` | Image backend provider registry | - |
| 028 | `028_brand_social_integrations.sql` | Social platform integrations | - |
| 029 | `029_content_drafts_metadata.sql` | Enhanced content draft metadata | - |
| 030 | `030_audit_indexes_and_search_path.sql` | Final audit indexes and search path configuration | - |
| 031 | `031_research_retriever_enum_expansion.sql` | Research retriever enum expansion | - |
| 032 | `032_brand_discovery_urls.sql` | Brand discovery URL tracking | - |
| 030 | `030_audit_indexes_and_search_path.sql` | Security hardening: SECURITY DEFINER helpers with explicit search_path; missing indexes on hot query paths | - |
| 031 | `031_feature_flags.sql` | Per-brand feature flags table (default-OFF gating for new capabilities) | - |
| 031 | `031_research_retriever_enum_expansion.sql` | Adds `duckduckgo` and `tavily` to `retriever_type` enum | - |
| 032 | `032_brand_integrations.sql` | Per-brand encrypted API key vault (`brand_integrations` table, Fernet-encrypted) | - |
| 032 | `032_brand_discovery_urls.sql` | Adds `discovery_urls` column to `brands` table | - |
| 033 | `033_brand_service_credentials.sql` | Per-brand external service credential vault (Fernet-encrypted, RLS) | - |
| 033 | `033_brevo_foundation.sql` | Local mirror of Brevo contacts per brand (`brevo_contacts` table) | - |
| 033 | `033_email_provider_config.sql` | Per-brand email provider configuration (Brevo, Mailchimp, Resend) | - |
| 034 | `034_llm_provider_metrics.sql` | Per-call LLM telemetry table (`llm_provider_metrics`) for cost/latency comparison | - |
| 034 | `034_newsletter_layout_type.sql` | Adds `layout_type` column to `newsletters` (digest \| single_story \| announcement) | - |
| 035 | `035_deep_research_jobs.sql` | Async deep research job queue (`deep_research_jobs`) for local-deep-research sidecar | - |
| 035 | `035_newsletter_subject_variants.sql` | Adds A/B subject line variant columns to `newsletters` | - |
| 036 | `036_competitor_snapshots.sql` | Competitor page snapshots table (`competitor_snapshots`) via Scrapling spider | - |
| 036 | `036_newsletter_ab_and_events.sql` | A/B campaign tracking columns on `newsletters`; `newsletter_events` table for ESP webhooks | - |
| 037 | `037_deep_research_retriever_type.sql` | Adds `deep_research` value to `retriever_type` enum | - |
| 037 | `037_notification_events.sql` | System-level pipeline events table (`notification_events`) for Telegram digest and activity feed | - |
| 038 | `038_video_tables.sql` | `video_templates` and `videos` tables for HyperFrames rendering pipeline | - |
| 039 | `039_carousel_to_reel_template.sql` | Seeds the system-level carousel-to-reel video template | - |
| 040 | `040_heygen_quota.sql` | `heygen_usage` table for per-brand monthly quota tracking; adds `kind` and `heygen_video_id` to `videos` | - |
| 041 | `041_brevo_campaigns.sql` | `brevo_campaigns` table for email campaign tracking and metrics | - |
| 042 | `042_email_automations.sql` | `email_automations` table for Brevo multi-step workflow definitions | - |

## Complete Schema

For a complete schema reference, see `schema_complete.sql` which combines all migrations into a single file suitable for fresh database setup.

## Applying Migrations

### Using Supabase CLI

```bash
# Link to your Supabase project
supabase link --project-ref YOUR_PROJECT_REF

# Apply all migrations
supabase db push

# Apply specific migration
supabase db push --include-migration 001_initial_schema.sql
```

### Manual Application

```bash
# Apply individual migrations in order
for file in supabase/migrations/*.sql; do
    psql "$DATABASE_URL" -f "$file"
done
```

## Migration Dependencies

- **001** is the foundation - must be applied first
- **002** depends on **001** (requires research_items table)
- **004-006** depend on **001** (require brands table)
- **008-009** depend on **001** (require content_drafts table)
- **010** depends on all previous tables (creates indexes)
- **011-012** depend on **001** (require brands and generation_logs)
- **013** depends on **012** (modifies generation_logs)
- **015-016** depend on **001** (modify brands and brand_sources)
- **017** depends on **001** (requires brands and auth.users)
- **018** depends on **001** (requires brands)
- **020** depends on **001** (modifies brand_sources)
- **022** depends on **001** (modifies brands cascade)
- **023-029** all depend on **001** (modify brands or add brand-related tables)
- **030** depends on all previous migrations (adds final indexes)
- **031-032** depend on **001** (extend brand-related enums and tables)
- **033** depends on **001** (adds credential vault with FK to brands)

## Rollback Strategy

Each migration is designed to be idempotent where possible. For rollbacks:

1. Identify the migration to rollback
2. Create a rollback migration (e.g., `031_rollback_feature.sql`)
3. Apply the rollback migration

**Note**: Some migrations (especially those involving data) may not be easily reversible. Always backup before major schema changes.
