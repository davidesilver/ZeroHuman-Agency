# Agent System

The platform uses a database-driven agent configuration model. Agent identities, tone, and skills are stored per tenant in the database and loaded at runtime — you can customize every agent's behavior per brand without touching code or redeploying.

---

## Concepts

### Agent identity

An **agent identity** is a system prompt that defines who an agent is: its persona, objectives, constraints, writing style, and decision rules. Identities are stored in the `agent_configs` table, one record per tenant per agent key.

### Agent skills

**Skills** are modular instruction blocks attached to an agent. They are concatenated after the identity prompt and let you compose behavior without rewriting the full identity. Examples: "always end posts with a question", "prioritize data-driven openings", "never use passive voice".

Skills are stored in `agent_skills`, ordered by `priority`, and loaded alongside the identity at runtime.

### Fallback behavior

If no database configuration exists for a given agent, the system falls back to hardcoded default prompts. This means the platform works out of the box on a fresh database and you can customize incrementally.

---

## Agent keys

| Key | Role in pipeline |
|---|---|
| `writer` | Produces the initial draft from a research item |
| `editor` | Refines the writer's draft for tone, flow, and grammar |
| `adapter` | Rewrites a draft for a different target platform |
| `god_advocate` | Critical analysis agent in GOD mode review |
| `god_factcheck` | Fact-verification agent in GOD mode review |
| `god_creative` | Enhancement suggestions agent in GOD mode review |
| `god_synthesis` | Produces final verdict (pass / needs revision / reject) |
| `humanizer` | Removes AI patterns and re-applies brand voice |

---

## GOD mode review

GOD mode runs four agents sequentially on a single draft. Each agent sees the full draft and the output of agents that ran before it.

```
draft
  ↓
god_advocate   → critique, weaknesses, strengths, score
  ↓
god_factcheck  → claim verification, issues list
  ↓
god_creative   → enhancement suggestions, alternative angles
  ↓
god_synthesis  → final verdict + rationale
                 pass | needs_revision | reject
```

The synthesis verdict gates the humanizer: only drafts that pass move to humanization.

---

## Humanizer

The humanizer runs a double-pass refinement:

1. **Pass 1** — Strips AI-specific patterns (filler phrases, hedging, passive constructions, hollow affirmations). Applies voice calibration using `gold_examples` and top-performing drafts from the brand's history.
2. **Pass 2** — Anti-AI audit. Checks the output of Pass 1 and runs a final refinement to catch anything that slipped through.

The humanizer only activates when:
- `brands.use_humanizer = true` for the brand
- The target platform is in `brands.humanizer_channels`
- The GOD mode verdict is `pass` (if GOD mode was run)

---

## Runtime resolution

```
Request arrives with brand_id
        ↓
agent_loader.get_agent_identity(brand_id, agent_key)
        ↓
Check in-memory TTL cache (5 min per brand+key)
        ↓ cache miss
Query agent_configs WHERE brand_id = ? AND agent_key = ? AND is_active = true
        ↓ no DB record
Use hardcoded default prompt (fallback)
        ↓
Append skills from agent_skills WHERE brand_id = ? AND target_agent = ?
        ORDER BY priority ASC AND is_active = true
        ↓
Return: identity_prompt + "\n\n## Active Skills\n" + skills
```

The cache is per-process and in-memory. Invalidation happens on TTL expiry (5 minutes). If you update an agent config in the database, the change takes effect within 5 minutes without restart.

---

## Database schema

### `agent_configs`

| Column | Type | Description |
|---|---|---|
| `id` | uuid | Primary key |
| `brand_id` | uuid | Tenant scope |
| `agent_key` | text | One of the supported keys above |
| `identity` | text | Full system prompt for this agent |
| `task_type_override` | text | Optional override for task routing |
| `is_active` | boolean | Soft-disable without deleting |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

Version history is preserved in `agent_config_versions` on every update.

### `agent_skills`

| Column | Type | Description |
|---|---|---|
| `id` | uuid | Primary key |
| `brand_id` | uuid | Tenant scope |
| `target_agent` | text | Which agent this skill applies to |
| `skill_name` | text | Human-readable name |
| `instructions` | text | The instruction block |
| `priority` | integer | Lower = applied first |
| `is_active` | boolean | Soft-disable |

---

## API

Agent configs and skills are managed via authenticated REST endpoints.

### Agent configs

```
GET    /api/v1/agent-configs              # list all configs for the active brand
POST   /api/v1/agent-configs              # create a config
GET    /api/v1/agent-configs/:id          # get one config
PATCH  /api/v1/agent-configs/:id          # update (saves version history)
DELETE /api/v1/agent-configs/:id          # soft-delete (sets is_active=false)
```

### Agent skills

```
GET    /api/v1/agent-skills               # list all skills for the active brand
POST   /api/v1/agent-skills               # create a skill
GET    /api/v1/agent-skills/:id           # get one skill
PATCH  /api/v1/agent-skills/:id           # update
DELETE /api/v1/agent-skills/:id           # soft-delete
```

All endpoints require an authenticated session. The `brand_id` is resolved from the session token — you cannot manage another tenant's agents.

---

## Example: customizing the writer

**Create a writer identity for a brand:**

```bash
curl -X POST http://localhost:3000/api/v1/agent-configs \
  -H "Authorization: Bearer <session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "writer",
    "identity": "You are a senior content strategist writing for operators and founders. You write in first person, use specific numbers when available, and always open with a concrete observation rather than a generic statement."
  }'
```

**Add a skill to that writer:**

```bash
curl -X POST http://localhost:3000/api/v1/agent-skills \
  -H "Authorization: Bearer <session-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "target_agent": "writer",
    "skill_name": "Close with a question",
    "instructions": "End every post with a single open question that invites the reader to share their experience or opinion. The question must be directly related to the post content, not generic.",
    "priority": 10
  }'
```

The next time the writer agent runs for this brand, it will use the custom identity and append the skill instruction.

---

## Extending to new agent keys

1. Add the new key to the `VALID_AGENT_KEYS` set in `routes_agents.py`.
2. Implement the agent logic in `python/src/content_engine/agents/`.
3. Call `agent_loader.get_agent_identity(brand_id, "your_key")` to load the identity.
4. Add a hardcoded fallback prompt in the agent module for tenants without DB configuration.

No migrations needed unless you want to store the key as an enum (currently stored as text with application-layer validation).
