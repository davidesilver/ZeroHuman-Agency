# Phase 3 — Agent Dashboard UI (Planned)

> **Status**: 📋 Pianificato  
> **Prerequisito**: Phase 2 (Agent Skills DB) ✅  
> **Stima**: ~2 giorni  
> **Stack**: Next.js, React, shadcn/ui, Sonner toast

## Overview

Dashboard per configurare le identità degli agenti e gestire le skills per brand.
Pagina accessibile da `/settings/agenti` nella dashboard esistente.

---

## 1. Struttura File

```
src/app/(dashboard)/settings/agenti/
├── page.tsx            # Pagina principale
├── components/
│   ├── agent-card.tsx     # Card identità per singolo agente
│   ├── skills-table.tsx   # Tabella skills con CRUD
│   ├── add-skill-dialog.tsx  # Dialog per aggiungere skill
│   └── version-history.tsx   # Timeline versioni per rollback
```

---

## 2. Layout Pagina

```
┌─────────────────────────────────────────────────────────────┐
│  [Configuration]                                             │
│  Agent Identities                        [Search] [Deploy]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ Writer  │ │ Editor  │ │ Adapter │ │  GOD    │  ...      │
│  │ [ACTIVE]│ │ [ACTIVE]│ │ [ACTIVE]│ │  Adv.  │          │
│  │         │ │         │ │         │ │ [ACTIVE]│          │
│  │ [text]  │ │ [text]  │ │ [text]  │ │ [text]  │          │
│  │ [area]  │ │ [area]  │ │ [area]  │ │ [area]  │          │
│  │         │ │         │ │         │ │         │          │
│  │ [Salva] │ │ [Salva] │ │ [Salva] │ │ [Salva] │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  [Capabilities]                                              │
│  Agent Skills                            [+ Aggiungi Skill]  │
├─────────────────────────────────────────────────────────────┤
│  Skill Name    │ Target Agent │ Priority │ Actions            │
│  ─────────────────────────────────────────────────────────── │
│  Hook virali   │ Writer       │ [HIGH]   │ [Edit] [🗑️]        │
│  SEO Awareness │ Writer       │ [MED]    │ [Edit] [🗑️]        │
│  Tone check    │ Editor       │ [LOW]    │ [Edit] [🗑️]        │
├─────────────────────────────────────────────────────────────┤
│  [Version History]                                           │
│  Agent: Writer  │ v3 → v2 (rollback)  │ v1 (original)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Componente Principal — `page.tsx`

```tsx
'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogHeader,
  DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from '@/components/ui/table'
import {
  PenLine, BookOpen, Shuffle, Shield, Search as SearchIcon,
  Sparkles, Plus, Trash2, RotateCcw, Eye, CheckCircle
} from 'lucide-react'
import { toast } from 'sonner'
import { useBrand } from '@/hooks/use-brand'

// ── Types ──────────────────────────────────────────────────

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

// ── Constants ──────────────────────────────────────────────

const AGENT_ICONS: Record<string, React.ElementType> = {
  writer: PenLine,
  editor: BookOpen,
  adapter: Shuffle,
  god_advocate: Shield,
  god_factcheck: Eye,
  god_creative: Sparkles,
  god_synthesis: CheckCircle,
}

const PRIORITY_COLORS: Record<string, string> = {
  high: 'bg-red-500/20 text-red-400 border-red-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-zinc-700 text-zinc-400 border-zinc-600',
}

const PYTHON_API = process.env.NEXT_PUBLIC_PYTHON_API || 'http://localhost:8000'
```

---

## 4. API Calls (Next.js → FastAPI)

```tsx
// Fetch agent configs + skills
const loadAgents = async (brandId: string) => {
  const res = await fetch(`${PYTHON_API}/agents/${brandId}/configs`)
  return res.json()  // { configs: AgentConfig[], skills: AgentSkill[] }
}

// Update identity
const saveIdentity = async (brandId: string, agentKey: string, identity: string) => {
  await fetch(`${PYTHON_API}/agents/${brandId}/configs/${agentKey}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identity }),
  })
}

// Add skill
const addSkill = async (brandId: string, skill: Partial<AgentSkill>) => {
  await fetch(`${PYTHON_API}/agents/${brandId}/skills`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(skill),
  })
}

// Delete skill
const deleteSkill = async (skillId: string) => {
  await fetch(`${PYTHON_API}/agents/skills/${skillId}`, {
    method: 'DELETE',
  })
}

// Rollback identity
const rollbackIdentity = async (brandId: string, agentKey: string, version: number) => {
  await fetch(`${PYTHON_API}/agents/${brandId}/configs/${agentKey}/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ version }),
  })
}
```

---

## 5. Feature: Conflict Detection UI

Quando l'utente aggiunge una skill, il frontend effettua una validazione:

```tsx
const CONFLICTING_PAIRS = [
  ['formale', 'informale'],
  ['breve', 'lungo'],
  ['aggressivo', 'pacato'],
  ['tecnico', 'divulgativo'],
]

function detectConflicts(existingTags: string[], newTags: string[]): string[] {
  const all = new Set([...existingTags, ...newTags])
  return CONFLICTING_PAIRS
    .filter(([a, b]) => all.has(a) && all.has(b))
    .map(([a, b]) => `⚠️ "${a}" e "${b}" sono in conflitto`)
}
```

Il warning appare prima del save:

```
┌─────────────────────────────────────┐
│ ⚠️ Conflitto rilevato              │
│                                     │
│ La skill "Tono Informale" è in      │
│ conflitto con "Tono Formale"        │
│ (già attiva per Writer).            │
│                                     │
│ Vuoi procedere comunque?            │
│                                     │
│       [Annulla]   [Procedi]         │
└─────────────────────────────────────┘
```

---

## 6. Feature: Version History Timeline

```tsx
function VersionHistory({ brandId, agentKey }: Props) {
  const [versions, setVersions] = useState<Version[]>([])
  
  // Timeline visuale delle versioni
  return (
    <div className="space-y-2">
      {versions.map(v => (
        <div key={v.version} className="flex items-center gap-3 p-2 rounded bg-zinc-900">
          <Badge className="bg-zinc-700">v{v.version}</Badge>
          <span className="text-xs text-zinc-400 flex-1">
            {v.identity.substring(0, 80)}...
          </span>
          <Button 
            size="sm" variant="ghost"
            onClick={() => rollbackIdentity(brandId, agentKey, v.version)}
          >
            <RotateCcw className="h-3 w-3 mr-1" /> Ripristina
          </Button>
        </div>
      ))}
    </div>
  )
}
```

---

## 7. Navigazione Dashboard

Aggiungere voce nel sidebar della dashboard:

```tsx
// In layout.tsx o sidebar component
{
  label: 'Agenti',
  href: '/settings/agenti',
  icon: Sparkles,
  badge: 'NEW',
}
```

---

## 8. Responsive Design

| Breakpoint | Layout |
|---|---|
| `xl` (5 col) | 7 card in griglia 5 + 2 |
| `lg` (3 col) | 3 card per riga |
| `md` (2 col) | 2 card per riga |
| `sm` (1 col) | Card impilate verticalmente |

---

## 9. Checklist Implementazione Phase 3

- [ ] Creare `src/app/(dashboard)/settings/agenti/page.tsx`
- [ ] Implementare `AgentCard` component con textarea identity
- [ ] Implementare `SkillsTable` con add/delete
- [ ] Implementare `AddSkillDialog` con conflict detection
- [ ] Implementare `VersionHistory` con rollback
- [ ] Aggiungere voce "Agenti" nel sidebar
- [ ] Design system: rispettare dark theme `#0f0f0f` + accent `#22c55e`
- [ ] Test: CRUD operations via dashboard
- [ ] Test: cache invalidation dopo save (verificare nei log Python)
- [ ] Test: responsive layout su mobile

---

→ Precedente: [Phase 2: Agent Skills DB](./AGENT_SKILLS_DB.md)
