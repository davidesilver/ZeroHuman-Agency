# Tenant Onboarding

A **tenant** in this platform is a **brand** — an isolated workspace with its own content sources, voice, agents, social accounts, and data. This guide explains how to create a new brand and make it fully operational without touching application code.

---

## What a working tenant needs

| Record | Table | Required |
|---|---|---|
| Brand configuration | `public.brands` | Yes |
| Auth user | `auth.users` (Supabase) | Yes |
| User-to-brand mapping | `public.brand_members` | Yes |
| Agent customizations | `public.agent_configs`, `agent_skills` | No (defaults apply) |
| Social integrations | `public.brand_social_integrations` | Only for social publishing |
| Brand visual assets | `public.brand_assets` | Only for image generation |

---

## Option A — Dashboard UI (recommended)

1. Sign in and go to **Settings → Brands → Add brand**
2. Fill in name, slug, and topics
3. The `create_brand_with_owner()` SQL function creates both the `brands` row and the `brand_members` entry atomically
4. Configure sources, voice, and scoring in **Settings → Brand Context**

This is the safest path — the function enforces constraints and handles the atomic insert.

---

## Option B — SQL (for automation or migration scripts)

### 1. Create the brand

```sql
INSERT INTO public.brands (
  name,
  slug,
  topics,
  tone_of_voice,
  scoring_weights,
  rss_sources
) VALUES (
  'Acme Corp',
  'acme-corp',
  ARRAY['supply chain', 'logistics', 'automation'],
  '{"style": "direct", "audience": "operators", "avoid": ["jargon", "fluff"]}'::jsonb,
  '{"applicability": 2, "credibility": 1, "alignment": 1, "trend_prediction": 1}'::jsonb,
  '[{"url": "https://example.com/feed.xml", "label": "Example Blog"}]'::jsonb
);
```

### 2. Create the user-to-brand mapping

After the user signs up through the Supabase Auth UI, link them to the brand:

```sql
INSERT INTO public.brand_members (user_id, brand_id, role)
VALUES (
  '<supabase-auth-user-uuid>',
  '<brand-uuid-from-step-1>',
  'owner'
);
```

Supported roles: `owner`, `editor`, `viewer`.

> **Note:** `public.users` still exists for legacy single-brand reads. `public.brand_members` is the current multi-tenant membership table (since migration 017). Both are maintained.

### 3. Verify

```sql
-- Confirm the brand exists
SELECT id, name, slug FROM public.brands WHERE slug = 'acme-corp';

-- Confirm the membership
SELECT bm.role, b.name
FROM public.brand_members bm
JOIN public.brands b ON b.id = bm.brand_id
WHERE bm.user_id = '<user-uuid>';
```

---

## Configure the brand

After creation, configure these fields in **Settings → Brand Context** or directly in SQL:

| Field | Purpose |
|---|---|
| `topics` | Keywords used by all research retrievers |
| `tone_of_voice` | JSON describing voice, style, and constraints |
| `scoring_weights` | Per-dimension weights for the scoring engine |
| `rss_sources` | Array of `{url, label}` objects for RSS retrieval |
| `research_sources` | Extended sources: YouTube channels, X accounts, Gmail labels |
| `founder_principles` | Non-negotiable content rules injected into agent prompts |
| `gold_examples` | High-quality example posts used for voice calibration |
| `discard_examples` | Examples of content to avoid |
| `use_humanizer` | Enable the humanizer pass |
| `humanizer_channels` | Platforms where humanizer runs (`linkedin`, `x`, etc.) |
| `daily_budget_usd` | Per-brand daily LLM spending cap |
| `from_email` / `from_name` | Newsletter sender identity |
| `image_backend` / `image_model` | Image generation configuration |

---

## Connect social accounts

1. Open the Postiz UI (self-hosted: `http://localhost:4200`, or your cloud instance)
2. Go to **Integrations → Add** and connect each platform via OAuth
3. Copy the integration ID for each platform
4. Paste into **Settings → Social Connections** in the Content Engine dashboard

The platform stores only the opaque integration ID — no OAuth tokens are held in the Content Engine database.

---

## Set up agent configuration (optional)

By default, all agents use the hardcoded fallback prompts. To customize:

1. Go to **Settings → Agents** in the dashboard
2. Select an agent key (e.g., `writer`, `editor`)
3. Write an identity prompt tailored to the brand
4. Optionally add skills for modular behavior injection

See [`docs/AGENTS.md`](AGENTS.md) for the full agent system reference.

---

## Upload brand assets (optional)

Brand assets (logos, palette files, design system PDFs, example newsletters) are stored in the `brand-assets` Supabase Storage bucket and referenced in `brand_assets`.

1. Go to **Settings → Brand Visual Assets**
2. Upload assets — they are stored under `<brand_id>/<uuid>.<ext>`
3. The image generator and text agents can reference these assets when generating content

---

## Validation checklist

Before handing a brand to a user, verify:

- [ ] User can sign in
- [ ] Brand selector shows the correct brand
- [ ] `GET /api/brands` returns only this brand's data (RLS check)
- [ ] Research trigger completes without errors
- [ ] At least one draft can be generated
- [ ] GOD mode runs on a draft (if enabled)
- [ ] Newsletter preview works (if Resend is configured)
- [ ] Social publish works (if Postiz is configured)

---

## Acceptance test sequence

```bash
# 1. Trigger research
curl -X POST http://localhost:3000/api/research/trigger \
  -H "Cookie: <session>" \
  -H "Content-Type: application/json" \
  -d '{"retrievers": ["rss", "semantic"]}'

# 2. Score items
curl -X POST http://localhost:3000/api/scoring/run \
  -H "Cookie: <session>"

# 3. Generate a draft
curl -X POST http://localhost:3000/api/content/generate \
  -H "Cookie: <session>" \
  -H "Content-Type: application/json" \
  -d '{"research_item_id": "<id>", "platform": "linkedin", "run_god": true}'
```

---

## Dev skills (Claude Code)

The project pins Claude Code skills in `skills-lock.json`. Each skill is loaded automatically when running Claude Code in this repo.

| Skill | Source | Purpose |
|---|---|---|
| `supabase-postgres-best-practices` | `supabase/agent-skills` | Postgres query optimization, RLS patterns, index design |
| `obra-superpowers` | `obra/superpowers` | Core agentic patterns: TDD, debugging, collaboration workflows |
| `thedotmack-claude-mem` | `thedotmack/claude-mem` | Persistent context across sessions — captures, compresses, and injects prior work |
| `yamadashy-repomix` | `yamadashy/repomix` | Pack the full repo into a single AI-friendly file for large context operations |
| `leonxlnx-taste-skill` | `leonxlnx/taste-skill` | Aesthetic judgment — prevents generic output, enforces opinionated design choices |

No manual setup needed. Skills are version-pinned by commit hash.

---

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Creating auth user but forgetting `brand_members` | 403 "User has no associated brand" | Insert the membership row |
| Topics left empty | Research returns nothing relevant | Set at least 3–5 specific topics |
| No RSS sources or search key | Research runs but finds nothing | Add `rss_sources` or configure `SERPER_API_KEY` |
| `SCHEDULER_BRAND_ID` not set | Scheduler jobs fail for multi-brand | Set the env variable or leave empty for fan-out to all brands |
| Social accounts not connected in Postiz | Publish fails with "no active integration" | Complete OAuth in Postiz UI first |
