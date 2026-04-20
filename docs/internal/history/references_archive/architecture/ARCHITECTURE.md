# Empty Box - Architettura del Content Engine

> Documentazione architetturale completa del sistema "Empty Box" -- un motore AI per l'automazione di contenuti multi-brand.

---

## Indice

1. [Visione del Progetto](#visione-del-progetto)
2. [Modello Operativo 95/5](#modello-operativo-955)
3. [Architettura Generale](#architettura-generale)
4. [Flusso Dati End-to-End](#flusso-dati-end-to-end)
5. [Componenti del Sistema (Dashboard)](#componenti-del-sistema-dashboard)
6. [Struttura Directory (Target)](#struttura-directory-target)
7. [Principi Architetturali](#principi-architetturali)

---

## Visione del Progetto

### Obiettivo

Costruire un sistema AI **95% automatizzato / 5% umano** per l'automazione completa della produzione e distribuzione di contenuti multi-brand. Il sistema deve essere in grado di ricercare fonti, generare contenuti di alta qualita, adattarli a ogni piattaforma, pubblicarli e apprendere dai risultati -- tutto con intervento umano minimo.

### Il Concetto "Empty Box"

**Empty Box** (Scatola Vuota) e il nome in codice del progetto. L'idea centrale e che il motore di contenuti e una **scatola vuota riutilizzabile**: cambiando solo la configurazione (`brand.config.ts`), lo stesso sistema puo produrre contenuti per brand completamente diversi.

- **Stessa architettura**, diversi brand
- **Stesso motore**, diversa voce
- **Stesso pipeline**, diversi canali
- **Stessa AI**, diversi principi editoriali

Un brand di tecnologia, uno di finanza personale, uno di lifestyle: tutti gestiti dallo stesso Content Engine, ognuno con la propria personalita, il proprio tono di voce e i propri criteri di selezione delle fonti.

### Ispirazione

Il progetto si ispira al sistema **"Spiegamelo"** di Marco Montemagno: un approccio sistematico alla produzione di contenuti dove l'automazione gestisce il lavoro ripetitivo e l'umano si concentra sulla direzione strategica e sulla qualita finale. Empty Box porta questo concetto al livello successivo, sostituendo i processi manuali con agenti AI orchestrati.

---

## Modello Operativo 95/5

Il cuore filosofico di Empty Box e la divisione netta tra cio che fa l'AI e cio che fa l'umano.

### L'AI gestisce (95%)

| Area | Attivita |
|------|----------|
| **Ricerca fonti** | Scanning di 1000+ fonti internazionali ogni giorno, aggregazione RSS, ricerca web, discovery video |
| **Scoring** | Valutazione automatica di ogni fonte su 6 parametri, classificazione per rilevanza |
| **Generazione contenuti** | Scrittura di post, articoli, newsletter in stile e tono del brand |
| **Editing** | Revisione multi-agente (advocate, factcheck, creative, synthesis) |
| **Adattamento piattaforma** | Trasformazione del contenuto per LinkedIn, Instagram, X, TikTok, Facebook, Blog |
| **Scheduling** | Pianificazione e pubblicazione automatica su tutti i canali |
| **Analytics** | Raccolta metriche, analisi performance, identificazione pattern |
| **Feedback loop** | Apprendimento continuo dai risultati per migliorare scoring e generazione |

### L'umano gestisce (5%)

| Area | Attivita |
|------|----------|
| **Visione strategica** | Definire la direzione editoriale, i temi prioritari, il posizionamento |
| **Approvazione finale** | Validare i contenuti prima della pubblicazione (soprattutto high-stakes) |
| **Feedback qualitativo** | Indicare cosa funziona, cosa no, cosa manca -- per addestrare il sistema |
| **Etica e sensibilita** | Decisioni su temi delicati, controversi o che richiedono giudizio umano |

### Ruolo dell'Umano: lo "Stimolatore"

L'umano non e l'esecutore. Non scrive, non formatta, non pubblica. L'umano e lo **stimolatore**: da la direzione, pone le domande giuste, approva o corregge il tiro. E il direttore d'orchestra, non il violinista.

Questo modello libera tempo creativo: invece di passare ore a produrre, l'umano puo concentrarsi su pensiero strategico, networking, e creazione di contenuti ad alto impatto che richiedono genuina esperienza umana.

---

## Architettura Generale

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EMPTY BOX CONTENT ENGINE                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  [CONFIG LAYER]                                                        │
│  brand.config.ts → parametri brand, tono di voce, principi founder,   │
│                    canali attivi, frequenza, target audience            │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  [RESEARCH LAYER]                                                      │
│  Serper + Firecrawl + RSS Feed Parser + YouTube Data API               │
│  → 1000+ fonti internazionali scansionate quotidianamente              │
│  → 5 tipi di retriever: web search, deep scraping, RSS, video, social  │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  [SCORING LAYER]                                                       │
│  LLM Scoring Engine (6 parametri):                                     │
│  ┌──────────────┐ ┌─────────────┐ ┌───────────┐                       │
│  │ Applicability│ │ Credibility │ │ Alignment │                       │
│  └──────────────┘ └─────────────┘ └───────────┘                       │
│  ┌──────────────┐ ┌─────────────┐ ┌───────────┐                       │
│  │    Trend     │ │Feedback Loop│ │  Novelty  │                       │
│  └──────────────┘ └─────────────┘ └───────────┘                       │
│  → Output: score HIGH / MEDIUM / LOW per ogni fonte                    │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  [APPROVAL LAYER]                                                      │
│  Dashboard Next.js → l'umano vede le fonti scored,                     │
│  approva/rifiuta/modifica priorita                                     │
│  HIGH  → approvazione automatica (con possibilita di override)         │
│  MEDIUM → review umano consigliato                                     │
│  LOW   → scartato (con possibilita di recupero)                        │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  [GENERATION LAYER]                                                    │
│  Pipeline di scrittura a 3 stadi:                                      │
│                                                                        │
│  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────┐   │
│  │  WRITER          │───▶│  EDITOR          │───▶│  ADAPTER       │   │
│  │  (Claude Opus)   │    │  (Claude Opus)   │    │  (Claude       │   │
│  │  Genera il       │    │  Revisiona,      │    │   Sonnet)      │   │
│  │  contenuto base  │    │  migliora,       │    │  Adatta per    │   │
│  │                  │    │  affina           │    │  piattaforma   │   │
│  └──────────────────┘    └──────────────────┘    └────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  [GOD SYSTEM] - Pipeline di revisione multi-agente sequenziale         │
│                                                                        │
│  ┌───────────┐    ┌───────────┐    ┌──────────┐    ┌───────────┐      │
│  │ ADVOCATE  │───▶│ FACTCHECK │───▶│ CREATIVE │───▶│ SYNTHESIS │      │
│  │ Difende   │    │ Verifica  │    │ Migliora │    │ Integra   │      │
│  │ il        │    │ fatti e   │    │ impatto  │    │ tutti i   │      │
│  │ lettore   │    │ fonti     │    │ emotivo  │    │ feedback  │      │
│  └───────────┘    └───────────┘    └──────────┘    └───────────┘      │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  [DISTRIBUTION LAYER]                                                  │
│  ┌──────────┐ ┌───────────┐ ┌────────┐ ┌───┐ ┌────────┐             │
│  │ LinkedIn │ │ Instagram │ │Facebook│ │ X │ │ TikTok │             │
│  └──────────┘ └───────────┘ └────────┘ └───┘ └────────┘             │
│  ┌──────────────────┐ ┌──────────────────────┐                        │
│  │ Newsletter       │ │ Blog (SEO optimized) │                        │
│  │ (Resend/Beehiiv) │ │                      │                        │
│  └──────────────────┘ └──────────────────────┘                        │
│  Orchestrato da: Postiz (open-source scheduler)                        │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  [ANALYTICS LAYER]                                                     │
│  Social metrics (engagement, reach, clicks) + A/B votes                │
│  → Feedback loop verso Scoring Layer                                   │
│  → Addestramento continuo dell'algoritmo di scoring                    │
│  → AutoResearch notturno per temi emergenti                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Flusso Dati End-to-End

Il sistema opera in **7 fasi** che si ripetono quotidianamente in un ciclo continuo.

### Fase 1: RESEARCH (Cron giornaliero alle 07:00)

**Obiettivo:** Raccogliere materia prima da 1000+ fonti internazionali.

Il sistema attiva 5 tipi di retriever in parallelo:

| Retriever | Tecnologia | Cosa fa |
|-----------|-----------|---------|
| **Web Search** | Serper API | Cerca notizie fresche su keyword predefinite nel `brand.config` |
| **Deep Scraping** | Firecrawl | Scraping profondo di siti specifici (blog di riferimento, competitor, thought leader) |
| **RSS Aggregation** | Feed Parser | Monitora 1000+ feed RSS categorizzati per tema |
| **Video Discovery** | YouTube Data API | Identifica video rilevanti da canali monitorati |
| **Social Listening** | API social | Monitora trend e conversazioni su piattaforme social |

**Output:** Un pool di centinaia di fonti grezze, salvate su Supabase con metadata (titolo, URL, snippet, data, tipo di fonte).

### Fase 2: SCORING AI

**Obiettivo:** Valutare ogni fonte e assegnare un punteggio di rilevanza per il brand.

Ogni fonte viene analizzata da un LLM su **6 parametri**:

| Parametro | Peso | Cosa misura |
|-----------|------|-------------|
| **Applicability** | 25% | Quanto il tema e rilevante per l'audience del brand |
| **Credibility** | 20% | Affidabilita della fonte (dominio, autore, citazioni) |
| **Alignment** | 20% | Quanto il tema si allinea con i principi e valori del founder |
| **Trend** | 15% | Quanto il tema e attuale e in crescita (trending) |
| **Feedback Loop** | 10% | Performance storica di temi simili (dati da analytics passati) |
| **Novelty** | 10% | Quanto il tema e nuovo rispetto a contenuti gia prodotti |

**Output:** Ogni fonte riceve un punteggio aggregato e viene classificata come **HIGH**, **MEDIUM** o **LOW**.

### Fase 3: APPROVAZIONE (Human in the Loop)

**Obiettivo:** L'umano valida le scelte dell'AI prima della generazione contenuti.

Il routing funziona cosi:

- **HIGH score (>80%):** Approvazione automatica. Il contenuto viene generato senza intervento umano. L'umano puo comunque fare override dalla dashboard.
- **MEDIUM score (50-80%):** Review umano consigliato. La dashboard evidenzia questi elementi per una decisione rapida (pollice su / pollice giu).
- **LOW score (<50%):** Scartato automaticamente. Rimane nel database per eventuale recupero manuale.

La dashboard mostra le fonti in una vista Kanban con card che riportano titolo, score, parametri di scoring e un preview del potenziale contenuto.

### Fase 4: CONTENT HUB (Generazione Multi-formato)

**Obiettivo:** Trasformare ogni fonte approvata in contenuti per tutti i canali attivi.

Da una singola fonte, il sistema genera fino a **7 formati diversi**:

| Formato | Piattaforma | Caratteristiche |
|---------|-------------|-----------------|
| **Post lungo** | LinkedIn | 1200-1500 caratteri, storytelling, hook forte |
| **Carousel** | Instagram | 7-10 slide, visual-first, CTA finale |
| **Post visuale** | Facebook | Testo + immagine, ottimizzato per engagement |
| **Thread/Post** | X (Twitter) | Conciso, provocatorio, con link |
| **Short script** | TikTok | Script per video breve, gancio nei primi 3 secondi |
| **Articolo SEO** | Blog | 1500-3000 parole, strutturato per SEO, internal linking |
| **Sezione newsletter** | Email | Blocco editoriale per la newsletter settimanale |

Il pipeline di generazione e a **3 stadi**: Writer (Claude Opus) genera il draft, Editor (Claude Opus) lo raffina, Adapter (Claude Sonnet) lo adatta al formato specifico della piattaforma.

### Fase 5: GOD MODE (Revisione Multi-agente)

**Obiettivo:** Sottoporre ogni contenuto generato a una revisione approfondita da parte di 4 agenti specializzati.

Il GOD System (Generative Orchestrated Debate) e un pipeline **sequenziale** dove 4 agenti AI con ruoli diversi revisionano il contenuto uno dopo l'altro:

| Agente | Ruolo | Cosa controlla |
|--------|-------|----------------|
| **Advocate** | Difensore del lettore | Il contenuto e utile? Chiaro? Rispetta il tempo del lettore? |
| **Factcheck** | Verificatore di fatti | I dati sono corretti? Le fonti sono citate? Ci sono affermazioni non verificabili? |
| **Creative** | Direttore creativo | L'hook e forte? Il tono e giusto? L'impatto emotivo c'e? |
| **Synthesis** | Integratore finale | Raccoglie tutti i feedback e produce la versione finale del contenuto |

Ogni agente puo **approvare**, **suggerire modifiche** o **bloccare** il contenuto. Solo dopo il passaggio di tutti e 4 gli agenti il contenuto e pronto per la pubblicazione.

### Fase 6: SCHEDULING & PUBLISH

**Obiettivo:** Pubblicare i contenuti approvati nei tempi e modi ottimali.

- **Volume target:** ~30 post/giorno distribuiti su tutti i canali
- **Newsletter settimanale:** Compilata automaticamente dai migliori contenuti della settimana
- **Blog:** 3-5 articoli SEO/settimana
- **Timing ottimale:** L'orario di pubblicazione viene determinato dai dati analytics di ogni piattaforma
- **Orchestratore:** Postiz (open-source) gestisce lo scheduling multi-piattaforma
- **Email:** Resend per l'MVP, migrazione a Beehiiv per scala

### Fase 7: FEEDBACK LOOP

**Obiettivo:** Chiudere il cerchio. Ogni contenuto pubblicato genera dati che migliorano il sistema.

Il feedback loop opera su 3 livelli:

| Livello | Cosa raccoglie | Come lo usa |
|---------|----------------|-------------|
| **Analytics social** | Engagement, reach, click, salvataggi, condivisioni | Aggiorna i pesi dello Scoring Layer (Fase 2) per temi simili |
| **A/B votes** | L'umano vota "meglio A" o "meglio B" su varianti di contenuto | Addestra lo stile di scrittura del Writer |
| **AutoResearch notturno** | Cron notturno che cerca approfondimenti sui temi che hanno performato meglio | Alimenta il Research Layer con ricerche mirate per il giorno successivo |

Il ciclo si chiude: i dati di oggi migliorano i contenuti di domani.

---

## Componenti del Sistema (Dashboard)

La dashboard e costruita in Next.js 15 e organizzata in **11 moduli** raggruppati in 4 aree funzionali.

### HOME

| Modulo | Funzione |
|--------|----------|
| **Content Hub** | Vista centrale di tutti i contenuti in pipeline: da approvare, in lavorazione, pubblicati. Kanban board con filtri per stato, piattaforma, score. |

### PRODUZIONE

| Modulo | Funzione |
|--------|----------|
| **Ricerca** | Gestione fonti: lista fonti scored, approvazione/rifiuto, ricerca manuale, filtri per retriever e parametro di scoring. |
| **Calendario** | Calendario editoriale visuale. Vista settimanale/mensile con drag & drop. Mostra contenuti schedulati per ogni piattaforma. |
| **Newsletter** | Composizione newsletter: selezione contenuti della settimana, preview, invio test, scheduling. |
| **Blog** | Gestione articoli blog: editor, SEO checker, preview, pubblicazione. |

### QUALITA

| Modulo | Funzione |
|--------|----------|
| **Writing Lab** | A/B testing di contenuti. L'umano confronta varianti e vota la migliore. I risultati alimentano il feedback loop. |
| **Metriche** | Dashboard analytics: performance per piattaforma, per tipo di contenuto, per tema. Trend nel tempo, confronti periodo su periodo. |
| **Newsletter Analytics** | Metriche specifiche newsletter: open rate, click rate, unsubscribe, crescita lista, performance singoli blocchi. |

### SISTEMA

| Modulo | Funzione |
|--------|----------|
| **Pipeline Health** | Monitoraggio stato di salute del sistema: cron attivi, errori, latenza, code di lavoro. Vista real-time dello stato di ogni layer. |
| **Revenue** | Tracking ricavi (se il brand monetizza): abbonamenti, sponsorship, affiliazioni. |
| **Costi API** | Monitoraggio spesa per API: OpenRouter, Serper, Firecrawl, ElevenLabs. Budget mensile, alert su soglie, previsione costi. |
| **Research V2** | Modulo avanzato di ricerca: configurazione retriever, gestione feed RSS, blacklist/whitelist domini, test query. |

---

## Struttura Directory (Target)

```
/content-engine/
│
├── /src                          # Next.js 15 frontend
│   ├── /app                      # App Router (pagine e layout)
│   │   ├── /dashboard            # Dashboard modules
│   │   ├── /api                  # API Routes
│   │   └── /auth                 # Autenticazione
│   ├── /components               # Componenti React (shadcn/ui)
│   ├── /lib                      # Utilities, hooks, tipi
│   └── /styles                   # Tailwind CSS
│
├── /python                       # Backend agents
│   ├── /agents                   # Agenti AI (writer, editor, adapter, god system)
│   ├── /retrievers               # Retriever per ogni tipo di fonte
│   ├── /scoring                  # Engine di scoring
│   ├── /distribution             # Connettori per pubblicazione
│   └── /analytics                # Raccolta e analisi metriche
│
├── /supabase                     # Database
│   ├── /migrations               # Schema migrations
│   ├── /functions                # Edge Functions
│   └── /seed                     # Dati di seed per sviluppo
│
├── /n8n                          # Orchestrazione
│   ├── /workflows                # Workflow JSON esportati
│   └── /credentials              # Template credenziali (no secrets)
│
├── /config                       # Configurazione brand
│   ├── brand.config.ts           # Configurazione principale del brand
│   ├── prompts/                  # System prompt per ogni agente
│   └── templates/                # Template per ogni formato di contenuto
│
├── /docs                         # Documentazione
│   ├── /architecture             # Questo file e documenti architetturali
│   ├── /guides                   # Guide operative
│   └── /api                      # Documentazione API
│
└── /scripts                      # Automazione
    ├── setup.sh                  # Setup iniziale ambiente
    ├── deploy.sh                 # Deploy su VPS
    └── backup.sh                 # Backup database
```

---

## Principi Architetturali

### 1. Modularita

Ogni componente del sistema e **indipendente e sostituibile**. Il Research Layer non sa nulla del Generation Layer. Lo Scoring Layer non dipende dalla Dashboard. Questo permette di:

- Sostituire un componente senza toccare gli altri (es. cambiare Serper con un altro search engine)
- Testare ogni componente in isolamento
- Scalare componenti singoli in base al carico

### 2. Configuration-driven

**Tutto e parametrizzabile via `brand.config.ts`.** Non ci sono valori hardcoded nel codice che dipendono dal brand specifico. Un nuovo brand richiede solo un nuovo file di configurazione, non modifiche al codice. Questo include:

- Tono di voce e stile di scrittura
- Canali attivi e frequenza di pubblicazione
- Fonti da monitorare e keyword di ricerca
- Pesi dei parametri di scoring
- Template per ogni formato di contenuto
- System prompt per ogni agente AI

### 3. API-first

Il backend Python espone **API RESTful** consumate dal frontend Next.js. Non c'e accoppiamento diretto tra frontend e backend. Questo permette di:

- Sviluppare frontend e backend indipendentemente
- Aggiungere client diversi in futuro (mobile app, CLI, integrazioni terze)
- Testare le API indipendentemente dalla UI

### 4. Progressive enhancement

**Partire semplice, iterare.** La prima versione di ogni componente e la piu semplice possibile che funziona. Si aggiunge complessita solo quando i dati mostrano che serve. Esempi:

- Scoring: si parte con 3 parametri, si aggiungono gli altri quando si hanno dati di feedback
- Canali: si parte con LinkedIn + Newsletter, si aggiungono gli altri progressivamente
- GOD System: si parte con 2 agenti (factcheck + synthesis), si aggiungono gli altri
- Analytics: si parte con metriche base, si aggiunge A/B testing quando il volume lo giustifica

### 5. Fail-safe

**Nessun contenuto si pubblica senza approvazione umana** (almeno nella fase iniziale). Anche i contenuti con score HIGH passano per un buffer di 30 minuti prima della pubblicazione, dando all'umano la possibilita di intervenire. Man mano che il sistema dimostra affidabilita, i guardrail si allentano progressivamente.

Principi di sicurezza:

- Ogni azione critica (pubblicazione, invio newsletter) ha un meccanismo di rollback
- I contenuti eliminati non vengono cancellati dal database ma segnati come "archived"
- Le credenziali API sono gestite via Supabase Vault, mai nel codice
- Ogni modifica alla configurazione viene versionata su Git

---

*Ultimo aggiornamento: Aprile 2026*
*Progetto: Empty Box Content Engine*
