# Content Engine "Empty Box" — Documentazione

> Sistema AI modulare per l'automazione completa di contenuti multi-brand.
> 95% AI agents / 5% supervisione umana.

---

## Cos'e' questo progetto?

**Empty Box** e' un motore di content automation che ricerca, valuta, genera, rivede e pubblica contenuti su piu' piattaforme — con intervento umano minimo. Il sistema e' una "scatola vuota": cambiando la configurazione del brand, lo stesso motore funziona per business completamente diversi.

Ispirato al sistema "Spiegamelo" di Marco Montemagno, progettato per scalare a piu' brand con costi operativi ~€400-500/mese per brand (vs €9.000-14.000/mese per un team umano equivalente).

---

## Indice Documentazione

Leggi i documenti in questo ordine per capire il progetto da zero:

### 1. Architettura e Stack
| Documento | Descrizione |
|-----------|-------------|
| [ARCHITECTURE.md](architecture/ARCHITECTURE.md) | Visione del progetto, modello 95/5, architettura generale, flusso dati end-to-end, componenti del sistema |
| [TECH_STACK.md](architecture/TECH_STACK.md) | Ogni tecnologia scelta con motivazione e alternative scartate |

### 2. Database
| Documento | Descrizione |
|-----------|-------------|
| [SCHEMA.md](database/SCHEMA.md) | Schema completo: 18 tabelle, relazioni, indici, RLS policies, views |
| [001_initial_schema.sql](database/001_initial_schema.sql) | Migration SQL pronta per Supabase (1200+ righe) |

### 3. API
| Documento | Descrizione |
|-----------|-------------|
| [API_SPECIFICATION.md](api/API_SPECIFICATION.md) | 50+ endpoint REST organizzati per modulo, request/response types, WebSocket events, rate limiting |

### 4. Agenti AI e Pipeline
| Documento | Descrizione |
|-----------|-------------|
| [AGENTS.md](agents/AGENTS.md) | Specifica di tutti i 14+ agenti AI: research, scoring, writer, editor, adapter, GOD system |
| [PIPELINES.md](agents/PIPELINES.md) | 8 pipeline di automazione: research, scoring, generation, GOD mode, newsletter, publishing, analytics, writing lab |

### 5. Configurazione
| Documento | Descrizione |
|-----------|-------------|
| [BRAND_CONFIG.md](config/BRAND_CONFIG.md) | Struttura completa `brand.config.ts` con tutti i parametri, esempio per brand "Vest", validazione |

### 6. Design UI
| Documento | Descrizione |
|-----------|-------------|
| [DESIGN_SYSTEM.md](design/DESIGN_SYSTEM.md) | Design tokens (colori, tipografia, spacing), componenti shadcn/ui, pattern layout |
| [SCREENS.md](design/SCREENS.md) | Specifica delle 10 schermate dashboard con dati, componenti e endpoint collegati |

### 7. Operativo
| Documento | Descrizione |
|-----------|-------------|
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Roadmap a 5 fasi (9 settimane), checklist per ogni fase, metriche di successo, rischi |
| [SECURITY.md](SECURITY.md) | Auth, RLS, GDPR, gestione secrets, OWASP, rate limiting, backup, monitoring |
| [COSTS.md](COSTS.md) | Breakdown costi dettagliato, confronto team umano, proiezioni multi-brand, ottimizzazione |

---

## Quick Start

Per iniziare a costruire il progetto:

1. **Leggi** [ARCHITECTURE.md](architecture/ARCHITECTURE.md) per capire il sistema
2. **Leggi** [TECH_STACK.md](architecture/TECH_STACK.md) per capire le scelte tecnologiche
3. **Esegui** [001_initial_schema.sql](database/001_initial_schema.sql) su Supabase
4. **Configura** il primo brand seguendo [BRAND_CONFIG.md](config/BRAND_CONFIG.md)
5. **Segui** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) fase per fase

---

## Struttura Directory Target

```
/content-engine/
├── docs/                    ← Questa documentazione
│   ├── architecture/        ← Architettura e tech stack
│   ├── database/            ← Schema e migration SQL
│   ├── api/                 ← Specifiche API
│   ├── agents/              ← Agenti AI e pipeline
│   ├── config/              ← Configurazione brand
│   └── design/              ← Design system e schermate
│
├── src/                     ← Next.js frontend
│   ├── app/                 ← App Router pages
│   ├── components/          ← Componenti React (shadcn/ui)
│   └── lib/                 ← Utilities, types, Supabase client
│
├── python/                  ← Backend Python
│   ├── agents/              ← Agenti AI (research, scoring, writer, GOD)
│   ├── pipelines/           ← Orchestrazione pipeline
│   └── utils/               ← Utilities comuni
│
├── supabase/                ← Database
│   └── migrations/          ← Migration SQL
│
├── config/                  ← Configurazioni brand
│   └── brands/              ← Un file per brand
│
├── n8n/                     ← Workflow n8n (esportati)
│
├── references/              ← Screenshot e reference visive
│   └── marco-montemagno/    ← 22 screenshot del sistema originale
│
└── scripts/                 ← Script automazione
```

---

## Fonti e Riferimenti

- **Perplexity Research**: [Conversazione completa](https://www.perplexity.ai/search/ho-un-obbiettivo-ambizioso-que-ojwu26vaQsOiBzq8sMjnYA#34) — 34+ messaggi con analisi dettagliata del sistema Montemagno
- **Google Stitch**: [Progetto UI](https://stitch.withgoogle.com/projects/11155826360611895417) — 10 schermate dashboard con design system "Chromatic Grid"
- **Marco Montemagno**: Sistema "Spiegamelo" — reference architetturale
- **Andrej Karpathy**: Concept AutoResearch per feedback loop automatico

---

## Stato del Progetto

| Fase | Status | Completamento |
|------|--------|---------------|
| Documentazione | ✅ Completata | 13/13 documenti |
| Database schema | ✅ Pronto | Migration SQL pronta |
| Design UI | ✅ Reference | 10 schermate specificate |
| Frontend | ⬜ Da iniziare | 0% |
| Backend agents | ⬜ Da iniziare | 0% |
| Distribution | ⬜ Da iniziare | 0% |
| Testing | ⬜ Da iniziare | 0% |
