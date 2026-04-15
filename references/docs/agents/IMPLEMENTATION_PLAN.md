# AI Content Engine — Agent System Implementation Plan

> **Status**: 🚀 In corso  
> **Version**: 1.0  
> **Data creazione**: 2026-04-15  
> **Stima completamento**: 3 settimane (fase 0-2), 6 settimane (tutte le fasi)

---

## 📋 Executive Summary

Questo piano implementa il sistema Agent System documentato in AGENTS.md, risolvendo i bug critici identificati nell'analisi di perplexity e seguendo un approccio data-driven.

**Metriche obiettivo**:
- Bug critici risolti: 100% (5 bug identificati)
- Copertura implementazione vs documentazione: dal 20% attuale al 80%
- Test coverage: >80% per agenti core
- Tempo di ciclo: fix → test → deploy → validare < 4 ore

---

## 🗺️ Strategia di Implementazione

### Principi Guida

1. **Fix Before Feature** — Tutti i bug bloccanti devono essere risolti prima di nuove feature
2. **Small Batches** — Ogni fase produce codice testabile in produzione
3. **Graceful Degradation** — Il sistema deve funzionare anche se DB tabelle non esistono
4. **Data-First** — Ogni feature ha metriche di successo verificabili
5. **Incremental Value** — Ogni fase aggiunge valore misurabile immediato

### Pattern Tecnici

- **Error Wrapping** — Try/except con logging e fallback
- **Type Hints** — Tutti gli agenti hanno signature ben definite
- **Cache Invalidation** — Invalidate dopo ogni update DB
- **Audit Trail** — Tutte le modifiche sono tracciabili
- **Rate Limiting** — Protezione contro abuso API

---

## 📦 FASE 0 — Fix Bug Critici (Blockers)

**Durata**: 1 giorno | **Priorità**: 🔥 Critica | **Dipendenze**: Nessuna | **Output**: Engine funzionante

### Obiettivo

Risolvere i 5 bug che bloccano il funzionamento base del sistema.

---

### 🐛 Bug 0.1: Fix `score_item()` crash

**Problema**: Variabile `brand_data` non definita in `score_item()` → `NameError`  
**File**: `python/src/content_engine/scoring/engine.py`  
**Riga**: 166-167

**Fix**:
```python
# PRIMA della funzione score_item(), aggiungere:
db = get_db()
brand = db.table("brands").select("*").eq("id", brand_id).single().execute()
brand_data = brand.data
```

**Test**:
```bash
# Genera un item di test e verifica che scoring non crasha
pytest tests/test_scoring.py::test_score_item_not_crash
```

**Metrica successo**: scoring run completa senza NameError

---

### 🐛 Bug 0.2: Export `generate_content` da writer.py

**Problema**: `auto_optimizer.py` importa `generate_content` che non è esportato  
**File**: `python/src/content_engine/agents/writer.py`  
**Riga**: 89-153 (aggiungere `__all__`)

**Fix**:
```python
# Alla fine di writer.py, aggiungere:
__all__ = ["WRITER_PROMPT", "generate_draft"]
```

**Test**:
```bash
pytest tests/test_writer.py::test_generate_content_importable
```

**Metrica successo**: Auto-optimizer può importare e chiamare generate_draft

---

### 🐛 Bug 0.3: Fix `founder_principles` lookup

**Problema**: Scorretta di fallback quando campo JSONB è vuoto  
**File**: `python/src/content_engine/scoring/engine.py`  
**Riga**: 136-137

**Fix**:
```python
principles = brand.get("founder_principles") or \
             (brand.get("scoring_weights") or {}).get("founder_principles", [])
```

**Test**:
```bash
pytest tests/test_scoring.py::test_founder_principles_fallback
```

**Metrica successo**: Scoring funziona con entrambe le colonne DB

---

### 🐛 Bug 0.4: Fix `feedback_bonus` injection

**Problema**: LLM suggerisce 5.0, ma il valore deve venire dal DB  
**File**: `python/src/content_engine/scoring/engine.py`  
**Riga**: 165-167 (rimuovere prompt injection)

**Fix**:
```python
# RIMUOVERE "feedback_bonus": 5.0 dal prompt SCORING_PROMPT (riga 42)

# DOPO il parsing della risposta LLM, aggiungere:
brand_data = db.table("brands").select("feedback_bonus").eq("id", brand_id).single().execute()
feedback_bonus = (brand_data.data or {}).get("feedback_bonus", 5.0)
parsed["feedback_bonus"] = feedback_bonus
```

**Test**:
```bash
pytest tests/test_scoring.py::test_feedback_bonus_from_db
```

**Metrica successo**: `feedback_bonus` varia in base al DB, non hardcoded

---

### 🐛 Bug 0.5: Add DB columns for Anti-Hype Gate

**Problema**: Anti-Hype Gate in "zero-shot mode" → fragile  
**File**: `supabase/migrations/007_anti_hype_gate_columns.sql` (NUOVO)

**SQL**:
```sql
-- Migration: 007_anti_hype_gate_columns.sql
-- Purpose: Add gold/discard examples for few-shot anti-hype learning

ALTER TABLE brands
  ADD COLUMN IF NOT EXISTS gold_examples text[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS discard_examples text[] DEFAULT '{}';

COMMENT ON COLUMN brands.gold_examples IS 
  'Examples of GOOD content that passes the anti-hype gate. Used for few-shot learning.';

COMMENT ON COLUMN brands.discard_examples IS 
  'Examples of HYPE content that should be blocked. Used for few-shot learning.';
```

**Esecuzione**:
```bash
supabase migration apply --project-id <PROJECT_ID> supabase/migrations/007_anti_hype_gate_columns.sql
```

**Test**:
```bash
pytest tests/test_anti_hype_gate.py::test_gate_reads_examples
```

**Metrica successo**: Gate legge examples dal DB invece di liste vuote

---

### ✅ Checklist Fase 0

- [ ] Fix `score_item()` NameError
- [ ] Export `generate_draft` da writer.py
- [ ] Fix `founder_principles` fallback
- [ ] Fix `feedback_bonus` injection
- [ ] Crea migration 007 per Anti-Hype Gate
- [ ] Tutti i test passano
- [ ] Run scoring end-to-end su 10 item
- [ ] Verifica nei log che `feedback_bonus` varia

**Metrica fase completata**: Scoring engine funziona senza crash

---

## 📦 FASE 1 — Wire DB System agli Agenti

**Durata**: 2-3 giorni | **Priorità**: 🔴 Alta | **Dipendenze**: Fase 0 | **Output**: Agenti leggono al DB

### Obiettivo

Connettere il sistema di agenti alle tabelle DB create in Fase 1 (Phase 1). Gli agenti devono leggere le configurazioni dal DB invece di usare solo fallback hardcoded.

---

### 🔗 Task 1.1: Aggiorna `writer.py` per usare `get_agent_identity()`

**File**: `python/src/content_engine/agents/writer.py`  
**Modifiche**:

```python
# AGGIUNGI import:
from .agent_loader import get_agent_identity

# NELLA funzione generate_draft(), SOSTITUIRE:
prompt = WRITER_PROMPT.format(
    # ... esistenti parametri ...
)

# DOPO, SOSTITUIRE con:
# 1. Carica identità dal DB (o fallback hardcoded)
identity = await get_agent_identity(brand_id, "writer")

# 2. Sostituisce <identity> nella prima riga del prompt
full_prompt = identity + prompt

raw_res = await call_llm(
    prompt=full_prompt,  # Usa full_prompt invece di prompt
    brand_id=brand_id,
    context="writer_agent",
    action="generate_draft",
    task_type="creative"
)
```

**Test**:
```bash
# Test fallback hardcoded
pytest tests/test_writer.py::test_writer_hardcoded_identity

# Test DB-based identity
pytest tests/test_writer.py::test_writer_db_identity
```

**Metrica successo**: Writer usa identità dal DB se configurata

---

### 🔗 Task 1.2: Aggiorna `editor.py` per usare `get_agent_identity()`

**File**: `python/src/content_engine/agents/editor.py`  
**Modifiche**: Stesso pattern di Task 1.1

```python
from .agent_loader import get_agent_identity

# In edit_draft(), aggiungere:
identity = await get_agent_identity(brand_id, "editor")
full_prompt = identity + EDITOR_PROMPT.format(...)
```

**Test**:
```bash
pytest tests/test_editor.py::test_editor_db_identity
```

**Metrica successo**: Editor usa identità dal DB

---

### 🔗 Task 1.3: Aggiorna `adapter.py` per usare `get_agent_identity()`

**File**: `python/src/content_engine/agents/adapter.py`  
**Modifiche**: Stesso pattern

```python
from .agent_loader import get_agent_identity

identity = await get_agent_identity(brand_id, "adapter")
full_prompt = identity + ADAPTER_PROMPT.format(...)
```

**Test**:
```bash
pytest tests/test_adapter.py::test_adapter_db_identity
```

**Metrica successo**: Adapter usa identità dal DB

---

### 🔗 Task 1.4: Aggiorna `god_system.py` per usare `get_agent_identity()`

**File**: `python/src/content_engine/agents/god_system.py`  
**Modifiche**: Per ognuno dei 4 agenti GOD

```python
from .agent_loader import get_agent_identity

# In ogni funzione (advocate_content, factcheck_content, creative_content, synthesize_content):
identity = await get_agent_identity(brand_id, "god_advocate")  # o _factcheck, _creative, _synthesis
full_prompt = identity + GOD_PROMPT.format(...)
```

**Test**:
```bash
pytest tests/test_god_system.py::test_god_agents_db_identity
```

**Metrica successo**: Tutti i 4 agenti GOD usano identità dal DB

---

### 🔗 Task 1.5: Cache Invalidation Testing

**Obiettivo**: Verificare che cache invalidation funziona dopo update

**Test**:
```python
# tests/test_agent_loader.py
async def test_cache_invalid_after_update():
    # 1. Carica identità
    id1 = await get_agent_identity("brand_1", "writer")
    
    # 2. Aggiorna nel DB
    db.table("agent_configs").update({"identity": "Nuova identità"}).execute()
    invalidate_agent_cache("brand_1", "writer")
    
    # 3. Ricarica → deve essere nuovo
    id2 = await get_agent_identity("brand_1", "writer")
    
    assert "Nuova identità" in id2
```

**Metrica successo**: Cache si invalida correttamente

---

### ✅ Checklist Fase 1

- [ ] Writer usa `get_agent_identity()`
- [ ] Editor usa `get_agent_identity()`
- [ ] Adapter usa `get_agent_identity()`
- [ ] GOD System (4 agenti) usa `get_agent_identity()`
- [ ] Tutti i test fallback passano
- [ ] Tutti i test DB-based passano
- [ ] Cache invalidation test passano
- [ ] TTL cache test passano

**Metrica fase completata**: Tutti gli agenti leggono al DB con cache funzionante

---

## 📦 FASE 2 — FastAPI Endpoints per CRUD Agenti

**Durata**: 2-3 giorni | **Priorità**: 🔴 Alta | **Dipendenze**: Fase 1 | **Output**: API REST funzionante

### Obiettivo

Creare endpoint FastAPI per permettere alla dashboard Next.js di leggere/scrivere le configurazioni degli agenti.

---

### 🔌 Task 2.1: Crea `routes_agents.py`

**File**: `python/src/content_engine/api/routes_agents.py` (NUOVO)

**Endpoint 1: GET `/agents/{brand_id}/configs`**  
```python
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
```

**Endpoint 2: PUT `/agents/{brand_id}/configs/{agent_key}`**  
```python
@router.put("/agents/{brand_id}/configs/{agent_key}")
async def update_agent_identity(brand_id: str, agent_key: str, body: dict):
    """Update an agent's identity for a brand."""
    db = get_db()
    identity = body.get("identity", "")
    task_type_override = body.get("task_type_override")
    
    # Salva versione per rollback
    current = db.table("agent_configs") \
        .select("id, identity, version") \
        .eq("brand_id", brand_id) \
        .eq("agent_key", agent_key) \
        .single() \
        .execute()
    
    if current.data:
        db.table("agent_config_versions").insert({
            "config_id": current.data["id"],
            "identity": current.data["identity"],
            "version": current.data["version"],
            "changed_by": "dashboard",  # TODO: inject from JWT
        }).execute()
    
    # Aggiorna config
    new_version = (current.data["version"] if current.data else 0) + 1
    result = db.table("agent_configs").update({
        "identity": identity,
        "task_type_override": task_type_override,
        "version": new_version,
        "updated_at": "now()",
    }).eq("brand_id", brand_id).eq("agent_key", agent_key).execute()
    
    # Invalida cache
    from ..agents.agent_loader import invalidate_agent_cache
    invalidate_agent_cache(brand_id, agent_key)
    
    return result.data[0] if result.data else {"ok": True}
```

**Endpoint 3: POST `/agents/{brand_id}/skills`**  
```python
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
    
    # Invalida cache per l'agent target
    from ..agents.agent_loader import invalidate_agent_cache
    invalidate_agent_cache(brand_id, body["target_agent"])
    
    return result.data[0]
```

**Endpoint 4: DELETE `/agents/skills/{skill_id}`**  
```python
@router.delete("/agents/skills/{skill_id}")
async def delete_agent_skill(skill_id: str):
    """Delete a skill."""
    db = get_db()
    skill = db.table("agent_skills") \
        .select("brand_id, target_agent") \
        .eq("id", skill_id) \
        .single() \
        .execute()
    
    db.table("agent_skills").delete().eq("id", skill_id).execute()
    
    if skill.data:
        from ..agents.agent_loader import invalidate_agent_cache
        invalidate_agent_cache(skill.data["brand_id"], skill.data["target_agent"])
    
    return {"ok": True}
```

**Endpoint 5: POST `/agents/{brand_id}/configs/{agent_key}/rollback`**  
```python
@router.post("/agents/{brand_id}/configs/{agent_key}/rollback")
async def rollback_agent_identity(brand_id: str, agent_key: str, body: dict):
    """Rollback an agent's identity to a previous version."""
    db = get_db()
    target_version = body.get("version")
    
    config = db.table("agent_configs") \
        .select("id") \
        .eq("brand_id", brand_id) \
        .eq("agent_key", agent_key) \
        .single() \
        .execute()
    
    if not config.data:
        raise HTTPException(404, "Agent config not found")
    
    history = db.table("agent_config_versions") \
        .select("*") \
        .eq("config_id", config.data["id"]) \
        .eq("version", target_version) \
        .single() \
        .execute()
    
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

### 🔌 Task 2.2: Wire routes in `main.py`

**File**: `python/src/content_engine/api/routes.py`

```python
# Aggiungere import:
from . import routes_agents

# Aggiungere router:
api.include_router(routes_agents.router, prefix="/agents", tags=["Agents"])
```

---

### 🔌 Task 2.3: Conflict Detection per Skills

**File**: `python/src/content_engine/api/routes_agents.py`

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
            tags_str = "' vs '".join(conflict_pair)
            warnings.append(
                f"⚠️ Tags conflittuali trovati: {tags_str}"
            )
    
    return warnings
```

**Integra in endpoint POST skills**:
```python
@router.post("/agents/{brand_id}/skills")
async def add_agent_skill(brand_id: str, body: dict):
    """Add a skill to an agent for a brand."""
    # ... esistente ...
    
    # Check conflitti
    new_tags = body.get("tags", [])
    conflicts = check_skill_conflicts(brand_id, body["target_agent"], new_tags)
    
    # Return conflitti se ce ne sono
    if conflicts:
        return {
            "conflicts": conflicts,
            "warning": "Skill ha tag conflittuali con skill esistenti"
        }
    
    # ... resto del codice ...
```

---

### ✅ Checklist Fase 2

- [ ] Crea `routes_agents.py` con 5 endpoint
- [ ] Wire routes in `main.py`
- [ ] Implementa conflict detection
- [ ] Test GET /agents/{brand_id}/configs
- [ ] Test PUT /agents/{brand_id}/configs/{agent_key}
- [ ] Test POST /agents/{brand_id}/skills (con conflitti)
- [ ] Test DELETE /agents/skills/{skill_id}
- [ ] Test POST rollback
- [ ] Verifica cache invalidation dopo update

**Metrica fase completata**: API REST completa e testata per CRUD agenti

---

## 📦 FASE 3 — Next.js Dashboard UI

**Durata**: 3-4 giorni | **Priorità**: 🔴 Alta | **Dipendenze**: Fase 2 | **Output**: Dashboard funzionante

### Obiettivo

Creare la dashboard Next.js per configurare agenti e skills, come documentato in AGENT_DASHBOARD_UI.md.

---

### 🎨 Task 3.1: Setup Progetto Next.js

Se non già esistente, creare struttura:
```bash
# In /Users/claw/Progetti/ai-automation/
npx create-next-app@latest agent-dashboard --typescript --tailwind --app
cd agent-dashboard
npx install lucide-react sonner clsx tailwind-merge @radix-ui/react-slot
npx install -D @radix-ui/ui
```

---

### 🎨 Task 3.2: Crea Page Principale `/settings/agenti`

**File**: `src/app/(dashboard)/settings/agenti/page.tsx`

```typescript
'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { toast } from 'sonner'

type AgentConfig = {
  id: string
  agent_key: string
  agent_name: string
  identity: string
  task_type_override: string | null
  is_active: boolean
  version: number
}

type AgentSkill = {
  id: string
  skill_name: string
  target_agent: string
  priority: 'high' | 'medium' | 'low'
  instructions: string
  tags: string[]
}

const PYTHON_API = process.env.NEXT_PUBLIC_PYTHON_API || 'http://localhost:8000'

export default function AgentiPage() {
  // TODO: Fetch brand ID da auth
  const brandId = 'demo-brand-id'
  
  const [agents, setAgents] = useState<AgentConfig[]>([])
  const [skills, setSkills] = useState<AgentSkill[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetch(`${PYTHON_API}/agents/${brandId}/configs`)
        const data = await res.json()
        setAgents(data.configs)
        setSkills(data.skills)
      } catch (error) {
        toast.error('Errore caricamento dati')
        console.error(error)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [brandId])

  const saveIdentity = async (agentKey: string, identity: string) => {
    try {
      await fetch(`${PYTHON_API}/agents/${brandId}/configs/${agentKey}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identity }),
      })
      toast.success('Identità salvata')
    } catch (error) {
      toast.error('Errore salvataggio')
    }
  }

  const addSkill = async (skill: Partial<AgentSkill>) => {
    try {
      await fetch(`${PYTHON_API}/agents/${brandId}/skills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(skill),
      })
      toast.success('Skill aggiunta')
    } catch (error) {
      toast.error('Errore aggiunta skill')
    }
  }

  const deleteSkill = async (skillId: string) => {
    try {
      await fetch(`${PYTHON_API}/agents/skills/${skillId}`, {
        method: 'DELETE',
      })
      toast.success('Skill eliminata')
    } catch (error) {
      toast.error('Errore eliminazione skill')
    }
  }

  if (loading) return <div>Caricamento...</div>

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Agent Identities</h1>
      
      {/* Agent Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
        {agents.map((agent) => (
          <AgentCard 
            key={agent.id} 
            agent={agent} 
            onSave={saveIdentity}
          />
        ))}
      </div>

      <h2 className="text-2xl font-bold mb-4">Agent Skills</h2>
      
      {/* Skills Table */}
      <SkillsTable 
        skills={skills}
        onAdd={addSkill}
        onDelete={deleteSkill}
      />
    </div>
  )
}

function AgentCard({ agent, onSave }: { agent: AgentConfig; onSave: (key: string, identity: string) => void }) {
  const [isEditing, setIsEditing] = useState(false)
  const [localIdentity, setLocalIdentity] = useState(agent.identity)

  const handleSave = () => {
    onSave(agent.agent_key, localIdentity)
    setIsEditing(false)
  }

  return (
    <Card className="p-4">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold">{agent.agent_name}</h3>
        <Badge variant={agent.is_active ? 'default' : 'secondary'}>
          {agent.is_active ? 'ACTIVE' : 'INACTIVE'}
        </Badge>
      </div>
      
      <p className="text-sm text-gray-600 mb-2">v{agent.version}</p>
      
      {isEditing ? (
        <>
          <Textarea
            value={localIdentity}
            onChange={(e) => setLocalIdentity(e.target.value)}
            rows={6}
            className="w-full mb-2"
          />
          <div className="flex gap-2">
            <Button onClick={handleSave} size="sm">Salva</Button>
            <Button onClick={() => setIsEditing(false)} variant="ghost" size="sm">Annulla</Button>
          </div>
        </>
      ) : (
        <div className="whitespace-pre-wrap text-sm">
          {agent.identity}
        </div>
      )}
      
      {!isEditing && (
        <Button onClick={() => setIsEditing(true)} variant="outline" size="sm" className="mt-2">
          Modifica
        </Button>
      )}
    </Card>
  )
}

function SkillsTable({ skills, onAdd, onDelete }: { 
  skills: AgentSkill[]; 
  onAdd: (skill: Partial<AgentSkill>) => void; 
  onDelete: (id: string) => void 
}) {
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [newSkill, setNewSkill] = useState<Partial<AgentSkill>>({
    skill_name: '',
    target_agent: 'writer',
    priority: 'medium',
    instructions: '',
    tags: []
  })

  const handleAdd = () => {
    if (newSkill.skill_name && newSkill.instructions) {
      onAdd(newSkill)
      setIsDialogOpen(false)
      setNewSkill({
        skill_name: '',
        target_agent: 'writer',
        priority: 'medium',
        instructions: '',
        tags: []
      })
    }
  }

  return (
    <Card className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Skills</h3>
        <Button onClick={() => setIsDialogOpen(true)} size="sm">
          + Aggiungi Skill
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Skill Name</TableHead>
            <TableHead>Target Agent</TableHead>
            <TableHead>Priority</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {skills.map((skill) => (
            <TableRow key={skill.id}>
              <TableCell>{skill.skill_name}</TableCell>
              <TableCell>{skill.target_agent}</TableCell>
              <TableCell>
                <Badge variant={
                  skill.priority === 'high' ? 'destructive' : 
                  skill.priority === 'medium' ? 'default' : 'secondary'
                }>
                  {skill.priority}
                </Badge>
              </TableCell>
              <TableCell>
                <Button 
                  onClick={() => onDelete(skill.id)} 
                  variant="ghost" 
                  size="sm"
                >
                  🗑️
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Add Skill Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Aggiungi Skill</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Input
              placeholder="Skill name"
              value={newSkill.skill_name}
              onChange={(e) => setNewSkill({...newSkill, skill_name: e.target.value})}
            />
            <select 
              value={newSkill.target_agent}
              onChange={(e) => setNewSkill({...newSkill, target_agent: e.target.value})}
            >
              <option value="writer">Writer</option>
              <option value="editor">Editor</option>
              <option value="adapter">Adapter</option>
              <option value="god_advocate">GOD Advocate</option>
              <option value="god_factcheck">GOD Fact-Checker</option>
              <option value="god_creative">GOD Creative</option>
              <option value="god_synthesis">GOD Synthesis</option>
            </select>
            <select 
              value={newSkill.priority}
              onChange={(e) => setNewSkill({...newSkill, priority: e.target.value as any})}
            >
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <Textarea
              placeholder="Instructions"
              value={newSkill.instructions}
              onChange={(e) => setNewSkill({...newSkill, instructions: e.target.value})}
              rows={4}
            />
            <Input 
              placeholder="Tags (comma separated)"
              onChange={(e) => setNewSkill({...newSkill, tags: e.target.value.split(',').map(t => t.trim())})}
            />
            <div className="flex justify-end gap-2">
              <Button onClick={() => setIsDialogOpen(false)} variant="ghost">
                Annulla
              </Button>
              <Button onClick={handleAdd}>Aggiungi</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
```

---

### 🎨 Task 3.3: Setup Shadcn/ui Components

```bash
cd agent-dashboard
npx shadcn@latest init
```

**Componenti richiesti**:
- button
- card
- input
- textarea
- dialog
- table
- badge

---

### 🎨 Task 3.4: Configura Environment

**File**: `.env.local`

```env
NEXT_PUBLIC_PYTHON_API=http://localhost:8000
```

---

### 🎨 Task 3.5: Integra con Dashboard Esistente

Se hai già una dashboard Next.js, aggiungi la voce al sidebar:

```typescript
// Nel tuo sidebar component:
{
  label: 'Agenti',
  href: '/settings/agenti',
  icon: Sparkles,  // o icona appropriata
  badge: 'NEW',
}
```

---

### ✅ Checklist Fase 3

- [ ] Setup progetto Next.js
- [ ] Installa dipendenze (shadcn/ui, lucide-react, sonner)
- [ ] Crea page.tsx principale
- [ ] Crea AgentCard component
- [ ] Crea SkillsTable component
- [ ] Crea AddSkillDialog component
- [ ] Test fetch dati API
- [ ] Test salvataggio identità
- [ ] Test aggiunta skill
- [ ] Test eliminazione skill
- [ ] Integra in dashboard esistente
- [ ] Responsive design su mobile

**Metrica fase completata**: Dashboard funzionante con CRUD completo

---

## 📦 FASE 4 — Postiz Integration (Feedback Loop Reale)

**Durata**: 4-5 giorni | **Priorità**: 🔴 Alta | **Dipendenze**: Fase 3 | **Output**: Loop funzionante

### Obiettivo

Integrare Postiz API per ottenere metriche engagement reali e aggiornare `feedback_bonus` automaticamente.

---

### 🔌 Task 4.1: Configura API Postiz

**File**: `python/src/content_engine/config.py`

```python
class Settings(BaseSettings):
    # ... esistente ...
    
    # AGGIUNGI:
    postiz_base_url: str = "https://api.postiz.com"
    postiz_api_key: str = ""  # TODO: from env
```

---

### 🔌 Task 4.2: Implementa Pull Metriche

**File**: `python/src/content_engine/services/postiz_analytics.py`

```python
"""Postiz Analytics Service — pulls engagement metrics for published posts."""

import httpx
import logging
from typing import List, Dict, Any

from ..config import settings
from ..db import get_db

logger = logging.getLogger(__name__)

async def pull_brand_metrics(brand_id: str) -> Dict[str, Any]:
    """
    Pull Postiz analytics for all published posts of a brand.
    
    Updates the social_metrics table with engagement data.
    """
    db = get_db()
    
    # Get published drafts with Postiz IDs
    drafts_resp = (
        db.table("content_drafts")
        .select("id, metadata")
        .eq("brand_id", brand_id)
        .eq("status", "published")
        .not_.like("metadata", "%fake_postiz_id%")  # Skip fake/test IDs
        .execute()
    )
    
    pulled = 0
    errors = []
    
    for draft in drafts_resp.data:
        draft_id = draft["id"]
        postiz_id = draft.get("metadata", {}).get("postiz_id")
        
        if not postiz_id:
            continue
        
        try:
            # Call Postiz Analytics API
            resp = await httpx_client.get(
                f"{settings.postiz_base_url}/public/v1/analytics/post/{postiz_id}",
                headers={
                    "Authorization": f"Bearer {settings.postiz_api_key}",
                },
                params={"date": "7"},  # Last 7 days
            )
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Save to social_metrics table
                db.table("social_metrics").insert({
                    "content_draft_id": draft_id,
                    "platform": data.get("platform"),
                    "impressions": data.get("impressions", 0),
                    "likes": data.get("likes", 0),
                    "shares": data.get("shares", 0),
                    "comments": data.get("comments", 0),
                    "created_at": "now()",
                }).execute()
                
                pulled += 1
            else:
                logger.warning(f"Failed to fetch metrics for post {postiz_id}: {resp.status_code}")
                errors.append(f"post {postiz_id}: HTTP {resp.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching metrics for draft {draft_id}: {e}")
            errors.append(f"draft {draft_id}: {str(e)}")
    
    return {
        "pulled": pulled,
        "errors": errors,
        "total": len(drafts_resp.data),
    }
```

---

### 🔌 Task 4.3: Implementa Calcolo Engagement Score

**File**: `python/src/content_engine/services/feedback_loop.py`

```python
"""Feedback Loop Service — computes feedback_bonus from engagement data."""

import math
from typing import List, Dict

from ..db import get_db

def compute_engagement_score(metrics: List[Dict]) -> float:
    """
    Compute engagement score from social metrics.
    
    Formula with time decay and platform normalization.
    """
    PLATFORM_BASELINE = {
        "linkedin": 0.02,
        "instagram": 0.04,
        "tiktok": 0.06,
    }
    
    weighted = []
    
    for m in metrics:
        impressions = m.get("impressions", 0)
        
        # Skip posts with < 100 impressions (not enough data)
        if impressions < 100:
            continue
        
        platform = m.get("platform", "linkedin")
        baseline = PLATFORM_BASELINE.get(platform, 0.02)
        
        # Engagement rate: weighted for action type
        eng_rate = (
            m.get("likes", 0) +
            m.get("comments", 0) * 3 +
            m.get("shares", 0) * 5
        ) / impressions
        
        # Normalize against platform baseline
        normalized = eng_rate / baseline  # 1.0 = average for platform
        
        # Time decay: 30 days ago posts weigh 22% of today's
        days_ago = (datetime.utcnow() - m["created_at"]).days
        weight = math.exp(-0.05 * days_ago)
        
        weighted.append(normalized * weight)
    
    if not weighted:
        return 5.0
    
    avg = sum(weighted) / len(weighted)
    
    # Scale to 0-10, center at 5.0
    return min(10.0, max(0.0, round(5.0 + avg * 2.5, 2)))

async def update_feedback_bonus(brand_id: str) -> Dict[str, Any]:
    """
    Update feedback_bonus for a brand based on recent performance.
    
    Computes engagement score for last 30 days and updates brands table.
    """
    db = get_db()
    
    # Get metrics for last 30 days
    metrics_resp = (
        db.table("social_metrics")
        .select("sm.*")
        .eq("brand_id", brand_id)  # Assumes social_metrics has brand_id via join
        .gte("created_at", "now() - interval '30 days'")
        .execute()
    )
    
    metrics = metrics_resp.data
    
    # Compute engagement score
    engagement_score = compute_engagement_score(metrics)
    
    # Update brands table
    db.table("brands").update({
        "feedback_bonus": engagement_score,
        "updated_at": "now()",
    }).eq("id", brand_id).execute()
    
    return {
        "brand_id": brand_id,
        "metrics_count": len(metrics),
        "engagement_score": engagement_score,
    }
```

---

### 🔌 Task 4.4: Crea Cron Job

**File**: `supabase/migrations/008_feedback_loop_cron.sql` (NUOVO)

```sql
-- Migration: 008_feedback_loop_cron.sql
-- Purpose: Set up cron jobs for feedback loop

-- 06:00 UTC — Pull Postiz metrics for all brands
SELECT cron.schedule(
  'pull-postiz-metrics',
  '0 6 * * *',
  $$ SELECT net.http_post(
      url := 'https://your-project.supabase.co/functions/v1/pull-metrics'
    ) $$
);

-- 07:00 UTC — Aggregate metrics and update feedback_bonus
SELECT cron.schedule(
  'update-feedback-bonus',
  '0 7 * * *',
  $$ SELECT net.http_post(
      url := 'https://your-project.supabase.co/functions/v1/update-bonus'
    ) $$
);
```

---

### 🔌 Task 4.5: Crea Edge Functions

**File**: `supabase/functions/pull-metrics/index.ts` (NUOVO)

```typescript
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'

serve(async (req) => {
  if (req.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 })
  }

  const { pull_brand_metrics } = await import('./src/postiz_analytics.ts')
  
  // TODO: Get brand IDs from DB or auth context
  const brandIds = ['brand-1', 'brand-2']
  
  const results = []
  
  for (const brandId of brandIds) {
    const result = await pull_brand_metrics(brandId)
    results.push(result)
  }
  
  return new Response(JSON.stringify(results), {
    headers: { 'Content-Type': 'application/json' },
  })
})
```

**File**: `supabase/functions/update-bonus/index.ts` (NUOVO)

```typescript
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'

serve(async (req) => {
  if (req.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 })
  }

  const { update_feedback_bonus } = await import('./src/feedback_loop.ts')
  
  // TODO: Get brand IDs from DB
  const brandIds = ['brand-1', 'brand-2']
  
  const results = []
  
  for (const brandId of brandIds) {
    const result = await update_feedback_bonus(brandId)
    results.push(result)
  }
  
  return new Response(JSON.stringify(results), {
    headers: { 'Content-Type': 'application/json' },
  })
})
```

---

### ✅ Checklist Fase 4

- [ ] Configura Postiz API in settings
- [ ] Implementa `pull_brand_metrics()`
- [ ] Implementa `compute_engagement_score()`
- [ ] Implementa `update_feedback_bonus()`
- [ ] Crea migration 008 per cron jobs
- [ ] Crea edge function pull-metrics
- [ ] Crea edge function update-bonus
- [ ] Deploy edge functions a Supabase
- [ ] Test cron job manualmente
- [ ] Verifica che feedback_bonus si aggiorna
- [ ] Monitora per 7 giorni per validare la formula

**Metrica fase completata**: Feedback loop automatizzato con metriche reali

---

## 📦 FASE 5 — Data Seeding & Testing

**Durata**: 1-2 giorni | **Priorità**: 🔴 Alta | **Dipendenze**: Tutte le fasi precedenti | **Output**: Sistema pronto per produzione

### Obiettivo

Popolare il DB con dati di test iniziali e validare end-to-end tutto il sistema.

---

### 🌱 Task 5.1: Seed Brand Examples per Anti-Hype Gate

**SQL**:
```sql
-- Per ogni brand, aggiungere gold/discard examples
UPDATE brands 
SET gold_examples = ARRAY[
  'Post con dati concreti e case study',
  'Tutorial pratico step-by-step',
  'Analisi con numeri verificabili'
]
WHERE slug IN ('brand-1', 'brand-2');

UPDATE brands 
SET discard_examples = ARRAY[
  'Affermazioni generiche senza dati',
  'Contenuto puramente promozionale',
  'Post "revolutionary" senza evidenze'
]
WHERE slug IN ('brand-1', 'brand-2');
```

---

### 🌱 Task 5.2: Seed Initial Agent Identities

**SQL**:
```sql
-- Le identità sono già seeded da migration 005
-- Aggiungo solo se vuote:

UPDATE agent_configs 
SET identity = 'Sei il Writer di {brand_name} — specializzato in contenuti B2B SaaS per fondatori. Il tuo stile è pratico, data-driven, con focus su metriche e ROI.'
WHERE agent_key = 'writer';
```

---

### 🌱 Task 5.3: End-to-End Test

**File**: `tests/test_e2e.py` (NUOVO)

```python
"""End-to-end test for Agent System."""

import pytest
import asyncio

from ..scoring.engine import run_scoring
from ..agents.writer import generate_draft
from ..services.postiz_analytics import pull_brand_metrics
from ..services.feedback_loop import update_feedback_bonus

@pytest.mark.asyncio
async def test_full_pipeline():
    """Test complete pipeline from research to publishing."""
    brand_id = "test-brand-id"
    
    # 1. Research → Scoring → Approval
    scoring_result = await run_scoring(brand_id, ScoringRequest())
    assert scoring_result["approved"] > 0
    
    # 2. Generate draft
    approved_item = await get_approved_item(brand_id)
    draft = await generate_draft(brand_id, approved_item["id"], "linkedin", "post")
    assert draft["title"]
    
    # 3. Simula pubblicazione
    simulate_publication(draft["id"])
    
    # 4. Pull metrics (mock)
    metrics = await pull_brand_metrics(brand_id)
    assert metrics["pulled"] >= 1
    
    # 5. Aggiorna feedback_bonus
    bonus = await update_feedback_bonus(brand_id)
    assert 0.0 <= bonus["engagement_score"] <= 10.0
```

---

### ✅ Checklist Fase 5

- [ ] Seed gold/discard examples per Anti-Hype Gate
- [ ] Verifica che agent identities sono popolate
- [ ] Esegui end-to-end test completo
- [ ] Verifica Anti-Hype Gate con examples reali
- [ ] Verifica feedback loop con metriche simulate
- [ ] Verifica cache invalidation in scenario reale
- [ ] Verifica che dashboard mostra dati corretti
- [ ] Verifica rollback delle versioni
- [ ] Verifica conflict detection UI
- [ ] Documenta setup produzione

**Metrica fase completata**: Sistema validato e pronto per produzione

---

## 📊 Tabella Riassuntiva

| Fase | Obiettivo | Durata | Priorità | Output | Dipendenze |
|------|---------|--------|----------|-------|------------|
| **0** | Fix bug critici | 1 giorno | 🔥 Critica | Engine funzionante | Nessuna |
| **1** | Wire DB agli agenti | 2-3 giorni | 🔴 Alta | Agenti leggono al DB | Fase 0 |
| **2** | FastAPI endpoints | 2-3 giorni | 🔴 Alta | API REST completa | Fase 1 |
| **3** | Dashboard Next.js | 3-4 giorni | 🔴 Alta | UI funzionante | Fase 2 |
| **4** | Postiz integration | 4-5 giorni | 🔴 Alta | Feedback loop reale | Fase 3 |
| **5** | Seeding & testing | 1-2 giorni | 🔴 Alta | Sistema pronto | Tutte |

**Totale stimato**: 13-18 giorni (3-4 settimane)

---

## 🎯 Metriche di Successo Globali

### Obiettivi Tecnici

| Metrica | Target | Come misurare |
|---------|--------|---------------|
| **Test Coverage** | >80% | pytest --cov=python/src/content_engine |
| **API Latency** | <200ms p50 | Load test su /agents endpoints |
| **Cache Hit Rate** | >70% | Monitora cache hits in logs |
| **Error Rate** | <1% | Monitora errori in production |

### Obiettivi Funzionali

| Metrica | Target | Come misurare |
|---------|--------|---------------|
| **Anti-Hype Precision** | >85% | Manually review 100 rejected items |
| **Feedback Loop Active** | 7 giorni consecutivi | Monitora cron job success |
| **Dashboard Usage** | >10 sessioni/giorno | Analytics su dashboard |
| **Agent Customization** | >50% brand hanno identity custom | Query DB |

---

## 🚦 Come Iniziare

### 1. Setup Iniziale

```bash
# Forka questo piano o salvalo come issue
git checkout -b feature/agent-implementation

# Crea branch di lavoro
git checkout -b davide/agents-implementation

# Inizia con Fase 0
```

### 2. Work In Sprints

```bash
# Sprint 1: Fase 0-1 (Fix + Wire) — 3-5 giorni
# Sprint 2: Fase 2-3 (API + Dashboard) — 5-7 giorni
# Sprint 3: Fase 4-5 (Postiz + Testing) — 5-7 giorni
```

### 3. Progress Tracking

```bash
# Per ogni fase:
1. Segna i task dalla checklist
2. Aggiorna questo file con [x] quando completato
3. Push con commit message descrittivo
```

---

## 📚 Note Importanti

### Best Practice Implementate

1. **Graceful Degradation** — Tutte le funzioni hanno try/except con fallback
2. **Type Safety** — Type hints ovunque per early error detection
3. **Audit Trail** — Ogni modifica è tracciabile (version table)
4. **Rate Limiting** — Protezione contro abuse API
5. **Cache Consistency** — Invalidazione esplicita dopo update

### Decisioni Architetturali

1. **Redis NON usato** — Cache in-memory è sufficiente per singolo processo
2. **No message queue** — Task diretti sono sufficienti per questo scope
3. **No event sourcing** — Cron job semplice invece di complessità
4. **No GraphQL** — REST API più semplice e adeguato per ora
5. **No microservices** — Monolite Python + Next.js più semplice da mantenere

### Trade-off

- **Performance vs Semplicità** — In-memory cache non è distribuita ma OK per singolo processo
- **Automation vs Controllo** — Cron job automatizzato ma si può disabilitare manualmente
- **Completeness vs Tempo** — Non tutti gli agenti 25+ sono implementati subito
- **Generic vs Specifico** — System è generico ma richiede data seeding per brand

---

## 🔄 Changelog

| Versione | Data | Cambiamenti |
|----------|------|------------|
| 1.0 | 2026-04-15 | Piano iniziale |

---

**Autore**: Piano generato da Claude Code basato su analisi di perplexity e best practice di sviluppo software.

→ Per domande o chiarimenti, creare issue nel repository.
