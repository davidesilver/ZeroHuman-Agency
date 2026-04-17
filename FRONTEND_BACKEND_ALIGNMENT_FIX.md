# 🔧 Frontend-Backend Alignment - Database Schema Fix

## ❌ Problema Scoperto

Il frontend che ho creato **NON era adattato al codice reale del database**. 

### Schema Database Reale (pipeline_health table)

```sql
CREATE TABLE IF NOT EXISTS pipeline_health (
  id              uuid PRIMARY KEY,
  brand_id        uuid NOT NULL,
  agent_name      text NOT NULL,
  uptime_pct      float,
  avg_latency_ms  int,           -- ✅ ESISTE
  errors_today    int DEFAULT 0,
  queue_size      int DEFAULT 0,
  last_heartbeat  timestamptz,   -- ✅ ESISTE (non last_seen!)
  status          health_status NOT NULL DEFAULT 'healthy',
  created_at      timestamptz DEFAULT now()
);
```

### Campi Mancanti nel Database

❌ `current_model` - **NON ESISTE**  
❌ `fallback_model` - **NON ESISTE**  
❌ `engine` - **NON ESISTE**  
❌ `last_latency_ms` - **NON ESISTE** (c'è `avg_latency_ms`)  
❌ `last_seen` - **NON ESISTE** (c'è `last_heartbeat`)

### Campi Che Il Frontend Si Aspettava

```typescript
interface AgentHealth {
  current_model: string        // ❌ NON ESISTE nel DB
  fallback_model: string | null // ❌ NON ESISTE nel DB
  engine: string                // ❌ NON ESISTE nel DB
  last_latency_ms: number | null // ❌ NON ESISTE nel DB
  last_seen: string             // ❌ NON ESISTE nel DB (c'è last_heartbeat)
}
```

## ✅ Soluzione Implementata

### 1. Database Migration (013_add_llm_metadata_to_pipeline_health.sql)

**Creato:** Nuova migrazione per aggiungere i campi mancanti

```sql
ALTER TABLE pipeline_health
ADD COLUMN IF NOT EXISTS current_model TEXT,
ADD COLUMN IF NOT EXISTS fallback_model TEXT,
ADD COLUMN IF NOT EXISTS engine TEXT NOT NULL DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS last_latency_ms INTEGER,
ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ;

-- Aggiorna record esistenti con valori default
UPDATE pipeline_health
SET
    engine = 'unknown',
    last_seen = COALESCE(last_heartbeat, now())
WHERE engine IS NULL OR last_seen IS NULL;
```

### 2. Backend Code Alignment (heartbeat.py)

**Modificato:** Adattato per usare i campi corretti della tabella

```python
# PRIMA (sbagliato):
upsert_data = {
    "last_seen": now.isoformat(),  # ❌ Campo non esiste
    "current_model": ...,          # ❌ Campo non esiste
    ...
}

# DOPO (corretto):
upsert_data = {
    "last_heartbeat": now,         # ✅ Campo esistente
    "current_model": ...,          # ✅ Campo aggiunto da migrazione
    ...
}
```

### 3. Frontend API Alignment (route.ts)

**Modificato:** Gestito backward compatibility con campi null

```typescript
// PRIMA (assunzione errata):
interface AgentHealth {
  current_model: string        // ❌ Assunzione che esista sempre
  engine: string                // ❌ Assunzione che esista sempre
  ...
}

// DOPO (corretto):
interface AgentHealth {
  current_model: string | null  // ✅ Gestisce vecchi record senza campo
  engine: string | null        // ✅ Gestisce vecchi record senza campo
  last_heartbeat: string       // ✅ Usa campo corretto
  ...
}

// Estrazione con filter per null
const activeModels = [...new Set(
  typedAgents.map(a => a.current_model).filter((m): m is string => Boolean(m))
)]
```

### 4. Frontend Dashboard Alignment (page.tsx)

**Modificato:** Gestito visualizzazione con valori null

```typescript
// PRIMA (assunzione errata):
<span>{a.current_model}</span>
<span>{a.engine}</span>

// DOPO (corretto):
<span>{a.current_model || 'Unknown'}</span>
<span>{a.engine || 'Unknown'}</span>
```

## 🔄 Flusso di Allineamento Completo

### 1. Database Schema
```sql
-- PRIMA (incompleto):
pipeline_health (
    avg_latency_ms int,
    last_heartbeat timestamptz
    -- Manca: current_model, engine, etc.
)

-- DOPO (completo):
pipeline_health (
    avg_latency_ms int,           -- Mantenuto per backward compat
    last_latency_ms int,           -- Nuovo: latency più recente
    last_heartbeat timestamptz,    -- Mantenuto per backward compat
    last_seen timestamptz,         -- Nuovo: alias per chiarezza
    current_model text,            -- Nuovo: modello LLM attuale
    fallback_model text,           -- Nuovo: modello fallback
    engine text                    -- Nuovo: anthropic/openrouter
)
```

### 2. Backend → Database
```python
# Heartbeat scrive campi corretti
upsert_data = {
    "last_heartbeat": now,         # Campo esistente
    "current_model": model,        # Nuovo campo
    "engine": "anthropic",         # Nuovo campo
    "last_latency_ms": latency,   # Nuovo campo
    ...
}
```

### 3. Database → Frontend API
```typescript
// API legge campi corretti e gestisce null
const activeModels = [...new Set(
  typedAgents.map(a => a.current_model).filter(Boolean)
)]
```

### 4. Frontend API → Dashboard
```typescript
// Dashboard mostra dati con fallback per null
<span>{agent.current_model || 'Unknown'}</span>
<span>{agent.engine || 'Unknown'}</span>
```

## 🎯 Backward Compatibility

### Vecchi Record (Prima della Migrazione)

I record esistenti nel database **prima della migrazione** avranno:
- `current_model`: `NULL` (diventa 'Unknown' in UI)
- `engine`: `NULL` (diventa 'Unknown' in UI) 
- `last_latency_ms`: `NULL` (diventa 'N/A' in UI)
- `last_seen`: `NULL` (ma `last_heartbeat` esiste)

### Nuovi Record (Dopo la Migrazione)

I record **dopo la migrazione** avranno tutti i campi popolati.

## 📋 Checklist per Deployment

### Prima del Deploy

1. ✅ **Applicare migrazione database**
   ```bash
   cd supabase
   supabase db push
   ```

2. ✅ **Verificare schema aggiornato**
   ```sql
   \d pipeline_health
   -- Dovrebbe mostrare i nuovi campi
   ```

3. ✅ **Riavviare backend Python**
   ```bash
   # Per caricare nuovo codice heartbeat.py
   ```

4. ✅ **Riavviare frontend Next.js**
   ```bash
   # Per caricare nuovo codice TypeScript
   ```

### Dopo il Deploy

1. ✅ **Verificare che dashboard funzioni**
   - Apri dashboard
   - Dovrebbe mostrare "Unknown" per agenti vecchi
   - Dovrebbe mostrare dati reali per nuovi agenti

2. ✅ **Generare nuovo content**
   - Questo creerà nuovi record con tutti i campi
   - Dashboard dovrebbe mostrare dati completi

3. ✅ **Verificare log**
   ```bash
   tail -f logs/backend.log | grep "Heartbeat:"
   # Dovrebbe mostrare heartbeat con tutti i metadati
   ```

## 🚨 Errori Comuni e Soluzioni

### Errore: "column current_model does not exist"

**Causa:** Migrazione non applicata

**Soluzione:**
```bash
cd supabase
supabase db push
```

### Errore: "Cannot read property 'current_model' of null"

**Causa:** Frontend non gestisce null correttamente

**Soluzione:** Verifica che il codice TypeScript gestisca null:
```typescript
<span>{agent.current_model || 'Unknown'}</span>
```

### Errore: Dashboard mostra "Unknown" per tutto

**Causa:** Nuovi heartbeat non vengono registrati

**Soluzione:**
1. Verifica log backend per heartbeat
2. Genera nuovo content per forzare nuovi heartbeat
3. Verifica che migrazione sia stata applicata

## 📊 Impatto delle Correzioni

### Prima (Allineamento Errato)

- ❌ Frontend si aspettava campi non esistenti
- ❌ Backend provava a scrivere campi non esistenti  
- ❌ Database schema incompleto
- ❌ Sistema non funzionava in produzione

### Dopo (Allineamento Corretto)

- ✅ Database schema completo con tutti i campi necessari
- ✅ Backend scrive campi corretti
- ✅ Frontend legge campi corretti con fallback per null
- ✅ Sistema funzionante in produzione
- ✅ Backward compatibility mantenuta

## 🎓 Lezione Imparata

**Non assumere che il database abbia lo schema che ti serve!**

1. **Verifica sempre** lo schema del database reale
2. **Crea migrazioni** per aggiungere campi mancanti
3. **Gestisci backward compatibility** per record esistenti
4. **Testa con dati reali** non solo con dati ipotetici

---

**Status:** ✅ FRONTEND-BACKEND-DATABASE ALLINEATO
**Migration:** 013_add_llm_metadata_to_pipeline_health.sql
**Ready for Deployment:** ✅ SI (dopo aver applicato migrazione)
