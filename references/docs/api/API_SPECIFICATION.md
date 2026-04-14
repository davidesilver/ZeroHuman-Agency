# Specifica API - AI Content Engine

> Documentazione completa di tutti gli endpoint API del sistema AI Content Engine.
> Ultimo aggiornamento: 2026-04-11

---

## Indice

- [Architettura](#architettura)
- [Autenticazione](#autenticazione)
- [Formato Risposte](#formato-risposte)
- [Rate Limiting](#rate-limiting)
- [Gestione Errori](#gestione-errori)
- [Endpoint per Modulo](#endpoint-per-modulo)
  - [Research](#research)
  - [Scoring](#scoring)
  - [Content](#content)
  - [Newsletter](#newsletter)
  - [Calendar](#calendar)
  - [Writing Lab](#writing-lab)
  - [Metrics](#metrics)
  - [Revenue](#revenue)
  - [System](#system)
  - [Brand Config](#brand-config)
- [WebSocket Events](#websocket-events)
- [Procedure tRPC](#procedure-trpc)

---

## Architettura

Il sistema utilizza **Next.js API Routes** come layer REST e **tRPC** per la comunicazione type-safe tra frontend e backend. Tutte le API sono esposte sotto il prefisso `/api/`.

```
Frontend (Next.js)
    |
    |-- tRPC Client (type-safe, per operazioni interne)
    |-- fetch/axios (per endpoint REST pubblici)
    |
    v
Next.js API Routes (/api/*)
    |
    |-- Middleware Auth (Supabase JWT verification)
    |-- tRPC Router (per procedure type-safe)
    |
    v
Supabase (PostgreSQL + RLS)
```

### Stack Tecnologico

| Componente | Tecnologia |
|---|---|
| Frontend | Next.js 14+ (App Router) |
| API Layer | Next.js API Routes + tRPC v11 |
| Autenticazione | Supabase Auth (JWT) |
| Database | Supabase PostgreSQL con RLS |
| Real-time | WebSocket (Supabase Realtime + custom) |
| Type Safety | TypeScript + Zod validation |

---

## Autenticazione

### Provider

**Supabase Auth** con token JWT.

### Headers Richiesti

Tutti gli endpoint (eccetto `/api/system/health`) richiedono l'header di autorizzazione:

```
Authorization: Bearer <supabase_jwt_token>
```

### Flusso di Autenticazione

1. Il client si autentica tramite Supabase Auth (email/password, OAuth, magic link)
2. Supabase rilascia un JWT contenente `user_id` e metadata
3. Il JWT viene inviato in ogni richiesta API nell'header `Authorization`
4. Il middleware API verifica il JWT tramite `supabase.auth.getUser()`
5. Il `brand_id` viene estratto dal profilo utente e iniettato nel contesto della richiesta
6. **Row Level Security (RLS)** di Supabase filtra automaticamente tutti i dati per `brand_id`

### Esempio di Richiesta Autenticata

```typescript
const response = await fetch('/api/research/runs', {
  headers: {
    'Authorization': `Bearer ${session.access_token}`,
    'Content-Type': 'application/json'
  }
});
```

### Ruoli

| Ruolo | Descrizione | Permessi |
|---|---|---|
| `owner` | Proprietario del brand | Accesso completo, gestione utenti |
| `editor` | Editor contenuti | CRUD contenuti, approvazione |
| `viewer` | Visualizzatore | Solo lettura |

---

## Formato Risposte

### Risposta di Successo

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

### Risposta di Errore

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Descrizione leggibile dell'errore",
    "details": [
      {
        "field": "title",
        "message": "Il campo title e' obbligatorio"
      }
    ]
  }
}
```

### Paginazione

Tutti gli endpoint che restituiscono liste supportano paginazione:

| Parametro | Tipo | Default | Descrizione |
|---|---|---|---|
| `page` | number | 1 | Numero pagina |
| `per_page` | number | 20 | Elementi per pagina (max 100) |
| `sort_by` | string | `created_at` | Campo di ordinamento |
| `sort_order` | string | `desc` | Direzione: `asc` o `desc` |

---

## Rate Limiting

I limiti sono applicati per utente autenticato (basati su `user_id` nel JWT).

| Categoria Endpoint | Limite | Finestra |
|---|---|---|
| **Lettura** (GET) | 200 richieste | 1 minuto |
| **Scrittura** (POST/PUT/PATCH) | 50 richieste | 1 minuto |
| **Generazione AI** (trigger, generate, god-mode) | 10 richieste | 5 minuti |
| **Invio Newsletter** (send) | 3 richieste | 1 ora |
| **WebSocket** | 5 connessioni simultanee | - |

### Headers di Rate Limiting

Ogni risposta include:

```
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 195
X-RateLimit-Reset: 1712851200
```

### Superamento Limite

Quando il limite viene superato, l'API restituisce:

```
HTTP 429 Too Many Requests

{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Limite richieste superato. Riprova tra 45 secondi.",
    "retry_after": 45
  }
}
```

---

## Gestione Errori

### Codici di Errore Standard

| Codice HTTP | Codice Errore | Descrizione |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Parametri di input non validi |
| 401 | `UNAUTHORIZED` | Token JWT mancante o non valido |
| 403 | `FORBIDDEN` | Permessi insufficienti per l'operazione |
| 404 | `NOT_FOUND` | Risorsa non trovata |
| 409 | `CONFLICT` | Conflitto di stato (es. newsletter gia' inviata) |
| 422 | `UNPROCESSABLE_ENTITY` | Richiesta ben formata ma semanticamente errata |
| 429 | `RATE_LIMIT_EXCEEDED` | Limite richieste superato |
| 500 | `INTERNAL_ERROR` | Errore interno del server |
| 502 | `AI_PROVIDER_ERROR` | Errore dal provider AI (Anthropic, Serper) |
| 503 | `SERVICE_UNAVAILABLE` | Servizio temporaneamente non disponibile |
| 504 | `AI_TIMEOUT` | Timeout nella generazione AI |

### Codici di Errore Specifici per Dominio

| Codice Errore | Descrizione |
|---|---|
| `RESEARCH_IN_PROGRESS` | Una sessione di ricerca e' gia' in corso |
| `SCORING_INCOMPLETE` | Scoring non completato per tutti gli items |
| `DRAFT_ALREADY_APPROVED` | La bozza e' gia' stata approvata |
| `NEWSLETTER_ALREADY_SENT` | La newsletter e' gia' stata inviata |
| `SLOT_ALREADY_FILLED` | Lo slot della newsletter e' gia' assegnato |
| `INSUFFICIENT_CANDIDATES` | Non ci sono abbastanza candidati per la newsletter |
| `BRAND_CONFIG_INCOMPLETE` | Configurazione brand incompleta |
| `WRITING_LAB_SESSION_CLOSED` | La sessione Writing Lab e' chiusa |

---

## Endpoint per Modulo

---

### Research

Gestione delle sessioni di ricerca automatica e degli items trovati dai retriever.

---

#### POST /api/research/trigger

Avvia una nuova sessione di ricerca. Attiva tutti i retriever configurati per il brand.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 10 req / 5 min |

**Request Body:**

```json
{
  "retrievers": ["semantic", "practitioner", "trusted_source", "keyword", "trend"],
  "force": false,
  "options": {
    "max_items_per_retriever": 100,
    "dedup_threshold": 0.85
  }
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `retrievers` | string[] | No | Retriever da attivare (default: tutti) |
| `force` | boolean | No | Forza esecuzione anche se un run e' in corso (default: false) |
| `options.max_items_per_retriever` | number | No | Limite items per retriever (default: 100) |
| `options.dedup_threshold` | number | No | Soglia deduplicazione 0-1 (default: 0.85) |

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "run_id": "run_abc123",
    "status": "running",
    "started_at": "2026-04-11T07:00:00Z",
    "retrievers_activated": ["semantic", "practitioner", "trusted_source", "keyword", "trend"],
    "estimated_duration_seconds": 180
  }
}
```

**Errori Specifici:**

| Codice | Descrizione |
|---|---|
| 409 `RESEARCH_IN_PROGRESS` | Una sessione e' gia' in esecuzione e `force` non e' `true` |
| 422 `BRAND_CONFIG_INCOMPLETE` | Manca configurazione topics o sources nel brand |

---

#### GET /api/research/runs

Restituisce la lista delle sessioni di ricerca, ordinate per data decrescente.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `status` | string | No | Filtra per stato: `running`, `completed`, `failed` |
| `from` | string (ISO date) | No | Data inizio range |
| `to` | string (ISO date) | No | Data fine range |
| `page` | number | No | Pagina (default: 1) |
| `per_page` | number | No | Elementi per pagina (default: 20) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": "run_abc123",
      "status": "completed",
      "started_at": "2026-04-11T07:00:00Z",
      "completed_at": "2026-04-11T07:03:12Z",
      "duration_seconds": 192,
      "total_items_found": 253,
      "items_after_dedup": 198,
      "retriever_counts": {
        "semantic": 83,
        "practitioner": 77,
        "trusted_source": 43,
        "keyword": 37,
        "trend": 13
      },
      "trigger_type": "cron"
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

---

#### GET /api/research/runs/:id

Restituisce il dettaglio completo di una sessione di ricerca.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Path Parameters:**

| Parametro | Tipo | Descrizione |
|---|---|---|
| `id` | string | ID della sessione di ricerca |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "run_abc123",
    "status": "completed",
    "started_at": "2026-04-11T07:00:00Z",
    "completed_at": "2026-04-11T07:03:12Z",
    "duration_seconds": 192,
    "trigger_type": "cron",
    "config_snapshot": {
      "topics": ["AI", "automation", "productivity"],
      "sources_count": 24,
      "dedup_threshold": 0.85
    },
    "retriever_results": [
      {
        "retriever": "semantic",
        "status": "completed",
        "items_found": 83,
        "items_after_dedup": 71,
        "duration_seconds": 45,
        "errors": []
      }
    ],
    "total_items_found": 253,
    "items_after_dedup": 198,
    "items_scored": 198,
    "items_approved": 0,
    "cost_estimate_usd": 0.42
  }
}
```

---

#### GET /api/research/items

Restituisce la lista degli items trovati dalla ricerca, con filtri avanzati.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `run_id` | string | No | Filtra per sessione di ricerca |
| `status` | string | No | `pending`, `approved`, `rejected`, `archived` |
| `retriever_type` | string | No | `semantic`, `practitioner`, `trusted_source`, `keyword`, `trend` |
| `score_min` | number | No | Score minimo (0-10) |
| `score_max` | number | No | Score massimo (0-10) |
| `is_top_pick` | boolean | No | Solo top picks |
| `search` | string | No | Ricerca full-text su titolo e summary |
| `page` | number | No | Pagina (default: 1) |
| `per_page` | number | No | Elementi per pagina (default: 20) |
| `sort_by` | string | No | `score`, `created_at`, `title` (default: `score`) |
| `sort_order` | string | No | `asc` o `desc` (default: `desc`) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": "item_xyz789",
      "run_id": "run_abc123",
      "title": "Come l'AI sta trasformando il project management",
      "url": "https://example.com/article",
      "source": "example.com",
      "summary": "Analisi dettagliata di 5 tool AI per PM...",
      "retriever_type": "semantic",
      "status": "pending",
      "is_top_pick": false,
      "score": {
        "final_score": 8.2,
        "scored_at": "2026-04-11T07:05:00Z"
      },
      "created_at": "2026-04-11T07:01:23Z",
      "content_drafts_count": 0
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 198,
    "total_pages": 10
  }
}
```

---

#### PATCH /api/research/items/:id

Aggiorna lo status di un item di ricerca (approvazione, rifiuto, archiviazione).

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Path Parameters:**

| Parametro | Tipo | Descrizione |
|---|---|---|
| `id` | string | ID dell'item |

**Request Body:**

```json
{
  "status": "approved",
  "notes": "Ottimo contenuto, adatto per newsletter"
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `status` | string | Si | `approved`, `rejected`, `archived` |
| `notes` | string | No | Note editoriali |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "item_xyz789",
    "status": "approved",
    "notes": "Ottimo contenuto, adatto per newsletter",
    "updated_at": "2026-04-11T10:15:00Z",
    "updated_by": "user_123"
  }
}
```

---

#### POST /api/research/items/:id/top-pick

Segna un item come top pick. I top picks hanno priorita' nella generazione contenuti e nella selezione newsletter.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Path Parameters:**

| Parametro | Tipo | Descrizione |
|---|---|---|
| `id` | string | ID dell'item |

**Request Body:**

```json
{
  "is_top_pick": true,
  "reason": "Perfetto per la rubrica 'Il Sistema' della newsletter"
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `is_top_pick` | boolean | Si | `true` per segnare, `false` per rimuovere |
| `reason` | string | No | Motivazione della selezione |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "item_xyz789",
    "is_top_pick": true,
    "reason": "Perfetto per la rubrica 'Il Sistema' della newsletter",
    "marked_at": "2026-04-11T10:20:00Z",
    "marked_by": "user_123"
  }
}
```

---

### Scoring

Gestione del sistema di scoring multi-parametro per valutare la qualita' e rilevanza degli items.

---

#### POST /api/scoring/run

Esegue lo scoring batch su tutti gli items non ancora valutati.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 10 req / 5 min |

**Request Body:**

```json
{
  "run_id": "run_abc123",
  "force_rescore": false,
  "items_filter": {
    "status": "pending",
    "retriever_type": null
  }
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `run_id` | string | No | Limita scoring a un run specifico |
| `force_rescore` | boolean | No | Riesegui scoring anche su items gia' valutati (default: false) |
| `items_filter` | object | No | Filtri aggiuntivi sugli items da processare |

**Response (202 Accepted):**

```json
{
  "success": true,
  "data": {
    "scoring_job_id": "score_job_456",
    "items_to_score": 87,
    "estimated_duration_seconds": 120,
    "estimated_cost_usd": 0.15,
    "status": "processing"
  }
}
```

---

#### GET /api/scoring/items/:id

Restituisce il dettaglio dello score di un item con breakdown per parametro.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Path Parameters:**

| Parametro | Tipo | Descrizione |
|---|---|---|
| `id` | string | ID dell'item |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "item_id": "item_xyz789",
    "final_score": 8.2,
    "scored_at": "2026-04-11T07:05:00Z",
    "scoring_model": "claude-sonnet-4-20250514",
    "breakdown": {
      "applicability_concreteness": {
        "score": 9.0,
        "weight": 0.25,
        "weighted_score": 2.25,
        "reasoning": "Contiene 3 framework applicabili immediatamente con esempi concreti"
      },
      "credibility": {
        "score": 8.5,
        "weight": 0.20,
        "weighted_score": 1.70,
        "reasoning": "Autore con track record verificabile, citazioni peer-reviewed"
      },
      "alignment": {
        "score": 7.5,
        "weight": 0.20,
        "weighted_score": 1.50,
        "reasoning": "Allineato ai principi del founder su automazione, leggermente tangenziale su AI"
      },
      "trend_prediction": {
        "score": 8.0,
        "weight": 0.15,
        "weighted_score": 1.20,
        "reasoning": "Tema in crescita confermata, finestra 3-6 mesi per early adoption"
      },
      "italy_relevance": {
        "score": 7.0,
        "weight": 0.10,
        "weighted_score": 0.70,
        "reasoning": "Applicabile al mercato italiano con adattamenti minimi"
      },
      "feedback_loop_bonus": {
        "score": 1.5,
        "weight": 0.10,
        "weighted_score": 0.15,
        "reasoning": "Topic simili hanno avuto engagement +25% nelle ultime 4 settimane"
      }
    },
    "total_weighted": 7.50,
    "feedback_adjusted": 8.20
  }
}
```

---

#### PUT /api/scoring/weights

Aggiorna i pesi del sistema di scoring per il brand corrente.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `owner` |
| **Rate Limit** | 50 req / min |

**Request Body:**

```json
{
  "weights": {
    "applicability_concreteness": 0.25,
    "credibility": 0.20,
    "alignment": 0.20,
    "trend_prediction": 0.15,
    "italy_relevance": 0.10,
    "feedback_loop_bonus": 0.10
  }
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `weights` | object | Si | Mappa parametro-peso. La somma dei pesi deve essere 1.0 |

**Validazione:** La somma di tutti i pesi deve essere esattamente `1.0`. In caso contrario, l'API restituisce un errore `VALIDATION_ERROR`.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "weights": {
      "applicability_concreteness": 0.25,
      "credibility": 0.20,
      "alignment": 0.20,
      "trend_prediction": 0.15,
      "italy_relevance": 0.10,
      "feedback_loop_bonus": 0.10
    },
    "updated_at": "2026-04-11T14:00:00Z",
    "updated_by": "user_123",
    "note": "Il rescoring degli items esistenti non e' automatico. Usa POST /api/scoring/run con force_rescore=true per applicare i nuovi pesi."
  }
}
```

---

### Content

Gestione della generazione, revisione e approvazione dei contenuti multi-formato.

---

#### GET /api/content/drafts

Restituisce la lista delle bozze di contenuto con filtri avanzati.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `status` | string | No | `draft`, `in_review`, `god_review`, `approved`, `published`, `archived` |
| `platform` | string | No | `linkedin`, `x`, `instagram`, `facebook`, `tiktok`, `newsletter`, `blog` |
| `content_type` | string | No | `post`, `carousel`, `video_script`, `article`, `newsletter_section` |
| `item_id` | string | No | Filtra per item di ricerca sorgente |
| `search` | string | No | Ricerca full-text |
| `page` | number | No | Pagina (default: 1) |
| `per_page` | number | No | Elementi per pagina (default: 20) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": "draft_001",
      "title": "5 Framework AI per il Project Management",
      "platform": "linkedin",
      "content_type": "post",
      "status": "draft",
      "source_item_id": "item_xyz789",
      "current_version": 2,
      "word_count": 450,
      "created_at": "2026-04-11T10:30:00Z",
      "updated_at": "2026-04-11T11:15:00Z",
      "god_review": null,
      "scheduled_at": null
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 34,
    "total_pages": 2
  }
}
```

---

#### POST /api/content/generate

Genera un nuovo contenuto a partire da un research item approvato.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 10 req / 5 min |

**Request Body:**

```json
{
  "item_id": "item_xyz789",
  "platform": "linkedin",
  "content_type": "post",
  "options": {
    "tone": "professional",
    "length": "medium",
    "include_cta": true,
    "language": "it",
    "custom_instructions": "Enfatizza l'aspetto pratico e includi un esempio concreto"
  }
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `item_id` | string | Si | ID dell'item di ricerca sorgente |
| `platform` | string | Si | Piattaforma target: `linkedin`, `x`, `instagram`, `facebook`, `tiktok`, `newsletter`, `blog` |
| `content_type` | string | Si | Tipo contenuto: `post`, `carousel`, `video_script`, `article`, `newsletter_section` |
| `options.tone` | string | No | Override tono (default: da brand config) |
| `options.length` | string | No | `short`, `medium`, `long` (default: `medium`) |
| `options.include_cta` | boolean | No | Includere CTA (default: true) |
| `options.language` | string | No | Lingua output (default: `it`) |
| `options.custom_instructions` | string | No | Istruzioni aggiuntive per il writer |

**Response (202 Accepted):**

```json
{
  "success": true,
  "data": {
    "draft_id": "draft_001",
    "status": "generating",
    "pipeline": {
      "steps": ["writer", "editor", "adapter"],
      "current_step": "writer",
      "estimated_duration_seconds": 45
    },
    "estimated_cost_usd": 0.08
  }
}
```

**Errori Specifici:**

| Codice | Descrizione |
|---|---|
| 404 `NOT_FOUND` | Item di ricerca non trovato |
| 422 `UNPROCESSABLE_ENTITY` | Item non approvato o configurazione brand incompleta |

---

#### GET /api/content/drafts/:id

Restituisce il dettaglio di una bozza con tutte le versioni.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Path Parameters:**

| Parametro | Tipo | Descrizione |
|---|---|---|
| `id` | string | ID della bozza |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "draft_001",
    "title": "5 Framework AI per il Project Management",
    "platform": "linkedin",
    "content_type": "post",
    "status": "draft",
    "source_item": {
      "id": "item_xyz789",
      "title": "Come l'AI sta trasformando il project management",
      "score": 8.2
    },
    "current_version": 2,
    "versions": [
      {
        "version": 1,
        "content": "Testo completo della versione 1...",
        "agent": "opus_writer",
        "created_at": "2026-04-11T10:30:00Z",
        "word_count": 420,
        "metadata": {
          "model": "claude-opus-4-20250514",
          "tokens_used": 1850,
          "generation_time_ms": 12400
        }
      },
      {
        "version": 2,
        "content": "Testo completo della versione 2 (post-editing)...",
        "agent": "opus_editor",
        "created_at": "2026-04-11T10:31:15Z",
        "word_count": 450,
        "changes_summary": "Migliorata struttura, aggiunto esempio concreto, rafforzata CTA",
        "metadata": {
          "model": "claude-opus-4-20250514",
          "tokens_used": 2100,
          "generation_time_ms": 8900
        }
      }
    ],
    "god_review": null,
    "scheduled_at": null,
    "created_at": "2026-04-11T10:30:00Z",
    "updated_at": "2026-04-11T11:15:00Z"
  }
}
```

---

#### PATCH /api/content/drafts/:id

Aggiorna manualmente una bozza (modifica contenuto, titolo, note).

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Request Body:**

```json
{
  "content": "Testo aggiornato manualmente...",
  "title": "Nuovo titolo opzionale",
  "notes": "Modifica manuale: sistemato refuso al paragrafo 3"
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `content` | string | No | Nuovo contenuto (crea nuova versione) |
| `title` | string | No | Nuovo titolo |
| `notes` | string | No | Note sulla modifica |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "draft_001",
    "current_version": 3,
    "status": "draft",
    "updated_at": "2026-04-11T12:00:00Z"
  }
}
```

---

#### POST /api/content/drafts/:id/approve

Approva una bozza per la pubblicazione.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Request Body:**

```json
{
  "scheduled_at": "2026-04-12T09:00:00Z",
  "notes": "Pronta per pubblicazione domani mattina"
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `scheduled_at` | string (ISO date) | No | Data/ora di pubblicazione programmata |
| `notes` | string | No | Note di approvazione |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "draft_001",
    "status": "approved",
    "approved_at": "2026-04-11T12:30:00Z",
    "approved_by": "user_123",
    "scheduled_at": "2026-04-12T09:00:00Z"
  }
}
```

**Errori Specifici:**

| Codice | Descrizione |
|---|---|
| 409 `DRAFT_ALREADY_APPROVED` | La bozza e' gia' stata approvata |

---

#### POST /api/content/drafts/:id/god-mode

Avvia la revisione GOD System sulla bozza. Attiva sequenzialmente: Advocate, Factchecker, Creative, Synthesis.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 10 req / 5 min |

**Request Body:**

```json
{
  "agents": ["advocate", "factchecker", "creative", "synthesis"],
  "strictness": "high",
  "focus_areas": ["accuracy", "originality"]
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `agents` | string[] | No | Agenti GOD da attivare (default: tutti) |
| `strictness` | string | No | Livello di rigore: `low`, `medium`, `high` (default: `medium`) |
| `focus_areas` | string[] | No | Aree di focus: `accuracy`, `originality`, `engagement`, `brand_voice` |

**Response (202 Accepted):**

```json
{
  "success": true,
  "data": {
    "review_id": "god_review_789",
    "draft_id": "draft_001",
    "status": "processing",
    "pipeline": {
      "steps": [
        {"agent": "advocate", "status": "processing"},
        {"agent": "factchecker", "status": "pending"},
        {"agent": "creative", "status": "pending"},
        {"agent": "synthesis", "status": "pending"}
      ]
    },
    "estimated_duration_seconds": 90,
    "estimated_cost_usd": 0.25
  }
}
```

---

#### DELETE /api/content/drafts/:id

Archivia una bozza (soft delete). La bozza non viene eliminata ma spostata nello stato `archived`.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "draft_001",
    "status": "archived",
    "archived_at": "2026-04-11T15:00:00Z",
    "archived_by": "user_123"
  }
}
```

**Errori Specifici:**

| Codice | Descrizione |
|---|---|
| 409 `CONFLICT` | Non e' possibile archiviare una bozza gia' pubblicata |

---

### Newsletter

Gestione del ciclo di vita completo della newsletter: generazione, composizione, preview e invio.

---

#### GET /api/newsletter

Restituisce la lista delle newsletter.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `status` | string | No | `draft`, `composing`, `preview`, `scheduled`, `sent` |
| `from` | string (ISO date) | No | Data inizio |
| `to` | string (ISO date) | No | Data fine |
| `page` | number | No | Pagina |
| `per_page` | number | No | Elementi per pagina |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": "nl_001",
      "subject": "AI Automation Weekly #42",
      "status": "sent",
      "edition_number": 42,
      "slots": {
        "sistema": {"filled": true, "item_title": "Framework AI per PM"},
        "strumento": {"filled": true, "item_title": "Review di Cursor AI"},
        "mossa": {"filled": true, "item_title": "Automatizzare il reporting"}
      },
      "scheduled_at": "2026-04-08T07:00:00Z",
      "sent_at": "2026-04-08T07:01:12Z",
      "recipients_count": 4850,
      "created_at": "2026-04-07T10:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 42,
    "total_pages": 3
  }
}
```

---

#### POST /api/newsletter/generate

Genera una nuova newsletter selezionando automaticamente i candidati migliori per ogni slot.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 10 req / 5 min |

**Request Body:**

```json
{
  "edition_number": 43,
  "subject_prefix": "AI Automation Weekly",
  "slots_config": {
    "sistema": {
      "candidates_count": 3,
      "min_score": 7.5,
      "preferred_retrievers": ["semantic", "practitioner"]
    },
    "strumento": {
      "candidates_count": 3,
      "min_score": 7.0,
      "preferred_retrievers": ["keyword", "trend"]
    },
    "mossa": {
      "candidates_count": 3,
      "min_score": 7.0,
      "preferred_retrievers": ["practitioner", "trusted_source"]
    }
  },
  "date_range": {
    "from": "2026-04-04",
    "to": "2026-04-11"
  }
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `edition_number` | number | Si | Numero edizione |
| `subject_prefix` | string | No | Prefisso oggetto (default: da brand config) |
| `slots_config` | object | No | Configurazione per slot (default: config standard) |
| `slots_config.*.candidates_count` | number | No | Numero candidati da generare per slot (default: 3) |
| `slots_config.*.min_score` | number | No | Score minimo candidati (default: 7.0) |
| `slots_config.*.preferred_retrievers` | string[] | No | Retriever preferiti per la selezione |
| `date_range` | object | No | Range date per items da considerare |

**Response (202 Accepted):**

```json
{
  "success": true,
  "data": {
    "newsletter_id": "nl_002",
    "edition_number": 43,
    "status": "composing",
    "slots": {
      "sistema": {
        "candidates_generating": 3,
        "status": "processing"
      },
      "strumento": {
        "candidates_generating": 3,
        "status": "processing"
      },
      "mossa": {
        "candidates_generating": 3,
        "status": "processing"
      }
    },
    "estimated_duration_seconds": 180,
    "estimated_cost_usd": 0.85
  }
}
```

---

#### GET /api/newsletter/:id

Restituisce il dettaglio della newsletter con tutti i candidati per ogni slot.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "nl_002",
    "edition_number": 43,
    "subject": "AI Automation Weekly #43",
    "status": "composing",
    "slots": {
      "sistema": {
        "selected_candidate_id": null,
        "candidates": [
          {
            "id": "cand_001",
            "source_item_id": "item_xyz789",
            "title": "Framework AI per PM",
            "preview": "I primi 200 caratteri del contenuto...",
            "score": 8.2,
            "god_review_score": null,
            "word_count": 650
          },
          {
            "id": "cand_002",
            "source_item_id": "item_abc456",
            "title": "AI e Decision Making",
            "preview": "I primi 200 caratteri...",
            "score": 7.8,
            "god_review_score": null,
            "word_count": 580
          }
        ]
      },
      "strumento": { "...": "..." },
      "mossa": { "...": "..." }
    },
    "intro": null,
    "outro": null,
    "created_at": "2026-04-11T10:00:00Z"
  }
}
```

---

#### POST /api/newsletter/:id/select-slot

Seleziona un candidato specifico per uno slot della newsletter.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Request Body:**

```json
{
  "slot": "sistema",
  "candidate_id": "cand_001"
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `slot` | string | Si | Nome dello slot: `sistema`, `strumento`, `mossa` |
| `candidate_id` | string | Si | ID del candidato selezionato |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "newsletter_id": "nl_002",
    "slot": "sistema",
    "selected_candidate_id": "cand_001",
    "all_slots_filled": false,
    "missing_slots": ["strumento", "mossa"]
  }
}
```

---

#### POST /api/newsletter/:id/preview

Genera la preview HTML completa della newsletter.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 10 req / 5 min |

**Request Body:**

```json
{
  "send_test_to": "test@example.com"
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `send_test_to` | string (email) | No | Invia email di test a questo indirizzo |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "newsletter_id": "nl_002",
    "preview_html": "<!DOCTYPE html><html>...</html>",
    "preview_url": "https://app.example.com/newsletter/nl_002/preview",
    "test_email_sent": true,
    "test_email_to": "test@example.com",
    "subject": "AI Automation Weekly #43",
    "estimated_read_time_minutes": 8,
    "word_count": 1850
  }
}
```

**Errori Specifici:**

| Codice | Descrizione |
|---|---|
| 422 `INSUFFICIENT_CANDIDATES` | Non tutti gli slot sono stati assegnati |

---

#### POST /api/newsletter/:id/send

Invia la newsletter a tutti gli iscritti.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `owner` |
| **Rate Limit** | 3 req / ora |

**Request Body:**

```json
{
  "scheduled_at": "2026-04-12T07:00:00Z",
  "segment": "all",
  "confirm": true
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `scheduled_at` | string (ISO date) | No | Programma invio (default: immediato) |
| `segment` | string | No | Segmento destinatari: `all`, `premium`, `free` (default: `all`) |
| `confirm` | boolean | Si | Conferma esplicita (deve essere `true`) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "newsletter_id": "nl_002",
    "status": "scheduled",
    "scheduled_at": "2026-04-12T07:00:00Z",
    "recipients_count": 4920,
    "segment": "all",
    "estimated_delivery_time_minutes": 15
  }
}
```

**Errori Specifici:**

| Codice | Descrizione |
|---|---|
| 409 `NEWSLETTER_ALREADY_SENT` | La newsletter e' gia' stata inviata |
| 422 `UNPROCESSABLE_ENTITY` | Campo `confirm` non impostato a `true` |

---

#### GET /api/newsletter/:id/stats

Restituisce le statistiche post-invio della newsletter.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "newsletter_id": "nl_002",
    "sent_at": "2026-04-12T07:01:12Z",
    "recipients_count": 4920,
    "delivery": {
      "delivered": 4875,
      "bounced": 45,
      "delivery_rate": 0.991
    },
    "engagement": {
      "unique_opens": 2340,
      "total_opens": 3120,
      "open_rate": 0.480,
      "unique_clicks": 890,
      "total_clicks": 1456,
      "click_rate": 0.181,
      "click_to_open_rate": 0.380
    },
    "links": [
      {
        "url": "https://example.com/article",
        "clicks": 345,
        "unique_clicks": 280,
        "position": "sistema"
      }
    ],
    "unsubscribes": 12,
    "unsubscribe_rate": 0.0024,
    "spam_reports": 1,
    "updated_at": "2026-04-12T19:00:00Z"
  }
}
```

---

### Calendar

Gestione del calendario editoriale per pianificazione e scheduling contenuti.

---

#### GET /api/calendar/events

Restituisce gli eventi del calendario editoriale filtrati per range di date.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `from` | string (ISO date) | Si | Data inizio range |
| `to` | string (ISO date) | Si | Data fine range |
| `platform` | string | No | Filtra per piattaforma |
| `status` | string | No | `planned`, `confirmed`, `published`, `cancelled` |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": "evt_001",
      "title": "Post LinkedIn: Framework AI per PM",
      "platform": "linkedin",
      "content_type": "post",
      "draft_id": "draft_001",
      "status": "confirmed",
      "scheduled_at": "2026-04-12T09:00:00Z",
      "color": "#0077B5",
      "created_by": "user_123",
      "created_at": "2026-04-11T10:00:00Z"
    }
  ]
}
```

---

#### POST /api/calendar/events

Crea un nuovo evento nel calendario editoriale.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Request Body:**

```json
{
  "title": "Post LinkedIn: Framework AI per PM",
  "platform": "linkedin",
  "content_type": "post",
  "draft_id": "draft_001",
  "scheduled_at": "2026-04-12T09:00:00Z",
  "notes": "Pubblicare dopo le 9 per massimo engagement",
  "recurrence": null
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `title` | string | Si | Titolo evento |
| `platform` | string | Si | Piattaforma target |
| `content_type` | string | Si | Tipo contenuto |
| `draft_id` | string | No | Collegamento a bozza esistente |
| `scheduled_at` | string (ISO date) | Si | Data/ora programmata |
| `notes` | string | No | Note |
| `recurrence` | object | No | Regola ricorrenza (null = evento singolo) |

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": "evt_002",
    "title": "Post LinkedIn: Framework AI per PM",
    "platform": "linkedin",
    "status": "planned",
    "scheduled_at": "2026-04-12T09:00:00Z",
    "created_at": "2026-04-11T10:00:00Z"
  }
}
```

---

#### PATCH /api/calendar/events/:id

Aggiorna un evento del calendario.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Request Body:**

```json
{
  "scheduled_at": "2026-04-13T10:00:00Z",
  "status": "confirmed",
  "notes": "Spostato a sabato per test engagement weekend"
}
```

Tutti i campi sono opzionali. Vengono aggiornati solo i campi forniti.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "evt_002",
    "scheduled_at": "2026-04-13T10:00:00Z",
    "status": "confirmed",
    "updated_at": "2026-04-11T14:00:00Z"
  }
}
```

---

#### DELETE /api/calendar/events/:id

Rimuove un evento dal calendario.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "evt_002",
    "deleted_at": "2026-04-11T15:00:00Z"
  }
}
```

---

### Writing Lab

Gestione delle sessioni di A/B testing per miglioramento continuo della scrittura.

---

#### GET /api/writing-lab/sessions

Restituisce la lista delle sessioni Writing Lab.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `status` | string | No | `active`, `completed`, `cancelled` |
| `page` | number | No | Pagina |
| `per_page` | number | No | Elementi per pagina |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": "wl_001",
      "title": "Test apertura newsletter: domanda vs affermazione",
      "status": "active",
      "rounds_completed": 3,
      "max_rounds": 5,
      "current_champion": "A",
      "champion_wins": 2,
      "challenger_wins": 1,
      "created_at": "2026-04-08T10:00:00Z"
    }
  ]
}
```

---

#### POST /api/writing-lab/sessions

Crea una nuova sessione di A/B testing.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 10 req / 5 min |

**Request Body:**

```json
{
  "title": "Test apertura newsletter: domanda vs affermazione",
  "description": "Verificare se l'apertura con domanda retorica genera piu' engagement",
  "content_type": "newsletter_intro",
  "champion": {
    "label": "Domanda retorica",
    "content": "Ti sei mai chiesto perche' il 90% delle automazioni fallisce?"
  },
  "challenger": {
    "label": "Affermazione diretta",
    "content": "Il 90% delle automazioni fallisce. Ecco perche'."
  },
  "max_rounds": 5,
  "evaluation_criteria": ["engagement", "clarity", "brand_voice"]
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `title` | string | Si | Titolo sessione |
| `description` | string | No | Descrizione obiettivo |
| `content_type` | string | Si | Tipo contenuto testato |
| `champion` | object | Si | Versione A (champion attuale) |
| `champion.label` | string | Si | Etichetta descrittiva |
| `champion.content` | string | Si | Testo champion |
| `challenger` | object | Si | Versione B (sfidante) |
| `challenger.label` | string | Si | Etichetta descrittiva |
| `challenger.content` | string | Si | Testo challenger |
| `max_rounds` | number | No | Numero massimo round (default: 5) |
| `evaluation_criteria` | string[] | No | Criteri valutazione |

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": "wl_002",
    "title": "Test apertura newsletter: domanda vs affermazione",
    "status": "active",
    "round_1": {
      "champion": { "label": "Domanda retorica", "content": "..." },
      "challenger": { "label": "Affermazione diretta", "content": "..." },
      "ai_analysis": "Analisi comparativa dei due approcci...",
      "vote": null
    },
    "created_at": "2026-04-11T10:00:00Z"
  }
}
```

---

#### GET /api/writing-lab/sessions/:id

Restituisce il dettaglio di una sessione con tutti i round.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "wl_002",
    "title": "Test apertura newsletter: domanda vs affermazione",
    "status": "active",
    "rounds": [
      {
        "round_number": 1,
        "champion": {
          "label": "Domanda retorica",
          "content": "Ti sei mai chiesto perche' il 90% delle automazioni fallisce?"
        },
        "challenger": {
          "label": "Affermazione diretta",
          "content": "Il 90% delle automazioni fallisce. Ecco perche'."
        },
        "ai_analysis": "La domanda retorica crea curiosita' ma...",
        "vote": "champion",
        "voted_at": "2026-04-08T11:00:00Z",
        "voted_by": "user_123"
      },
      {
        "round_number": 2,
        "champion": { "label": "Domanda retorica", "content": "..." },
        "challenger": {
          "label": "Affermazione diretta v2",
          "content": "Testo evoluto dal challenger..."
        },
        "ai_analysis": "Il challenger ha migliorato...",
        "vote": "challenger",
        "voted_at": "2026-04-09T14:00:00Z",
        "voted_by": "user_123"
      }
    ],
    "current_champion": "challenger",
    "score": { "champion_wins": 1, "challenger_wins": 1 },
    "created_at": "2026-04-08T10:00:00Z"
  }
}
```

---

#### POST /api/writing-lab/sessions/:id/vote

Registra il voto umano per un round (champion o challenger vince).

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Request Body:**

```json
{
  "winner": "champion",
  "feedback": "La domanda retorica funziona meglio per il nostro pubblico"
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `winner` | string | Si | `champion` o `challenger` |
| `feedback` | string | No | Motivazione del voto |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "session_id": "wl_002",
    "round_number": 3,
    "winner": "champion",
    "new_champion": "Domanda retorica",
    "score": { "champion_wins": 2, "challenger_wins": 1 },
    "session_status": "active",
    "rounds_remaining": 2
  }
}
```

---

#### POST /api/writing-lab/sessions/:id/next-round

Genera il prossimo round con un challenger evoluto basato sul feedback precedente.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 10 req / 5 min |

**Request Body:**

```json
{
  "evolution_strategy": "iterate",
  "custom_instructions": "Prova un approccio piu' diretto, meno domande"
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `evolution_strategy` | string | No | `iterate` (migliora perdente), `mutate` (nuovo approccio), `hybrid` (default: `iterate`) |
| `custom_instructions` | string | No | Istruzioni per la generazione del nuovo challenger |

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "session_id": "wl_002",
    "round_number": 4,
    "champion": {
      "label": "Domanda retorica",
      "content": "Ti sei mai chiesto perche' il 90% delle automazioni fallisce?"
    },
    "challenger": {
      "label": "Approccio diretto v3",
      "content": "Nuovo testo generato dall'AI basato sul feedback..."
    },
    "ai_analysis": "In questo round il challenger prova un approccio...",
    "vote": null
  }
}
```

**Errori Specifici:**

| Codice | Descrizione |
|---|---|
| 409 `WRITING_LAB_SESSION_CLOSED` | La sessione ha raggiunto il massimo dei round o e' stata chiusa |

---

### Metrics

Metriche e analytics aggregate per monitorare le performance dei contenuti.

---

#### GET /api/metrics/newsletter

Restituisce le metriche aggregate delle newsletter.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `period` | string | No | `7d`, `30d`, `90d`, `12m`, `all` (default: `30d`) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "period": "30d",
    "subscribers": {
      "total": 4920,
      "new": 340,
      "churned": 45,
      "net_growth": 295,
      "growth_rate": 0.064
    },
    "performance": {
      "newsletters_sent": 4,
      "avg_open_rate": 0.472,
      "avg_click_rate": 0.178,
      "avg_click_to_open_rate": 0.377,
      "best_open_rate": 0.52,
      "best_edition": 41
    },
    "trend": [
      {
        "date": "2026-03-12",
        "edition": 39,
        "open_rate": 0.45,
        "click_rate": 0.16,
        "subscribers": 4580
      }
    ]
  }
}
```

---

#### GET /api/metrics/social

Restituisce le metriche social aggregate per piattaforma.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `platform` | string | No | Filtra per piattaforma (default: tutte) |
| `period` | string | No | `7d`, `30d`, `90d` (default: `30d`) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "period": "30d",
    "platforms": {
      "linkedin": {
        "followers": 12450,
        "followers_growth": 890,
        "posts_published": 22,
        "total_impressions": 185000,
        "total_engagement": 4560,
        "avg_engagement_rate": 0.0246,
        "top_post": {
          "draft_id": "draft_045",
          "impressions": 24500,
          "engagement": 780
        }
      },
      "x": {
        "followers": 8900,
        "followers_growth": 450,
        "posts_published": 35,
        "total_impressions": 120000,
        "total_engagement": 2890,
        "avg_engagement_rate": 0.0241
      },
      "instagram": { "...": "..." },
      "facebook": { "...": "..." },
      "tiktok": { "...": "..." }
    }
  }
}
```

---

#### GET /api/metrics/content

Restituisce le performance dei singoli contenuti.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `platform` | string | No | Filtra per piattaforma |
| `period` | string | No | `7d`, `30d`, `90d` (default: `30d`) |
| `sort_by` | string | No | `impressions`, `engagement`, `engagement_rate` (default: `engagement`) |
| `page` | number | No | Pagina |
| `per_page` | number | No | Elementi per pagina |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "draft_id": "draft_045",
      "title": "5 Framework AI per il Project Management",
      "platform": "linkedin",
      "content_type": "carousel",
      "published_at": "2026-04-05T09:00:00Z",
      "impressions": 24500,
      "engagement": 780,
      "engagement_rate": 0.0318,
      "likes": 520,
      "comments": 145,
      "shares": 85,
      "saves": 30,
      "source_item_score": 8.2,
      "retriever_type": "semantic"
    }
  ]
}
```

---

#### GET /api/metrics/heatmap

Restituisce la heatmap degli orari ottimali per pubblicazione/invio per piattaforma.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `platform` | string | Si | Piattaforma di analisi |
| `metric` | string | No | `impressions`, `engagement`, `engagement_rate` (default: `engagement_rate`) |
| `period` | string | No | Periodo di raccolta dati (default: `90d`) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "platform": "linkedin",
    "metric": "engagement_rate",
    "period": "90d",
    "timezone": "Europe/Rome",
    "heatmap": [
      { "day": "monday", "hour": 8, "value": 0.032, "posts_count": 5 },
      { "day": "monday", "hour": 9, "value": 0.041, "posts_count": 8 },
      { "day": "monday", "hour": 10, "value": 0.038, "posts_count": 6 }
    ],
    "optimal_slots": [
      { "day": "tuesday", "hour": 9, "avg_engagement_rate": 0.045 },
      { "day": "thursday", "hour": 8, "avg_engagement_rate": 0.043 },
      { "day": "wednesday", "hour": 10, "avg_engagement_rate": 0.041 }
    ]
  }
}
```

---

### Revenue

Gestione e monitoraggio delle fonti di ricavo.

---

#### GET /api/revenue/summary

Restituisce il sommario dei ricavi: MRR, affiliati, sponsorship.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `owner` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `period` | string | No | `current_month`, `last_month`, `quarter`, `ytd` (default: `current_month`) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "period": "current_month",
    "currency": "EUR",
    "mrr": {
      "total": 2450.00,
      "subscribers_paying": 245,
      "avg_revenue_per_user": 10.00,
      "churn_rate": 0.032,
      "growth_rate": 0.085
    },
    "affiliates": {
      "total": 890.00,
      "active_programs": 8,
      "clicks": 3400,
      "conversions": 45,
      "conversion_rate": 0.013
    },
    "sponsorship": {
      "total": 1500.00,
      "active_deals": 2,
      "pipeline_value": 4500.00
    },
    "total_revenue": 4840.00,
    "total_previous_period": 4120.00,
    "growth_rate": 0.175
  }
}
```

---

#### GET /api/revenue/deals

Restituisce la lista dei deal attivi (sponsorship, partnership).

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `owner` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `status` | string | No | `active`, `negotiating`, `completed`, `cancelled` |
| `type` | string | No | `sponsorship`, `affiliate`, `partnership` |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": "deal_001",
      "company": "ToolAI Corp",
      "type": "sponsorship",
      "status": "active",
      "value_eur": 1500.00,
      "start_date": "2026-04-01",
      "end_date": "2026-06-30",
      "deliverables": [
        "2 menzioni newsletter/mese",
        "1 post LinkedIn dedicato/mese"
      ],
      "created_at": "2026-03-15T10:00:00Z"
    }
  ]
}
```

---

#### POST /api/revenue/deals

Crea un nuovo deal.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `owner` |
| **Rate Limit** | 50 req / min |

**Request Body:**

```json
{
  "company": "ToolAI Corp",
  "type": "sponsorship",
  "status": "negotiating",
  "value_eur": 2000.00,
  "start_date": "2026-05-01",
  "end_date": "2026-07-31",
  "deliverables": [
    "3 menzioni newsletter/mese",
    "1 post LinkedIn dedicato/mese",
    "1 carousel Instagram/mese"
  ],
  "contact_name": "Mario Rossi",
  "contact_email": "mario@toolai.com",
  "notes": "In trattativa, attendere conferma budget Q2"
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": "deal_002",
    "company": "ToolAI Corp",
    "type": "sponsorship",
    "status": "negotiating",
    "value_eur": 2000.00,
    "created_at": "2026-04-11T10:00:00Z"
  }
}
```

---

#### PATCH /api/revenue/deals/:id

Aggiorna un deal esistente.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `owner` |
| **Rate Limit** | 50 req / min |

**Request Body:**

```json
{
  "status": "active",
  "value_eur": 1800.00,
  "notes": "Confermato a 1800 EUR. Primo deliverable 1 maggio."
}
```

Tutti i campi sono opzionali.

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "id": "deal_002",
    "status": "active",
    "value_eur": 1800.00,
    "updated_at": "2026-04-11T15:00:00Z"
  }
}
```

---

#### GET /api/revenue/forecast

Restituisce la proiezione dei ricavi per il trimestre corrente.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `owner` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `quarter` | string | No | `Q1`, `Q2`, `Q3`, `Q4` (default: trimestre corrente) |
| `year` | number | No | Anno (default: anno corrente) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "quarter": "Q2",
    "year": 2026,
    "forecast": {
      "mrr_projected": 8200.00,
      "affiliates_projected": 3200.00,
      "sponsorship_confirmed": 5400.00,
      "sponsorship_pipeline": 4500.00,
      "total_projected": 16800.00,
      "total_optimistic": 21300.00,
      "total_conservative": 14200.00
    },
    "assumptions": {
      "subscriber_growth_rate": 0.08,
      "churn_rate": 0.035,
      "affiliate_conversion_rate": 0.013,
      "pipeline_close_rate": 0.40
    },
    "monthly_breakdown": [
      { "month": "2026-04", "projected": 5200.00 },
      { "month": "2026-05", "projected": 5600.00 },
      { "month": "2026-06", "projected": 6000.00 }
    ]
  }
}
```

---

### System

Monitoraggio dello stato di salute del sistema, costi API e attivita' degli agenti.

---

#### GET /api/system/health

Restituisce lo stato di salute della pipeline e di tutti i servizi.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | **Non richiesta** (endpoint pubblico per monitoring) |
| **Rate Limit** | 60 req / min |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2026-04-11T15:00:00Z",
    "uptime_seconds": 2592000,
    "services": {
      "database": { "status": "healthy", "latency_ms": 12 },
      "ai_provider": { "status": "healthy", "latency_ms": 450 },
      "serper_api": { "status": "healthy", "latency_ms": 230 },
      "email_provider": { "status": "healthy", "latency_ms": 180 },
      "postiz": { "status": "healthy", "latency_ms": 340 },
      "n8n": { "status": "healthy", "latency_ms": 95 },
      "websocket": { "status": "healthy", "connections": 3 }
    },
    "pipeline": {
      "last_research_run": "2026-04-11T07:03:12Z",
      "last_scoring_run": "2026-04-11T07:05:00Z",
      "pending_items": 45,
      "drafts_in_review": 8,
      "scheduled_publications": 12
    }
  }
}
```

---

#### GET /api/system/costs

Restituisce i costi API aggregati per periodo.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `owner` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `period` | string | No | `today`, `week`, `month`, `quarter` (default: `today`) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "period": "today",
    "currency": "USD",
    "total_cost": 4.85,
    "breakdown_by_provider": {
      "anthropic": {
        "total": 4.20,
        "calls": 145,
        "input_tokens": 485000,
        "output_tokens": 125000
      },
      "serper": {
        "total": 0.45,
        "calls": 89
      },
      "email_provider": {
        "total": 0.20,
        "emails_sent": 0
      }
    },
    "budget": {
      "monthly_limit": 150.00,
      "used_this_month": 68.50,
      "remaining": 81.50,
      "usage_percentage": 0.457
    }
  }
}
```

---

#### GET /api/system/costs/breakdown

Restituisce il breakdown dei costi per agente.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `owner` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `period` | string | No | `today`, `week`, `month` (default: `month`) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "period": "month",
    "total_cost": 68.50,
    "agents": [
      {
        "agent_id": "opus_writer",
        "name": "Writer Agent",
        "model": "claude-opus-4-20250514",
        "cost": 5.14,
        "percentage": 7.5,
        "calls": 34,
        "avg_cost_per_call": 0.151
      },
      {
        "agent_id": "opus_editor",
        "name": "Editor Agent",
        "model": "claude-opus-4-20250514",
        "cost": 3.77,
        "percentage": 5.5,
        "calls": 34,
        "avg_cost_per_call": 0.111
      },
      {
        "agent_id": "sonnet_adapter",
        "name": "Adapter Agent",
        "model": "claude-sonnet-4-20250514",
        "cost": 1.85,
        "percentage": 2.7,
        "calls": 85,
        "avg_cost_per_call": 0.022
      },
      {
        "agent_id": "scoring_agent",
        "name": "Scoring Agent",
        "model": "claude-sonnet-4-20250514",
        "cost": 12.30,
        "percentage": 18.0,
        "calls": 890,
        "avg_cost_per_call": 0.014
      }
    ]
  }
}
```

---

#### GET /api/system/activity

Restituisce il log delle attivita' degli agenti. Supporta anche la connessione WebSocket per aggiornamenti in tempo reale.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Query Parameters:**

| Parametro | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `agent_id` | string | No | Filtra per agente specifico |
| `level` | string | No | `info`, `warning`, `error` (default: tutti) |
| `from` | string (ISO date) | No | Data inizio |
| `limit` | number | No | Numero massimo di entry (default: 50, max: 200) |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": "act_001",
      "timestamp": "2026-04-11T07:01:23Z",
      "agent_id": "research_orchestrator",
      "agent_name": "Research Orchestrator",
      "level": "info",
      "action": "research_started",
      "message": "Sessione di ricerca avviata con 5 retriever",
      "metadata": {
        "run_id": "run_abc123",
        "retrievers": ["semantic", "practitioner", "trusted_source", "keyword", "trend"]
      },
      "duration_ms": null,
      "cost_usd": null
    },
    {
      "id": "act_002",
      "timestamp": "2026-04-11T07:01:45Z",
      "agent_id": "retriever_semantic",
      "agent_name": "Retriever Semantic",
      "level": "info",
      "action": "retrieval_completed",
      "message": "83 items trovati tramite ricerca semantica",
      "metadata": {
        "run_id": "run_abc123",
        "items_found": 83,
        "queries_executed": 12
      },
      "duration_ms": 22000,
      "cost_usd": 0.08
    }
  ]
}
```

---

### Brand Config

Gestione della configurazione del brand corrente: tono, fonti, parametri.

---

#### GET /api/config/brand

Restituisce la configurazione completa del brand corrente.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "brand_id": "brand_001",
    "name": "AI Automation Weekly",
    "description": "Newsletter e contenuti su AI e automazione per professionisti italiani",
    "tone_of_voice": {
      "primary": "professionale ma accessibile",
      "secondary": "pratico e orientato all'azione",
      "avoid": ["gergo tecnico eccessivo", "tono accademico", "clickbait"],
      "examples": [
        "Questa settimana ho testato 3 tool AI per il PM. Ecco cosa funziona davvero."
      ]
    },
    "founder_principles": [
      "L'automazione deve liberare tempo per il pensiero strategico",
      "Ogni tool va validato sul campo, non sulla carta",
      "Il mercato italiano ha esigenze specifiche"
    ],
    "topics": ["AI", "automation", "productivity", "no-code", "project management"],
    "target_audience": "Professionisti e imprenditori italiani 30-50 anni",
    "languages": ["it"],
    "platforms": {
      "linkedin": { "enabled": true, "handle": "@brand" },
      "x": { "enabled": true, "handle": "@brand" },
      "instagram": { "enabled": true, "handle": "@brand" },
      "facebook": { "enabled": false },
      "tiktok": { "enabled": true, "handle": "@brand" }
    },
    "newsletter": {
      "provider": "resend",
      "from_name": "AI Automation Weekly",
      "from_email": "newsletter@example.com",
      "slots": ["sistema", "strumento", "mossa"],
      "schedule": "weekly_tuesday_0700"
    },
    "scoring_weights": {
      "applicability_concreteness": 0.25,
      "credibility": 0.20,
      "alignment": 0.20,
      "trend_prediction": 0.15,
      "italy_relevance": 0.10,
      "feedback_loop_bonus": 0.10
    },
    "visual": {
      "primary_color": "#1a1a2e",
      "secondary_color": "#e94560",
      "font_family": "Inter",
      "logo_url": "https://cdn.example.com/logo.svg"
    },
    "api_costs_budget_usd": 150.00,
    "updated_at": "2026-04-01T10:00:00Z"
  }
}
```

---

#### PUT /api/config/brand

Aggiorna la configurazione del brand.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `owner` |
| **Rate Limit** | 50 req / min |

**Request Body:**

Accetta un oggetto parziale con le stesse chiavi della risposta GET. Vengono aggiornati solo i campi forniti (merge profondo).

```json
{
  "tone_of_voice": {
    "primary": "professionale ma accessibile e diretto"
  },
  "topics": ["AI", "automation", "productivity", "no-code", "project management", "data analytics"],
  "api_costs_budget_usd": 200.00
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "brand_id": "brand_001",
    "updated_fields": ["tone_of_voice.primary", "topics", "api_costs_budget_usd"],
    "updated_at": "2026-04-11T16:00:00Z",
    "updated_by": "user_123"
  }
}
```

---

#### GET /api/config/sources

Restituisce la lista delle fonti RSS/web configurate per la ricerca.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `viewer` |
| **Rate Limit** | 200 req / min |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": "src_001",
      "name": "The Verge - AI",
      "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
      "type": "rss",
      "retriever": "trusted_source",
      "enabled": true,
      "last_fetched_at": "2026-04-11T07:00:00Z",
      "items_fetched_total": 342,
      "created_at": "2026-01-15T10:00:00Z"
    }
  ]
}
```

---

#### POST /api/config/sources

Aggiunge una nuova fonte RSS/web.

| Proprieta' | Valore |
|---|---|
| **Autenticazione** | Richiesta |
| **Ruolo minimo** | `editor` |
| **Rate Limit** | 50 req / min |

**Request Body:**

```json
{
  "name": "MIT Technology Review",
  "url": "https://www.technologyreview.com/feed/",
  "type": "rss",
  "retriever": "trusted_source",
  "enabled": true,
  "tags": ["AI", "research", "english"]
}
```

| Campo | Tipo | Richiesto | Descrizione |
|---|---|---|---|
| `name` | string | Si | Nome descrittivo della fonte |
| `url` | string | Si | URL del feed RSS o della pagina web |
| `type` | string | Si | `rss`, `web`, `api` |
| `retriever` | string | Si | Retriever associato: `trusted_source`, `keyword`, `semantic` |
| `enabled` | boolean | No | Attiva/disattiva (default: true) |
| `tags` | string[] | No | Tag per categorizzazione |

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": "src_025",
    "name": "MIT Technology Review",
    "url": "https://www.technologyreview.com/feed/",
    "type": "rss",
    "retriever": "trusted_source",
    "enabled": true,
    "validation": {
      "status": "valid",
      "items_available": 25,
      "last_item_date": "2026-04-10T18:00:00Z"
    },
    "created_at": "2026-04-11T16:30:00Z"
  }
}
```

---

## WebSocket Events

Il sistema utilizza WebSocket per aggiornamenti in tempo reale. La connessione viene stabilita tramite Supabase Realtime con autenticazione JWT.

### Connessione

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Sottoscrizione a canale brand-specifico
const channel = supabase.channel(`brand:${brand_id}`);
```

### Eventi Disponibili

---

#### `pipeline:status`

Stato della pipeline di ricerca/generazione in tempo reale.

**Payload:**

```json
{
  "event": "pipeline:status",
  "data": {
    "pipeline_type": "research",
    "run_id": "run_abc123",
    "status": "running",
    "current_step": "retriever_semantic",
    "progress": 0.35,
    "items_found": 83,
    "started_at": "2026-04-11T07:00:00Z",
    "estimated_completion": "2026-04-11T07:03:00Z"
  }
}
```

**Status possibili:** `started`, `running`, `step_completed`, `completed`, `failed`

---

#### `agent:activity`

Log attivita' degli agenti AI in tempo reale.

**Payload:**

```json
{
  "event": "agent:activity",
  "data": {
    "agent_id": "opus_writer",
    "agent_name": "Writer Agent",
    "action": "generation_started",
    "message": "Generazione post LinkedIn in corso...",
    "draft_id": "draft_001",
    "model": "claude-opus-4-20250514",
    "timestamp": "2026-04-11T10:30:00Z"
  }
}
```

---

#### `cost:update`

Aggiornamento costi in tempo reale dopo ogni chiamata API ai provider AI.

**Payload:**

```json
{
  "event": "cost:update",
  "data": {
    "agent_id": "opus_writer",
    "cost_usd": 0.15,
    "model": "claude-opus-4-20250514",
    "input_tokens": 2400,
    "output_tokens": 1850,
    "daily_total": 4.85,
    "monthly_total": 68.50,
    "budget_remaining": 81.50,
    "timestamp": "2026-04-11T10:31:15Z"
  }
}
```

### Sottoscrizione Esempio Completo

```typescript
const channel = supabase
  .channel(`brand:${brand_id}`)
  .on('broadcast', { event: 'pipeline:status' }, (payload) => {
    console.log('Pipeline status:', payload.data);
    updatePipelineUI(payload.data);
  })
  .on('broadcast', { event: 'agent:activity' }, (payload) => {
    console.log('Agent activity:', payload.data);
    appendActivityLog(payload.data);
  })
  .on('broadcast', { event: 'cost:update' }, (payload) => {
    console.log('Cost update:', payload.data);
    updateCostDashboard(payload.data);
  })
  .subscribe();

// Disconnessione
channel.unsubscribe();
```

---

## Procedure tRPC

Oltre agli endpoint REST, il sistema espone procedure tRPC per comunicazione type-safe tra frontend e backend. Le procedure sono organizzate in router modulari.

### Configurazione Client

```typescript
// lib/trpc.ts
import { createTRPCReact } from '@trpc/react-query';
import type { AppRouter } from '@/server/trpc/router';

export const trpc = createTRPCReact<AppRouter>();
```

### Router Principali

| Router | Descrizione | Procedure Principali |
|---|---|---|
| `research` | Gestione ricerca | `trigger`, `getRuns`, `getItems`, `updateItem`, `toggleTopPick` |
| `scoring` | Sistema scoring | `runScoring`, `getBreakdown`, `updateWeights` |
| `content` | Contenuti | `getDrafts`, `generate`, `getDraft`, `updateDraft`, `approve`, `godMode`, `archive` |
| `newsletter` | Newsletter | `list`, `generate`, `get`, `selectSlot`, `preview`, `send`, `getStats` |
| `calendar` | Calendario | `getEvents`, `createEvent`, `updateEvent`, `deleteEvent` |
| `writingLab` | Writing Lab | `getSessions`, `createSession`, `getSession`, `vote`, `nextRound` |
| `metrics` | Metriche | `newsletter`, `social`, `content`, `heatmap` |
| `revenue` | Ricavi | `summary`, `getDeals`, `createDeal`, `updateDeal`, `forecast` |
| `system` | Sistema | `health`, `costs`, `costsBreakdown`, `activity` |
| `config` | Configurazione | `getBrand`, `updateBrand`, `getSources`, `addSource` |

### Esempio di Utilizzo nel Frontend

```tsx
// components/ResearchDashboard.tsx
import { trpc } from '@/lib/trpc';

function ResearchDashboard() {
  const { data: runs, isLoading } = trpc.research.getRuns.useQuery({
    status: 'completed',
    page: 1,
    per_page: 10
  });

  const triggerMutation = trpc.research.trigger.useMutation({
    onSuccess: (data) => {
      toast.success(`Ricerca avviata: ${data.run_id}`);
    }
  });

  const handleTrigger = () => {
    triggerMutation.mutate({
      retrievers: ['semantic', 'practitioner', 'trusted_source'],
      force: false
    });
  };

  // ...
}
```

---

## Appendice

### Variabili d'Ambiente Richieste

| Variabile | Descrizione | Esempio |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL istanza Supabase | `https://xxx.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Chiave pubblica Supabase | `eyJ...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Chiave servizio Supabase (solo server) | `eyJ...` |
| `ANTHROPIC_API_KEY` | API key Anthropic | `sk-ant-...` |
| `SERPER_API_KEY` | API key Serper | `...` |
| `POSTIZ_API_KEY` | API key Postiz | `...` |
| `RESEND_API_KEY` | API key Resend (email) | `re_...` |
| `N8N_WEBHOOK_URL` | URL base webhook n8n | `https://n8n.example.com` |

### Convenzioni di Naming

- **ID risorse:** prefisso descrittivo + underscore + ID alfanumerico (es. `run_abc123`, `draft_001`, `nl_002`)
- **Date:** sempre in formato ISO 8601 con timezone UTC
- **Valute:** EUR per ricavi, USD per costi API
- **Percentuali:** valori decimali 0-1 (non 0-100)
