# Documentazione Pipeline - AI Content Engine

> Descrizione dettagliata di tutti i workflow automatizzati del sistema, con trigger, step, gestione errori e struttura n8n.
> Ultimo aggiornamento: 2026-04-11

---

## Indice

- [Panoramica Pipeline](#panoramica-pipeline)
- [Pipeline 1: Daily Research](#pipeline-1-daily-research)
- [Pipeline 2: Content Scoring](#pipeline-2-content-scoring)
- [Pipeline 3: Content Generation](#pipeline-3-content-generation)
- [Pipeline 4: GOD Mode Review](#pipeline-4-god-mode-review)
- [Pipeline 5: Newsletter Composition](#pipeline-5-newsletter-composition)
- [Pipeline 6: Social Publishing](#pipeline-6-social-publishing)
- [Pipeline 7: Analytics Feedback Loop](#pipeline-7-analytics-feedback-loop)
- [Pipeline 8: Writing Lab A/B](#pipeline-8-writing-lab-ab)
- [Diagramma Integrato](#diagramma-integrato)
- [Monitoraggio e Alerting](#monitoraggio-e-alerting)

---

## Panoramica Pipeline

Il sistema opera attraverso 8 pipeline principali che coprono l'intero ciclo di vita del contenuto: dalla scoperta al monitoraggio post-pubblicazione.

```
    07:00               07:03              Manuale             Manuale
      |                   |                  |                   |
  [Research]  -------> [Scoring] ------> [Content Gen] ----> [GOD Review]
      |                   |                  |                   |
      v                   v                  v                   v
  253 items           198 scored         Draft generato      Draft finale
  (grezzo)            (0-10)             (Writer+Editor)     (4 agenti GOD)
                                              |                   |
                                              v                   v
                                     [Social Publishing]   [Newsletter]
                                              |                   |
                                              v                   v
                                        Postiz API          Email inviata
                                              |                   |
                                              +-------+----------+
                                                      |
                                              [Feedback Loop]
                                                      |
                                                      v
                                              Aggiornamento
                                              scoring weights
```

### Connessioni tra Pipeline

| Pipeline Sorgente | Evento | Pipeline Target |
|---|---|---|
| Daily Research | Completamento run | Content Scoring |
| Content Scoring | Item con score > soglia | Content Generation (manuale) |
| Content Generation | Draft completato | GOD Mode Review (opzionale) |
| GOD Mode Review | Contenuto approvato | Social Publishing / Newsletter |
| Social Publishing | Contenuto pubblicato | Analytics Feedback Loop |
| Newsletter Composition | Newsletter inviata | Analytics Feedback Loop |
| Analytics Feedback Loop | Nuovi dati performance | Content Scoring (aggiorna pesi) |

---

## Pipeline 1: Daily Research

### Informazioni Generali

| Proprieta' | Valore |
|---|---|
| **Trigger** | Cron giornaliero 07:00 CET, oppure manuale via `POST /api/research/trigger` |
| **Durata Attesa** | 2-4 minuti |
| **Costo Medio** | ~$0.42 per run |
| **Output** | ~198 research items deduplicati e pronti per scoring |
| **Workflow n8n** | `daily-research-pipeline` |

### Step-by-Step

#### Step 1: Inizializzazione

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Research Orchestrator |
| **Input** | Brand config (topics, sources, scoring weights, founder principles) |
| **Output** | Configurazione sessione con parametri per ogni retriever |
| **Durata** | <1 secondo |

**Azioni:**
1. Crea un nuovo record `research_run` con status `running`
2. Carica la configurazione brand corrente dal database
3. Verifica che non ci sia un altro run in corso (a meno che `force: true`)
4. Emette evento WebSocket `pipeline:status` con stato `started`
5. Prepara la configurazione per ogni retriever

#### Step 2: Esecuzione Retriever (Parallelo)

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | 5 Retriever Agents (in parallelo) |
| **Input** | Configurazione specifica per ogni retriever |
| **Output** | ~253 items grezzi totali |
| **Durata** | 30-60 secondi (il piu' lento determina la durata) |

**Esecuzione parallela:**

```
Research Orchestrator
    |
    +-- [Semantic Retriever]    --> ~83 items   (Serper + AI query generation)
    |
    +-- [Practitioner Retriever] --> ~77 items  (Serper + lista autori)
    |
    +-- [Trusted Source Retriever] --> ~43 items (RSS parsing)
    |
    +-- [Keyword Retriever]      --> ~37 items  (Serper + keyword config)
    |
    +-- [Trend Retriever]        --> ~13 items  (Serper + YouTube + AI analysis)
```

**Gestione errori per retriever:**
- Timeout singolo retriever (>60s): skip, log warning, continua
- API error: retry 2x con backoff esponenziale (2s, 4s), poi skip
- Se 3+ retriever falliscono: warning critico ma il run continua
- Se TUTTI i retriever falliscono: run marcato come `failed`, notifica

#### Step 3: Aggregazione e Deduplicazione

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Research Orchestrator |
| **Input** | ~253 items grezzi da tutti i retriever |
| **Output** | ~198 items deduplicati |
| **Durata** | 10-20 secondi |

**Logica:**
1. Merge di tutti gli items in un pool unico
2. Normalizzazione URL (rimozione parametri tracking, www, trailing slash)
3. Deduplicazione per URL esatto
4. Deduplicazione semantica (embedding similarity > 0.85):
   - Calcola embedding per titolo + primo paragrafo di ogni item
   - Per ogni coppia con similarity > soglia, mantiene il migliore
   - Criterio: priorita' retriever > data piu' recente > lunghezza summary
5. Annotazione items con metadata di provenienza
6. Salvataggio nel database come `research_items` con status `pending`

#### Step 4: Trigger Scoring Automatico

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Research Orchestrator --> Scoring Agent |
| **Input** | Lista items deduplicati |
| **Output** | Avvio pipeline di scoring |
| **Durata** | <1 secondo (solo trigger) |

**Azioni:**
1. Aggiorna il run con statistiche finali
2. Emette evento WebSocket `pipeline:status` con `step_completed`
3. Avvia automaticamente la Pipeline 2 (Content Scoring)
4. Aggiorna lo status del run a `scoring`

#### Step 5: Completamento

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Research Orchestrator |
| **Input** | Conferma completamento scoring |
| **Output** | Run completato |
| **Durata** | <1 secondo |

**Azioni:**
1. Aggiorna run status a `completed`
2. Calcola statistiche finali (items per retriever, costi, durata)
3. Emette evento WebSocket `pipeline:status` con `completed`
4. Log completo nel sistema di attivita'

### Struttura Workflow n8n

```
[Cron Trigger 07:00] --> [HTTP Request: POST /api/research/trigger]
                              |
                              v
                    [Wait for Webhook: research.completed]
                              |
                              v
                    [IF: items_after_dedup > 0]
                         |            |
                        YES          NO
                         |            |
                         v            v
              [Log: Success]    [Notification: No items]
                         |
                         v
              [HTTP Request: POST /api/scoring/run]
```

**Nodi n8n:**
1. **Cron Trigger:** Schedule node configurato per 07:00 CET, lunedi-domenica
2. **HTTP Request (trigger):** POST a `/api/research/trigger` con JWT service account
3. **Wait for Webhook:** Attende il completamento del run (timeout 10 minuti)
4. **IF Node:** Verifica che ci siano items da processare
5. **HTTP Request (scoring):** Avvia lo scoring automatico
6. **Error Workflow:** Workflow separato per gestione errori con notifica Slack/email

---

## Pipeline 2: Content Scoring

### Informazioni Generali

| Proprieta' | Valore |
|---|---|
| **Trigger** | Automatico dopo Pipeline 1, oppure manuale via `POST /api/scoring/run` |
| **Durata Attesa** | 1-3 minuti (dipende dal numero di items) |
| **Costo Medio** | ~$0.15 per batch di ~200 items |
| **Output** | Items con score 0-10 su 6 parametri |
| **Workflow n8n** | `content-scoring-pipeline` |

### Step-by-Step

#### Step 1: Preparazione Batch

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Scoring Agent |
| **Input** | Lista items da `research_items` con status `pending` e `score IS NULL` |
| **Output** | Batch da 10 items ciascuno |
| **Durata** | <1 secondo |

**Azioni:**
1. Query database per items non ancora scored
2. Suddivisione in batch da 10 items
3. Caricamento pesi scoring dal brand config
4. Caricamento founder principles per parametro "Alignment"
5. Caricamento dati feedback loop (performance storica per topic)

#### Step 2: Scoring Batch (Semi-Parallelo)

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Scoring Agent (Claude Sonnet) |
| **Input** | Batch di 10 items + brand config + pesi |
| **Output** | Score 0-10 per 6 parametri + reasoning per ogni item |
| **Durata** | 5-8 secondi per batch |

**Logica:**
1. Per ogni batch, costruisce un prompt strutturato con:
   - I 6 parametri di scoring con pesi e descrizione
   - I founder principles
   - I 10 items da valutare (titolo, URL, summary, fonte, retriever)
2. Il modello restituisce JSON strutturato con score e reasoning
3. Parsing e validazione della risposta
4. Calcolo `final_score = sum(score_i * weight_i)`
5. Applicazione feedback loop bonus
6. Salvataggio nel database

**Concorrenza:** massimo 3 batch in parallelo per rispettare rate limit Anthropic.

#### Step 3: Feedback Loop Adjustment

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Scoring Agent |
| **Input** | Score base + dati performance storica |
| **Output** | Score aggiustato con feedback bonus |
| **Durata** | <1 secondo per batch |

**Logica del Feedback Loop:**
1. Per ogni item, identifica topic e retriever di provenienza
2. Cerca contenuti simili pubblicati nelle ultime 4 settimane
3. Se contenuti simili hanno avuto engagement sopra la media:
   - Bonus positivo (fino a +1.5 punti)
4. Se contenuti simili hanno avuto engagement sotto la media:
   - Nessuna penalita' ma nessun bonus
5. Il bonus e' pesato al 10% del score finale (configurabile)

#### Step 4: Completamento e Ordinamento

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Scoring Agent |
| **Input** | Tutti gli items scored |
| **Output** | Items ordinati per score decrescente |
| **Durata** | <1 secondo |

**Azioni:**
1. Aggiorna tutti gli items nel database con i relativi score
2. Ordina per `final_score` decrescente
3. Calcola statistiche (media, mediana, distribuzione)
4. Emette evento WebSocket `pipeline:status` con `scoring_completed`
5. Gli items con score >= 7.5 sono candidati per generazione contenuto

### Punto Decisionale: Approvazione Umana

Dopo lo scoring, il flusso si interrompe per l'intervento umano:

```
Items Scored (198)
    |
    v
[Dashboard: Research Items]
    |
    +-- Score >= 8.0 (evidenziati come "consigliati") --> ~30 items
    +-- Score 6.0-7.9 (visibili, non evidenziati) --> ~80 items
    +-- Score < 6.0 (nascosti per default) --> ~88 items
    |
    v
[Azione Umana]
    +-- Approva --> item.status = "approved" --> disponibile per Content Gen
    +-- Rifiuta --> item.status = "rejected"
    +-- Top Pick --> item.is_top_pick = true --> priorita' per newsletter
    +-- Archivia --> item.status = "archived"
```

### Struttura Workflow n8n

```
[Webhook: scoring.trigger] --> [Function: Prepare Batches]
                                       |
                                       v
                              [Split In Batches: size=10]
                                       |
                                       v
                              [HTTP Request: Anthropic API (Sonnet)]
                                       |
                                       v
                              [Function: Parse Scores + Feedback Loop]
                                       |
                                       v
                              [Supabase: Upsert Scores]
                                       |
                                       v
                              [Webhook Response: scoring.completed]
```

---

## Pipeline 3: Content Generation

### Informazioni Generali

| Proprieta' | Valore |
|---|---|
| **Trigger** | Manuale via `POST /api/content/generate` (dopo approvazione item) |
| **Durata Attesa** | 25-45 secondi |
| **Costo Medio** | ~$0.08 per singola generazione (writer + editor) |
| **Output** | Draft completo con 2 versioni (writer + editor) |
| **Workflow n8n** | `content-generation-pipeline` |

### Step-by-Step

#### Step 1: Validazione e Preparazione

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Content Service |
| **Input** | `item_id`, `platform`, `content_type`, `options` |
| **Output** | Contesto completo per il Writer Agent |
| **Durata** | <1 secondo |

**Azioni:**
1. Verifica che l'item sia in status `approved`
2. Carica il dettaglio completo dell'item (titolo, URL, summary, score breakdown)
3. Carica la configurazione brand (tone of voice, founder principles, target audience)
4. Carica le specifiche della piattaforma target (limiti, formati, best practice)
5. Crea il record `content_draft` con status `generating`
6. Emette evento WebSocket `pipeline:status` con `generation_started`

#### Step 2: Generazione Contenuto (Writer Agent)

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Writer Agent (`opus_writer`) - Claude Opus 4.6 |
| **Input** | Research item + brand config + generation params |
| **Output** | Draft v1 (testo completo, hook, CTA, hashtag) |
| **Durata** | 12-18 secondi |

**Azioni:**
1. Costruisce il prompt con:
   - Research item completo con score breakdown (per contesto qualita')
   - Tone of voice e founder principles
   - Specifiche piattaforma e tipo contenuto
   - Istruzioni custom dell'utente (se presenti)
2. Chiama Claude Opus con streaming
3. Parsing dell'output strutturato (titolo, contenuto, hook, CTA, hashtag)
4. Salvataggio come versione 1 del draft
5. Log: tokens usati, costo, durata

#### Step 3: Revisione Editoriale (Editor Agent)

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Editor Agent (`opus_editor`) - Claude Opus 4.6 |
| **Input** | Draft v1 + editing guidelines + brand config |
| **Output** | Draft v2 (testo migliorato, changelog) |
| **Durata** | 8-12 secondi |

**Azioni:**
1. Riceve il draft v1 dal Writer Agent
2. Applica le editing guidelines:
   - Controllo grammaticale e stilistico
   - Miglioramento struttura e flusso
   - Verifica coerenza brand voice
   - Riduzione ridondanze
   - Rafforzamento hook e CTA
3. Produce il draft v2 con sommario delle modifiche
4. Salvataggio come versione 2 del draft
5. Aggiorna status draft a `draft` (pronto per review umana)

#### Step 4: Completamento

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Content Service |
| **Input** | Draft v2 completato |
| **Output** | Draft disponibile per review/approvazione |
| **Durata** | <1 secondo |

**Azioni:**
1. Aggiorna status draft a `draft`
2. Emette evento WebSocket `pipeline:status` con `generation_completed`
3. Notifica dashboard con link al draft
4. Log costo totale pipeline (writer + editor)

### Punto Decisionale Post-Generazione

```
Draft v2 (pronto)
    |
    v
[Dashboard: Content Drafts]
    |
    +-- Modifica manuale --> v3 (umana)
    +-- Approva direttamente --> status "approved" --> Calendar/Publishing
    +-- Avvia GOD Review --> Pipeline 4
    +-- Archivia --> status "archived"
```

### Gestione Errori

| Errore | Comportamento |
|---|---|
| Writer timeout (>30s) | Retry 1x, poi errore con notifica |
| Writer output malformato | Re-prompt con istruzione piu' esplicita |
| Editor timeout (>30s) | Salva draft v1 come unica versione, flag `editor_skipped` |
| Item non approvato | Errore 422, no generazione |
| Budget API superato | Errore 402 con notifica owner |

### Struttura Workflow n8n

```
[Webhook: content.generate] --> [Function: Validate + Prepare Context]
                                         |
                                         v
                                [HTTP Request: Anthropic Opus (Writer)]
                                         |
                                         v
                                [Function: Parse Writer Output]
                                         |
                                         v
                                [Supabase: Save Draft v1]
                                         |
                                         v
                                [HTTP Request: Anthropic Opus (Editor)]
                                         |
                                         v
                                [Function: Parse Editor Output]
                                         |
                                         v
                                [Supabase: Save Draft v2 + Update Status]
                                         |
                                         v
                                [Webhook Response: draft_id + status]
```

---

## Pipeline 4: GOD Mode Review

### Informazioni Generali

| Proprieta' | Valore |
|---|---|
| **Trigger** | Manuale via `POST /api/content/drafts/:id/god-mode` |
| **Durata Attesa** | 60-120 secondi |
| **Costo Medio** | ~$0.25 per review completa |
| **Output** | Contenuto finale revisionato con report qualita' |
| **Workflow n8n** | `god-mode-review-pipeline` |

### Step-by-Step

I 4 agenti GOD operano in sequenza. Ogni agente riceve l'output dei precedenti.

#### Step 1: God Advocate (Analisi Critica)

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | God Advocate (Claude Sonnet) |
| **Input** | Draft finale + brand config |
| **Output** | Lista criticita', punti di forza, rischi |
| **Durata** | 5-8 secondi |

**Azioni:**
1. Analizza il draft con occhio critico
2. Identifica affermazioni non supportate
3. Verifica coerenza logica
4. Valuta valore reale per il lettore
5. Segnala rischi reputazionali
6. Produce report strutturato con severity (high/medium/low)

**Punto Decisionale:**
- Se ci sono criticita' `severity: high` > 3: flag `needs_major_revision`
- Se ci sono solo criticita' `medium/low`: continua pipeline normalmente

#### Step 2: God Factchecker (Verifica Fatti)

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | God Factchecker (Claude Sonnet + Serper API) |
| **Input** | Draft + feedback Advocate |
| **Output** | Lista claim con verdetti (verified/unverified/false) |
| **Durata** | 10-15 secondi |

**Azioni:**
1. Estrae tutti i claim verificabili dal testo
2. Per ogni claim, genera 1-2 query di verifica
3. Esegue ricerche Serper per trovare conferme/smentite
4. Confronta claim con risultati della ricerca
5. Assegna verdetto e livello di confidenza
6. Suggerisce correzioni per claim falsi/fuorvianti

**Punto Decisionale:**
- Se claim `false` > 0: flag `factcheck_failed`, il Synthesis deve correggere
- Se `overall_accuracy` < 0.7: flag `low_accuracy`, consigliata revisione umana
- Se tutti `verified`: continua senza flag

#### Step 3: God Creative (Miglioramenti Creativi)

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | God Creative (Claude Sonnet) |
| **Input** | Draft + feedback Advocate + (opzionale) focus areas |
| **Output** | Suggerimenti creativi, angoli alternativi, metafore |
| **Durata** | 5-8 secondi |

**Azioni:**
1. Analizza il draft nel contesto del feedback dell'Advocate
2. Propone hook alternativi piu' efficaci
3. Suggerisce metafore e analogie pertinenti
4. Identifica opportunita' di storytelling
5. Propone elementi di "pattern interrupt"
6. Tutte le proposte rispettano il brand voice

#### Step 4: God Synthesis (Integrazione Finale)

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | God Synthesis (Claude Opus 4.6) |
| **Input** | Draft originale + feedback Advocate + risultati Factcheck + suggerimenti Creative |
| **Output** | Contenuto finale + report delle scelte |
| **Durata** | 15-20 secondi |

**Azioni:**
1. Raccoglie tutti i feedback dei 3 agenti precedenti
2. Valuta ogni suggerimento/correzione nel contesto globale
3. Accetta le correzioni fattuali (claim falsi sostituiti)
4. Seleziona i miglioramenti creativi piu' adatti al brand
5. Integra i cambiamenti mantenendo coerenza narrativa
6. Produce il testo finale
7. Documenta ogni scelta fatta (accettata/rifiutata con motivazione)
8. Calcola quality metrics finali

**Punto Decisionale Finale:**

```
Quality Metrics del Synthesis
    |
    +-- overall >= 8.5 AND accuracy >= 9.0
    |     --> approval_recommendation: "auto_approve"
    |     --> Draft automaticamente approvato (se configurato)
    |
    +-- overall >= 6.5 AND accuracy >= 7.0
    |     --> approval_recommendation: "human_review"
    |     --> Draft in attesa di review umana
    |
    +-- overall < 6.5 OR accuracy < 7.0
          --> approval_recommendation: "needs_revision"
          --> Draft marcato per revisione, notifica all'editor
```

#### Step 5: Salvataggio e Notifica

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Content Service |
| **Input** | Output God Synthesis |
| **Output** | Draft aggiornato con review completa |
| **Durata** | <1 secondo |

**Azioni:**
1. Salva il contenuto finale come nuova versione del draft
2. Salva il report GOD completo (tutti i feedback + scelte)
3. Aggiorna status draft basato su `approval_recommendation`
4. Emette evento WebSocket `pipeline:status` con `god_review_completed`
5. Log costo totale GOD review

### Gestione Errori

| Errore | Comportamento |
|---|---|
| Advocate timeout | Skip Advocate, continua con Factchecker (degraded) |
| Factchecker timeout | Ritenuto critico: retry 2x, poi errore pipeline |
| Factchecker Serper error | Continua con fact-check solo AI (meno affidabile, flag) |
| Creative timeout | Skip Creative, Synthesis lavora solo con Advocate + Factcheck |
| Synthesis timeout | Retry 2x con Opus, poi fallback a Sonnet (qualita' degradata) |
| Synthesis fallback a Sonnet | Flag `synthesis_degraded` nel report |

### Struttura Workflow n8n

```
[Webhook: god-mode.trigger]
         |
         v
[HTTP Request: Anthropic Sonnet (Advocate)]
         |
         v
[Function: Check Advocate Severity]
         |
    [IF: high_severity_count > 3]
         |            |
        YES          NO
         |            |
         v            v
[Flag: major_rev]  [Continue]
         |            |
         +-----+------+
               |
               v
[HTTP Request: Anthropic Sonnet (Factchecker)] + [HTTP Request: Serper]
               |
               v
[Function: Merge Factcheck Results]
               |
               v
[HTTP Request: Anthropic Sonnet (Creative)]
               |
               v
[Function: Aggregate All Feedback]
               |
               v
[HTTP Request: Anthropic Opus (Synthesis)]
               |
               v
[Function: Parse Synthesis + Quality Metrics]
               |
               v
[Supabase: Update Draft + Save GOD Report]
               |
               v
[Switch: approval_recommendation]
    |            |            |
auto_approve  human_review  needs_revision
    |            |            |
    v            v            v
[Update:     [Notify:      [Notify:
 approved]    review]       revision]
```

---

## Pipeline 5: Newsletter Composition

### Informazioni Generali

| Proprieta' | Valore |
|---|---|
| **Trigger** | Manuale via `POST /api/newsletter/generate` (settimanale, tipicamente lunedi) |
| **Durata Attesa** | 3-8 minuti (generazione candidati + GOD review) |
| **Costo Medio** | ~$0.85 per newsletter completa |
| **Output** | Newsletter pronta per invio con 3 sezioni (sistema, strumento, mossa) |
| **Workflow n8n** | `newsletter-composition-pipeline` |

### Step-by-Step

#### Step 1: Selezione Candidati

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Newsletter Service |
| **Input** | Configurazione slot + items approvati della settimana |
| **Output** | 3 candidati per ogni slot (9 totali) |
| **Durata** | 2-5 secondi |

**Logica di Selezione per ogni Slot:**

| Slot | Descrizione | Criteri di Selezione |
|---|---|---|
| **Sistema** | Framework, strategia, visione | Score >= 7.5, retriever preferiti: semantic, practitioner. Focus su applicability |
| **Strumento** | Tool, software, tecnologia | Score >= 7.0, retriever preferiti: keyword, trend. Focus su concreteness |
| **Mossa** | Azione pratica, how-to | Score >= 7.0, retriever preferiti: practitioner, trusted_source. Focus su applicability |

**Algoritmo di Selezione:**
1. Per ogni slot, filtra items per:
   - Status `approved` e non ancora usati in newsletter precedenti
   - Score minimo del slot
   - Top picks hanno priorita' assoluta
2. Ordina per score decrescente con bonus per retriever preferiti
3. Seleziona i top 3 come candidati

#### Step 2: Generazione Contenuto Candidati

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Writer Agent (Opus) per ogni candidato |
| **Input** | 9 items selezionati come candidati |
| **Output** | 9 bozze di sezione newsletter (600-800 parole ciascuna) |
| **Durata** | 90-180 secondi (3 paralleli x 3 sequenziali) |

**Azioni:**
1. Per ogni candidato, genera una bozza di sezione newsletter tramite Writer Agent
2. Parallelismo: 3 generazioni simultanee (1 per slot)
3. Ogni bozza include: titolo sezione, corpo, key takeaway, link sorgente
4. Salvataggio come candidati della newsletter

#### Step 3: Selezione Umana dei Candidati

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Dashboard (intervento umano) |
| **Input** | 3 candidati per slot visualizzati nella dashboard |
| **Output** | 1 candidato selezionato per slot (3 totali) |
| **Durata** | Variabile (attesa decisione umana) |

**Flusso nella Dashboard:**
1. L'editor visualizza i 3 candidati per ogni slot con preview
2. Per ogni slot, seleziona il candidato migliore via `POST /api/newsletter/:id/select-slot`
3. Possibilita' di rigenerare candidati per uno slot specifico
4. Quando tutti e 3 gli slot sono assegnati, procede al passo successivo

#### Step 4: GOD Review Newsletter

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | NL GOD System (nl_god_factcheck, nl_god_creative, nl_god_synthesis) |
| **Input** | 3 sezioni selezionate + intro/outro template |
| **Output** | Newsletter completa revisionata |
| **Durata** | 60-90 secondi |

**Differenze rispetto al GOD standard:**
- Factcheck opera sull'intero corpo (piu' claim da verificare)
- Creative si concentra su transizioni tra sezioni e filo narrativo
- Synthesis assembla intro, 3 sezioni e outro in un testo coerente

#### Step 5: Preview e Test

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Newsletter Service |
| **Input** | Newsletter completa |
| **Output** | HTML renderizzato + email di test |
| **Durata** | 5-10 secondi |

**Azioni:**
1. Rendering HTML dal template newsletter con contenuti
2. Generazione URL di preview
3. Invio email di test (se richiesto) all'indirizzo specificato
4. Calcolo statistiche: word count, tempo lettura stimato, link count

#### Step 6: Approvazione e Invio

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Newsletter Service + Email Provider (Resend) |
| **Input** | Newsletter approvata + conferma invio |
| **Output** | Newsletter inviata a tutti gli iscritti |
| **Durata** | 10-20 minuti (invio graduale) |

**Azioni:**
1. L'owner approva l'invio via `POST /api/newsletter/:id/send`
2. Conferma esplicita richiesta (`confirm: true`)
3. Possibilita' di invio immediato o programmato (`scheduled_at`)
4. Invio tramite Resend API con rate limiting (evita blocco per spam)
5. Monitoraggio delivery in tempo reale
6. Aggiornamento status a `sent` al completamento

### Gestione Errori

| Errore | Comportamento |
|---|---|
| Candidati insufficienti per un slot | Allarga criteri (riduce score minimo di 0.5), retry. Se ancora insufficienti, notifica editor |
| Writer timeout per candidato | Retry 1x, poi marca candidato come `generation_failed` |
| GOD review fallisce | Newsletter salvata senza review GOD, flag `god_review_skipped` |
| Email provider error | Retry con backoff, max 3 tentativi. Se fallisce, notifica owner |
| Partial delivery failure | Log bounce, continua con gli altri destinatari |

### Struttura Workflow n8n

```
[Webhook: newsletter.generate]
         |
         v
[Function: Select Candidates (3 per slot)]
         |
         v
[Split In Batches: per slot]
         |
         v
[HTTP Request: Anthropic Opus (Writer x3 per slot)]
         |
         v
[Wait: Human Selection via Dashboard]
         |
         v
[Webhook: newsletter.slots_filled]
         |
         v
[HTTP Request: NL GOD Factcheck]
         |
         v
[HTTP Request: NL GOD Creative]
         |
         v
[HTTP Request: NL GOD Synthesis]
         |
         v
[Function: Render HTML Template]
         |
         v
[Wait: Human Approval]
         |
         v
[Webhook: newsletter.send_approved]
         |
         v
[HTTP Request: Resend API (Send)]
         |
         v
[Function: Monitor Delivery]
         |
         v
[Supabase: Update Status to "sent"]
```

---

## Pipeline 6: Social Publishing

### Informazioni Generali

| Proprieta' | Valore |
|---|---|
| **Trigger** | Automatico da Calendar (scheduled_at), oppure manuale |
| **Durata Attesa** | 5-15 secondi per pubblicazione |
| **Costo Medio** | Incluso nel costo infrastruttura (Postiz) |
| **Output** | Post pubblicato sulla piattaforma target |
| **Workflow n8n** | `social-publishing-pipeline` |

### Step-by-Step

#### Step 1: Verifica Scheduling

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Calendar Service |
| **Input** | Eventi con `scheduled_at` nel prossimo intervallo |
| **Output** | Lista pubblicazioni da eseguire |
| **Durata** | <1 secondo |

**Azioni:**
1. Cron ogni 5 minuti verifica eventi nel calendario
2. Seleziona eventi con `scheduled_at` entro i prossimi 5 minuti
3. Verifica che il draft collegato sia in status `approved`
4. Prepara il payload per la pubblicazione

#### Step 2: Adattamento Piattaforma Finale

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Social Curation Agent (specifico per piattaforma) |
| **Input** | Draft approvato + specifiche piattaforma |
| **Output** | Contenuto formattato e ottimizzato per la piattaforma |
| **Durata** | 3-5 secondi |

**Azioni:**
1. Applica le ultime ottimizzazioni platform-specific
2. Verifica limiti di caratteri
3. Formatta hashtag secondo le convenzioni della piattaforma
4. Prepara media allegati (immagini, video) se presenti

#### Step 3: Pubblicazione via Postiz

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Postiz API |
| **Input** | Contenuto formattato + media + scheduling info |
| **Output** | Post ID dalla piattaforma + conferma pubblicazione |
| **Durata** | 5-10 secondi |

**Azioni:**
1. Chiama Postiz API con il contenuto e i media
2. Postiz gestisce la pubblicazione sulla piattaforma target
3. Riceve il post ID dalla piattaforma
4. Salva il post ID nel database per tracking analytics

#### Step 4: Conferma e Tracking

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Content Service |
| **Input** | Conferma pubblicazione da Postiz |
| **Output** | Draft aggiornato con status `published` |
| **Durata** | <1 secondo |

**Azioni:**
1. Aggiorna status draft a `published`
2. Salva timestamp di pubblicazione e post ID
3. Aggiorna evento calendario a `published`
4. Inizia tracking analytics (dopo 24-48h)
5. Emette evento WebSocket `pipeline:status` con `published`

### Logica di Retry

```
Tentativo di pubblicazione
    |
    +-- Successo --> Conferma + Tracking
    |
    +-- Errore
         |
         +-- Rate limit Postiz --> Wait 60s --> Retry (max 3x)
         |
         +-- Errore piattaforma (400) --> Log errore, notifica editor
         |
         +-- Timeout (>30s) --> Retry (max 2x)
         |
         +-- Errore autenticazione (401) --> Notifica owner (token scaduto)
         |
         +-- Dopo 3 fallimenti --> Status "failed", notifica editor
              con opzione di riprogrammazione manuale
```

### Gestione Multi-Piattaforma

Se un contenuto e' programmato per piu' piattaforme contemporaneamente:

1. Le pubblicazioni vengono eseguite in sequenza con 30s di intervallo
2. Il fallimento su una piattaforma non blocca le altre
3. Ogni piattaforma ha il suo stato indipendente
4. Il report finale mostra lo stato per piattaforma

### Struttura Workflow n8n

```
[Cron Trigger: ogni 5 min]
         |
         v
[Supabase: Query events WHERE scheduled_at <= NOW + 5min]
         |
         v
[IF: events.length > 0]
         |
        YES
         |
         v
[Split In Batches: per evento]
         |
         v
[HTTP Request: Social Curation Agent]
         |
         v
[HTTP Request: Postiz API (Publish)]
         |
         v
[IF: publish_success]
    |            |
   YES          NO
    |            |
    v            v
[Supabase:   [Wait 60s]
 Update       |
 "published"] v
            [Retry: max 3x]
              |
              v
            [IF: still_failed]
              |
              v
            [Notification: publish_failed]
```

---

## Pipeline 7: Analytics Feedback Loop

### Informazioni Generali

| Proprieta' | Valore |
|---|---|
| **Trigger** | Cron notturno 02:00 CET (AutoResearch), oppure dopo 48h dalla pubblicazione |
| **Durata Attesa** | 5-10 minuti |
| **Costo Medio** | ~$0.05 per ciclo |
| **Output** | Scoring weights aggiornati + dati per il feedback loop bonus |
| **Workflow n8n** | `analytics-feedback-loop` |

### Step-by-Step

#### Step 1: Raccolta Metriche Social

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Analytics Service + Postiz API |
| **Input** | Lista post pubblicati nelle ultime 48h-7 giorni |
| **Output** | Metriche engagement per ogni post |
| **Durata** | 30-60 secondi |

**Azioni:**
1. Query database per post pubblicati con `published_at` nel range
2. Per ogni post, chiama Postiz API per raccogliere metriche aggiornate
3. Metriche raccolte: impressioni, like, commenti, share, save, click
4. Calcola engagement rate per ogni post
5. Salva le metriche nel database

#### Step 2: Raccolta Metriche Newsletter

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Analytics Service + Resend API |
| **Input** | Newsletter inviate nelle ultime 2 settimane |
| **Output** | Metriche engagement newsletter (open rate, CTR, unsubscribe) |
| **Durata** | 10-20 secondi |

**Azioni:**
1. Query database per newsletter con `sent_at` nel range
2. Per ogni newsletter, chiama Resend API per metriche aggiornate
3. Metriche: opens, clicks, bounces, unsubscribes, spam reports
4. Calcola metriche aggregate e per sezione (quale slot performa meglio)
5. Salva nel database

#### Step 3: Analisi Correlazione Topic-Performance

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Content Trend Agents (Claude Sonnet) |
| **Input** | Metriche + metadata dei contenuti (topic, retriever, score) |
| **Output** | Correlazioni topic-performance |
| **Durata** | 30-60 secondi |

**Azioni:**
1. Per ogni contenuto pubblicato, mappa:
   - Topic/keyword del research item sorgente
   - Retriever di provenienza
   - Score originale (breakdown per parametro)
   - Performance effettiva (engagement rate)
2. Identifica pattern:
   - Quali topic hanno performato sopra/sotto la media
   - Quali retriever producono items a maggior engagement
   - Quale parametro di scoring correla meglio con l'engagement reale
3. Genera report correlazioni

#### Step 4: Aggiornamento Feedback Loop Data

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Scoring Service |
| **Input** | Correlazioni topic-performance |
| **Output** | Dati aggiornati per il feedback_loop_bonus dello scoring |
| **Durata** | <5 secondi |

**Azioni:**
1. Aggiorna la tabella `topic_performance` con i nuovi dati
2. Ricalcola i bonus/malus per topic:
   - Topic con engagement > 1.5x media --> bonus +1.0 a +1.5
   - Topic con engagement 1.0x-1.5x media --> bonus +0.5
   - Topic con engagement < 1.0x media --> nessun bonus
3. Questi dati alimenteranno il parametro "Feedback Loop Bonus" nello scoring futuro

#### Step 5: Suggerimento Aggiornamento Pesi (Opzionale)

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Analytics AI Agent (Claude Sonnet) |
| **Input** | Correlazioni storiche (ultimi 30-90 giorni) |
| **Output** | Suggerimenti per aggiornamento pesi scoring |
| **Durata** | 10-15 secondi |

**Azioni:**
1. Analizza quali parametri di scoring correlano meglio con l'engagement reale
2. Se la correlazione e' significativamente diversa dai pesi attuali:
   - Propone nuovi pesi ottimizzati
   - Notifica l'owner con il suggerimento
   - **Non applica automaticamente** (decisione umana)
3. Report con:
   - Correlazione attuale per parametro
   - Pesi suggeriti
   - Impatto stimato sul futuro scoring

### Punto Decisionale

```
Suggerimento nuovi pesi
    |
    v
[Notifica Owner]
    |
    +-- Owner accetta --> PUT /api/scoring/weights (nuovi pesi)
    |                     + POST /api/scoring/run (force_rescore: true)
    |
    +-- Owner rifiuta --> Nessuna azione, prossimo ciclo ricalcola
    |
    +-- Owner modifica --> Owner regola manualmente i pesi suggeriti
```

### Struttura Workflow n8n

```
[Cron Trigger: 02:00 CET]
         |
         v
[Supabase: Query published content (last 7 days)]
         |
         v
[Split: Social posts / Newsletter]
    |                    |
    v                    v
[HTTP Request:     [HTTP Request:
 Postiz API         Resend API
 (get metrics)]     (get metrics)]
    |                    |
    +--------+-----------+
             |
             v
[Supabase: Save Metrics]
             |
             v
[HTTP Request: Anthropic Sonnet (Trend Analysis)]
             |
             v
[Function: Calculate Topic Performance Bonuses]
             |
             v
[Supabase: Update topic_performance table]
             |
             v
[IF: significant_weight_change_suggested]
    |            |
   YES          NO
    |            |
    v            v
[Notification: [Log: No
 Weight        changes
 Suggestion]   needed]
```

---

## Pipeline 8: Writing Lab A/B

### Informazioni Generali

| Proprieta' | Valore |
|---|---|
| **Trigger** | Manuale via `POST /api/writing-lab/sessions` |
| **Durata Attesa** | 5-10 secondi per round |
| **Costo Medio** | ~$0.03 per round |
| **Output** | Champion ottimizzato dopo N round di A/B testing |
| **Workflow n8n** | `writing-lab-ab-pipeline` |

### Step-by-Step

#### Step 1: Creazione Sessione

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Writing Lab Service |
| **Input** | Testi champion e challenger + criteri di valutazione |
| **Output** | Sessione creata con Round 1 pronto |
| **Durata** | 5-8 secondi |

**Azioni:**
1. Crea record sessione con configurazione
2. Genera analisi AI comparativa del Round 1 (champion vs challenger)
3. L'analisi evidenzia punti di forza e debolezza di ciascuna versione
4. Presenta il round all'utente per il voto

#### Step 2: Voto Umano

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Dashboard (intervento umano) |
| **Input** | Champion e Challenger con analisi AI |
| **Output** | Voto (champion o challenger) + feedback opzionale |
| **Durata** | Variabile (attesa decisione umana) |

**Flusso:**
1. L'editor visualizza entrambe le versioni affiancate
2. Legge l'analisi AI comparativa
3. Vota il vincitore via `POST /api/writing-lab/sessions/:id/vote`
4. Opzionalmente fornisce feedback testuale

**Logica Post-Voto:**
- Se il **challenger vince:** il challenger diventa il nuovo champion
- Se il **champion vince:** il champion resta invariato
- Il perdente viene usato come base per la prossima evoluzione

#### Step 3: Generazione Prossimo Round

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Writing Lab AI Agent (Claude Sonnet) |
| **Input** | Champion corrente + storico round + feedback umano |
| **Output** | Nuovo challenger evoluto |
| **Durata** | 5-8 secondi |

**Strategie di Evoluzione:**

| Strategia | Descrizione |
|---|---|
| `iterate` | Migliora il testo perdente basandosi sul feedback. Piccoli cambiamenti mirati. Default. |
| `mutate` | Genera un approccio completamente nuovo, diverso sia dal champion che dal challenger precedente |
| `hybrid` | Combina elementi vincenti di entrambi in una nuova versione |

**Azioni:**
1. Analizza lo storico dei round (chi ha vinto, perche')
2. Incorpora il feedback umano
3. Genera un nuovo challenger secondo la strategia scelta
4. Produce analisi comparativa per il nuovo round
5. Il ciclo si ripete finche':
   - Si raggiunge `max_rounds` (default: 5)
   - L'utente chiude manualmente la sessione
   - Il champion vince 3 round consecutivi (convergenza)

#### Step 4: Completamento Sessione

| Proprieta' | Dettaglio |
|---|---|
| **Servizio** | Writing Lab Service |
| **Input** | Sessione con tutti i round completati |
| **Output** | Champion finale + report evoluzione |
| **Durata** | <1 secondo |

**Azioni:**
1. Sessione marcata come `completed`
2. Champion finale salvato come "best version"
3. Generazione report evoluzione:
   - Percorso di miglioramento round per round
   - Insight su cosa funziona meglio per il brand
   - Suggerimenti per applicare i learning ad altri contenuti
4. Opzionale: il champion finale puo' essere usato come template/riferimento per future generazioni

### Gestione Errori

| Errore | Comportamento |
|---|---|
| AI generation timeout | Retry 1x, poi offri opzione di scrivere challenger manualmente |
| Analisi comparativa fallisce | Presenta i due testi senza analisi, voto comunque possibile |
| Sessione con 0 voti dopo 7 giorni | Notifica reminder all'editor |

### Struttura Workflow n8n

```
[Webhook: writing-lab.create]
         |
         v
[HTTP Request: Anthropic Sonnet (Generate Analysis Round 1)]
         |
         v
[Supabase: Save Session + Round 1]
         |
         v
[Wait: Human Vote via Dashboard]
         |
         v
[Webhook: writing-lab.vote]
         |
         v
[Function: Update Score + Determine New Champion]
         |
         v
[IF: rounds_remaining > 0 AND NOT convergence]
    |            |
   YES          NO
    |            |
    v            v
[HTTP Request: [Function:
 Anthropic      Close Session
 Sonnet         + Generate
 (New           Report]
 Challenger)]
    |
    v
[Supabase: Save New Round]
    |
    v
[Loop back to: Wait Human Vote]
```

---

## Diagramma Integrato

Visualizzazione completa di tutte le pipeline e le loro interconnessioni nel ciclo settimanale tipico.

```
LUNEDI' 07:00
    |
    v
[P1: Daily Research] --auto--> [P2: Scoring]
    |                               |
    v                               v
LUNEDI'-VENERDI'              Items scored
07:00 ogni giorno              nella dashboard
    |                               |
    |                          [Approvazione Umana]
    |                               |
    |         +---------------------+---------------------+
    |         |                     |                     |
    |    Top Picks              Approved              Approved
    |    per NL                 per Social            per Blog
    |         |                     |                     |
    |         v                     v                     v
    |    [P5: Newsletter]      [P3: Content Gen]    [P3: Content Gen]
    |         |                     |                     |
    |    MARTEDI' (comp.)          |                     |
    |         |                [P4: GOD Review]      [P4: GOD Review]
    |         v                     |                     |
    |    GOD Review NL              |                     |
    |         |                     v                     |
    |    MARTEDI' 07:00        [P6: Social Pub]          |
    |    (invio)               via Calendar              |
    |         |                     |                     |
    |         v                     v                     v
    |    Metriche NL           Metriche Social       SEO Tracking
    |         |                     |                     |
    |         +----------+----------+                     |
    |                    |                                |
    |                    v                                |
    |           [P7: Feedback Loop]                       |
    |           OGNI NOTTE 02:00                          |
    |                    |                                |
    |                    v                                |
    |           Scoring aggiornato                        |
    |                                                     |
    |    +--- [P8: Writing Lab] (quando necessario) ------+
    |    |    Sessioni A/B per miglioramento continuo
    |    |
    v    v
CICLO SETTIMANALE SI RIPETE
```

### Tempistiche Tipiche Settimanali

| Giorno | Orario | Pipeline | Azione |
|---|---|---|---|
| Lun-Dom | 07:00 | P1 + P2 | Daily Research + Scoring automatico |
| Lun-Ven | 09:00-18:00 | P3 + P4 | Generazione + Review contenuti (manuale) |
| Lun | 10:00 | P5 (step 1-3) | Composizione newsletter (selezione candidati) |
| Mar | 06:00 | P5 (step 4-6) | GOD Review + Invio newsletter |
| Lun-Ven | Configurati | P6 | Pubblicazione social (da calendario) |
| Ogni notte | 02:00 | P7 | Analytics Feedback Loop |
| Su richiesta | - | P8 | Writing Lab A/B testing |

---

## Monitoraggio e Alerting

### Dashboard di Monitoraggio

Tutte le pipeline sono monitorate tramite:

1. **WebSocket Real-time:** eventi `pipeline:status` per tracking live
2. **Activity Log:** tutte le azioni degli agenti loggate con `GET /api/system/activity`
3. **Health Check:** `GET /api/system/health` per stato generale

### Soglie di Alert

| Metrica | Soglia Warning | Soglia Critical | Azione |
|---|---|---|---|
| Research run duration | > 5 min | > 10 min | Notifica, verifica retriever |
| Scoring batch failure rate | > 10% | > 30% | Notifica, verifica API key |
| Content generation timeout | > 45s | > 90s | Retry, poi notifica |
| GOD review timeout | > 120s | > 180s | Skip agente fallito, notifica |
| Newsletter send failure | > 1% bounce | > 5% bounce | Verifica lista, notifica |
| API cost daily | > $8 | > $15 | Notifica owner |
| API cost monthly | > 80% budget | > 95% budget | Notifica + throttle opzionale |

### Log e Tracciabilita'

Ogni esecuzione di pipeline genera:

```typescript
{
  pipeline_id: string;
  pipeline_type: "research" | "scoring" | "content_gen" | "god_review" | "newsletter" | "social_pub" | "feedback_loop" | "writing_lab";
  started_at: string;
  completed_at: string;
  status: "completed" | "failed" | "partial";
  steps: [
    {
      step_name: string;
      agent_id: string;
      started_at: string;
      completed_at: string;
      status: "completed" | "failed" | "skipped";
      input_summary: string;
      output_summary: string;
      cost_usd: number;
      tokens_used: number;
      error: string | null;
    }
  ];
  total_cost_usd: number;
  total_duration_ms: number;
}
```

### Recovery e Idempotenza

- Ogni pipeline e' progettata per essere **idempotente**: rieseguirla con gli stessi input produce lo stesso risultato
- In caso di fallimento parziale, la pipeline puo' essere **ripresa** dall'ultimo step riuscito
- I dati intermedi sono salvati nel database a ogni step, permettendo il debug
- Le operazioni di scrittura usano **transazioni** per garantire consistenza
