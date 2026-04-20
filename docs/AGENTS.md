# Agents

The platform uses database-driven agent configuration instead of hardcoded prompt identities.

## Core Model

Two tables define agent behavior:

- `agent_configs`: one record per tenant and agent key
- `agent_skills`: optional skills attached to a target agent

Version history is stored in:

- `agent_config_versions`

Primary implementation files:

- [`python/src/content_engine/agents/agent_loader.py`](/Users/claw/Progetti/ai-automation/python/src/content_engine/agents/agent_loader.py)
- [`python/src/content_engine/api/routes_agents.py`](/Users/claw/Progetti/ai-automation/python/src/content_engine/api/routes_agents.py)

## Supported Agent Keys

The CRUD layer currently validates these keys:

- `writer`
- `editor`
- `adapter`
- `god_advocate`
- `god_factcheck`
- `god_creative`
- `god_synthesis`

If you add new runtime agents in code, you must also update the validation layer and the migration strategy.

## How Agent Resolution Works

At runtime the backend:

1. resolves the tenant from the authenticated request
2. loads the matching agent config
3. merges any applicable skills
4. runs the requested operation with that prompt context

This allows each tenant to keep its own:

- writing style
- review thresholds
- formatting rules
- adaptation logic

## CRUD Endpoints

Available backend routes:

- `GET /api/v1/agent-configs`
- `POST /api/v1/agent-configs`
- `GET /api/v1/agent-configs/{config_id}`
- `PUT /api/v1/agent-configs/{config_id}`
- `DELETE /api/v1/agent-configs/{config_id}`
- `GET /api/v1/agent-skills`
- `POST /api/v1/agent-skills`
- `GET /api/v1/agent-skills/{skill_id}`
- `PUT /api/v1/agent-skills/{skill_id}`
- `DELETE /api/v1/agent-skills/{skill_id}`

All of them are tenant-scoped.

## Operational Guidance

- Keep `agent_key` stable because code paths depend on it.
- Prefer skill records for incremental behavior changes.
- Use config replacement only for identity-level changes.
- Treat the database as the source of truth for prompts, not the README or comments.
