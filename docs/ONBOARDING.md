# Tenant Onboarding

This guide explains how to activate a new tenant without changing application code.

## Goal

A tenant is operational only when all of these exist:

- one row in `public.brands`
- one or more Supabase auth users
- one row in `public.users` for each auth user
- optional agent customizations, RSS sources, social accounts, and newsletter settings

## 1. Create The Tenant Record

Minimum SQL:

```sql
insert into public.brands (
  name,
  slug,
  topics,
  tone_of_voice,
  scoring_weights,
  rss_sources,
  social_accounts
) values (
  'Example Workspace',
  'example-workspace',
  array['topic-a', 'topic-b'],
  '{"style":"clear","format":"operator-friendly"}'::jsonb,
  '{"applicability":1,"credibility":1,"alignment":1,"trend_prediction":1,"italy_relevance":1}'::jsonb,
  '[]'::jsonb,
  '{}'::jsonb
);
```

Recommended fields to review after creation:

- `topics`
- `tone_of_voice`
- `scoring_weights`
- `rss_sources`
- `social_accounts`
- `use_humanizer`
- `humanizer_channels`

## 2. Create The User Mapping

After creating the auth user in Supabase, add the application-level user row:

```sql
insert into public.users (
  id,
  brand_id,
  email,
  role
) values (
  '<auth-user-uuid>',
  '<brand-uuid>',
  'editor@example.com',
  'editor'
);
```

Supported roles:

- `owner`
- `editor`
- `viewer`

## 3. Verify Agent Defaults

The agent migration creates tenant-scoped defaults in:

- `agent_configs`
- `agent_skills`

Review these tables if the tenant needs:

- a different writing identity
- custom editorial rules
- per-agent skills or priorities

See [`docs/AGENTS.md`](/Users/claw/Progetti/ai-automation/docs/AGENTS.md).

## 4. Configure Sources

Content discovery depends on tenant data, not hardcoded code changes.

Typical fields:

- `brands.rss_sources` for feeds
- `brands.topics` for topical context
- `brands.scoring_weights` for scoring emphasis

If social publishing is required, store account metadata in `brands.social_accounts`.

## 5. Validate Access

Checklist:

1. user can sign in from the login page
2. dashboard loads successfully
3. `GET /api/brands` returns only the tenant row
4. research trigger works
5. content generation creates a draft under the correct `brand_id`

## 6. Recommended Acceptance Test

1. add at least one source
2. run a research cycle
3. score discovered items
4. generate one draft
5. run GOD mode on that draft
6. if enabled, run humanizer
7. preview or send one newsletter

## 7. Common Mistakes

- Creating the auth user but forgetting the `public.users` row
- Setting up `brands` without usable `rss_sources` or topics
- Expecting scheduler jobs to work without `SCHEDULER_BRAND_ID`
- Storing frontend-only credentials instead of service credentials in environment variables
