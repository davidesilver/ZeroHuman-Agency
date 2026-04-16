# Synergy Sync — Piano di Implementazione Completo

## Executive Summary

Questo piano completa l'architettura "Synergy Sync" che abbandona l'approccio di placeholder hardcoded e adotta un sistema dinamico, database-driven come "Source of Truth" per tutti gli agenti.

**Stato attuale:**
- ✅ Database schema completo (migrations 011, 012)
- ✅ LLM client con fallback chain e logging
- ⚠️ Dashboard con status base ma senza metadati LLM
- ❌ Heartbeat recording non implementato
- ❌ Gerarchia God System non gestita

**Obietivo:**
- Completare il loop di feedback: LLM calls → heartbeat recording → dashboard visualization
- Trasformare dashboard da status simple a observability system completo
- Implementare gerarchia per agenti compositi (God System)

**Stima:**
- Fase 1 (Backend): 2-3 giorni
- Fase 2 (Frontend): 2 giorni  
- Fase 3 (Testing): 1-2 giorni
- **Totale: 5-7 giorni per un singolo sviluppatore**

---

## Gap Analysis Dettagliata

### 1. Backend Foundation — Gap 40%

**Cosa manca:**
- Funzione `record_agent_heartbeat()` non esiste
- Classi base agenti non chiamano heartbeat
- God System non registra metadati per singoli sub-agenti
- Nessun tracking di latencies real-time

**Impatto:**
- Database `pipeline_health` ha colonne giuste ma rimane vuoto
- Fallback log esiste ma dashboard non lo mostra
- Dashboard mostra dati obsoleti o incompleti

### 2. Frontend Dashboard — Gap 70%

**Cosa manca:**
- API health ritorna solo status base
- Frontend non mostra Current Model, Fallback Model, Engine
- Nessun badge per failover status
- God System mostrato come agenti flat, non gerarchia
- No expandable rows per drill-down

**Impatto:**
- Monitoring inefficace (non vedi modelli reali)
- Debugging difficile (non sai quale LLM sta usando)
- Cost management opaco (non vedi fallback attempts)

### 3. Testing & Validation — Gap 100%

**Cosa manca:**
- Nessun test end-to-end per heartbeat flow
- Nessun test per dashboard visualization
- Nessun test per God System gerarchia

**Impatto:**
- Rischio di regressioni
- Incertezza se implementazione funzioni

---

## Piano di Implementazione in 3 Fasi

### FASE 1: Backend Foundation (2-3 giorni)

#### Task 1.1: Implementare Heartbeat System
**File:** `python/src/content_engine/utils/heartbeat.py` (NUOVO)
**Stima:** 4 ore

Crea modulo heartbeat con funzioni asincrone:

```python
"""Agent heartbeat and LLM metadata tracking system."""

import time
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger("content_engine.heartbeat")

# Cache in-memory per heartbeat (TTL: 1 minuto)
_heartbeat_cache: Dict[str, Dict[str, Any]] = {}
_HEARTBEAT_CACHE_TTL = 60

def _get_cache_key(brand_id: str, agent_key: str) -> str:
    return f"{brand_id}:{agent_key}"

async def record_agent_heartbeat(
    brand_id: str,
    agent_key: str,
    llm_meta: Optional[Dict[str, Any]] = None,
    status: str = "healthy",
    sub_agent: Optional[str] = None,  # Per God System: "advocate", "factcheck", etc.
) -> None:
    """
    Registra heartbeat dell'agente con metadati LLM.
    
    Args:
        brand_id: Brand ID
        agent_key: Chiave agente (es. "writer", "advocate")  
        llm_meta: Dict con metadati LLM: {model, engine, latency_ms, tokens}
        status: "healthy", "degraded", "down"
        sub_agent: Opzionale, per sub-agenti God System
    """
    try:
        from .db import get_db
        db = get_db()
        
        # Costruisci la chiave completa (include sub_agent se presente)
        full_agent_key = f"{agent_key}" if not sub_agent else f"{agent_key}_{sub_agent}"
        
        # Aggiorna cache
        cache_key = _get_cache_key(brand_id, full_agent_key)
        _heartbeat_cache[cache_key] = {
            "agent_key": full_agent_key,
            "status": status,
            "llm_meta": llm_meta or {},
            "timestamp": time.time(),
        }
        
        # Prepara dati per database
        now = datetime.utcnow().isoformat()
        
        # Estrai metadati LLM con fallback su valori di default
        current_model = llm_meta.get("model_used", "unknown") if llm_meta else "unknown"
        fallback_model = llm_meta.get("fallback_to", None)
        engine = llm_meta.get("engine", "unknown") if llm_meta else "unknown"
        latency_ms = llm_meta.get("latency_ms") if llm_meta else None
        tokens_prompt = llm_meta.get("tokens_prompt", 0) if llm_meta else 0
        tokens_completion = llm_meta.get("tokens_completion", 0) if llm_meta else 0
        
        # Calcola uptime (se status != "down", incrementa)
        # NOTA: Per MVP semplice, uptime_pct viene calcolato periodicamente da cron job
        
        # Upsert in pipeline_health
        upsert_data = {
            "brand_id": brand_id,
            "agent_name": full_agent_key,
            "status": status,
            "last_seen": now,
            "current_model": current_model,
            "fallback_model": fallback_model,
            "engine": engine,
            "last_latency_ms": latency_ms,
        }
        
        # Usa upsert logic: update se esiste, insert se no
        existing = db.table("pipeline_health").select("*").eq("brand_id", brand_id).eq("agent_name", full_agent_key).maybe_single().execute()
        
        if existing.data:
            db.table("pipeline_health").update(upsert_data).eq("id", existing.data["id"]).execute()
        else:
            upsert_data["uptime_pct"] = 100.0  # Default per nuovo agente
            upsert_data["errors_today"] = 0
            upsert_data["queue_size"] = 0
            db.table("pipeline_health").insert(upsert_data).execute()
            
        logger.debug(
            f"Heartbeat recorded: brand={brand_id} agent={full_agent_key} "
            f"model={current_model} engine={engine} status={status}"
        )
        
    except Exception as e:
        # Non fallire heartbeat se DB fallisce
        logger.error(f"Failed to record heartbeat for {brand_id}:{full_agent_key}: {e}")

def get_cached_heartbeat(brand_id: str, agent_key: str) -> Optional[Dict[str, Any]]:
    """
    Ottieni heartbeat dalla cache (per dashboard real-time).
    
    Returns None se non in cache o expired.
    """
    cache_key = _get_cache_key(brand_id, agent_key)
    entry = _heartbeat_cache.get(cache_key)
    
    if not entry:
        return None
    
    # Check TTL
    if time.time() - entry["timestamp"] > _HEARTBEAT_CACHE_TTL:
        del _heartbeat_cache[cache_key]
        return None
    
    return entry
```

#### Task 1.2: Integrare Heartbeat in LLM Client
**File:** `python/src/content_engine/utils/llm_client.py`
**Stima:** 2 ore

Modifica `call_llm()` per calcolare e restituire metadati:

```python
# Alla fine di call_llm(), prima di restituire:

# Calcola latency
end_time = time.monotonic()
latency_ms = int((end_time - start_time) * 1000) if 'start_time' in locals() else None

# Restituisci metadati aggiuntivi
return LLMResponse(
    content=content, 
    model_used=current_model, 
    tokens_prompt=prompt_tok, 
    tokens_completion=comp_tok,
    # Campi aggiuntivi
    engine="openrouter" if use_claude is False else "anthropic",
    latency_ms=latency_ms,
    fallback_to=None  # Sarà popolato se c'è fallback
)
```

#### Task 1.3: Wrappare call_llm() per registrazione automatica
**File:** `python/src/content_engine/utils/llm_client.py`  
**Stima:** 3 ore

Crea wrapper decorator per registrazione heartbeat:

```python
# Aggiungi in cima al file
import functools
from .heartbeat import record_agent_heartbeat

def _track_llm_call(context: str, action: str, agent_key: str):
    """
    Wrapper decorator che registra heartbeat automatico.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Chiama funzione originale
            result = await func(*args, **kwargs)
            
            # Registra heartbeat (async fire-and-forget)
            try:
                brand_id = kwargs.get("brand_id", args[0] if args else "unknown")
                
                # Estrai metadati LLM dal risultato
                llm_meta = {
                    "model_used": result.model_used,
                    "engine": getattr(result, "engine", "unknown"),
                    "latency_ms": getattr(result, "latency_ms", None),
                    "tokens_prompt": result.tokens_prompt,
                    "tokens_completion": result.tokens_completion,
                }
                
                # Registra in background (non bloccare)
                asyncio.create_task(
                    record_agent_heartbeat(
                        brand_id=brand_id,
                        agent_key=agent_key,
                        llm_meta=llm_meta,
                        status="healthy",
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to register heartbeat: {e}")
            
            return result
        return wrapper
    return decorator

# Modifica signature di call_llm per aggiungere agent_key
async def call_llm(
    prompt: str,
    brand_id: str,
    agent_key: str,  # AGGIUNTO
    context: str = "general",
    action: str = "call_llm",
    system_prompt: Optional[str] = None,
    task_type: str = "creative",
    temperature: float = 0.7,
) -> LLMResponse:
    """
    Call LLM con automatic heartbeat recording.
    """
    # Implementazione esistente...
```

#### Task 1.4: Aggiornare God System per tracciare sub-agenti
**File:** `python/src/content_engine/agents/god_system.py`
**Stima:** 4 ore

Aggiungi heartbeat per ogni sub-agente:

```python
# In ogni funzione run_*(), dopo chiamata a call_llm():

# Esempio in run_advocate():
adv_resp = await call_llm(
    adv_prompt, 
    brand_id, 
    agent_key="advocate",  # AGGIUNTO
    context="god_advocate", 
    action="advocate", 
    task_type="knowledge"
)

# Il wrapper in call_llm() registrerà heartbeat automatico

# Simile per run_factcheck(), run_creative(), run_synthesis()
# Usa agent_key="factcheck", "creative", "synthesis" rispettivamente
```

#### Task 1.5: Aggiornare agenti singoli (Writer, Editor, etc.)
**File:** `python/src/content_engine/agents/writer.py`, `editor.py`, `adapter.py`
**Stima:** 3 ore

Aggiungi parametro `agent_key` nelle chiamate LLM:

```python
# writer.py - esempio
content_resp = await call_llm(
    writing_prompt,
    brand_id,
    agent_key="writer",  # AGGIUNTO
    context="writer_initial",
    action="generate_content",
    task_type="creative"
)

# editor.py - esempio
edit_resp = await call_llm(
    edit_prompt,
    brand_id, 
    agent_key="editor",  # AGGIUNTO
    context="editor_refine",
    action="edit_content",
    task_type="reasoning"
)
```

---

### FASE 2: Frontend Enhancement (2 giorni)

#### Task 2.1: Aggiornare Health API per metadati completi
**File:** `src/app/api/system/health/route.ts`
**Stima:** 2 ore

```typescript
import { createClient } from '@/lib/supabase/server'
import { jsonResponse, errorResponse } from '@/lib/api-helpers'
import { requireAuth } from '@/lib/supabase/auth-helpers'
import { NextRequest } from 'next/server'

interface AgentHealth {
  id: string
  brand_id: string
  agent_name: string
  status: 'healthy' | 'degraded' | 'down'
  last_seen: string
  current_model: string
  fallback_model: string | null
  engine: 'anthropic' | 'openrouter' | 'unknown'
  last_latency_ms: number | null
  uptime_pct: number
  errors_today: number
  queue_size: number
}

interface HealthSummary {
  agents_healthy: number
  agents_degraded: number
  agents_down: number
  avg_uptime: number
  total_errors: number
  total_queue: number
  active_models: string[]  // NEW
  active_engines: string[]  // NEW
  emergency_fallbacks_24h: number  // NEW
}

export async function GET(request: NextRequest) {
  try {
    const { auth, response } = await requireAuth()
    if (!auth) return response

    const supabase = await createClient()

    // Fetch agent health
    const { data: agents, error } = await supabase
      .from('pipeline_health')
      .select('*')
      .eq('brand_id', auth.brandId)
      .order('agent_name')

    if (error) return errorResponse(error.message, 500)

    const typedAgents: AgentHealth[] = agents || []

    // Calculate aggregate metrics
    const avgUptime = typedAgents.length > 0
      ? typedAgents.reduce((sum, a) => sum + (a.uptime_pct || 0), 0) / typedAgents.length
      : 0
    const totalErrors = typedAgents.reduce((sum, a) => sum + (a.errors_today || 0), 0)
    const totalQueue = typedAgents.reduce((sum, a) => sum + (a.queue_size || 0), 0)
    
    // NEW: Extract active models and engines
    const activeModels = [...new Set(
      typedAgents.map(a => a.current_model).filter(Boolean)
    ])
    const activeEngines = [...new Set(
      typedAgents.map(a => a.engine).filter(Boolean)
    ])
    
    // NEW: Count emergency fallbacks in last 24h
    const { data: fallbacks } = await supabase
      .from('llm_fallback_log')
      .select('*')
      .eq('brand_id', auth.brandId)
      .eq('is_emergency', true)
      .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())

    const emergencyCount = fallbacks?.length || 0

    return jsonResponse({
      agents: typedAgents,
      summary: {
        avg_uptime: Math.round(avgUptime * 10) / 10,
        total_errors: totalErrors,
        total_queue: totalQueue,
        agents_healthy: typedAgents.filter(a => a.status === 'healthy').length,
        agents_degraded: typedAgents.filter(a => a.status === 'degraded').length,
        agents_down: typedAgents.filter(a => a.status === 'down').length,
        active_models: activeModels,
        active_engines: activeEngines,
        emergency_fallbacks_24h: emergencyCount,
      },
    })
  } catch (err) {
    return errorResponse('Failed to fetch health data', 500)
  }
}
```

#### Task 2.2: Creare Componenti Dashboard Migliorati
**File:** `src/components/dashboard/agent-status.tsx` (NUOVO)
**Stima:** 3 ore

```typescript
'use client'

import { Badge } from '@/components/ui/badge'

interface AgentHealthProps {
  agent: {
    agent_name: string
    status: 'healthy' | 'degraded' | 'down'
    current_model: string
    fallback_model: string | null
    engine: 'anthropic' | 'openrouter' | 'unknown'
    last_latency_ms: number | null
  }
  isExpandable?: boolean
  subAgents?: AgentHealthProps['agent'][]
}

export function AgentStatusRow({ agent, isExpandable, subAgents }: AgentHealthProps) {
  const [expanded, setExpanded] = useState(false)
  
  // Detect if using fallback
  const isUsingFallback = agent.fallback_model !== null
  
  // Engine badge colors
  const getEngineBadgeVariant = (engine: string) => {
    if (engine === 'anthropic') return 'default'  // Primary
    if (engine === 'openrouter') return 'secondary'  // Fallback/Free
    return 'outline'  // Unknown
  }
  
  return (
    <>
      <div className="flex items-center justify-between p-2 border-b last:border-0">
        <div className="flex items-center gap-2">
          {isExpandable && (
            <button 
              onClick={() => setExpanded(!expanded)}
              className="text-muted-foreground hover:text-foreground"
            >
              {expanded ? '▼' : '▶'}
            </button>
          )}
          <span className="text-sm font-medium">{agent.agent_name}</span>
          
          {/* Status Badge */}
          <Badge
            variant={
              agent.status === 'healthy' ? 'default' : 
              agent.status === 'degraded' ? 'secondary' : 
              'outline'
            }
            className="text-xs"
          >
            {agent.status === 'healthy' ? 'Online' : 
             agent.status === 'degraded' ? 'Degraded' : 'Offline'}
          </Badge>
          
          {/* Failover Indicator */}
          {isUsingFallback && (
            <Badge variant="destructive" className="text-xs">
              Fallback: {agent.fallback_model}
            </Badge>
          )}
        </div>
        
        {/* Engine Badge */}
        <Badge variant={getEngineBadgeVariant(agent.engine)} className="text-xs">
          {agent.engine === 'anthropic' ? '🔷 Anthropic' : '🌐 OpenRouter'}
        </Badge>
        
        {/* Current Model */}
        <div className="text-xs text-muted-foreground">
          {agent.current_model}
        </div>
        
        {/* Latency */}
        {agent.last_latency_ms !== null && (
          <div className={`text-xs ${
            agent.last_latency_ms > 5000 ? 'text-red-500' : 
            agent.last_latency_ms > 2000 ? 'text-yellow-500' : 
            'text-green-500'
          }`}>
            {agent.last_latency_ms}ms
          </div>
        )}
      </div>
      
      {/* Expandable Sub-Agents */}
      {expanded && subAgents && (
        <div className="ml-6">
          {subAgents.map(sub => (
            <AgentStatusRow key={sub.agent_name} agent={sub} />
          ))}
        </div>
      )}
    </>
  )
}
```

#### Task 2.3: Aggiornare Dashboard Page
**File:** `src/app/(dashboard)/page.tsx`
**Stima:** 3 ore

```typescript
'use client'

import { useCallback, useEffect, useState } from 'react'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AgentStatusRow } from '@/components/dashboard/agent-status'

interface HealthSummary {
  agents_healthy: number
  agents_degraded: number
  agents_down: number
  avg_uptime: number
  total_errors: number
  total_queue: number
  active_models: string[]
  active_engines: string[]
  emergency_fallbacks_24h: number
}

export default function DashboardPage() {
  // ... stato esistente ...
  
  const [health, setHealth] = useState<{
    agents: any[]
    summary: HealthSummary
  }>({ agents: [], summary: {
    agents_healthy: 0, agents_degraded: 0, agents_down: 0,
    avg_uptime: 0, total_errors: 0, total_queue: 0,
    active_models: [], active_engines: [], emergency_fallbacks_24h: 0
  }})

  // ... fetchData esistente ...

  return (
    <div>
      {/* KPI cards - AGGIUNTI */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard title="Content in pipeline" value={totalPipeline} />
        <KPICard title="Published" value={stats.published} />
        <KPICard 
          title={`Active agents (${health.summary.agents_healthy}/${health.agents.length})`}
          subtitle={`${health.summary.agents_degraded} degraded`}
        />
        <KPICard title="API spend today" value={`$${costs.spend_today.toFixed(2)}`} />
      </div>

      {/* NEW: LLM Observability Cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <KPICard 
          title="Active LLM Models" 
          value={health.summary.active_models.length}
          subtitle={health.summary.active_models.slice(0, 3).join(', ')}
        />
        <KPICard 
          title="Engines Active" 
          value={health.summary.active_engines.length}
          subtitle={health.summary.active_engines.join(', ')}
        />
        <KPICard 
          title="Emergency Fallbacks (24h)" 
          value={health.summary.emergency_fallbacks_24h}
          subtitle={health.summary.emergency_fallbacks_24h > 0 ? '⚠️ Alert!' : '✓ Normal'}
          variant={health.summary.emergency_fallbacks_24h > 0 ? 'destructive' : 'default'}
        />
      </div>

      {/* Pipeline mini */}
      <Card className="mb-6">
        {/* ... esistente ... */}
      </Card>

      {/* Activity log + ENHANCED Agent Status */}
      <div className="grid grid-cols-2 gap-4">
        {/* Activity log - esistente */}
        
        {/* ENHANCED Agent Status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Agent Status</CardTitle>
          </CardHeader>
          <CardContent>
            {health.agents.length === 0 ? (
              <p className="text-center text-sm text-muted-foreground py-8">
                No agents active yet
              </p>
            ) : (
              <div className="space-y-2">
                {health.agents.map(agent => {
                  // Check if this is God System (has sub-agents)
                  const isGodSystem = agent.agent_name.startsWith('god_')
                  const subAgents = isGodSystem 
                    ? health.agents.filter(a => 
                        a.agent_name !== agent.agent_name && 
                        a.agent_name.startsWith('god_')
                      )
                    : undefined
                  
                  return (
                    <AgentStatusRow 
                      key={agent.agent_name} 
                      agent={agent}
                      isExpandable={isGodSystem}
                      subAgents={subAgents}
                    />
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

#### Task 2.4: Aggiornare Agent Settings per God System
**File:** `src/app/(dashboard)/settings/agenti/page.tsx`
**Stima:** 2 ore

Aggiungi configurazioni per agenti compositi:

```typescript
// AGGIUNTI AGENT_LABELS
const AGENT_LABELS = {
  // ... esistenti ...
  
  // Humanizer (già aggiunto in 011)
  'humanizer': {
    name: 'Humanizer Agent',
    description: 'Detects and removes AI-generated patterns from content',
    category: 'content-enhancement',
  },
  
  // God System composito
  'god_advocate': {
    name: 'Devil\'s Advocate',
    description: 'Critical analysis of content quality and rigor',
    category: 'content-review',
    parent: 'god_system',
  },
  'god_factcheck': {
    name: 'Fact Checker',
    description: 'Verifies factual claims and identifies risks',
    category: 'content-review',
    parent: 'god_system',
  },
  'god_creative': {
    name: 'Creative Director',
    description: 'Enhances emotional engagement and hooks',
    category: 'content-review',
    parent: 'god_system',
  },
  'god_synthesis': {
    name: 'Synthesis Engine',
    description: 'Combines all feedback into final polished content',
    category: 'content-review',
    parent: 'god_system',
  },
} as const
```

---

### FASE 3: Testing & Validation (1-2 giorni)

#### Task 3.1: Test Heartbeat Recording
**File:** `python/tests/test_heartbeat.py` (NUOVO)
**Stima:** 3 ore

```python
"""Test heartbeat recording system."""

import pytest
import asyncio
from content_engine.utils.heartbeat import record_agent_heartbeat, get_cached_heartbeat
from content_engine.utils.llm_client import LLMResponse

@pytest.mark.asyncio
async def test_heartbeat_recording():
    """Test che heartbeat viene registrato correttamente."""
    brand_id = "test-brand-123"
    agent_key = "test_writer"
    
    llm_meta = {
        "model_used": "claude-3-5-haiku-20241022",
        "engine": "anthropic",
        "latency_ms": 1234,
        "tokens_prompt": 100,
        "tokens_completion": 50,
    }
    
    # Registra heartbeat
    await record_agent_heartbeat(
        brand_id=brand_id,
        agent_key=agent_key,
        llm_meta=llm_meta,
        status="healthy"
    )
    
    # Verifica cache
    cached = get_cached_heartbeat(brand_id, agent_key)
    assert cached is not None
    assert cached["status"] == "healthy"
    assert cached["llm_meta"]["model_used"] == "claude-3-5-haiku-20241022"

@pytest.mark.asyncio
async def test_god_system_sub_agents():
    """Test heartbeat per sub-agenti God System."""
    brand_id = "test-brand-456"
    
    sub_agents = ["god_advocate", "god_factcheck", "god_creative", "god_synthesis"]
    
    for sub_agent in sub_agents:
        await record_agent_heartbeat(
            brand_id=brand_id,
            agent_key="god_system",
            sub_agent=sub_agent,
            llm_meta={"model_used": "claude-3-5-sonnet-20241022", "engine": "anthropic"},
            status="healthy"
        )
    
    # Verifica che tutti siano in cache con chiavi corrette
    for sub_agent in sub_agents:
        full_key = f"god_system_{sub_agent}"
        cached = get_cached_heartbeat(brand_id, full_key)
        assert cached is not None
        assert cached["agent_key"] == full_key
```

#### Task 3.2: Test Dashboard API
**File:** Create test file or use Postman collection
**Stima:** 2 ore

Verifica che API health ritorni metadati completi:

```bash
# Test 1: Verifica che API ritorni metadati LLM
curl http://localhost:3000/api/system/health \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.agents[0] | jq '{current_model, engine, last_latency_ms}'

# Output atteso: {"current_model": "...", "engine": "...", "last_latency_ms": 1234}

# Test 2: Verifica summary con nuovi campi
curl http://localhost:3000/api/system/health | jq '.summary | jq '{active_models, active_engines, emergency_fallbacks_24h}'
```

#### Task 3.3: Test End-to-End Integration
**File:** Manual testing procedure
**Stima:** 3 ore

1. **Attiva content pipeline** (es. crea nuovo draft)
2. **Verifica dashboard in real-time:**
   - Agenti diventano "Online"
   - Current Model aggiornato
   - Latency mostrato
3. **Trigger fallback** (simula Anthropic API down)
4. **Verifica dashboard:**
   - Engine badge cambia da Anthropic → OpenRouter
   - Emergency fallback counter incrementa
5. **Verifica God System:**
   - Expandable row funziona
   - Sub-agenti mostrati con metadati

#### Task 3.4: Performance Testing
**File:** `python/tests/test_heartbeat_performance.py` (NUOVO)
**Stima:** 2 ore

```python
"""Test performance di heartbeat system."""

import pytest
import asyncio
import time
from content_engine.utils.heartbeat import record_agent_heartbeat

@pytest.mark.asyncio
async def test_heartbeat_throughput():
    """Test che heartbeat regisce 100 calls/sec senza bloccare."""
    brand_id = "test-brand-perf"
    
    start = time.time()
    
    # Crea 100 heartbeat paralleli
    tasks = [
        record_agent_heartbeat(
            brand_id=brand_id,
            agent_key=f"agent_{i}",
            llm_meta={"model_used": "test-model", "engine": "test"},
            status="healthy"
        )
        for i in range(100)
    ]
    
    await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    throughput = 100 / elapsed
    
    print(f"Heartbeat throughput: {throughput:.2f} calls/sec")
    
    # Deve essere > 50 calls/sec
    assert throughput > 50
```

---

## Piano di Rollout

### Day 1-2: Backend Foundation
- [ ] Task 1.1: Implementare Heartbeat System (4h)
- [ ] Task 1.2: Integrare Heartbeat in LLM Client (2h)
- [ ] Task 1.3: Wrappare call_llm() per registrazione automatica (3h)
- [ ] Task 1.4: Aggiornare God System (4h)
- [ ] Task 1.5: Aggiornare agenti singoli (3h)

### Day 3-4: Frontend Enhancement  
- [ ] Task 2.1: Aggiornare Health API (2h)
- [ ] Task 2.2: Creare Componenti Dashboard Migliorati (3h)
- [ ] Task 2.3: Aggiornare Dashboard Page (3h)
- [ ] Task 2.4: Aggiornare Agent Settings (2h)

### Day 5-6: Testing & Validation
- [ ] Task 3.1: Test Heartbeat Recording (3h)
- [ ] Task 3.2: Test Dashboard API (2h)
- [ ] Task 3.3: Test End-to-End Integration (3h)
- [ ] Task 3.4: Performance Testing (2h)

---

## Rischi e Mitigazioni

### Rischio 1: Performance Database
**Rischio:** Heartbeat frequente può sovraccaricare database
**Mitigazione:**
- Cache in-memory (TTL 1 minuto) riduce chiamate DB
- Upsert invece di insert+update evita race conditions
- Background recording (async fire-and-forget)

### Rischio 2: Cache Stale
**Rischio:** Dashboard mostra dati obsoleti da cache
**Mitigazione:**
- TTL breve (1 minuto) per heartbeat cache
- API health sempre legge da database (no cache)
- Solo dashboard frontend usa cache per real-time feel

### Rischio 3: God System Gerarchia
**Rischio:** Gerarchia complessa diventa difficile da mantenere
**Mitigazione:**
- Start semplice: lista flat con prefissi `god_*`
- Expandable rows come enhancement, non feature MVP
- Documentation chiara per mapping agenti → sub-agenti

### Rischio 4: Regressioni Agenti Esistenti
**Rischio:** Modificando `call_llm()` può rompere agenti esistenti
**Mitigazione:**
- Parametro `agent_key` con default per backward compatibility
- Test completi per tutti gli agenti prima di deploy
- Rollback plan se problemi critici

---

## Success Criteria

### Technical Success
- [ ] Tutti gli agenti registrano heartbeat automatico
- [ ] Dashboard mostra metadati LLM real-time
- [ ] God System sub-agenti tracciati come gerarchia
- [ ] Emergency fallbacks visibili su dashboard
- [ ] Performance: >50 heartbeat/sec senza lag
- [ ] Zero regressioni in funzionalità esistente

### User Success
- [ ] Dashboard trasparente: vedi sempre quale LLM sta usando
- [ ] Debugging veloce: latencies mostrate in real-time
- [ ] Cost management: fallback attempts visibili
- [ ] God system completo: puoi drill-down in ogni fase

### Business Success
- [ ] Migliore debug capability = ridotto time troubleshooting
- [ ] Migliore cost visibility = ottimizzazioni provider LLM
- [ ] Migliore reliability = detection rapida outages
- [ ] Foundation per avanzate: adaptive LLM routing basato su dati reali

---

## Next Steps Post-Implementation

1. **Adoptive LLM Routing**: Basato su dati reali, routing automatico a modello più cost-effective
2. **Predictive Scaling**: Prevedere picchi LLM in base su pattern usage
3. **Cost Optimization**: Automatic switch a modelli più economici per task semplici
4. **Real-time Alerts**: Notifiche instantanee per outages, latencies anomale, escalation costi

---

## Appendix: File da Modificare

### Backend (Python)
1. `python/src/content_engine/utils/heartbeat.py` [NUOVO]
2. `python/src/content_engine/utils/llm_client.py` [MODIFY]
3. `python/src/content_engine/agents/god_system.py` [MODIFY]
4. `python/src/content_engine/agents/writer.py` [MODIFY]
5. `python/src/content_engine/agents/editor.py` [MODIFY]
6. `python/src/content_engine/agents/adapter.py` [MODIFY]

### Frontend (Next.js)
1. `src/app/api/system/health/route.ts` [MODIFY]
2. `src/components/dashboard/agent-status.tsx` [NUOVO]
3. `src/app/(dashboard)/page.tsx` [MODIFY]
4. `src/app/(dashboard)/settings/agenti/page.tsx` [MODIFY]

### Testing
1. `python/tests/test_heartbeat.py` [NUOVO]
2. `python/tests/test_heartbeat_performance.py` [NUOVO]

---

**Version:** 1.0  
**Created:** 2026-04-15  
**Author:** Claude Sonnet  
**Status:** Ready for Implementation
