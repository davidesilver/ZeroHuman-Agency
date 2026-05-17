# Plan: Fast Setup — Docker One-Click, Brand Auto-Discovery, Research Fallback

> Source PRD: [#19 — Fast Setup](https://github.com/davidesilver/ZeroHuman-Agency/issues/19)

## Architectural decisions

Durable decisions that apply across all phases:

- **Supabase**: Cloud-only (free tier). L'utente crea un progetto Supabase e fornisce URL + chiavi. Nessun Supabase locale in Docker.
- **Docker**: Un `docker-compose.full.yaml` che orchestra backend Python + frontend Next.js. Supabase resta esterno (cloud). Postiz opzionale via Docker Compose profiles.
- **CLI Wizard**: Bash script (`setup.sh`) per massima portabilità. Genera `.env.local`, applica migrazioni via `supabase db push`, avvia i servizi. Supporta modalità non-interattiva via flag.
- **Retriever pattern**: Nuovi retriever (DuckDuckGo, Tavily, RSS potenziato) estendono `BaseRetriever` e si registrano in `RETRIEVER_MAP`. L'orchestrator seleziona automaticamente i retriever disponibili in base alle API key configurate.
- **RetrieverType enum**: Esteso con nuovi valori (`DUCKDUCKGO`, `TAVILY`) via migrazione SQL che aggiunge valori all'enum `retriever_type`.
- **Brand discovery endpoint**: `POST /api/brand-discovery` sul backend Python. Accetta URL e profili social, usa trafilatura + LLM, restituisce JSON strutturato.
- **Template di settore**: File JSON statici in `data/brand-templates/`. Caricati dal frontend, non dal backend.
- **Dashboard wizard**: Nuova route `/setup` con stepper component. Non sostituisce le settings pages esistenti — le orchestra.
- **Research cascade**: L'orchestrator `research.py` cambia da "mappa statica" a "mappa dinamica" che include solo i retriever le cui dipendenze (API key) sono soddisfatte. Nessuna modifica all'interfaccia `BaseRetriever`.
- **Migrazioni**: Continuano la numerazione esistente (031+). Ogni fase aggiunge le proprie.
- **Nessuna API key in database**: Le API key restano in `.env.local` (file-based). La dashboard le mostra come configurate/non configurate (booleano) ma non le memorizza nel DB. Questo è coerente con il pattern attuale di `GET /api/system/config`.

---

## Phase 1: Docker One-Click + CLI Wizard

**User stories**: 1, 2, 3, 4, 5, 6, 17, 20, 21, 26

### What to build

Un sistema di bootstrap che porta l'utente da "ho clonato il repo" a "stack funzionante su localhost:3000" con il minimo numero di decisioni manuali.

**Docker Compose full stack** (`docker-compose.full.yaml`):
- Servizio `backend`: immagine Python (Dockerfile da creare) con FastAPI, porta 8000. Legge `.env.local` montato come volume.
- Servizio `frontend`: immagine Next.js (Dockerfile da creare) con la dashboard, porta 3000. Legge `.env.local`.
- Servizio `postiz-*`: l'intero stack Postiz (Redis, Temporal, Temporal UI, Postiz App) sotto il profile `social`, attivabile con `COMPOSE_PROFILES=social`. Riusa la config esistente da `docker-compose.postiz.yaml`.
- Nessun database nel compose — Supabase Cloud è il database.
- Network condiviso tra tutti i servizi.

**CLI Wizard** (`setup.sh`):
1. Rileva ambiente: verifica che Docker, Node.js 20+, Python 3.11+ siano disponibili. Segnala cosa manca.
2. Chiede il percorso di setup: Docker (consigliato) o manuale (npm + uv).
3. Chiede le credenziali Supabase: URL e anon key (obbligatorie), service role key (obbligatoria).
4. Chiede LLM provider: Anthropic API key OPPURE OpenRouter API key (almeno uno obbligatorio).
5. Chiede servizi opzionali (con default "skip"):
   - Research APIs: Serper key, YouTube key, Tavily key (tutti opzionali — "la ricerca funzionerà con DuckDuckGo gratuito")
   - Email: Resend API key (opzionale — "newsletter disabilitata")
   - Social: Postiz mode (disabled/self_hosted/cloud) + API key se applicabile
   - Alerts: Telegram bot token + chat ID (opzionale)
6. Genera automaticamente: `SCHEDULER_SECRET` (via `openssl rand -hex 32`), `ALLOWED_ORIGINS`.
7. Scrive `.env.local` con tutti i valori.
8. Applica migrazioni: `supabase link --project-ref <ref>` + `supabase db push`.
9. Avvia servizi: `docker compose -f docker-compose.full.yaml up -d` oppure avvio manuale.
10. Health check: chiama `GET /api/health` (frontend) e `GET /api/health` (backend). Riporta stato.
11. Stampa: "Setup completo! Apri http://localhost:3000"

**Modalità non-interattiva**: `./setup.sh --supabase-url=... --supabase-anon-key=... --anthropic-key=... --no-social --no-newsletter` per CI/CD e deployment automatizzati.

**Validazione env vars at startup**: Il backend Python valida all'avvio che le variabili obbligatorie siano presenti e stampa errori chiari. Il frontend Next.js fa lo stesso al build time per le `NEXT_PUBLIC_*`.

### Acceptance criteria

- [ ] `docker-compose.full.yaml` esiste e porta up backend + frontend con `docker compose up`
- [ ] Dockerfile per backend Python builda e avvia FastAPI correttamente
- [ ] Dockerfile per frontend Next.js builda e avvia la dashboard correttamente
- [ ] Il profilo `social` in Docker Compose avvia lo stack Postiz completo quando attivato
- [ ] `setup.sh` in modalità interattiva guida l'utente e genera un `.env.local` valido
- [ ] `setup.sh` in modalità non-interattiva (tutti i flag) genera `.env.local` senza prompt
- [ ] `setup.sh` auto-genera `SCHEDULER_SECRET` e `ALLOWED_ORIGINS`
- [ ] `setup.sh` rileva tool mancanti (Docker, Node, Python, Supabase CLI) e guida l'utente
- [ ] `setup.sh` applica tutte le migrazioni Supabase con successo
- [ ] `setup.sh` esegue health check finale e riporta stato di tutti i servizi
- [ ] Il backend Python stampa errori chiari all'avvio se mancano variabili obbligatorie (Supabase URL/key, almeno un LLM key)
- [ ] Il frontend Next.js fallisce al build con messaggio chiaro se mancano `NEXT_PUBLIC_SUPABASE_URL` o `NEXT_PUBLIC_SUPABASE_ANON_KEY`

---

## Phase 2: Research Fallback Gratuiti

**User stories**: 12, 13, 14, 15, 25

### What to build

Un sistema di cascata a 3 livelli per la ricerca contenuti che permette alla pipeline di funzionare senza nessuna API key a pagamento.

**DuckDuckGo Retriever** (nuovo):
- Nuova classe che estende `BaseRetriever` con `retriever_type = RetrieverType.DUCKDUCKGO`.
- Usa la libreria Python `duckduckgo-search` (zero API key, zero costi).
- Accetta gli stessi parametri di config dei retriever Serper (topics, principles, max_items, language).
- Costruisce query di ricerca dai topic del brand (stessa logica di `SemanticRetriever._build_queries()`).
- Rispetta rate limiting interno (max ~20 req/min per evitare blocchi temporanei da DDG).
- Restituisce `ResearchItemCreate` nello stesso formato degli altri retriever.

**Tavily Retriever** (nuovo):
- Nuova classe con `retriever_type = RetrieverType.TAVILY`.
- Usa l'API Tavily Search (1000 ricerche/mese gratis, qualità superiore a DDG).
- Nuova env var: `TAVILY_API_KEY` in `Settings`.
- Attivato solo se `tavily_api_key` è configurata.

**RSS Retriever potenziato**:
- L'`RSSRetriever` esistente diventa un retriever "always-on" — funziona senza API key perché i feed RSS sono gratuiti.
- Esteso per supportare auto-discovery di feed RSS da URL di siti web (cerca `<link rel="alternate" type="application/rss+xml">` nelle pagine).

**Cascata dinamica nell'orchestrator**:
- `RETRIEVER_MAP` nell'orchestrator cambia da mappa statica a costruzione dinamica basata sulle API key disponibili.
- Logica: per il tipo `SEMANTIC`, se `serper_api_key` è presente usa `SemanticRetriever`; se `tavily_api_key` è presente usa `TavilyRetriever`; altrimenti usa `DuckDuckGoRetriever`.
- Stessa logica per `KEYWORD` e `PRACTITIONER` (DDG come fallback universale).
- `TRUSTED_SOURCE` (RSS) è sempre attivo.
- `TREND` (YouTube) è attivo solo se `youtube_api_key` è presente (nessun fallback gratuito per video trends).

**Migrazione SQL**: Aggiunge `duckduckgo` e `tavily` all'enum `retriever_type`.

**UI nella settings page**: La pagina System Config (`/settings`) mostra il livello di ricerca attivo ("Gratuito: DuckDuckGo + RSS", "Intermedio: Tavily", "Premium: Serper + YouTube") con indicazione di cosa migliorerebbe configurando API key aggiuntive.

### Acceptance criteria

- [ ] `DuckDuckGoRetriever` implementato e registrato nell'orchestrator
- [ ] La pipeline di ricerca completa (trigger → retrieve → dedup → save) funziona con zero API key a pagamento
- [ ] `TavilyRetriever` implementato e si attiva automaticamente quando `TAVILY_API_KEY` è presente
- [ ] L'orchestrator sceglie automaticamente il retriever migliore disponibile per ogni tipo
- [ ] RSS Retriever è "always-on" e funziona come fonte gratuita di base
- [ ] La pagina System Config mostra il livello di ricerca attivo (Free/Tavily/Premium)
- [ ] Migrazione SQL aggiunge i nuovi enum values senza rompere dati esistenti
- [ ] `duckduckgo-search` e `tavily-python` (opzionale) aggiunti alle dipendenze Python
- [ ] Rate limiting interno per DDG previene blocchi temporanei
- [ ] I risultati DDG/Tavily passano la stessa deduplicazione (URL + semantica) dei risultati Serper

---

## Phase 3: Brand Auto-Discovery + Template di Settore

**User stories**: 8, 9, 10, 11, 23, 24, 27

### What to build

Un sistema che permette all'utente di popolare il brand context (tone rules, principi, gold examples) in 5 minuti invece di 60, partendo da URL esistenti o template di settore.

**Endpoint brand-discovery** (Python backend):
- `POST /api/brand-discovery` con body `{ urls: string[], social_profiles: string[] }`.
- Pipeline:
  1. Scrapa ogni URL con trafilatura (già presente come dipendenza). Limite: max 5 pagine per URL (home + about + 3 blog post recenti se disponibili). Per i social profiles: scrapa la pagina pubblica del profilo.
  2. Concatena tutto il testo estratto (troncato a ~8000 token per rimanere nei limiti LLM).
  3. Invia al LLM configurato (Anthropic o OpenRouter) con un prompt strutturato che chiede di estrarre:
     - 3-5 tone rules con spiegazione
     - 3-5 principi del brand
     - 3-5 gold examples (citazioni reali dal contenuto scrappato)
     - 3-5 discard examples (anti-pattern opposti al brand voice rilevato)
     - Topics suggeriti per la ricerca
     - Confidence score (0-1) per ogni elemento estratto
  4. Restituisce JSON strutturato.
- Gestione errori: se un URL non è raggiungibile, lo segnala ma continua con gli altri. Se nessun URL è raggiungibile, restituisce errore.
- Costo stimato per discovery: ~$0.02-0.05 (una chiamata LLM).

**Frontend: pagina "Brand Discovery"**:
- Accessibile dalla pagina brand-context (`/settings/brand-context`) come azione primaria quando il brand non ha memory facts.
- Step 1: input per URL del sito web + URL profili social (multi-input, uno per campo). Pulsante "Analizza".
- Step 2: loading state con progress ("Scraping sito...", "Analizzando tone...", "Generando brand context...").
- Step 3: "Review & Confirm" — mostra ogni elemento estratto in cards editabili raggruppate per tipo (tone rules, principi, gold examples, discard examples). Ogni card ha: testo (editabile inline), confidence badge, checkbox per includere/escludere. L'utente può aggiungere altri elementi manualmente.
- Step 4: "Salva" — salva tutti gli elementi selezionati a `memory_semantic` via le API esistenti (`POST /api/memory`).

**Template di settore**:
- File JSON statici in `data/brand-templates/`: `tech-saas.json`, `food-restaurant.json`, `fashion.json`, `fitness.json`, `finance.json`, `agency-marketing.json`, `generic.json`.
- Ogni template contiene: `{ name, description, tone_rules[], principles[], example_topics[], suggested_scoring_weights }`.
- UI: griglia di card con nome + descrizione + preview dei tone rules. Click su un template → pre-popola lo step "Review & Confirm" con i dati del template (identico flusso dell'auto-discovery, ma senza scraping).
- I template sono combinabili con l'auto-discovery: l'utente può partire da un template e poi raffinare con discovery.

**Import batch di gold examples**:
- Nella pagina brand-context, un pulsante "Importa esempi in batch" che apre un textarea dove l'utente incolla 5-10 post separati da linee vuote.
- Ogni post viene salvato come `gold_example` in `memory_semantic` con tier `core`.

**Re-discovery**:
- L'azione di brand discovery è disponibile in qualsiasi momento, non solo al primo setup.
- Se ci sono già memory facts, l'auto-discovery mostra i nuovi accanto agli esistenti, evidenziando sovrapposizioni.
- Nuovo campo nella tabella `brands`: `discovery_urls` (text[]) per ricordare gli URL usati.

### Acceptance criteria

- [ ] `POST /api/brand-discovery` accetta URL e profili social e restituisce brand context strutturato
- [ ] Scraping con trafilatura funziona per siti web standard (homepage, about, blog)
- [ ] Il prompt LLM estrae tone rules, principi, gold/discard examples con confidence score
- [ ] La UI "Review & Confirm" mostra elementi estratti in cards editabili e raggruppate per tipo
- [ ] L'utente può includere/escludere/editare ogni elemento prima del salvataggio
- [ ] Il salvataggio scrive correttamente in `memory_semantic` via API esistente
- [ ] Almeno 5 template di settore JSON sono disponibili e selezionabili
- [ ] I template pre-popolano la stessa UI di review dell'auto-discovery
- [ ] L'import batch di gold examples funziona (textarea → bulk save)
- [ ] La re-discovery funziona su brand con memory facts esistenti senza sovrascriverli
- [ ] `discovery_urls` salvato nella tabella `brands` (migrazione SQL)
- [ ] Gestione errori: URL irraggiungibili segnalati ma non bloccanti

---

## Phase 4: Dashboard Setup Wizard + Settings UX

**User stories**: 7, 16, 18, 19, 22

### What to build

Un flusso guidato nella dashboard che orchestra le funzionalità costruite nelle fasi 1-3, rendendo il primo setup accessibile a utenti semi-tecnici senza terminale.

**Setup Wizard page** (`/setup`):
- Route dedicata, accessibile sia dal menu laterale sia auto-redirect al primo login quando l'utente non ha brand.
- Stepper component (basato su shadcn/ui) con 6 step:
  1. **Benvenuto**: spiegazione di cosa è ZeroHuman, cosa verrà configurato, tempo stimato (~5 min).
  2. **LLM Provider**: form per verificare che almeno un LLM sia configurato. Mostra stato attuale da `/api/system/config`. Se nessun LLM è configurato, guida l'utente (link a dove ottenere la chiave, input per inserirla nel `.env.local` — non nel DB).
  3. **Crea Brand**: il form esistente di creazione brand (nome, slug, topics, budget) embedded nello stepper.
  4. **Brand Voice**: tre percorsi presentati come tabs:
     - "Auto-Discovery" → integra la UI di Phase 3 (URL → scraping → review)
     - "Template" → griglia di template di Phase 3
     - "Manuale" → link alla pagina brand-context esistente
  5. **Ricerca**: mostra il livello attuale (Free/Tavily/Premium da Phase 2). Se Free, spiega cosa fanno i livelli superiori con link per configurare.
  6. **Riepilogo**: checklist completa di cosa è configurato, cosa usa fallback, cosa è disabilitato. Link diretti alle settings pages per ogni voce.
- Ogni step è opzionale dopo il 2 e 3 — l'utente può saltare e completare dopo.
- Lo stato di completamento è persistito (nuova tabella `setup_progress` o campo JSON nella tabella `brands`).

**Getting Started checklist**:
- Nella dashboard principale (home), un banner/card "Getting Started" che mostra lo stato di completamento.
- Checklist items: LLM configurato, Brand creato, Brand voice configurato, Prima ricerca completata, Primo draft generato.
- Il banner si nasconde quando tutti gli items sono completati (o l'utente lo dismisses).
- Basato su query reali: count dei memory facts, count dei research items, count dei drafts.

**Settings UX migliorata**:
- La pagina System Config (`/settings`) mostra in modo più chiaro lo stato di ogni integrazione con icone colorate (verde = attivo, giallo = fallback gratuito, grigio = non configurato).
- Ogni sezione ha un link "Come configurare" che apre un collapsible con istruzioni step-by-step.
- I livelli di ricerca (Phase 2) sono visualizzati prominentemente.

### Acceptance criteria

- [ ] La route `/setup` esiste e mostra lo stepper a 6 step
- [ ] Auto-redirect a `/setup` al primo login se l'utente non ha brand
- [ ] Lo step "LLM Provider" verifica e mostra lo stato attuale degli LLM configurati
- [ ] Lo step "Crea Brand" usa il form esistente e crea il brand correttamente
- [ ] Lo step "Brand Voice" integra auto-discovery e template dalla Phase 3
- [ ] Lo step "Ricerca" mostra il livello di ricerca attivo dalla Phase 2
- [ ] Lo step "Riepilogo" mostra una checklist accurata dello stato di configurazione
- [ ] L'utente può saltare step opzionali e tornare dopo
- [ ] Il banner "Getting Started" appare nella dashboard home per utenti nuovi
- [ ] Il banner mostra stato di completamento basato su dati reali (memory facts, research items, drafts)
- [ ] Il banner è dismissibile e non riappare dopo il dismiss
- [ ] La pagina System Config mostra icone di stato colorate per ogni integrazione
- [ ] Lo stato di completamento del setup è persistito tra sessioni
