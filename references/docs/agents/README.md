# Agent Identity System — Complete Implementation

## Overview

The AI Content Engine now features a fully dynamic, database-driven Agent Identity System. Brands can customize every AI agent's personality and skills through a comprehensive dashboard, enabling truly personalized content generation at scale.

---

## Quick Start

### For Developers

**1. Apply Migrations:**
```bash
supabase db push --linked
```

**2. Run Seed Script:**
```bash
cd python
python -m scripts.seed_agent_system
```

**3. Run Tests:**
```bash
cd python
pytest tests/test_agent_system_e2e.py -v
```

### For Brands/Administrators

**Access Dashboard:**
Navigate to `/settings/agenti` in the application

**Create Agent Identity:**
1. Select agent type (e.g., Writer, Editor)
2. Define name and personality
3. Write identity prompt
4. Click "Create"

**Add Agent Skill:**
1. Switch to "Agent Skills" tab
2. Select target agent
3. Define skill name and description
4. Write instructions
5. Set priority (high/medium/low)
6. Add optional tags
7. Click "Create"

---

## What's New

### Dynamic Agent Personalities

Previously, all agent identities were hardcoded in Python files. Now:

- ✅ Identities stored in `agent_configs` table
- ✅ Per-brand customization
- ✅ Version control support
- ✅ Instant updates via dashboard
- ✅ No code changes required

### Composable Agent Skills

Add modular capabilities to any agent:

- ✅ Skills stored in `agent_skills` table
- ✅ Priority-based execution
- ✅ Tag-based categorization
- ✅ Enable/disable per brand
- ✅ 9 default skills seeded

### Enhanced GOD System

All 4 GOD agents now use DB-loaded identities:

- ✅ Devil's Advocate — Critical guardian
- ✅ Fact-Checker — Factual truth sentinel
- ✅ Creative Director — Engagement alchemist
- ✅ Synthesizer — Final orchestrator

### Real Feedback Loop

Automatic optimization based on performance:

- ✅ Pulls metrics from Postiz API (automated daily at 06:00 UTC)
- ✅ Computes engagement scores
- ✅ Updates brand feedback_bonus (automated daily at 07:00 UTC)
- ✅ Complete audit trail
- ✅ Supabase Cron Jobs configured (migration `009_feedback_loop_cron_jobs.sql`)

See `/references/docs/cron-jobs.md` for complete setup instructions.

### Anti-Hype Gate

Few-shot learning for quality control:

- ✅ Gold examples stored per brand
- ✅ Discard examples stored per brand
- ✅ Filters low-quality content
- ✅ Improves over time

---

## System Architecture

```
User Request
    │
    ▼
┌──────────────────┐
│  Dashboard UI   │
│  /settings/agenti │
└─────┬────────┘
      │
      ▼
┌──────────────────┐
│  FastAPI Routes  │
│  /api/v1/*       │
└─────┬────────┘
      │
      ▼
┌─────────────────────────────┐
│     Agent System DB          │
│  • agent_configs            │
│  • agent_skills              │
│  • social_metrics             │
│  • feedback_loop_audit        │
└─────┬─────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│     Agent Loader (Cache)      │
│  • 5-min TTL              │
│  • Auto-invalidation         │
└─────┬─────────────────────┘
      │
      ▼
┌──────────────────┐
│  Agent System    │
│  • Writer       │
│  • Editor       │
│  • Adapter      │
│  • GOD System  │
└─────┬────────┘
      │
      ▼
┌──────────────────┐
│  Generated     │
│  Content        │
└───────────────┘
```

---

## API Reference

### Agent Configs

#### List All
```http
GET /api/v1/agent-configs?agent_key=writer&is_active=true&page=1&per_page=20
```

#### Create
```http
POST /api/v1/agent-configs
Content-Type: application/json

{
  "agent_key": "writer",
  "agent_name": "Creative Writer",
  "identity": "You are the creative voice...",
  "brand_id": "optional-uuid"
}
```

#### Update
```http
PUT /api/v1/agent-configs/{config_id}
Content-Type: application/json

{
  "identity": "Updated identity prompt...",
  "is_active": true
}
```

#### Delete
```http
DELETE /api/v1/agent-configs/{config_id}
```

### Agent Skills

#### List All
```http
GET /api/v1/agent-skills?target_agent=writer&is_active=true&page=1&per_page=20
```

#### Create
```http
POST /api/v1/agent-skills
Content-Type: application/json

{
  "target_agent": "writer",
  "skill_name": "seo_optimization",
  "description": "Optimize content for SEO",
  "instructions": "Naturally incorporate keywords...",
  "priority": "high",
  "tags": ["seo", "optimization"],
  "brand_id": "optional-uuid"
}
```

#### Update
```http
PUT /api/v1/agent-skills/{skill_id}
Content-Type: application/json

{
  "description": "Updated description...",
  "instructions": "Updated instructions...",
  "is_active": true,
  "priority": "high",
  "tags": ["seo", "new-tag"]
}
```

#### Delete
```http
DELETE /api/v1/agent-skills/{skill_id}
```

---

## Default Agent Identities

### Writer
```
You are the Writer for {brand_name} — the creative voice and
founder in digital communication. Your goal is to transform approved
research into compelling, original content that embodies our brand's
personality.
```

### Editor
```
You are the Editor for {brand_name} — the guardian of quality and
coherence. Your goal is to refine drafts into polished, error-free
content while preserving the core message.
```

### Adapter
```
You are the Adapter for {brand_name} — the multi-platform specialist.
Your goal is to seamlessly adapt content across different platforms while
maintaining brand voice.
```

### GOD Advocate
```
You are the Devil's Advocate of the GOD System for {brand_name} —
the intellectual counterweight protecting our brand from mediocrity.
Your goal is to meticulously scrutinize content, identify logical flaws,
and prevent reputational risks.
```

### GOD Fact-Checker
```
You are the Fact-Checker of the GOD System for {brand_name} —
the sentinel of factual truth. Your goal is to scrutinize every statement,
identify unverifiable claims, and prevent factual errors.
```

### GOD Creative
```
You are the Creative Director of the GOD System for {brand_name} —
the alchemist who transforms 'correct' content into 'memorable' content.
Your goal is to find hidden opportunities and elevate the narrative.
```

### GOD Synthesis
```
You are the Synthesizer of the GOD System for {brand_name} —
the orchestrator who merges contrasting perspectives into a flawless
final piece. Your goal is to balance rigorous logic, creativity,
and accuracy.
```

---

## Default Agent Skills

### Writer Skills

**seo_optimization** (high)
- Naturally incorporate relevant keywords
- Focus on semantic SEO
- Avoid keyword stuffing

**brand_voice_consistency** (high)
- Maintain consistent brand voice
- Use established tone and vocabulary

**engagement_hooks** (medium)
- Create magnetic opening hooks
- Compel reader to continue
- Avoid generic openings

### Editor Skills

**clarity_enhancement** (high)
- Maximum clarity and readability
- Short paragraphs, simple language
- Remove jargon unless valuable

**cta_sharpening** (medium)
- Strong calls to action
- Specific, actionable directions
- Replace weak CTAs

**fact_verification** (high)
- Verify all factual claims
- Check statistics and data points
- Flag unsupported assertions

### Adapter Skills

**platform_compliance** (high)
- Follow platform-specific rules
- Respect character limits
- Adapt to platform conventions

**emoji_optimization** (low)
- Strategic emoji usage per platform
- LinkedIn: moderate
- Instagram: higher
- X: minimal (as bullets)

**hashtag_strategy** (medium)
- Tailor hashtags per platform
- LinkedIn: 3-5
- Instagram: 15-20
- Facebook: 1-2
- TikTok: 3-5

---

## Database Schema

### agent_configs

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| brand_id | UUID | FK to brands |
| agent_key | TEXT | writer, editor, adapter, god_advocate, etc. |
| agent_name | TEXT | Display name |
| identity | TEXT | Full identity prompt |
| is_active | BOOLEAN | Enabled/disabled |
| version | INTEGER | Version number |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update |

### agent_skills

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| brand_id | UUID | FK to brands |
| skill_name | TEXT | Skill identifier |
| target_agent | TEXT | Which agent uses this skill |
| description | TEXT | Brief description |
| instructions | TEXT | The skill prompt |
| priority | TEXT | high/medium/low |
| tags | TEXT[] | Categorization tags |
| is_active | BOOLEAN | Enabled/disabled |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update |

### social_metrics

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| draft_id | UUID | FK to content_drafts |
| platform | TEXT | Platform name |
| impressions | INTEGER | View count |
| clicks | INTEGER | Click count |
| likes | INTEGER | Like count |
| shares | INTEGER | Share count |
| comments | INTEGER | Comment count |
| saves | INTEGER | Save count |
| recorded_at | TIMESTAMPTZ | When recorded |

### feedback_loop_audit

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| brand_id | UUID | FK to brands |
| previous_bonus | NUMERIC | Old feedback bonus |
| new_bonus | NUMERIC | New feedback bonus |
| metrics_used | INTEGER | Number of metrics |
| score_delta | NUMERIC | Auto-calculated delta |
| executed_at | TIMESTAMPTZ | When executed |

### brands (modified)

| Column | Type | Description |
|--------|------|-------------|
| gold_examples | TEXT[] | Good content examples |
| discard_examples | TEXT[] | Hype content examples |

---

## Performance

### Cache Strategy
- **TTL**: 5 minutes per (brand_id, agent_type) pair
- **Invalidation**: Automatic on config updates
- **Hit Rate**: Expected >95% after warmup
- **Memory**: ~10KB per brand (7 agents × 1KB each)

### Query Performance
- **Indexes**: On (brand_id, agent_key) and (brand_id, target_agent)
- **Pagination**: All list endpoints support pagination
- **RLS**: Brand-level isolation
- **Async**: All DB operations non-blocking

### Response Times (Expected)
- List configs: <100ms
- Create config: <200ms
- List skills: <100ms
- Create skill: <200ms
- Generate content: <5s (includes LLM call)

---

## Security

### Authentication
- JWT middleware for brand scoping
- User roles: owner, editor, viewer
- Permission checks on all mutations

### Data Safety
- SQL injection protection (Supabase client)
- Input validation (Pydantic models)
- XSS prevention (auto-escaped in prompts)
- Rate limiting (PersistentRateLimitMiddleware)

### RLS Policies
- **agent_configs**: Brand isolation
- **agent_skills**: Brand isolation
- **social_metrics**: Read-only for brand members
- **feedback_loop_audit**: Read-only for brand members

---

## Monitoring

### Key Metrics to Track
1. **Cache Effectiveness**
   - Hit rate
   - Miss latency
   - Invalidations per hour

2. **API Performance**
   - Response times (p95, p99)
   - Error rates
   - Rate limit hits

3. **Content Quality**
   - Feedback bonus trends
   - GOD pass/reject rates
   - Engagement scores

4. **User Adoption**
   - Dashboard usage
   - Custom configs created
   - Skills added/modified

### Alerting
- Feedback loop failures
- Cache poisoning attempts
- API error rate spikes
- Identity loading errors

---

## Troubleshooting

### Content not using custom identity?

**Check:**
1. Config is `is_active: true`
2. Config belongs to correct brand
3. Cache hasn't expired (5-min TTL)
4. No override in code using hardcoded prompt

**Fix:**
```sql
-- Verify config exists and is active
SELECT * FROM agent_configs
WHERE brand_id = 'your-brand-id'
  AND agent_key = 'writer'
  AND is_active = true;

-- Clear cache if needed (wait 5 min or restart backend)
```

### Skills not applying?

**Check:**
1. Skill is `is_active: true`
2. Skill's `target_agent` matches the agent
3. Agent loader includes skill in prompt construction

**Fix:**
```sql
-- Verify skill configuration
SELECT * FROM agent_skills
WHERE brand_id = 'your-brand-id'
  AND target_agent = 'writer'
  AND is_active = true;
```

### Feedback loop not updating?

**Check:**
1. Postiz API credentials configured
2. Drafts have `published` status
3. `postiz_id` in draft metadata
4. Cron job scheduled

**Fix:**
```bash
# Manually trigger feedback loop
curl -X POST http://localhost:8000/api/analytics/feedback-loop \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### GOD system failing?

**Check:**
1. All 4 GOD agent configs exist
2. All configs are active
3. Draft has content to review
4. LLM credits available

**Fix:**
```sql
-- Verify GOD agents exist
SELECT agent_key, is_active FROM agent_configs
WHERE agent_key LIKE 'god_%'
ORDER BY agent_key;
```

---

## Support

### Documentation
- **Implementation Plan**: `/references/docs/agents/IMPLEMENTATION_PLAN.md`
- **Complete Guide**: `/references/docs/agents/IMPLEMENTATION_COMPLETE.md`
- **This README**: `/references/docs/agents/README.md`

### Code
- **Test Suite**: `/python/tests/test_agent_system_e2e.py`
- **Seed Script**: `/python/scripts/seed_agent_system.py`
- **API Routes**: `/python/src/content_engine/api/routes_agents.py`

### Database
- **Migration 005**: `/supabase/migrations/005_agent_system.sql`
- **Migration 007**: `/supabase/migrations/007_anti_hype_gate_columns.sql`
- **Migration 008**: `/supabase/migrations/008_feedback_loop_cron.sql`

---

## Version History

### v1.0.0 (2026-04-15)
- ✅ Phase 1: DB-based agent identities
- ✅ Phase 2: Complete CRUD API
- ✅ Phase 3: Dashboard UI
- ✅ Phase 4: Postiz integration & feedback loop
- ✅ Phase 5: E2E tests & seed data

### v0.5.0 (Previous)
- Hardcoded agent identities
- No skill system
- Basic GOD system
- Manual feedback adjustments

---

## License

Part of AI Content Engine — See project LICENSE for details.

---

## Credits

Implemented following the detailed implementation plan in:
`/references/docs/agents/IMPLEMENTATION_PLAN.md`

All 5 phases completed without interruption as requested.
