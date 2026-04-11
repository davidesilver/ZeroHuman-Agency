# AI Content Engine - Schema del Database

## Panoramica

| Proprieta           | Valore                                      |
|---------------------|---------------------------------------------|
| **Database**        | Supabase (PostgreSQL 15+)                   |
| **Estensioni**      | `pgvector`, `pg_cron`, `uuid-ossp`          |
| **Multi-tenancy**   | Isolamento tramite `brand_id` + Row Level Security (RLS) |
| **Embedding Model** | OpenAI `text-embedding-3-small` (1536 dim)  |
| **Naming**          | snake_case per tabelle e colonne            |
| **Timestamps**      | Tutti in `timestamptz` (UTC)                |

---

## Entity Relationship Diagram

```
                                ┌──────────────────────┐
                                │       brands         │
                                │──────────────────────│
                                │ id (PK)              │
                                │ name                 │
                                │ slug                 │
                                │ topics[]             │
                                │ tone_of_voice        │
                                │ scoring_weights      │
                                │ rss_sources          │
                                │ social_accounts      │
                                └──────────┬───────────┘
                                           │
              ┌────────────────┬───────────┼───────────┬──────────────────┐
              │                │           │           │                  │
              ▼                ▼           ▼           ▼                  ▼
     ┌────────────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────┐
     │ research_runs  │ │   users   │ │campaigns │ │calendar_events│ │ api_costs    │
     │────────────────│ │───────────│ │──────────│ │──────────────│ │──────────────│
     │ id (PK)        │ │ id (PK)   │ │ id (PK)  │ │ id (PK)      │ │ id (PK)      │
     │ brand_id (FK)  │ │ brand_id  │ │ brand_id │ │ brand_id(FK) │ │ brand_id(FK) │
     │ status         │ │ role      │ │ status   │ │ draft_id(FK) │ │ agent_name   │
     │ retriever_stats│ │ email     │ │ results  │ │ campaign(FK) │ │ cost_usd     │
     └───────┬────────┘ └───────────┘ └──────────┘ └──────────────┘ └──────────────┘
             │
             ▼
     ┌────────────────────┐
     │  research_items    │        ┌────────────────────┐
     │────────────────────│        │  content_drafts    │
     │ id (PK)            │        │────────────────────│
     │ brand_id (FK)      │◄──────▶│ id (PK)            │
     │ run_id (FK)        │        │ brand_id (FK)      │
     │ url                │        │ research_item_id   │
     │ embedding (vector) │        │ content_type       │
     │ status             │        │ platform           │
     └───────┬────────────┘        │ status             │
             │                     │ parent_draft_id    │◄─┐ (self-ref)
             │                     └──────┬──────┬──────┘  │
             │                            │      │         │
             ▼                            │      └─────────┘
     ┌────────────────┐                   │
     │    scores      │                   ▼
     │────────────────│          ┌──────────────────┐
     │ id (PK)        │          │god_mode_reviews  │
     │ research_item  │          │──────────────────│
     │   _id (FK, UQ) │          │ id (PK)          │
     │ applicability  │          │ draft_id (FK)    │
     │ final_score    │          │ final_verdict    │
     └────────────────┘          └──────────────────┘

     ┌────────────────────┐      ┌──────────────────────────┐
     │   newsletters      │      │  newsletter_candidates   │
     │────────────────────│      │──────────────────────────│
     │ id (PK)            │◄─────│ newsletter_id (FK)       │
     │ brand_id (FK)      │      │ research_item_id (FK)    │
     │ slot_sistema (FK)──┼──┐   │ slot_type                │
     │ slot_strumento(FK)─┼──┼──▶│ selected                 │
     │ slot_mossa (FK)────┼──┘   └──────────────────────────┘
     │ status             │
     └────────────────────┘

     ┌────────────────────┐      ┌──────────────────┐
     │ social_metrics     │      │    feedback       │
     │────────────────────│      │──────────────────│
     │ id (PK)            │      │ id (PK)          │
     │ content_draft_id   │      │ brand_id (FK)    │
     │   (FK)             │      │ content_draft_id │
     │ platform           │      │ research_item_id │
     │ impressions        │      │ feedback_type    │
     └────────────────────┘      └──────────────────┘

     ┌──────────────────────┐    ┌──────────────────────┐
     │ writing_lab_sessions │    │  writing_lab_rounds   │
     │──────────────────────│    │──────────────────────│
     │ id (PK)              │◄───│ session_id (FK)      │
     │ brand_id (FK)        │    │ round_number         │
     │ topic                │    │ champion_text        │
     │ current_champion     │    │ challenger_text      │
     │ status               │    │ winner               │
     └──────────────────────┘    └──────────────────────┘

     ┌────────────────────┐      ┌──────────────────┐
     │  revenue_deals     │      │ pipeline_health  │
     │────────────────────│      │──────────────────│
     │ id (PK)            │      │ id (PK)          │
     │ brand_id (FK)      │      │ brand_id (FK)    │
     │ partner_name       │      │ agent_name       │
     │ deal_type          │      │ uptime_pct       │
     │ amount             │      │ status           │
     └────────────────────┘      └──────────────────┘
```

---

## Tabelle

### 1. `brands` - Configurazione multi-brand

Tabella centrale per la gestione multi-tenant. Ogni brand rappresenta un progetto editoriale indipendente con propri topic, tono di voce e sorgenti di contenuto.

| Colonna            | Tipo          | Vincoli                        | Descrizione                                      |
|--------------------|---------------|--------------------------------|--------------------------------------------------|
| `id`               | `uuid`        | PK, DEFAULT `gen_random_uuid()`| Identificativo univoco del brand                 |
| `name`             | `text`        | NOT NULL                       | Nome visualizzato del brand                      |
| `slug`             | `text`        | NOT NULL, UNIQUE               | Slug URL-safe per identificazione                |
| `topics`           | `text[]`      | DEFAULT `'{}'`                 | Array di topic/nicchie seguite dal brand         |
| `tone_of_voice`    | `jsonb`       | DEFAULT `'{}'`                 | Configurazione tono: stile, registro, personalita|
| `scoring_weights`  | `jsonb`       | DEFAULT `'{}'`                 | Pesi personalizzati per il calcolo dello score   |
| `rss_sources`      | `jsonb`       | DEFAULT `'[]'`                 | Elenco feed RSS monitorati                       |
| `social_accounts`  | `jsonb`       | DEFAULT `'{}'`                 | Account social collegati (token, piattaforma)    |
| `created_at`       | `timestamptz` | DEFAULT `now()`                | Data creazione                                   |
| `updated_at`       | `timestamptz` | DEFAULT `now()`                | Data ultimo aggiornamento (auto-trigger)         |

---

### 2. `users` - Utenti autenticati (estensione Supabase Auth)

Estende la tabella `auth.users` di Supabase con profilo e ruolo per brand. Ogni utente appartiene a un singolo brand.

| Colonna       | Tipo          | Vincoli                                   | Descrizione                          |
|---------------|---------------|-------------------------------------------|--------------------------------------|
| `id`          | `uuid`        | PK, FK `auth.users(id)` ON DELETE CASCADE | ID sincronizzato con Supabase Auth   |
| `brand_id`    | `uuid`        | FK `brands(id)`, NOT NULL                 | Brand di appartenenza                |
| `role`        | `user_role`   | NOT NULL, DEFAULT `'viewer'`              | Ruolo: `owner`, `editor`, `viewer`   |
| `email`       | `text`        | NOT NULL                                  | Email dell'utente                    |
| `full_name`   | `text`        |                                           | Nome completo                        |
| `avatar_url`  | `text`        |                                           | URL avatar                           |
| `created_at`  | `timestamptz` | DEFAULT `now()`                           | Data registrazione                   |

---

### 3. `research_runs` - Sessioni di ricerca pipeline

Ogni esecuzione della pipeline di ricerca viene tracciata come una "run". Registra statistiche su quante fonti sono state scandagliate e quanti elementi trovati.

| Colonna            | Tipo          | Vincoli                       | Descrizione                              |
|--------------------|---------------|-------------------------------|------------------------------------------|
| `id`               | `uuid`        | PK, DEFAULT `gen_random_uuid()` | ID della sessione di ricerca           |
| `brand_id`         | `uuid`        | FK `brands(id)`, NOT NULL     | Brand proprietario                       |
| `status`           | `run_status`  | NOT NULL, DEFAULT `'running'` | Stato: `running`, `completed`, `failed`  |
| `started_at`       | `timestamptz` | DEFAULT `now()`               | Inizio esecuzione                        |
| `completed_at`     | `timestamptz` |                               | Fine esecuzione                          |
| `sources_scanned`  | `int`         | DEFAULT 0                     | Numero fonti analizzate                  |
| `items_found`      | `int`         | DEFAULT 0                     | Elementi trovati in questa run           |
| `retriever_stats`  | `jsonb`       | DEFAULT `'{}'`                | Statistiche per tipo di retriever        |
| `error_log`        | `text`        |                               | Log errori (se status = failed)          |

---

### 4. `research_items` - Contenuti scoperti dalla ricerca

Cuore del sistema di ricerca. Ogni elemento rappresenta un contenuto scoperto (articolo, video, post) con embedding vettoriale per ricerca semantica.

| Colonna          | Tipo              | Vincoli                                         | Descrizione                                |
|------------------|-------------------|--------------------------------------------------|---------------------------------------------|
| `id`             | `uuid`            | PK, DEFAULT `gen_random_uuid()`                  | ID univoco                                  |
| `brand_id`       | `uuid`            | FK `brands(id)`, NOT NULL                        | Brand proprietario                          |
| `run_id`         | `uuid`            | FK `research_runs(id)`                           | Sessione di ricerca di origine              |
| `url`            | `text`            | NOT NULL, UNIQUE per brand (vedi indice)         | URL sorgente del contenuto                  |
| `title`          | `text`            |                                                  | Titolo del contenuto                        |
| `summary`        | `text`            |                                                  | Riassunto generato via LLM                  |
| `source_name`    | `text`            |                                                  | Nome della fonte (es. "TechCrunch")         |
| `source_type`    | `source_type`     | NOT NULL                                         | Tipo: `rss`, `search`, `youtube`, `scrape`  |
| `retriever_type` | `retriever_type`  | NOT NULL                                         | Retriever: `semantic`, `practitioner`, `trusted_source`, `keyword`, `trend` |
| `raw_content`    | `text`            |                                                  | Contenuto grezzo estratto                   |
| `metadata`       | `jsonb`           | DEFAULT `'{}'`                                   | Metadati aggiuntivi (autore, data pub, ecc.)|
| `embedding`      | `vector(1536)`    |                                                  | Embedding vettoriale per similarita semantica|
| `status`         | `item_status`     | NOT NULL, DEFAULT `'new'`                        | Stato: `new`, `scored`, `approved`, `rejected`, `archived` |
| `created_at`     | `timestamptz`     | DEFAULT `now()`                                  | Data scoperta                               |

**Vincolo UNIQUE composito**: `(brand_id, url)` -- evita duplicati dello stesso URL per lo stesso brand.

---

### 5. `scores` - Punteggi dei contenuti

Sistema di scoring multi-dimensionale. Ogni research_item riceve un punteggio composto su 5 assi + bonus feedback. Il `final_score` e calcolato come media ponderata.

| Colonna                  | Tipo          | Vincoli                              | Descrizione                                |
|--------------------------|---------------|--------------------------------------|--------------------------------------------|
| `id`                     | `uuid`        | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                 |
| `research_item_id`       | `uuid`        | FK `research_items(id)`, UNIQUE      | Item valutato (rapporto 1:1)               |
| `applicability`          | `float`       | CHECK (0..10)                        | Quanto e applicabile/pratico               |
| `credibility`            | `float`       | CHECK (0..10)                        | Affidabilita della fonte                   |
| `alignment`              | `float`       | CHECK (0..10)                        | Allineamento con la strategia del brand    |
| `trend_prediction`       | `float`       | CHECK (0..10)                        | Potenziale di trend futuro                 |
| `italy_relevance`        | `float`       | CHECK (0..10)                        | Rilevanza per il mercato italiano          |
| `feedback_bonus`         | `float`       | DEFAULT 0                            | Bonus da feedback umano                    |
| `final_score`            | `float`       | GENERATED (computed)                 | Score finale calcolato: media 5 assi + bonus|
| `model_used`             | `text`        |                                      | Modello LLM usato per lo scoring           |
| `scoring_prompt_version` | `int`         |                                      | Versione del prompt di scoring             |
| `created_at`             | `timestamptz` | DEFAULT `now()`                      | Data valutazione                           |

**Formula `final_score`**: `(applicability + credibility + alignment + trend_prediction + italy_relevance) / 5.0 + feedback_bonus`

---

### 6. `content_drafts` - Bozze contenuti generati

Contenuti generati dal sistema o creati manualmente. Supporta versioning tramite `parent_draft_id` (self-referencing) e workflow di approvazione completo.

| Colonna              | Tipo              | Vincoli                              | Descrizione                                   |
|----------------------|-------------------|--------------------------------------|-----------------------------------------------|
| `id`                 | `uuid`            | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                    |
| `brand_id`           | `uuid`            | FK `brands(id)`, NOT NULL            | Brand proprietario                            |
| `research_item_id`   | `uuid`            | FK `research_items(id)`, NULLABLE    | Item di ricerca di origine (null se manuale)   |
| `content_type`       | `content_type`    | NOT NULL                             | Tipo: `post`, `blog`, `newsletter_section`, `carousel`, `video_script`, `thread` |
| `platform`           | `platform`        | NOT NULL                             | Piattaforma: `linkedin`, `instagram`, `facebook`, `x`, `tiktok`, `blog`, `newsletter` |
| `title`              | `text`            |                                      | Titolo del contenuto                          |
| `body`               | `text`            |                                      | Corpo del contenuto                           |
| `media_urls`         | `text[]`          | DEFAULT `'{}'`                       | URL media allegati                            |
| `version`            | `int`             | DEFAULT 1                            | Numero versione                               |
| `parent_draft_id`    | `uuid`            | FK `content_drafts(id)`, NULLABLE    | Versione precedente (self-ref per versioning) |
| `status`             | `draft_status`    | NOT NULL, DEFAULT `'draft'`          | Stato workflow: `draft`, `in_review`, `god_mode`, `approved`, `scheduled`, `published`, `archived` |
| `god_mode_result`    | `jsonb`           |                                      | Risultato sintetico del GOD review            |
| `seo_score`          | `int`             |                                      | Punteggio SEO (0-100)                         |
| `scheduled_at`       | `timestamptz`     |                                      | Data/ora di pubblicazione programmata         |
| `published_at`       | `timestamptz`     |                                      | Data/ora di pubblicazione effettiva           |
| `published_url`      | `text`            |                                      | URL del contenuto pubblicato                  |
| `created_at`         | `timestamptz`     | DEFAULT `now()`                      | Data creazione                                |
| `updated_at`         | `timestamptz`     | DEFAULT `now()`                      | Data ultimo aggiornamento (auto-trigger)      |

---

### 7. `god_mode_reviews` - Risultati del GOD system

Sistema di revisione a tre agenti (Advocate, Factcheck, Creative) con sintesi finale. Ogni draft puo passare attraverso il GOD mode per validazione automatica.

| Colonna                | Tipo           | Vincoli                           | Descrizione                                |
|------------------------|----------------|-----------------------------------|--------------------------------------------|
| `id`                   | `uuid`         | PK, DEFAULT `gen_random_uuid()`   | ID univoco                                 |
| `draft_id`             | `uuid`         | FK `content_drafts(id)`, NOT NULL | Draft valutato                             |
| `advocate_feedback`    | `text`         |                                   | Feedback dell'agente Advocate              |
| `advocate_score`       | `float`        |                                   | Punteggio Advocate                         |
| `factcheck_feedback`   | `text`         |                                   | Feedback del Fact-Checker                  |
| `factcheck_issues`     | `jsonb`        |                                   | Lista problemi factuali trovati            |
| `creative_feedback`    | `text`         |                                   | Feedback dell'agente Creative              |
| `creative_suggestions` | `jsonb`        |                                   | Suggerimenti creativi strutturati          |
| `synthesis_result`     | `text`         |                                   | Sintesi finale dei tre agenti              |
| `final_verdict`        | `god_verdict`  | NOT NULL                          | Verdetto: `pass`, `needs_revision`, `reject`|
| `model_config`         | `jsonb`        |                                   | Configurazione modelli usati per la review |
| `created_at`           | `timestamptz`  | DEFAULT `now()`                   | Data review                                |

---

### 8. `newsletters` - Newsletter composte

Newsletter strutturata in 3 slot tematici (Sistema, Strumento Lampo, Mossa). Ogni slot e collegato a un `content_draft` dedicato.

| Colonna                | Tipo           | Vincoli                              | Descrizione                                |
|------------------------|----------------|--------------------------------------|--------------------------------------------|
| `id`                   | `uuid`         | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                 |
| `brand_id`             | `uuid`         | FK `brands(id)`, NOT NULL            | Brand proprietario                         |
| `title`                | `text`         | NOT NULL                             | Titolo edizione                            |
| `edition_number`       | `int`          | NOT NULL                             | Numero progressivo edizione                |
| `slot_sistema_id`      | `uuid`         | FK `content_drafts(id)`, NULLABLE    | Draft per slot "Il Sistema"                |
| `slot_strumento_id`    | `uuid`         | FK `content_drafts(id)`, NULLABLE    | Draft per slot "Strumento Lampo"           |
| `slot_mossa_id`        | `uuid`         | FK `content_drafts(id)`, NULLABLE    | Draft per slot "La Mossa"                  |
| `html_body`            | `text`         |                                      | HTML renderizzato completo                 |
| `status`               | `newsletter_status` | NOT NULL, DEFAULT `'draft'`     | Stato: `draft`, `in_review`, `approved`, `scheduled`, `sent` |
| `scheduled_at`         | `timestamptz`  |                                      | Data invio programmato                     |
| `sent_at`              | `timestamptz`  |                                      | Data invio effettivo                       |
| `recipients_count`     | `int`          |                                      | Numero destinatari                         |
| `open_rate`            | `float`        |                                      | Tasso di apertura (0.0 - 1.0)             |
| `click_rate`           | `float`        |                                      | Tasso di click (0.0 - 1.0)                |
| `unsubscribe_count`    | `int`          |                                      | Numero disiscrizioni                       |
| `created_at`           | `timestamptz`  | DEFAULT `now()`                      | Data creazione                             |
| `updated_at`           | `timestamptz`  | DEFAULT `now()`                      | Data ultimo aggiornamento (auto-trigger)   |

---

### 9. `newsletter_candidates` - Candidati per ogni slot newsletter

Per ogni slot della newsletter vengono selezionati candidati dalla ricerca. Il sistema propone opzioni e l'utente (o l'AI) sceglie.

| Colonna              | Tipo          | Vincoli                              | Descrizione                                   |
|----------------------|---------------|--------------------------------------|-----------------------------------------------|
| `id`                 | `uuid`        | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                    |
| `newsletter_id`      | `uuid`        | FK `newsletters(id)`, NOT NULL       | Newsletter di appartenenza                    |
| `slot_type`          | `slot_type`   | NOT NULL                             | Tipo slot: `sistema`, `strumento_lampo`, `mossa` |
| `research_item_id`   | `uuid`        | FK `research_items(id)`, NOT NULL    | Item candidato                                |
| `score`              | `float`       |                                      | Punteggio di idoneita per lo slot             |
| `selected`           | `boolean`     | DEFAULT `false`                      | Se il candidato e stato selezionato           |
| `created_at`         | `timestamptz` | DEFAULT `now()`                      | Data candidatura                              |

---

### 10. `campaigns` - Campagne di distribuzione

Raggruppa piu contenuti per distribuzione coordinata su piu piattaforme.

| Colonna              | Tipo          | Vincoli                              | Descrizione                                   |
|----------------------|---------------|--------------------------------------|-----------------------------------------------|
| `id`                 | `uuid`        | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                    |
| `brand_id`           | `uuid`        | FK `brands(id)`, NOT NULL            | Brand proprietario                            |
| `name`               | `text`        | NOT NULL                             | Nome campagna                                 |
| `content_draft_ids`  | `uuid[]`      | DEFAULT `'{}'`                       | Array di ID draft inclusi                     |
| `platforms`          | `text[]`      | DEFAULT `'{}'`                       | Piattaforme target                            |
| `scheduled_at`       | `timestamptz` |                                      | Data lancio programmato                       |
| `status`             | `campaign_status` | NOT NULL, DEFAULT `'draft'`      | Stato: `draft`, `scheduled`, `publishing`, `completed`, `failed` |
| `results`            | `jsonb`       |                                      | Risultati distribuzione per piattaforma       |
| `created_at`         | `timestamptz` | DEFAULT `now()`                      | Data creazione                                |

---

### 11. `calendar_events` - Calendario editoriale

Vista calendario per pianificazione editoriale. Collega draft e campagne a date specifiche.

| Colonna              | Tipo          | Vincoli                              | Descrizione                                   |
|----------------------|---------------|--------------------------------------|-----------------------------------------------|
| `id`                 | `uuid`        | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                    |
| `brand_id`           | `uuid`        | FK `brands(id)`, NOT NULL            | Brand proprietario                            |
| `content_draft_id`   | `uuid`        | FK `content_drafts(id)`, NULLABLE    | Draft collegato                               |
| `campaign_id`        | `uuid`        | FK `campaigns(id)`, NULLABLE         | Campagna collegata                            |
| `event_type`         | `event_type`  | NOT NULL                             | Tipo: `newsletter`, `social`, `blog_video`, `sponsorship` |
| `title`              | `text`        | NOT NULL                             | Titolo evento in calendario                   |
| `scheduled_date`     | `date`        | NOT NULL                             | Data pianificata                              |
| `scheduled_time`     | `time`        |                                      | Ora pianificata (opzionale)                   |
| `status`             | `event_status`| NOT NULL, DEFAULT `'planned'`        | Stato: `planned`, `confirmed`, `published`    |
| `color`              | `text`        |                                      | Colore visualizzazione calendario             |
| `created_at`         | `timestamptz` | DEFAULT `now()`                      | Data creazione                                |

---

### 12. `api_costs` - Tracking costi API

Tracciamento granulare dei costi per ogni chiamata API (LLM, embedding, scraping). Fondamentale per il controllo budget e ottimizzazione.

| Colonna          | Tipo              | Vincoli                           | Descrizione                                |
|------------------|-------------------|-----------------------------------|--------------------------------------------|
| `id`             | `uuid`            | PK, DEFAULT `gen_random_uuid()`   | ID univoco                                 |
| `brand_id`       | `uuid`            | FK `brands(id)`, NOT NULL         | Brand che ha generato il costo             |
| `agent_name`     | `text`            | NOT NULL                          | Nome agente (es. "scorer", "writer")       |
| `model`          | `text`            | NOT NULL                          | Modello usato (es. "gpt-4o", "claude-3.5") |
| `operation`      | `text`            | NOT NULL                          | Operazione (es. "score", "generate", "embed")|
| `tokens_input`   | `int`             | DEFAULT 0                         | Token in input                             |
| `tokens_output`  | `int`             | DEFAULT 0                         | Token in output                            |
| `cost_usd`       | `decimal(10,6)`   | NOT NULL                          | Costo in USD                               |
| `latency_ms`     | `int`             |                                   | Latenza in millisecondi                    |
| `created_at`     | `timestamptz`     | DEFAULT `now()`                   | Data registrazione                         |

---

### 13. `social_metrics` - Metriche social

Metriche di performance raccolte dalle API social per ogni contenuto pubblicato.

| Colonna              | Tipo          | Vincoli                              | Descrizione                                   |
|----------------------|---------------|--------------------------------------|-----------------------------------------------|
| `id`                 | `uuid`        | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                    |
| `content_draft_id`   | `uuid`        | FK `content_drafts(id)`, NOT NULL    | Draft di riferimento                          |
| `platform`           | `text`        | NOT NULL                             | Piattaforma (linkedin, instagram, ecc.)       |
| `impressions`        | `int`         | DEFAULT 0                            | Visualizzazioni                               |
| `engagement`         | `int`         | DEFAULT 0                            | Interazioni totali                            |
| `clicks`             | `int`         | DEFAULT 0                            | Click sul link                                |
| `shares`             | `int`         | DEFAULT 0                            | Condivisioni                                  |
| `comments`           | `int`         | DEFAULT 0                            | Commenti                                      |
| `saves`              | `int`         | DEFAULT 0                            | Salvataggi                                    |
| `followers_gained`   | `int`         | DEFAULT 0                            | Nuovi follower attribuiti                     |
| `fetched_at`         | `timestamptz` | DEFAULT `now()`                      | Data raccolta metriche                        |
| `raw_data`           | `jsonb`       |                                      | Dati grezzi dalla API social                  |

---

### 14. `writing_lab_sessions` - Sessioni Writing Lab A/B

Sessioni di A/B testing per ottimizzazione copy. Fino a 50 round per sessione, con tracciamento del "campione" corrente.

| Colonna              | Tipo          | Vincoli                              | Descrizione                                   |
|----------------------|---------------|--------------------------------------|-----------------------------------------------|
| `id`                 | `uuid`        | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                    |
| `brand_id`           | `uuid`        | FK `brands(id)`, NOT NULL            | Brand proprietario                            |
| `topic`              | `text`        | NOT NULL                             | Argomento della sessione                      |
| `content_type`       | `text`        | NOT NULL                             | Tipo di contenuto testato                     |
| `rounds_completed`   | `int`         | DEFAULT 0                            | Round completati                              |
| `max_rounds`         | `int`         | DEFAULT 50                           | Numero massimo di round                       |
| `current_champion`   | `text`        |                                      | Testo del campione attuale                    |
| `champion_version`   | `int`         |                                      | Versione del campione                         |
| `hook_types_tried`   | `jsonb`       | DEFAULT `'[]'`                       | Tipi di hook testati                          |
| `user_votes`         | `jsonb`       | DEFAULT `'{}'`                       | Voti utente aggregati                         |
| `status`             | `lab_status`  | NOT NULL, DEFAULT `'active'`         | Stato: `active`, `completed`, `paused`        |
| `created_at`         | `timestamptz` | DEFAULT `now()`                      | Data creazione                                |
| `updated_at`         | `timestamptz` | DEFAULT `now()`                      | Data ultimo aggiornamento (auto-trigger)      |

---

### 15. `writing_lab_rounds` - Round individuali A/B

Singolo round di confronto A/B tra campione e sfidante.

| Colonna                  | Tipo          | Vincoli                              | Descrizione                                |
|--------------------------|---------------|--------------------------------------|--------------------------------------------|
| `id`                     | `uuid`        | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                 |
| `session_id`             | `uuid`        | FK `writing_lab_sessions(id)`, NOT NULL | Sessione di appartenenza                |
| `round_number`           | `int`         | NOT NULL                             | Numero progressivo del round               |
| `champion_text`          | `text`        | NOT NULL                             | Testo del campione                         |
| `challenger_text`        | `text`        | NOT NULL                             | Testo dello sfidante                       |
| `hook_type_champion`     | `text`        |                                      | Tipo di hook del campione                  |
| `hook_type_challenger`   | `text`        |                                      | Tipo di hook dello sfidante                |
| `winner`                 | `round_winner`|                                      | Vincitore: `champion`, `challenger`, `draw`|
| `user_feedback`          | `text`        |                                      | Commento utente sul round                  |
| `created_at`             | `timestamptz` | DEFAULT `now()`                      | Data round                                 |

---

### 16. `revenue_deals` - Deal revenue e sponsorship

Tracciamento delle opportunita di monetizzazione: sponsorship, affiliazioni, feature in newsletter.

| Colonna          | Tipo              | Vincoli                              | Descrizione                                   |
|------------------|-------------------|--------------------------------------|-----------------------------------------------|
| `id`             | `uuid`            | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                    |
| `brand_id`       | `uuid`            | FK `brands(id)`, NOT NULL            | Brand proprietario                            |
| `partner_name`   | `text`            | NOT NULL                             | Nome partner/sponsor                          |
| `deal_type`      | `deal_type`       | NOT NULL                             | Tipo: `sponsorship`, `affiliate`, `newsletter_feature`, `product` |
| `amount`         | `decimal(10,2)`   | NOT NULL                             | Importo del deal                              |
| `currency`       | `text`            | DEFAULT `'EUR'`                      | Valuta                                        |
| `recurrence`     | `recurrence_type` | NOT NULL                             | Ricorrenza: `one_time`, `monthly`, `quarterly`|
| `start_date`     | `date`            | NOT NULL                             | Data inizio                                   |
| `end_date`       | `date`            |                                      | Data fine (null se ongoing)                   |
| `status`         | `deal_status`     | NOT NULL, DEFAULT `'proposal'`       | Stato: `proposal`, `negotiation`, `confirmed`, `active`, `completed`, `cancelled` |
| `notes`          | `text`            |                                      | Note interne                                  |
| `created_at`     | `timestamptz`     | DEFAULT `now()`                      | Data creazione                                |
| `updated_at`     | `timestamptz`     | DEFAULT `now()`                      | Data ultimo aggiornamento (auto-trigger)      |

---

### 17. `pipeline_health` - Stato salute del sistema

Monitoraggio in tempo reale di ogni agente della pipeline. Heartbeat periodico per rilevamento anomalie.

| Colonna            | Tipo          | Vincoli                              | Descrizione                                   |
|--------------------|---------------|--------------------------------------|-----------------------------------------------|
| `id`               | `uuid`        | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                    |
| `brand_id`         | `uuid`        | FK `brands(id)`, NOT NULL            | Brand monitorato                              |
| `agent_name`       | `text`        | NOT NULL                             | Nome agente                                   |
| `uptime_pct`       | `float`       |                                      | Percentuale uptime (0-100)                    |
| `avg_latency_ms`   | `int`         |                                      | Latenza media in ms                           |
| `errors_today`     | `int`         | DEFAULT 0                            | Errori nelle ultime 24h                       |
| `queue_size`       | `int`         | DEFAULT 0                            | Dimensione coda lavoro                        |
| `last_heartbeat`   | `timestamptz` |                                      | Ultimo heartbeat ricevuto                     |
| `status`           | `health_status`| NOT NULL, DEFAULT `'healthy'`       | Stato: `healthy`, `degraded`, `down`          |
| `created_at`       | `timestamptz` | DEFAULT `now()`                      | Data registrazione                            |

---

### 18. `feedback` - Feedback umano su contenuti

Raccoglie feedback esplicito degli utenti su contenuti e research items. Alimenta il `feedback_bonus` nello scoring.

| Colonna              | Tipo          | Vincoli                              | Descrizione                                   |
|----------------------|---------------|--------------------------------------|-----------------------------------------------|
| `id`                 | `uuid`        | PK, DEFAULT `gen_random_uuid()`      | ID univoco                                    |
| `brand_id`           | `uuid`        | FK `brands(id)`, NOT NULL            | Brand di riferimento                          |
| `content_draft_id`   | `uuid`        | FK `content_drafts(id)`, NULLABLE    | Draft valutato (opzionale)                    |
| `research_item_id`   | `uuid`        | FK `research_items(id)`, NULLABLE    | Item valutato (opzionale)                     |
| `feedback_type`      | `feedback_type`| NOT NULL                            | Tipo: `like`, `dislike`, `top_pick`, `comment`|
| `value`              | `text`        |                                      | Testo del commento (se type = comment)        |
| `source`             | `feedback_source`| NOT NULL                           | Origine: `manual`, `writing_lab`, `analytics` |
| `created_at`         | `timestamptz` | DEFAULT `now()`                      | Data feedback                                 |

---

## Row Level Security (RLS)

Tutte le tabelle hanno RLS abilitato. Le policy garantiscono isolamento completo tra brand.

### Principi

1. **Isolamento brand**: ogni utente vede solo i dati del proprio `brand_id`
2. **Ruoli gerarchici**:
   - `owner` - accesso completo (CRUD + gestione utenti)
   - `editor` - puo creare e modificare contenuti, non puo gestire utenti o configurazione brand
   - `viewer` - solo lettura su tutti i dati del brand
3. **Service role**: il ruolo `service_role` di Supabase bypassa tutte le policy RLS per le operazioni background della pipeline

### Policy per ruolo

| Operazione | Owner | Editor | Viewer | Service Role |
|------------|-------|--------|--------|--------------|
| SELECT     | Si (proprio brand) | Si (proprio brand) | Si (proprio brand) | Si (tutti) |
| INSERT     | Si    | Si     | No     | Si (tutti) |
| UPDATE     | Si    | Si     | No     | Si (tutti) |
| DELETE     | Si    | No     | No     | Si (tutti) |

### Implementazione

Ogni tabella con `brand_id` ha le seguenti policy:

```sql
-- Lettura: tutti i ruoli del brand
CREATE POLICY "brand_isolation_select" ON tabella
  FOR SELECT USING (
    brand_id = (SELECT brand_id FROM users WHERE id = auth.uid())
  );

-- Scrittura: solo owner e editor
CREATE POLICY "brand_isolation_insert" ON tabella
  FOR INSERT WITH CHECK (
    brand_id = (SELECT brand_id FROM users WHERE id = auth.uid())
    AND (SELECT role FROM users WHERE id = auth.uid()) IN ('owner', 'editor')
  );

-- Aggiornamento: solo owner e editor
CREATE POLICY "brand_isolation_update" ON tabella
  FOR UPDATE USING (
    brand_id = (SELECT brand_id FROM users WHERE id = auth.uid())
    AND (SELECT role FROM users WHERE id = auth.uid()) IN ('owner', 'editor')
  );

-- Cancellazione: solo owner
CREATE POLICY "brand_isolation_delete" ON tabella
  FOR DELETE USING (
    brand_id = (SELECT brand_id FROM users WHERE id = auth.uid())
    AND (SELECT role FROM users WHERE id = auth.uid()) = 'owner'
  );
```

---

## Indici

### Indici primari per performance

| Tabella             | Colonne                                    | Tipo      | Scopo                                    |
|---------------------|--------------------------------------------|-----------|------------------------------------------|
| `research_items`    | `(brand_id, status, created_at)`           | B-tree    | Filtraggio pipeline per brand e stato    |
| `research_items`    | `(brand_id, url)`                          | B-tree UQ | Deduplicazione URL per brand             |
| `research_items`    | `embedding`                                | IVFFlat   | Ricerca similarita vettoriale            |
| `scores`            | `(final_score DESC)`                       | B-tree    | Ranking contenuti per score              |
| `content_drafts`    | `(brand_id, status, platform)`             | B-tree    | Filtraggio contenuti per stato e piatt.  |
| `api_costs`         | `(brand_id, created_at)`                   | B-tree    | Aggregazione costi per periodo           |
| `calendar_events`   | `(brand_id, scheduled_date)`               | B-tree    | Query calendario per data                |
| `social_metrics`    | `(content_draft_id, fetched_at)`           | B-tree    | Storico metriche per contenuto           |
| `pipeline_health`   | `(brand_id, agent_name, created_at)`       | B-tree    | Monitoraggio per agente                  |
| `feedback`          | `(brand_id, content_draft_id)`             | B-tree    | Lookup feedback per contenuto            |

### Nota su IVFFlat

L'indice vettoriale IVFFlat per `research_items.embedding` usa `vector_cosine_ops` con `lists = 100`. Richiede almeno ~1000 righe per funzionare in modo ottimale. Per dataset piu piccoli, usare ricerca sequenziale.

---

## Views

### `v_content_pipeline`

Vista completa della pipeline: unisce research items, scores e content drafts per una visione end-to-end.

```sql
SELECT
  ri.id, ri.title, ri.source_name, ri.status AS research_status,
  s.final_score, s.applicability, s.credibility,
  cd.id AS draft_id, cd.content_type, cd.platform, cd.status AS draft_status,
  cd.scheduled_at, cd.published_at
FROM research_items ri
LEFT JOIN scores s ON s.research_item_id = ri.id
LEFT JOIN content_drafts cd ON cd.research_item_id = ri.id;
```

### `v_daily_costs`

Aggregazione costi giornalieri per agente e modello.

```sql
SELECT
  brand_id,
  date_trunc('day', created_at) AS day,
  agent_name,
  model,
  COUNT(*) AS calls,
  SUM(tokens_input) AS total_tokens_in,
  SUM(tokens_output) AS total_tokens_out,
  SUM(cost_usd) AS total_cost_usd
FROM api_costs
GROUP BY brand_id, day, agent_name, model;
```

### `v_newsletter_performance`

Metriche newsletter aggregate con tassi di apertura e click.

```sql
SELECT
  n.brand_id,
  n.id AS newsletter_id,
  n.title,
  n.edition_number,
  n.status,
  n.recipients_count,
  n.open_rate,
  n.click_rate,
  n.unsubscribe_count,
  n.sent_at,
  COUNT(nc.id) AS candidates_count,
  COUNT(nc.id) FILTER (WHERE nc.selected) AS selected_count
FROM newsletters n
LEFT JOIN newsletter_candidates nc ON nc.newsletter_id = n.id
GROUP BY n.id;
```

---

## Convenzioni

- **UUID v4** per tutte le primary key (generati lato database)
- **Soft delete** non implementato: i record vengono archiviati tramite cambio `status` (es. `archived`)
- **Timestamps** sempre in UTC con timezone (`timestamptz`)
- **JSONB** preferito a JSON per indicizzazione e query
- **Array PostgreSQL** (`text[]`, `uuid[]`) usati dove appropriato per evitare tabelle ponte semplici
- **Trigger `updated_at`** su tutte le tabelle con colonna `updated_at` per aggiornamento automatico
