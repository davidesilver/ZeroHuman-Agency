# Phase 2 — Agent Skills DB (Planned)

> **Status**: 📋 Pianificato  
> **Prerequisito**: Phase 1 (Agent Identity System) ✅  
> **Stima**: ~2 giorni  
> **Dipendenze**: Supabase migration, FastAPI endpoint, agent_loader.py già creato

## Overview

Tabelle Supabase per configurazione agenti per brand e skills componibili,
con endpoint FastAPI per CRUD. Il `agent_loader.py` (creato in Phase 1) è già
predisposto per leggere da queste tabelle con caching TTL.

---

## 1. Migrazione SQL — `migrations/004_agent_configs.sql`

```sql
-- Agent identity configuration per brand
CREATE TABLE IF NOT EXISTS agent_configs (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id            UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  agent_key           TEXT NOT NULL,
  agent_name          TEXT NOT NULL,
  identity            TEXT NOT NULL DEFAULT '',
  task_type_override  TEXT,  -- override del task_type per questo agente+brand
  is_active           BOOLEAN NOT NULL DEFAULT true,
  version             INTEGER NOT NULL DEFAULT 1,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(brand_id, agent_key)
);

-- Versioning per rollback
CREATE TABLE IF NOT EXISTS agent_config_versions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_id   UUID NOT NULL REFERENCES agent_configs(id) ON DELETE CASCADE,
  identity    TEXT NOT NULL,
  version     INTEGER NOT NULL,
  changed_by  TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Agent skills con conflict detection
CREATE TABLE IF NOT EXISTS agent_skills (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  skill_name      TEXT NOT NULL,
  target_agent    TEXT NOT NULL,
  priority        TEXT NOT NULL DEFAULT 'medium'
                  CHECK (priority IN ('high', 'medium', 'low')),
  instructions    TEXT NOT NULL DEFAULT '',
  tags            TEXT[] DEFAULT '{}',
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agent_configs_brand ON agent_configs(brand_id, agent_key);
CREATE INDEX IF NOT EXISTS idx_agent_skills_brand ON agent_skills(brand_id, target_agent);

-- RLS Policies (brand isolation)
ALTER TABLE agent_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_skills ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_configs_brand_isolation ON agent_configs
  USING (brand_id = auth_user_brand_id());

CREATE POLICY agent_skills_brand_isolation ON agent_skills
  USING (brand_id = auth_user_brand_id());

-- Seed 7 agenti per ogni brand esistente
INSERT INTO agent_configs (brand_id, agent_key, agent_name, identity)
SELECT 
  b.id, a.agent_key, a.agent_name, a.default_identity
FROM brands b
CROSS JOIN (VALUES
  ('writer',        'Writer',           'Sei il Writer del brand — il braccio destro del founder nella comunicazione digitale.'),
  ('editor',        'Editor',           'Sei l''Editor — il guardiano della qualità e della coerenza del brand.'),
  ('adapter',       'Adapter',          'Sei l''Adapter — lo specialista multi-piattaforma del brand.'),
  ('god_advocate',  'GOD Advocate',     'Sei l''Avvocato del Diavolo del GOD System — il contrappeso intellettuale.'),
  ('god_factcheck', 'GOD Fact-Checker', 'Sei il Fact-Checker del GOD System — la sentinella della verità fattuale.'),
  ('god_creative',  'GOD Creative',     'Sei il Direttore Creativo del GOD System — l''alchimista del contenuto.'),
  ('god_synthesis', 'GOD Synthesis',    'Sei il Sintetizzatore del GOD System — il maestro d''orchestra finale.')
) AS a(agent_key, agent_name, default_identity)
ON CONFLICT (brand_id, agent_key) DO NOTHING;
```

---

## 2. Endpoint FastAPI

### File: `python/src/content_engine/api/routes.py`

```python
# ── Agent Config CRUD ────────────────────────────────────────────────────────

@router.get("/agents/{brand_id}/configs")
async def get_agent_configs(brand_id: str):
    """Get all agent configurations for a brand."""
    db = get_db()
    configs = db.table("agent_configs") \
        .select("*") \
        .eq("brand_id", brand_id) \
        .order("agent_key") \
        .execute()
    skills = db.table("agent_skills") \
        .select("*") \
        .eq("brand_id", brand_id) \
        .order("created_at") \
        .execute()
    return {"configs": configs.data, "skills": skills.data}


@router.put("/agents/{brand_id}/configs/{agent_key}")
async def update_agent_identity(brand_id: str, agent_key: str, body: dict):
    """Update an agent's identity for a brand."""
    db = get_db()
    identity = body.get("identity", "")
    task_type_override = body.get("task_type_override")
    
    # Save version for rollback
    current = db.table("agent_configs") \
        .select("id, identity, version") \
        .eq("brand_id", brand_id) \
        .eq("agent_key", agent_key) \
        .single().execute()
    
    if current.data:
        db.table("agent_config_versions").insert({
            "config_id": current.data["id"],
            "identity": current.data["identity"],
            "version": current.data["version"],
            "changed_by": "dashboard",  # TODO: inject from JWT
        }).execute()
    
    # Update config
    new_version = (current.data["version"] if current.data else 0) + 1
    result = db.table("agent_configs").update({
        "identity": identity,
        "task_type_override": task_type_override,
        "version": new_version,
        "updated_at": "now()",
    }).eq("brand_id", brand_id).eq("agent_key", agent_key).execute()
    
    # Invalidate cache
    from ..agents.agent_loader import invalidate_agent_cache
    invalidate_agent_cache(brand_id, agent_key)
    
    return result.data[0] if result.data else {"ok": True}


@router.post("/agents/{brand_id}/skills")
async def add_agent_skill(brand_id: str, body: dict):
    """Add a skill to an agent for a brand."""
    db = get_db()
    result = db.table("agent_skills").insert({
        "brand_id": brand_id,
        "skill_name": body["skill_name"],
        "target_agent": body["target_agent"],
        "priority": body.get("priority", "medium"),
        "instructions": body["instructions"],
        "tags": body.get("tags", []),
    }).execute()
    
    # Invalidate cache for the target agent
    from ..agents.agent_loader import invalidate_agent_cache
    invalidate_agent_cache(brand_id, body["target_agent"])
    
    return result.data[0]


@router.delete("/agents/skills/{skill_id}")
async def delete_agent_skill(skill_id: str):
    """Delete a skill."""
    db = get_db()
    # Get brand/agent info before delete for cache invalidation
    skill = db.table("agent_skills") \
        .select("brand_id, target_agent") \
        .eq("id", skill_id) \
        .single().execute()
    
    db.table("agent_skills").delete().eq("id", skill_id).execute()
    
    if skill.data:
        from ..agents.agent_loader import invalidate_agent_cache
        invalidate_agent_cache(skill.data["brand_id"], skill.data["target_agent"])
    
    return {"ok": True}


@router.post("/agents/{brand_id}/configs/{agent_key}/rollback")
async def rollback_agent_identity(brand_id: str, agent_key: str, body: dict):
    """Rollback an agent's identity to a previous version."""
    db = get_db()
    target_version = body.get("version")
    
    config = db.table("agent_configs") \
        .select("id") \
        .eq("brand_id", brand_id) \
        .eq("agent_key", agent_key) \
        .single().execute()
    
    if not config.data:
        raise HTTPException(404, "Agent config not found")
    
    history = db.table("agent_config_versions") \
        .select("*") \
        .eq("config_id", config.data["id"]) \
        .eq("version", target_version) \
        .single().execute()
    
    if not history.data:
        raise HTTPException(404, f"Version {target_version} not found")
    
    db.table("agent_configs").update({
        "identity": history.data["identity"],
        "updated_at": "now()",
    }).eq("id", config.data["id"]).execute()
    
    from ..agents.agent_loader import invalidate_agent_cache
    invalidate_agent_cache(brand_id, agent_key)
    
    return {"ok": True, "rolled_back_to": target_version}
```

---

## 3. Wiring nel Runtime degli Agenti

Una volta che le tabelle esistono, il `agent_loader.py` (già creato) le legge automaticamente.
Il passo finale è wiring nelle funzioni degli agenti:

```python
# Esempio: writer.py aggiornato per Phase 2
async def generate_draft(brand_id, research_item_id, platform="linkedin", content_type="post"):
    from .agent_loader import get_agent_identity, get_task_type_override
    
    # Carica identità dal DB (o fallback hardcoded)
    identity = await get_agent_identity(brand_id, "writer")
    task_override = await get_task_type_override(brand_id, "writer")
    
    # Inject le variabili specifiche del task
    prompt = identity.format(
        brand_name=brand_data.get("name", ""),
        tone_rules=tone_rules,
        principles=principles_text,
        title=title, source_name=source_name,
        summary=summary, platform=platform,
        content_type=content_type,
        length_hint=PLATFORM_LENGTH.get(platform, "medio"),
    )
    
    result = await call_llm(
        prompt=prompt,
        brand_id=brand_id,
        context="writer_agent",
        action="generate_draft",
        task_type=task_override or "creative",  # override dal DB se configurato
    )
```

---

## 4. Conflict Detection per Skills

Quando si aggiungono skills, il sistema verifica automaticamente conflitti:

```python
CONFLICTING_TAGS = {
    frozenset({"formale", "informale"}),
    frozenset({"breve", "lungo"}),
    frozenset({"aggressivo", "pacato"}),
    frozenset({"tecnico", "divulgativo"}),
}

def check_skill_conflicts(brand_id: str, target_agent: str, new_tags: list[str]) -> list[str]:
    """Check if new skill conflicts with existing ones."""
    db = get_db()
    existing = db.table("agent_skills") \
        .select("skill_name, tags") \
        .eq("brand_id", brand_id) \
        .eq("target_agent", target_agent) \
        .eq("is_active", True) \
        .execute()
    
    warnings = []
    all_existing_tags = set()
    for s in existing.data:
        all_existing_tags.update(s.get("tags", []))
    
    combined = all_existing_tags | set(new_tags)
    for conflict_pair in CONFLICTING_TAGS:
        if conflict_pair.issubset(combined):
            warnings.append(
                f"⚠️ Tags conflittuali trovati: {' vs '.join(conflict_pair)}"
            )
    
    return warnings
```

---

## 5. Checklist Implementazione Phase 2

- [ ] Creare migrazione SQL `004_agent_configs.sql`
- [ ] Eseguire migrazione su Supabase
- [ ] Aggiungere endpoint FastAPI nel router
- [ ] Implementare conflict detection
- [ ] Wire `agent_loader` dentro `writer.py`, `editor.py`, `adapter.py`, `god_system.py`
- [ ] Test: verifica che DB override funziona
- [ ] Test: verifica fallback a hardcoded quando DB è vuoto
- [ ] Test: verifica cache invalidation dopo update

---

## Appendice: Schema ER

```
brands (1) ──────┬──── (N) agent_configs ──── (N) agent_config_versions
                 │
                 └──── (N) agent_skills
```

→ Precedente: [Phase 1: Agent Identity System](./AGENT_IDENTITY_SYSTEM.md)  
→ Successivo: [Phase 3: Agent Dashboard UI](./AGENT_DASHBOARD_UI.md)
