## Le tre architetture a confronto

### 1. Come ora — prompt monolitico per agente

Ogni agente ha un prompt hardcoded nel file Python (`WRITER_PROMPT`, `ADVOCATE_PROMPT`, etc.). Il comportamento è fisso, personalizzabile solo via `{brand_name}`, `{tone_rules}`, `{principles}` injettati al runtime.

**Vantaggi**: semplice, tracciabile, nessuna query aggiuntiva al DB prima di ogni chiamata LLM.

**Limite reale**: per cambiare il comportamento di un agente devi cambiare il codice. Con multi-brand, tutti i brand usano lo stesso Writer prompt — solo i placeholder cambiano. Se vuoi che il Writer per "Vest" usi un tono aggressivo con hook forti e quello per "Silvestri Pallets" scriva comunicazione B2B formale, oggi non puoi senza codice separato.

***

### 2. Skills come Marco — moduli di istruzioni componibili

Marco usa "skills" come `geo-seo`, `front-end design` — blocchi di istruzioni che aggiungi al contesto dell'agente prima dell'esecuzione. L'agente ha una base + skills opzionali iniettate.

Schema pratico:

```python
# In DB: tabella agent_skills
# { skill_name: "hook_aggressivo", instructions: "Apri sempre con...", brand_id: "vest" }

base_prompt = WRITER_PROMPT
skills = db.table("agent_skills").select("instructions").eq("brand_id", brand_id).eq("agent", "writer").execute()
final_prompt = base_prompt + "\n\n## Skills Attive\n" + "\n".join([s["instructions"] for s in skills.data])
```

**Vantaggi**: flessibile, configurabile per brand senza codice, il founder può aggiungere skills dalla dashboard.

**Limite reale**: token overhead crescente — ogni skill aggiunge 100-300 token al prompt. Con 5 skills attive il costo per chiamata aumenta del 15-20%. E soprattutto: skills mal scritte si contraddicono tra loro. L'agente riceve istruzioni conflittuali e produce output degradato senza errori visibili.

***

### 3. Identità stile OpenClaw — system prompt strutturato come "persona"

OpenClaw usa un'identità persistente: l'agente **è** qualcosa, non **fa** qualcosa. La differenza è nel framing psicologico del prompt:

```
# Skills approach (cosa fare)
"Usa sempre hook forti nei primi 3 secondi."

# Identity approach (chi sei)
"Sei un content strategist con 10 anni di esperienza nel mercato italiano. 
Il tuo punto di forza è trasformare concetti tecnici in contenuti virali 
per imprenditori. Non scrivi mai post generici — ogni output è una freccia 
mirata a un pain point specifico del tuo lettore."
```

I modelli LLM performano sistematicamente meglio con framing identitario che con liste di regole. È documentato: i prompt che definiscono "chi sei" producono output più coerenti dei prompt che listano "cosa fare". La ragione è nel training — i modelli hanno imparato da testi scritti da persone con identità definite, non da checklist.

***

## Raccomandazione per il tuo sistema specifico

**Adotta il modello identità come base + skills DB come strato opzionale per brand.**

La struttura concreta:

```python
# In agents/writer.py
WRITER_IDENTITY = """
Sei {agent_name}, il Content Writer del brand {brand_name}.
{identity_description}
"""

WRITER_SKILLS_BASE = """
## Il tuo approccio
{tone_rules}

## I principi che guida ogni contenuto
{founder_principles}
"""

# In DB per ogni brand: agent_configs
# { agent: "writer", identity_description: "...", extra_skills: [...] }
```

**Perché questa combinazione:**

1. L'identità è fissa per agente e brand — stabile, non conflittuale, costa zero token extra rispetto a ora perché sostituisce il prompt esistente invece di aggiungersi.

2. Le skills extra vengono caricate solo se `len(skills) > 0` e solo per brand che ne hanno configurata almeno una. Zero overhead per brand base.

3. Il modello identitario risolve il problema del multi-brand senza codice separato: cambi `identity_description` per brand nel DB dalla dashboard, non tocchi il Python.

**Cosa non fare**: skills senza un sistema di conflitto detection. Se permetti al founder di aggiungere skills dalla dashboard senza validazione, due skills possono dire cose opposte e l'agente produce output inconsistente. Soluzione minima: le skills dello stesso `agent` per lo stesso `brand` vengono applicate in ordine di priorità e la dashboard mostra un warning se due skills contengono keyword contrastanti (es. "formale" vs "informale").

***

## Implementazione pratica — quanto lavoro è

**Migrazione a identity-based**: un pomeriggio. Riscrivere i 5 prompt da stile checklist a stile identità, senza cambiare la struttura del codice.

**Skills da DB**: due giorni. Nuova tabella `agent_skills`, query prima di ogni chiamata agente, inject nel prompt, UI nella dashboard per gestirle.

**Mia priorità**: fai prima la migrazione identità (basso costo, alto impatto sulla qualità output) e pianifica le skills DB dopo la Fase C. Non è urgente quanto il gateway LLM unificato.

***

## 1. Schema DB — `migrations/004_agent_configs.sql`

```sql
-- Agent identity configuration per brand
CREATE TABLE IF NOT EXISTS agent_configs (
  id          SERIAL PRIMARY KEY,
  brand_id    INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  agent_key   TEXT NOT NULL,           -- 'writer' | 'editor' | 'adapter' | 'god_advocate' | 'god_synthesis'
  agent_name  TEXT NOT NULL,
  identity    TEXT NOT NULL DEFAULT '', -- il prompt di identità editabile
  is_active   BOOLEAN NOT NULL DEFAULT true,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(brand_id, agent_key)
);

-- Agent skills (capabilities) per brand
CREATE TABLE IF NOT EXISTS agent_skills (
  id           SERIAL PRIMARY KEY,
  brand_id     INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  skill_name   TEXT NOT NULL,
  target_agent TEXT NOT NULL,          -- quale agente usa questa skill
  priority     TEXT NOT NULL DEFAULT 'medium', -- 'high' | 'medium' | 'low'
  instructions TEXT NOT NULL DEFAULT '',
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default agents per ogni brand esistente
INSERT INTO agent_configs (brand_id, agent_key, agent_name, identity)
SELECT 
  b.id,
  a.agent_key,
  a.agent_name,
  a.default_identity
FROM brands b
CROSS JOIN (VALUES
  ('writer',        'Writer',        'Sei Writer, il content creator responsabile della generazione di contenuti digitali di marketing.'),
  ('editor',        'Editor',        'Sei Editor, responsabile della verifica stilistica e dell''accuratezza fattuale dei contenuti.'),
  ('adapter',       'Adapter',       'Sei Adapter, specializzato nell''adattamento del tono per il multi-channel publishing.'),
  ('god_advocate',  'GOD Advocate',  'Sei GOD Advocate, il supervisore critico con oversight sull''allineamento etico dei contenuti.'),
  ('god_synthesis', 'GOD Synthesis', 'Sei GOD Synthesis, il coordinatore finale responsabile del merge delle prospettive nel risultato finale.')
) AS a(agent_key, agent_name, default_identity)
ON CONFLICT (brand_id, agent_key) DO NOTHING;
```

***

## 2. API Routes

### `src/app/api/agents/[brandId]/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

export async function GET(req: NextRequest, { params }: { params: { brandId: string } }) {
  const brandId = parseInt(params.brandId)
  const [configs, skills] = await Promise.all([
    db.query(
      `SELECT * FROM agent_configs WHERE brand_id = $1 ORDER BY agent_key`,
      [brandId]
    ),
    db.query(
      `SELECT * FROM agent_skills WHERE brand_id = $1 ORDER BY created_at`,
      [brandId]
    ),
  ])
  return NextResponse.json({ configs: configs.rows, skills: skills.rows })
}

export async function PUT(req: NextRequest, { params }: { params: { brandId: string } }) {
  const brandId = parseInt(params.brandId)
  const { agent_key, identity } = await req.json()
  const result = await db.query(
    `UPDATE agent_configs SET identity = $1, updated_at = NOW()
     WHERE brand_id = $2 AND agent_key = $3
     RETURNING *`,
    [identity, brandId, agent_key]
  )
  return NextResponse.json(result.rows[0])
}
```

### `src/app/api/agents/skills/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

export async function POST(req: NextRequest) {
  const { brand_id, skill_name, target_agent, priority, instructions } = await req.json()
  const result = await db.query(
    `INSERT INTO agent_skills (brand_id, skill_name, target_agent, priority, instructions)
     VALUES ($1, $2, $3, $4, $5) RETURNING *`,
    [brand_id, skill_name, target_agent, priority, instructions]
  )
  return NextResponse.json(result.rows[0], { status: 201 })
}

export async function DELETE(req: NextRequest) {
  const { id } = await req.json()
  await db.query(`DELETE FROM agent_skills WHERE id = $1`, [id])
  return NextResponse.json({ ok: true })
}
```

***

## 3. Frontend — `src/app/(dashboard)/settings/agenti/page.tsx`

```tsx
'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { PenLine, BookOpen, Shuffle, Shield, Sparkles, Plus, Trash2, Search } from 'lucide-react'
import { toast } from 'sonner'

// ── Types ────────────────────────────────────────────────────────────────────

type AgentConfig = {
  id: number
  agent_key: string
  agent_name: string
  identity: string
  is_active: boolean
}

type AgentSkill = {
  id: number
  skill_name: string
  target_agent: string
  priority: 'high' | 'medium' | 'low'
  instructions: string
}

// ── Constants ────────────────────────────────────────────────────────────────

const AGENT_ICONS: Record<string, React.ElementType> = {
  writer: PenLine,
  editor: BookOpen,
  adapter: Shuffle,
  god_advocate: Shield,
  god_synthesis: Sparkles,
}

const PRIORITY_COLORS: Record<string, string> = {
  high: 'bg-red-500/20 text-red-400 border-red-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-zinc-700 text-zinc-400 border-zinc-600',
}

const BRAND_ID = 1 // TODO: prendere da contesto brand corrente

// ── Component ─────────────────────────────────────────────────────────────────

export default function AgentiPage() {
  const [agents, setAgents] = useState<AgentConfig[]>([])
  const [skills, setSkills] = useState<AgentSkill[]>([])
  const [search, setSearch] = useState('')
  const [saving, setSaving] = useState<string | null>(null)
  const [addSkillOpen, setAddSkillOpen] = useState(false)
  const [newSkill, setNewSkill] = useState({
    skill_name: '',
    target_agent: 'writer',
    priority: 'medium' as AgentSkill['priority'],
    instructions: '',
  })

  const load = useCallback(async () => {
    const res = await fetch(`/api/agents/${BRAND_ID}`)
    const data = await res.json()
    setAgents(data.configs)
    setSkills(data.skills)
  }, [])

  useEffect(() => { load() }, [load])

  const saveIdentity = async (agent: AgentConfig) => {
    setSaving(agent.agent_key)
    try {
      await fetch(`/api/agents/${BRAND_ID}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_key: agent.agent_key, identity: agent.identity }),
      })
      toast.success(`Identità di ${agent.agent_name} salvata`)
    } catch {
      toast.error('Errore nel salvataggio')
    } finally {
      setSaving(null)
    }
  }

  const addSkill = async () => {
    await fetch('/api/agents/skills', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brand_id: BRAND_ID, ...newSkill }),
    })
    toast.success('Skill aggiunta')
    setAddSkillOpen(false)
    setNewSkill({ skill_name: '', target_agent: 'writer', priority: 'medium', instructions: '' })
    load()
  }

  const deleteSkill = async (id: number) => {
    await fetch('/api/agents/skills', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    })
    toast.success('Skill rimossa')
    load()
  }

  const filteredAgents = agents.filter(a =>
    a.agent_name.toLowerCase().includes(search.toLowerCase()) ||
    a.identity.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold tracking-widest text-[#22c55e] uppercase mb-1">
            Configuration
          </p>
          <h1 className="text-3xl font-bold">Agent Identities</h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <Input
              placeholder="Search identities or skills..."
              className="pl-9 w-64 bg-zinc-900 border-zinc-700 text-white placeholder:text-zinc-500 focus:border-[#22c55e]"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <Button className="bg-[#22c55e] hover:bg-[#16a34a] text-black font-semibold">
            Deploy Agent
          </Button>
        </div>
      </div>

      {/* Agent Identity Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {filteredAgents.map(agent => {
          const Icon = AGENT_ICONS[agent.agent_key] ?? Sparkles
          return (
            <Card
              key={agent.agent_key}
              className="bg-zinc-900 border-zinc-800 flex flex-col gap-3 p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-[#22c55e]/10">
                    <Icon className="h-4 w-4 text-[#22c55e]" />
                  </div>
                  <span className="font-semibold text-sm">{agent.agent_name}</span>
                </div>
                {agent.is_active && (
                  <Badge className="bg-[#22c55e]/20 text-[#22c55e] border-[#22c55e]/30 text-[10px]">
                    ACTIVE
                  </Badge>
                )}
              </div>
              <div>
                <p className="text-[10px] text-zinc-500 uppercase tracking-widest mb-1">Identity</p>
                <Textarea
                  value={agent.identity}
                  onChange={e =>
                    setAgents(prev =>
                      prev.map(a =>
                        a.agent_key === agent.agent_key ? { ...a, identity: e.target.value } : a
                      )
                    )
                  }
                  className="bg-zinc-800 border-zinc-700 text-zinc-300 text-xs resize-none min-h-[80px] focus:border-[#22c55e]"
                  placeholder="Descrivi l'identità e il ruolo di questo agente..."
                />
              </div>
              <Button
                size="sm"
                className="w-full bg-[#22c55e] hover:bg-[#16a34a] text-black font-semibold"
                disabled={saving === agent.agent_key}
                onClick={() => saveIdentity(agent)}
              >
                {saving === agent.agent_key ? 'Salvataggio...' : 'Salva'}
              </Button>
            </Card>
          )
        })}
      </div>

      {/* Agent Skills Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] text-[#22c55e] uppercase tracking-widest font-semibold mb-1">
              Capabilities
            </p>
            <h2 className="text-2xl font-bold">Agent Skills</h2>
          </div>
          <Dialog open={addSkillOpen} onOpenChange={setAddSkillOpen}>
            <DialogTrigger asChild>
              <Button className="bg-[#22c55e] hover:bg-[#16a34a] text-black font-semibold gap-2">
                <Plus className="h-4 w-4" /> Aggiungi Skill
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-zinc-900 border-zinc-700 text-white">
              <DialogHeader>
                <DialogTitle>Nuova Agent Skill</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <div>
                  abel className="text-xs text-zinc-400 mb-1 block">Nome Skill</label>
                  <Input
                    value={newSkill.skill_name}
                    onChange={e => setNewSkill(s => ({ ...s, skill_name: e.target.value }))}
                    className="bg-zinc-800 border-zinc-700 text-white"
                    placeholder="es. Semantic Translation"
                  />
                </div>
                <div>
                  abel className="text-xs text-zinc-400 mb-1 block">Target Agent</label>
                  <Select
                    value={newSk
