# Documentazione Agenti AI - AI Content Engine

> Catalogo completo di tutti gli agenti AI del sistema, con ruoli, modelli, input/output e costi.
> Ultimo aggiornamento: 2026-04-11

---

## Indice

- [Panoramica Agenti](#panoramica-agenti)
- [Mappa Interazioni](#mappa-interazioni)
- [Research Agents](#research-agents)
  - [Research Orchestrator](#1-research-orchestrator)
  - [Retriever: Semantic](#2-retriever-semantic)
  - [Retriever: Practitioner](#3-retriever-practitioner)
  - [Retriever: Trusted Source](#4-retriever-trusted-source)
  - [Retriever: Keyword](#5-retriever-keyword)
  - [Retriever: Trend](#6-retriever-trend)
- [Scoring Agent](#scoring-agent)
- [Content Generation Agents](#content-generation-agents)
  - [Writer Agent](#7-writer-agent-opus_writer)
  - [Editor Agent](#8-editor-agent-opus_editor)
  - [Adapter Agent](#9-adapter-agent-sonnet_adapter)
  - [Carousel Generator](#10-carousel-generator)
- [GOD System Agents](#god-system-agents)
  - [God Advocate](#11-god-advocate)
  - [God Factchecker](#12-god-factchecker)
  - [God Creative](#13-god-creative)
  - [God Synthesis](#14-god-synthesis)
- [Social Curation Agents](#social-curation-agents)
- [Newsletter Agents](#newsletter-agents)
- [Utility Agents](#utility-agents)
- [Tabella Riepilogativa Costi](#tabella-riepilogativa-costi)
- [Gestione Modelli e Fallback](#gestione-modelli-e-fallback)

---

## Panoramica Agenti

Il sistema AI Content Engine impiega **oltre 25 agenti specializzati**, organizzati in 7 categorie funzionali. Ogni agente ha un ruolo preciso, un modello AI assegnato in base al rapporto qualita'/costo richiesto, e confini di responsabilita' ben definiti.

### Principi di Design degli Agenti

1. **Specializzazione:** ogni agente fa una cosa sola e la fa bene
2. **Composabilita':** gli agenti si combinano in pipeline sequenziali o parallele
3. **Tracciabilita':** ogni azione e' loggata con costi, durata e output
4. **Resilienza:** ogni agente gestisce i propri errori con retry e fallback
5. **Cost-awareness:** il modello AI e' scelto in base alla complessita' del task

### Distribuzione Modelli

| Modello | Utilizzo | Agenti | % Budget Tipica |
|---|---|---|---|
| Claude Opus 4.6 | Task ad alta qualita' (scrittura, sintesi finale) | 3 | ~18% |
| Claude Sonnet | Task a volume (scoring, adattamento, analisi) | 15+ | ~72% |
| Nessun LLM | Generazione visuale, parsing | 2 | ~10% (infra) |

---

## Mappa Interazioni

```
                                    +-----------------------+
                                    |   RESEARCH PIPELINE   |
                                    +-----------------------+
                                              |
                         +--------------------+--------------------+
                         |                    |                    |
                    +----v----+         +-----v-----+        +----v----+
                    | Semantic|         |Practitioner|        | Trusted |
                    | Retriever|        | Retriever  |        | Source  |
                    +----+----+         +-----+-----+        +----+----+
                         |                    |                    |
                         |    +--------+      |      +--------+   |
                         |    |Keyword |      |      | Trend  |   |
                         |    |Retriever|     |      |Retriever|  |
                         |    +---+----+      |      +---+----+   |
                         |        |           |          |        |
                         +--------+-----------+----------+--------+
                                              |
                                    +---------v----------+
                                    | Research            |
                                    | Orchestrator        |
                                    | (dedup + merge)     |
                                    +---------+----------+
                                              |
                                    +---------v----------+
                                    |   SCORING AGENT     |
                                    |   (6 parametri)     |
                                    +---------+----------+
                                              |
                                    +---------v----------+
                                    |  APPROVAZIONE UMANA |
                                    +---------+----------+
                                              |
                              +---------------+---------------+
                              |                               |
                    +---------v----------+          +---------v----------+
                    |   WRITER AGENT     |          |  NEWSLETTER GEN    |
                    |   (Opus)           |          |  (candidati slot)  |
                    +---------+----------+          +---------+----------+
                              |                               |
                    +---------v----------+          +---------v----------+
                    |   EDITOR AGENT     |          |  NL GOD System     |
                    |   (Opus)           |          |  (factcheck+synth) |
                    +---------+----------+          +---------+----------+
                              |                               |
                    +---------v----------+          +---------v----------+
                    |   GOD SYSTEM       |          |  APPROVAZIONE      |
                    |   (4 agenti)       |          |  + INVIO           |
                    +---------+----------+          +--------------------+
                              |
                    +---------v----------+
                    |  ADAPTER AGENT     |
                    |  (multi-platform)  |
                    +---------+----------+
                              |
              +---------------+---------------+---------------+
              |               |               |               |
        +-----v-----+  +-----v-----+  +-----v-----+  +------v----+
        |  LinkedIn  |  |     X     |  | Instagram  |  |  TikTok   |
        |  Curation  |  |  Curation |  |  Curation  |  | Curation  |
        +-----+-----+  +-----+-----+  +-----+-----+  +-----+-----+
              |               |               |              |
              +---------------+---------------+--------------+
                              |
                    +---------v----------+
                    |   POSTIZ API       |
                    |   (publishing)     |
                    +--------------------+
```

---

## Research Agents

### 1. Research Orchestrator

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `research_orchestrator` |
| **Ruolo** | Coordina tutti i retriever, gestisce il funnel Discovery --> Final Pool |
| **Modello AI** | Claude Sonnet (coordinamento, non richiede Opus) |
| **Trigger** | Cron giornaliero 07:00 CET, oppure manuale da dashboard |
| **Costo medio per run** | ~$0.12 |

#### Responsabilita'

- Avvia tutti i retriever configurati in parallelo
- Raccoglie i risultati da ciascun retriever
- Esegue **deduplicazione semantica** (soglia di similarita' configurabile, default 0.85)
- Merge dei risultati in un pool unificato
- Assegna metadata di provenienza a ogni item
- Avvia automaticamente il processo di scoring sul pool risultante
- Gestisce errori dei singoli retriever senza bloccare l'intero run

#### Input

```typescript
{
  brand_config: {
    topics: string[];           // ["AI", "automation", "productivity"]
    sources: Source[];           // Lista fonti configurate
    scoring_weights: Weights;   // Pesi per parametri scoring
    founder_principles: string[]; // Principi del founder per allineamento
  },
  options: {
    retrievers: string[];       // Retriever da attivare
    max_items_per_retriever: number; // Limite per retriever
    dedup_threshold: number;    // Soglia deduplicazione (0-1)
  }
}
```

#### Output

```typescript
{
  run_id: string;
  total_items_found: number;    // Totale grezzo da tutti i retriever
  items_after_dedup: number;    // Totale dopo deduplicazione
  research_items: ResearchItem[]; // Items pronti per scoring
  retriever_stats: {
    [retriever: string]: {
      items_found: number;
      duration_ms: number;
      errors: Error[];
    }
  };
  dedup_removed: number;        // Items rimossi per duplicazione
}
```

#### Logica di Deduplicazione

1. Per ogni coppia di items, calcola la similarita' coseno tra gli embedding dei titoli e dei summary
2. Se la similarita' supera la soglia (default 0.85), mantiene l'item con:
   - Score sorgente piu' alto (se gia' presente)
   - Provenienza dal retriever con priorita' piu' alta
   - Data di pubblicazione piu' recente
3. Annota l'item mantenuto con i riferimenti agli items duplicati rimossi

#### Gestione Errori

| Errore | Comportamento |
|---|---|
| Retriever timeout (>60s) | Skip retriever, log warning, continua con gli altri |
| Retriever API error | Retry 2 volte con backoff esponenziale, poi skip |
| Tutti i retriever falliscono | Fallimento del run, notifica via WebSocket |
| Errore deduplicazione | Procedi senza dedup, log errore |

---

### 2. Retriever: Semantic

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `retriever_semantic` |
| **Ruolo** | Cerca contenuti per similarita' concettuale ai principi del founder |
| **Sorgente Dati** | Serper API (Google Search) |
| **Modello AI** | Claude Sonnet (per generazione query) |
| **Count Tipico** | ~83 items per run |
| **Costo medio per run** | ~$0.08 |

#### Logica Operativa

1. Riceve i `founder_principles` dalla configurazione brand
2. Genera embedding semantici dei principi tramite il modello AI
3. Produce 10-15 query di ricerca che catturano i concetti chiave dei principi
4. Esegue le query tramite Serper API
5. Filtra risultati per rilevanza linguistica e freschezza (ultimi 7 giorni di default)
6. Estrae titolo, URL, snippet, data pubblicazione per ogni risultato
7. Restituisce la lista di items al Research Orchestrator

#### Esempio Query Generate

Per il principio _"L'automazione deve liberare tempo per il pensiero strategico"_:

```
- "AI automation strategic thinking productivity"
- "automazione processi risparmio tempo decisioni"
- "workflow automation cognitive load reduction"
```

#### Configurazione

```typescript
{
  max_queries: 15,
  results_per_query: 10,
  freshness: "7d",        // Ultimi 7 giorni
  language: "it,en",      // Italiano e inglese
  exclude_domains: ["reddit.com", "quora.com"] // Escludi piattaforme UGC
}
```

---

### 3. Retriever: Practitioner

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `retriever_practitioner` |
| **Ruolo** | Cerca contenuti di professionisti con track record comprovato |
| **Sorgente Dati** | Serper API + lista curata di autori |
| **Modello AI** | Claude Sonnet (per filtraggio qualita') |
| **Count Tipico** | ~77 items per run |
| **Costo medio per run** | ~$0.07 |

#### Logica Operativa

1. Mantiene una **lista curata di autori/practitioner** riconosciuti nel settore
2. Per ogni autore, cerca i contenuti pubblicati recentemente
3. Cerca anche contenuti di nuovi autori che citano o vengono citati dagli autori in lista
4. Valuta la credibilita' del contenuto tramite AI (track record dell'autore, presenza di dati, case study)
5. Filtra per contenuti pratici e applicabili (no contenuti puramente teorici)

#### Lista Autori (Esempio)

```typescript
{
  curated_authors: [
    { name: "Ethan Mollick", platforms: ["substack", "twitter"] },
    { name: "Lenny Rachitsky", platforms: ["substack"] },
    { name: "Simon Willison", platforms: ["blog", "twitter"] },
    // ... 50+ autori curati
  ],
  discovery_mode: true, // Scopri nuovi autori automaticamente
  min_credibility_score: 6.0
}
```

---

### 4. Retriever: Trusted Source

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `retriever_trusted_source` |
| **Ruolo** | Monitora fonti autoritative pre-selezionate |
| **Sorgente Dati** | RSS Feed Parser + lista curata fonti |
| **Modello AI** | Nessuno (parsing deterministico) |
| **Count Tipico** | ~43 items per run |
| **Costo medio per run** | ~$0.01 (solo costo infrastruttura) |

#### Logica Operativa

1. Legge i feed RSS configurati nel brand (`/api/config/sources`)
2. Filtra per articoli pubblicati dall'ultimo run
3. Estrae titolo, URL, autore, data, summary dal feed
4. Non utilizza AI per il parsing: logica deterministica basata su standard RSS/Atom
5. E' il retriever piu' economico e affidabile

#### Fonti Tipiche

| Categoria | Esempi |
|---|---|
| Tech News | The Verge, Ars Technica, TechCrunch |
| AI Specifico | MIT Technology Review, AI Newsletter |
| Italiano | Il Sole 24 Ore Tech, Wired Italia |
| Substack | Newsletter di settore selezionate |
| Blog Aziendali | Blog Anthropic, OpenAI, Google DeepMind |

#### Configurazione Feed

```typescript
{
  feeds: Source[],            // Da /api/config/sources
  check_interval: "daily",   // Frequenza controllo
  max_age_hours: 48,         // Eta' massima articoli
  dedup_by_url: true         // Dedup basata su URL normalizzato
}
```

---

### 5. Retriever: Keyword

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `retriever_keyword` |
| **Ruolo** | Ricerca specifica per termini/keyword configurati |
| **Sorgente Dati** | Serper API |
| **Modello AI** | Nessuno (query pre-configurate) |
| **Count Tipico** | ~37 items per run |
| **Costo medio per run** | ~$0.04 |

#### Logica Operativa

1. Utilizza i `topics` configurati nel brand come keyword base
2. Espande le keyword con varianti linguistiche (IT/EN)
3. Esegue ricerche mirate per ogni keyword e combinazione
4. Filtra per freschezza e rilevanza
5. Non utilizza AI per la generazione query: le keyword sono deterministiche

#### Configurazione

```typescript
{
  keywords: string[],         // Da brand config topics
  combinations: boolean,      // Combina keyword (default: true)
  max_combinations: 20,       // Limite combinazioni
  freshness: "7d",
  search_type: "news",        // Priorita' notizie
  language: "it"
}
```

---

### 6. Retriever: Trend

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `retriever_trend` |
| **Ruolo** | Incrocia contenuti con predizioni trend a 6 mesi |
| **Sorgente Dati** | Serper API + YouTube Data API |
| **Modello AI** | Claude Sonnet (per analisi trend) |
| **Count Tipico** | ~13 items per run |
| **Costo medio per run** | ~$0.06 |

#### Logica Operativa

1. Analizza i trend correnti nel settore tramite Serper (Google Trends data)
2. Cerca video YouTube recenti ad alto engagement sui topic rilevanti
3. Utilizza Claude Sonnet per identificare **pattern emergenti** non ancora mainstream
4. Predice la finestra temporale di opportunita' (3-6 mesi)
5. Cerca contenuti specifici legati ai trend identificati
6. Assegna un **trend_confidence_score** a ogni item trovato

#### Analisi Trend

```typescript
{
  trend_sources: ["google_trends", "youtube", "twitter_trending"],
  prediction_horizon_months: 6,
  min_growth_rate: 0.15,     // Crescita minima 15% per essere considerato trend
  geographic_focus: "IT",     // Focus Italia
  cross_reference: true       // Incrocia con dati storici
}
```

#### Output Specifico

Oltre ai campi standard di ResearchItem, aggiunge:

```typescript
{
  trend_data: {
    trend_name: "AI Agents for SMBs",
    confidence: 0.78,
    predicted_peak: "2026-09",
    current_growth_rate: 0.34,
    geographic_relevance_it: 0.65
  }
}
```

---

## Scoring Agent

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `scoring_agent` |
| **Ruolo** | Valuta ogni research item su 6 parametri di qualita' e rilevanza |
| **Modello AI** | Claude Sonnet (cost-effective per scoring batch ad alto volume) |
| **Trigger** | Automatico dopo completamento research run, o manuale |
| **Costo medio per batch** | ~$0.15 (per ~200 items) |
| **Throughput** | ~200 items in 2 minuti |

### Parametri di Scoring

| # | Parametro | Peso Default | Descrizione |
|---|---|---|---|
| 1 | **Applicability / Concreteness** | 0.25 | Quanto il contenuto e' applicabile nella pratica. Valuta presenza di framework, step-by-step, esempi concreti, case study |
| 2 | **Credibility** | 0.20 | Attendibilita' dell'autore e della fonte. Valuta track record, citazioni, dati verificabili, peer review |
| 3 | **Alignment** | 0.20 | Allineamento con i principi del founder e il posizionamento del brand. Valuta coerenza tematica e valoriale |
| 4 | **Trend Prediction** | 0.15 | Capacita' di anticipare trend futuri. Valuta originalita', timing, potenziale di early adoption |
| 5 | **Italy Relevance** | 0.10 | Rilevanza per il mercato italiano. Valuta applicabilita' al contesto economico, culturale e normativo italiano |
| 6 | **Feedback Loop Bonus** | 0.10 | Bonus basato su performance storica di contenuti simili. Utilizza dati engagement precedenti per premiare topic vincenti |

### Logica di Scoring

1. **Batch Processing:** gli items vengono processati in batch da 10 per ottimizzare le chiamate API
2. **Context Window:** ogni item viene valutato con il contesto completo (titolo, URL, summary, fonte, retriever di provenienza)
3. **Prompt Strutturato:** il prompt include i founder_principles, i pesi configurati e le istruzioni per ogni parametro
4. **Output Strutturato:** il modello restituisce JSON con score 0-10 per parametro e reasoning

### Calcolo Score Finale

```
final_score = sum(parametro_score * parametro_weight) per tutti i parametri

// Con feedback loop bonus:
adjusted_score = final_score + (feedback_bonus * feedback_weight)

// Dove feedback_bonus dipende da:
// - Engagement rate medio di contenuti simili (topic, retriever) nelle ultime 4 settimane
// - Trend di crescita/declino dell'engagement per quel topic
```

### Prompt di Scoring (Struttura)

```
Sei un analista di contenuti per il brand [brand_name].
Il founder crede fermamente in: [founder_principles]

Valuta il seguente contenuto su una scala 0-10 per ciascun parametro.
Per ogni parametro, fornisci:
- score: numero da 0 a 10 (un decimale)
- reasoning: 1-2 frasi di giustificazione

Parametri da valutare:
1. Applicability/Concreteness (peso: [weight]): ...
2. Credibility (peso: [weight]): ...
[...]

Contenuto da valutare:
- Titolo: [title]
- Fonte: [source]
- Summary: [summary]
- Retriever: [retriever_type]

Rispondi in JSON strutturato.
```

### Gestione Errori

| Errore | Comportamento |
|---|---|
| Timeout API (>30s per item) | Retry 1 volta, poi score = null con flag `scoring_failed` |
| Risposta malformata | Re-prompt con istruzione piu' esplicita, poi fallback a score medio |
| Rate limit Anthropic | Backoff esponenziale, riprende automaticamente |
| Batch parzialmente fallito | Completa gli items riusciti, ritenta i falliti |

---

## Content Generation Agents

### 7. Writer Agent (opus_writer)

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `opus_writer` |
| **Ruolo** | Scrive il contenuto principale (newsletter, blog, post) |
| **Modello AI** | Claude Opus 4.6 |
| **Costo medio per generazione** | ~$0.15 |
| **% Budget API mensile** | ~7.5% |
| **Durata media** | 12-18 secondi |

#### Responsabilita'

- Generare contenuto originale a partire da un research item approvato
- Mantenere coerenza con il tone of voice del brand
- Strutturare il contenuto secondo il formato richiesto (post, articolo, sezione newsletter)
- Integrare dati e insight dal research item senza copiare il testo sorgente
- Produrre contenuto in italiano (o nella lingua configurata)

#### Input

```typescript
{
  research_item: {
    title: string;
    url: string;
    summary: string;
    score_breakdown: ScoreBreakdown;
  },
  brand_config: {
    tone_of_voice: ToneOfVoice;
    founder_principles: string[];
    target_audience: string;
  },
  generation_params: {
    platform: Platform;
    content_type: ContentType;
    length: "short" | "medium" | "long";
    include_cta: boolean;
    language: string;
    custom_instructions?: string;
  }
}
```

#### Output

```typescript
{
  draft: {
    title: string;
    content: string;         // Testo completo formattato
    word_count: number;
    hooks: string[];          // 2-3 hook alternativi per l'apertura
    cta: string | null;       // Call-to-action se richiesta
    hashtags: string[];       // Hashtag suggeriti
    key_takeaways: string[];  // 3-5 punti chiave
  },
  metadata: {
    model: string;
    tokens_used: number;
    generation_time_ms: number;
    confidence_score: number; // 0-1, autovalutazione qualita'
  }
}
```

#### Linee Guida Interne

- **Mai copiare** frasi dal contenuto sorgente: rielaborare sempre
- **Sempre aprire** con un hook che cattura l'attenzione
- **Usare dati concreti** quando disponibili dal research item
- **Chiudere** con un invito all'azione o una riflessione che stimola commenti
- **Adattare la lunghezza** al formato: post LinkedIn 1200-1500 caratteri, X 280 caratteri, newsletter 600-800 parole per sezione

---

### 8. Editor Agent (opus_editor)

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `opus_editor` |
| **Ruolo** | Rivede, migliora e corregge il draft del Writer Agent |
| **Modello AI** | Claude Opus 4.6 |
| **Costo medio per revisione** | ~$0.11 |
| **% Budget API mensile** | ~5.5% |
| **Durata media** | 8-12 secondi |

#### Responsabilita'

- Revisione grammaticale e stilistica
- Miglioramento della struttura e del flusso narrativo
- Verifica coerenza con il tone of voice del brand
- Riduzione ridondanze e miglioramento concisione
- Rafforzamento hook e CTA
- Segnalazione di eventuali problemi (claim non verificabili, tono incoerente)

#### Input

```typescript
{
  draft: Draft;                    // Output del Writer Agent
  editing_guidelines: {
    focus: string[];               // Es: ["conciseness", "engagement", "brand_voice"]
    max_word_count: number | null; // Limite parole se applicabile
    preserve: string[];            // Elementi da non modificare
  },
  brand_config: BrandConfig;
}
```

#### Output

```typescript
{
  edited_draft: {
    content: string;               // Testo rivisto
    word_count: number;
    changes_summary: string;       // Sommario delle modifiche
    changes_count: number;
    issues_found: Issue[];         // Problemi riscontrati
  },
  comparison: {
    readability_before: number;    // Indice leggibilita' 0-100
    readability_after: number;
    conciseness_improvement: number; // % riduzione parole superflue
  }
}
```

---

### 9. Adapter Agent (sonnet_adapter)

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `sonnet_adapter` |
| **Ruolo** | Adatta il contenuto approvato al formato e tono di ogni piattaforma social |
| **Modello AI** | Claude Sonnet |
| **Costo medio per adattamento** | ~$0.02 |
| **% Budget API mensile** | ~2.7% |
| **Durata media** | 3-5 secondi per piattaforma |

#### Responsabilita'

- Adattare un contenuto approvato alle specifiche di ogni piattaforma
- Rispettare limiti di caratteri, formati e convenzioni di ogni piattaforma
- Generare hashtag platform-specific
- Adattare il tono: piu' professionale su LinkedIn, piu' diretto su X, piu' visuale su Instagram
- Suggerire orario ottimale di pubblicazione basato sulla heatmap

#### Specifiche per Piattaforma

| Piattaforma | Limite Caratteri | Formato | Note |
|---|---|---|---|
| **LinkedIn** | 3000 (ideale 1200-1500) | Testo con line break, emoji moderate | Hook forte in prima riga (pre-"vedi altro") |
| **X (Twitter)** | 280 (thread fino a 10 tweet) | Thread se >280 char, tono diretto | Primo tweet deve funzionare standalone |
| **Instagram** | 2200 caption | Caption + suggerimento immagine/carousel | Hashtag in primo commento, non in caption |
| **Facebook** | 63206 (ideale 100-250) | Breve e conversazionale | Domanda finale per engagement |
| **TikTok** | 2200 caption | Script video + caption | Hook nei primi 3 secondi |

#### Input

```typescript
{
  approved_draft: Draft;
  target_platforms: Platform[];
  brand_config: BrandConfig;
  scheduling_hints: {
    optimal_times: HeatmapSlot[]; // Dalla heatmap
  }
}
```

#### Output

```typescript
{
  adaptations: {
    [platform: string]: {
      content: string;
      hashtags: string[];
      suggested_time: string;     // ISO datetime
      media_suggestions: string[];// Suggerimenti media
      character_count: number;
      format_notes: string;
    }
  }
}
```

---

### 10. Carousel Generator

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `carousel_generator` |
| **Ruolo** | Genera slide carousel e video da contenuti strutturati |
| **Stack** | Remotion (React --> video/immagini) |
| **Modello AI** | Nessuno (rendering deterministico) |
| **Costo medio** | ~$0.05 (costo infrastruttura rendering) |
| **Durata media** | 15-30 secondi |

#### Responsabilita'

- Convertire contenuto strutturato in slide visualmente accattivanti
- Applicare brand visual config (colori, font, logo)
- Generare immagini statiche per LinkedIn/Instagram carousel
- Generare video per TikTok/Reels
- Supportare template personalizzabili

#### Input

```typescript
{
  structured_content: {
    title: string;
    slides: {
      heading: string;
      body: string;
      icon?: string;
      data_point?: string;        // Dato numerico da enfatizzare
    }[];
    cta_slide: {
      text: string;
      url?: string;
    }
  },
  visual_config: {
    primary_color: string;
    secondary_color: string;
    font_family: string;
    logo_url: string;
    template: string;             // "minimal", "bold", "data-heavy"
  },
  output_formats: ("png" | "mp4")[]
}
```

#### Output

```typescript
{
  carousel_images: string[];     // URL delle immagini generate
  video_url: string | null;      // URL del video se richiesto
  thumbnail_url: string;         // Thumbnail per preview
  dimensions: {
    width: number;
    height: number;
  },
  format_metadata: {
    slides_count: number;
    duration_seconds: number | null; // Solo per video
  }
}
```

---

## GOD System Agents

Il **GOD System** (Generate, Optimize, Deliver) e' una pipeline di revisione a 4 fasi che garantisce la massima qualita' dei contenuti prima della pubblicazione. I 4 agenti operano in sequenza, ciascuno aggiungendo un layer di analisi e miglioramento.

### Flusso GOD System

```
Draft --> [Advocate] --> [Factchecker] --> [Creative] --> [Synthesis] --> Contenuto Finale
              |                |                |              |
              v                v                v              v
         Criticita'       Verdetti          Idee           Testo
         e debolezze     fact-check        creative        finale
```

---

### 11. God Advocate

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `god_advocate` |
| **Ruolo** | Avvocato del diavolo: critica il contenuto e trova punti deboli |
| **Modello AI** | Claude Sonnet |
| **Costo medio** | ~$0.03 |
| **Durata media** | 5-8 secondi |

#### Responsabilita'

- Analizzare il draft con occhio critico e costruttivo
- Identificare affermazioni non supportate o troppo generiche
- Verificare la coerenza logica dell'argomentazione
- Valutare se il contenuto aggiunge reale valore al lettore
- Segnalare rischi reputazionali o controversie potenziali
- Suggerire punti di forza da enfatizzare

#### Output

```typescript
{
  overall_assessment: "strong" | "adequate" | "needs_work",
  criticisms: [
    {
      severity: "high" | "medium" | "low",
      type: "unsupported_claim" | "vague_statement" | "logical_gap" | "tone_issue" | "value_gap",
      location: string,           // Porzione di testo interessata
      issue: string,              // Descrizione del problema
      suggestion: string          // Suggerimento di miglioramento
    }
  ],
  strengths: string[],            // Punti di forza da mantenere
  risk_flags: string[]            // Rischi reputazionali
}
```

---

### 12. God Factchecker

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `god_factchecker` |
| **Ruolo** | Verifica fatti, dati e claim. Elimina allucinazioni |
| **Modello AI** | Claude Sonnet + Serper API (per fact-checking online) |
| **Costo medio** | ~$0.06 (include costi Serper per verifiche) |
| **Durata media** | 10-15 secondi |

#### Responsabilita'

- Estrarre tutti i claim verificabili dal draft
- Verificare dati numerici, statistiche e percentuali
- Controllare attribuzioni (chi ha detto cosa)
- Verificare date, nomi e fatti storici
- Cercare conferme online tramite Serper API
- Assegnare verdetto a ogni claim

#### Logica di Verifica

1. **Estrazione Claim:** il modello identifica ogni affermazione verificabile nel testo
2. **Categorizzazione:** classifica i claim per tipo (dato numerico, attribuzione, fatto storico, previsione)
3. **Ricerca:** per ogni claim, genera query di verifica ed esegue ricerche Serper
4. **Valutazione:** confronta il claim con i risultati della ricerca
5. **Verdetto:** assegna uno stato a ogni claim

#### Output

```typescript
{
  claims_analyzed: number,
  claims: [
    {
      claim: string,                    // Il claim originale nel testo
      type: "statistic" | "attribution" | "fact" | "prediction",
      verdict: "verified" | "unverified" | "false" | "misleading" | "outdated",
      confidence: number,               // 0-1
      sources: string[],                // URL di conferma/smentita
      correction: string | null,        // Correzione suggerita se false/misleading
      notes: string
    }
  ],
  summary: {
    verified: number,
    unverified: number,
    false: number,
    misleading: number,
    outdated: number
  },
  overall_accuracy: number             // 0-1
}
```

---

### 13. God Creative

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `god_creative` |
| **Ruolo** | Aggiunge angoli creativi, metafore e prospettive inaspettate |
| **Modello AI** | Claude Sonnet |
| **Costo medio** | ~$0.03 |
| **Durata media** | 5-8 secondi |

#### Responsabilita'

- Proporre angoli narrativi alternativi
- Suggerire metafore, analogie e storytelling
- Identificare opportunita' per hook piu' efficaci
- Suggerire elementi di "pattern interrupt" per mantenere l'attenzione
- Proporre domande retoriche che stimolano la riflessione
- Mantenere le proposte coerenti con il brand voice

#### Input

Riceve sia il draft originale che il feedback dell'Advocate.

```typescript
{
  draft: Draft;
  advocate_feedback: AdvocateFeedback;
  brand_voice: ToneOfVoice;
  creativity_level: "conservative" | "moderate" | "bold"; // Default: "moderate"
}
```

#### Output

```typescript
{
  suggestions: [
    {
      type: "hook" | "metaphor" | "angle" | "pattern_interrupt" | "closing",
      current_text: string,         // Testo attuale
      proposed_text: string,        // Proposta creativa
      rationale: string,            // Perche' funzionerebbe meglio
      impact: "high" | "medium" | "low"
    }
  ],
  alternative_angles: [
    {
      angle: string,
      summary: string,
      target_emotion: string        // "curiosity", "urgency", "inspiration"
    }
  ],
  storytelling_opportunities: string[]
}
```

---

### 14. God Synthesis

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `god_synthesis` |
| **Ruolo** | Meta-agente che integra tutti i feedback e produce il testo finale |
| **Modello AI** | Claude Opus 4.6 (qualita' massima per output finale) |
| **Costo medio** | ~$0.18 |
| **Durata media** | 15-20 secondi |

#### Responsabilita'

- Raccogliere e analizzare il feedback di Advocate, Factchecker e Creative
- Decidere quali suggerimenti accettare e quali scartare
- Integrare le correzioni fattuali
- Incorporare miglioramenti creativi che si adattano al brand
- Produrre il testo finale pronto per approvazione umana
- Documentare le scelte fatte e le motivazioni

#### Input

```typescript
{
  original_draft: Draft;
  advocate_feedback: AdvocateFeedback;
  factcheck_results: FactcheckResults;
  creative_suggestions: CreativeSuggestions;
  brand_config: BrandConfig;
  strictness: "low" | "medium" | "high";
}
```

#### Output

```typescript
{
  final_content: string;           // Testo finale
  word_count: number;
  changes_made: [
    {
      source: "advocate" | "factchecker" | "creative" | "synthesis",
      change: string,
      reason: string,
      accepted: boolean
    }
  ],
  rejected_suggestions: [
    {
      source: string,
      suggestion: string,
      rejection_reason: string
    }
  ],
  quality_metrics: {
    accuracy_score: number,         // 0-10 (da factchecker)
    creativity_score: number,       // 0-10
    brand_alignment: number,        // 0-10
    readability: number,            // 0-100
    overall: number                 // 0-10
  },
  approval_recommendation: "auto_approve" | "human_review" | "needs_revision"
}
```

#### Logica Decisionale

| Condizione | Azione |
|---|---|
| Tutti i claim verificati + nessuna criticita' alta | `auto_approve` |
| Claim non verificati presenti ma non critici | `human_review` |
| Claim falsi o criticita' alta | `needs_revision` |
| Accuracy score < 7.0 | `needs_revision` |
| Overall quality > 8.5 e accuracy > 9.0 | `auto_approve` |

---

## Social Curation Agents

Agenti specializzati per l'adattamento fine dei contenuti a ciascuna piattaforma social. Operano dopo l'Adapter Agent per applicare le ultime ottimizzazioni platform-specific.

### Agenti Social

| ID Agente | Piattaforma | Modello | % Budget |
|---|---|---|---|
| `curation_social_linkedin` | LinkedIn | Claude Sonnet | ~2.8% |
| `curation_social_x` | X (Twitter) | Claude Sonnet | ~2.4% |
| `curation_social_instagram` | Instagram | Claude Sonnet | ~2.6% |
| `curation_social_facebook` | Facebook | Claude Sonnet | ~2.4% |

### Responsabilita' Comuni

- Ottimizzare il contenuto per l'algoritmo specifico della piattaforma
- Applicare best practice aggiornate (formato, lunghezza, timing)
- Generare varianti di copy per A/B testing se richiesto
- Ottimizzare hashtag per reach e discovery
- Suggerire formati media (immagine, video, carousel, sondaggio)

### Ottimizzazioni Platform-Specific

#### LinkedIn (`curation_social_linkedin`)

- Prima riga come hook (visibile pre-"vedi altro")
- Uso strategico di line break per leggibilita'
- Menzione di numeri e risultati concreti
- CTA che invita al commento (non al like)
- Max 3-5 hashtag, posizionati alla fine
- Evitare link esterni nel post (abbassano la reach)

#### X (`curation_social_x`)

- Primo tweet autosufficiente (deve funzionare da solo)
- Thread max 7-10 tweet per argomenti complessi
- Tono diretto e pungente
- Uso di emoji come "bullet point"
- Retweet-friendly: frasi quotabili
- Max 2 hashtag

#### Instagram (`curation_social_instagram`)

- Caption orientata allo storytelling
- Hashtag nel primo commento (non in caption)
- 15-20 hashtag misti (5 ampi, 10 di nicchia, 5 branded)
- Suggerimento per immagine/carousel/reel
- CTA "salva questo post" (metriche che pesano)

#### Facebook (`curation_social_facebook`)

- Tono conversazionale e accessibile
- Post brevi (100-250 caratteri ideali)
- Domanda finale per stimolare commenti
- Nessun hashtag o massimo 1-2
- Adatto a condivisione

---

## Newsletter Agents

Versioni specializzate del GOD System ottimizzate per il formato newsletter. Operano con prompt e logiche specifiche per contenuti long-form e multi-sezione.

### Agenti Newsletter

| ID Agente | Ruolo | Modello | Descrizione |
|---|---|---|---|
| `nl_god_synthesis` | Sintesi newsletter | Claude Opus 4.6 | Produce la versione finale della newsletter assemblando i contenuti delle sezioni |
| `nl_god_factcheck` | Factcheck newsletter | Claude Sonnet | Verifica fatti su tutto il corpo della newsletter (piu' claim da verificare rispetto a un singolo post) |
| `nl_god_creative` | Creative newsletter | Claude Sonnet | Suggerimenti creativi specifici per long-form: transizioni tra sezioni, filo narrativo, intro e outro |

### Differenze rispetto al GOD System Standard

| Aspetto | GOD Standard | GOD Newsletter |
|---|---|---|
| Lunghezza input | 200-500 parole | 1500-3000 parole |
| Claim da verificare | 3-8 | 10-25 |
| Focus creativo | Hook singolo | Filo narrativo multi-sezione |
| Struttura | Testo unico | Intro + 3 slot + Outro |
| Coerenza | Interna al post | Tra le sezioni della newsletter |

---

## Utility Agents

Agenti di supporto per task specifici.

### Content Trend Agents

| ID Agente | Ruolo | Modello |
|---|---|---|
| `content_trend_linkedin` | Analizza trend di contenuti LinkedIn nel settore | Claude Sonnet |
| `content_trend_newsletter` | Analizza trend di newsletter nel settore | Claude Sonnet |
| `content_trend_twitter` | Analizza trend di conversazioni X/Twitter | Claude Sonnet |

**Responsabilita':**
- Monitorare i contenuti con piu' engagement nel settore di riferimento
- Identificare formati emergenti (thread, carousel, sondaggi)
- Segnalare topic in crescita o in declino
- Alimentare il Feedback Loop dello scoring

### Geo SEO Agent

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `geo_seo` |
| **Ruolo** | Ottimizzazione SEO on-page per contenuti blog |
| **Modello AI** | Claude Sonnet |

**Responsabilita':**
- Analisi keyword per contenuti blog
- Ottimizzazione meta tag (title, description)
- Suggerimenti per heading structure (H1, H2, H3)
- Internal linking suggestions
- Schema markup recommendations
- Ottimizzazione specifica per il mercato italiano (keyword IT)

### Script Agent

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `script` |
| **Ruolo** | Generazione script per video (YouTube, TikTok, Reel) |
| **Modello AI** | Claude Sonnet |

**Responsabilita':**
- Scrivere script con timing preciso (intro, corpo, CTA)
- Indicazioni per B-roll e grafiche
- Hook nei primi 3 secondi per video brevi
- Adattamento durata: short (30s), medium (1-3min), long (5-15min)

### Combined Script Agent

| Proprieta' | Valore |
|---|---|
| **ID Agente** | `combined_script` |
| **Ruolo** | Script multi-formato da un singolo contenuto |
| **Modello AI** | Claude Sonnet |

**Responsabilita':**
- Genera simultaneamente script per piu' formati video
- Mantiene coerenza del messaggio tra i formati
- Ottimizza per le specifiche di ogni piattaforma video
- Output: un set coordinato di script pronti per la produzione

---

## Tabella Riepilogativa Costi

Stima basata su un mese tipico con 1 research run/giorno, ~30 contenuti generati, 4 newsletter.

| Agente | Modello | Chiamate/Mese | Costo/Chiamata | Costo Mensile | % Budget |
|---|---|---|---|---|---|
| Scoring Agent | Sonnet | ~4000 | $0.014 | $56.00 | 37.3% |
| Writer Agent | Opus | ~30 | $0.150 | $4.50 | 3.0% |
| Editor Agent | Opus | ~30 | $0.110 | $3.30 | 2.2% |
| God Synthesis | Opus | ~30 | $0.180 | $5.40 | 3.6% |
| God Advocate | Sonnet | ~30 | $0.030 | $0.90 | 0.6% |
| God Factchecker | Sonnet | ~30 | $0.060 | $1.80 | 1.2% |
| God Creative | Sonnet | ~30 | $0.030 | $0.90 | 0.6% |
| Adapter Agent | Sonnet | ~120 | $0.020 | $2.40 | 1.6% |
| Social Curation (4x) | Sonnet | ~120 | $0.022 | $2.64 | 1.8% |
| Research Orchestrator | Sonnet | ~30 | $0.120 | $3.60 | 2.4% |
| Retriever Semantic | Sonnet | ~30 | $0.080 | $2.40 | 1.6% |
| Retriever Practitioner | Sonnet | ~30 | $0.070 | $2.10 | 1.4% |
| Retriever Trend | Sonnet | ~30 | $0.060 | $1.80 | 1.2% |
| NL GOD System (3x) | Mix | ~12 | $0.250 | $3.00 | 2.0% |
| Utility Agents | Sonnet | ~60 | $0.030 | $1.80 | 1.2% |
| Serper API | - | ~800 | $0.005 | $4.00 | 2.7% |
| **Infrastruttura** | - | - | - | ~$55.00 | 36.7% |
| **TOTALE** | | | | **~$150.00** | **100%** |

---

## Gestione Modelli e Fallback

### Strategia di Selezione Modello

| Complessita' Task | Modello Primario | Fallback | Criteri |
|---|---|---|---|
| Alta (scrittura, sintesi) | Claude Opus 4.6 | Claude Sonnet (degraded) | Task che richiedono creativita', sfumature, qualita' massima |
| Media (analisi, scoring) | Claude Sonnet | Claude Haiku (degraded) | Task analitici, strutturati, ad alto volume |
| Bassa (parsing, formatting) | Nessun LLM | - | Logica deterministica, regex, template |

### Fallback Chain

```
Opus 4.6 (primario)
  --> timeout/error
    --> Retry 1x con Opus
      --> fallimento
        --> Sonnet (qualita' degradata, flag nel log)
          --> timeout/error
            --> Retry 1x con Sonnet
              --> fallimento
                --> Errore con notifica all'utente
```

### Monitoraggio Performance Modelli

- **Latenza:** ogni chiamata e' tracciata con `generation_time_ms`
- **Token usage:** input e output tokens per ogni chiamata
- **Costo:** calcolato in tempo reale e trasmesso via WebSocket
- **Qualita':** self-assessment del modello + feedback umano nel tempo
- **Rate limit:** monitoraggio proattivo con pre-emptive backoff
