# Plan: CLI/MCP Integration + Multi-Brand Credential Vault

> Source: research session — PrintingPress CLI factory, token efficiency analysis, Postiz multi-tenant gap

## Architectural decisions

- **Retriever pattern**: `BaseRetriever(ABC)` con `fetch(config) -> list[ResearchItemCreate]` — i CLI sostituiscono le chiamate `httpx` dentro `fetch()`, senza cambiare l'interfaccia pubblica
- **CLI execution**: `asyncio.create_subprocess_exec` per mantenere compatibilità con `asyncio.gather()` nella research pipeline; stdout JSON parsato inline
- **CLI binary location**: `~/.local/bin/` (o `$GOPATH/bin`) — risolto a runtime via `shutil.which()`; fallback a httpx se binario non trovato
- **SQLite cache location**: `~/.cache/content-engine/<cli-name>/` — per-machine, non per-brand (i dati pubblici come search results sono condivisibili)
- **Credential storage**: nuova tabella `brand_service_credentials` su Supabase, colonna `encrypted_credentials jsonb` criptata via `pgcrypto` con `BRAND_SECRETS_ENCRYPTION_KEY`; RLS per isolamento brand
- **CLI credential injection**: le credenziali per-brand vengono passate al CLI come variabili d'ambiente al momento dell'esecuzione (non in chiaro in argv)
- **MCP per publishing**: il MCP `antoniolg/postiz-mcp` gestisce le operazioni stateful (OAuth, publishing); il CLI Postiz gestisce le operazioni di sola lettura (analytics, cache)
- **Config promotion**: le chiavi globali in `.env` restano il default; le chiavi per-brand nel DB le sovrascrivono a runtime

---

## Phase 1: CLI Runner + X/Twitter

**User stories**: l'agente di ricerca ottiene risultati X/Twitter via CLI locale con cache SQLite, riducendo i token della research pipeline

### What to build

Un `CLIRunner` utility in `python/src/content_engine/utils/` che esegue un binario CLI in modo asincrono, cattura lo stdout JSON, gestisce errori e timeout, e logga il comando eseguito. Il retriever `retrievers/x.py` viene modificato per usare questo runner al posto di `httpx`, mantenendo l'interfaccia `BaseRetriever` invariata.

Installare il CLI `x-twitter` da PrintingPress (già nel catalogo, zero lavoro di generazione). Il CLI porta SQLite locale con full-text search — le query duplicate sugli stessi topic nelle ultime N ore non fanno round-trip di rete.

### Acceptance criteria

- [ ] `CLIRunner` esegue un binario CLI async e parsa stdout JSON; ritorna errore strutturato se il binario non è trovato (fallback a httpx)
- [ ] `retrievers/x.py` usa `CLIRunner` con il binario `x-twitter`; i risultati rispettano il tipo `list[ResearchItemCreate]`
- [ ] Una research run con topic invariati entro 1h non fa chiamate di rete a Twitter API (usa cache SQLite)
- [ ] La research pipeline (`orchestrator/research.py`) non richiede modifiche — `asyncio.gather()` funziona invariato
- [ ] Variabile d'ambiente `X_BEARER_TOKEN` viene passata al CLI via env injection, non in argv

---

## Phase 2: Firecrawl CLI per content enrichment

**User stories**: l'arricchimento degli articoli di ricerca evita re-scrape di URL già visitati usando cache SQLite locale

### What to build

Installare il CLI `firecrawl` da PrintingPress (già nel catalogo). Modificare `services/content_enrichment.py` per usare il CLI tramite `CLIRunner` invece delle chiamate `httpx` dirette. Il CLI mantiene una cache SQLite degli URL già scraped: se un URL è stato scraped nelle ultime 24h, ritorna il contenuto cached senza chiamata di rete.

### Acceptance criteria

- [ ] `services/content_enrichment.py` usa il CLI `firecrawl` via `CLIRunner`; fallback a httpx se il binario non è presente
- [ ] URL già scraped nelle ultime 24h non generano chiamate a `api.firecrawl.dev` (verificabile via `--data-source local`)
- [ ] Il contenuto estratto rispetta il formato esistente atteso dal pipeline di enrichment
- [ ] `FIRECRAWL_API_KEY` viene iniettata via env, non in argv

---

## Phase 3: CLI generati per Serper, Tavily, YouTube

**User stories**: tutti i retriever ad alto volume di token migrano a CLI con cache locale; risparmio stimato -85% token sulla research phase

### What to build

Generare tre CLI con PrintingPress:
- **Serper**: da HAR file catturato da `google.serper.dev` (singolo endpoint `POST /search`) — o da spec minimo scritto a mano (è 1 endpoint)
- **Tavily**: da spec OpenAPI community (disponibile su Postman + `tryAGI/Tavily` repo .NET)
- **YouTube**: da Google Discovery spec (`googleapis.com/discovery/v1/apis/youtube/v3/rest`) convertito in OpenAPI

Per ciascuno: adattare il retriever corrispondente (`serper.py`, `tavily.py`, `youtube.py`) per usare `CLIRunner`. Il fallback tiered esistente (Serper > Tavily > DuckDuckGo) resta invariato — se il CLI non è disponibile, si usa httpx.

### Acceptance criteria

- [ ] CLI `serper`, `tavily`, `youtube` installati e funzionanti (`<cli> --help` ritorna output valido)
- [ ] `retrievers/serper.py`, `retrievers/tavily.py`, `retrievers/youtube.py` usano i rispettivi CLI via `CLIRunner`
- [ ] Query identiche sullo stesso topic entro la finestra di cache non fanno round-trip di rete
- [ ] Il fallback tiered (Serper > Tavily > DuckDuckGo) funziona se un CLI non è installato
- [ ] Test di integrazione: una research run completa con 3 retriever attivi completa senza errori

---

## Phase 4: CLI + MCP per Postiz

**User stories**: le analytics Postiz usano cache locale (no polling ripetuto); il publishing usa MCP stateful con OAuth gestito

### What to build

**CLI Postiz (analytics/read)**: generare CLI da `/api-json` dell'istanza self-hosted Postiz (NestJS espone Swagger a questo path automaticamente). Il CLI con SQLite cache è ottimale per le analytics pull degli ultimi 7 giorni — evita query ripetute allo stesso endpoint.

**MCP Postiz (publishing)**: integrare `antoniolg/postiz-mcp` (Node.js, già pronto) come sidecar. `services/postiz_client.py` e `postiz_publisher.py` rimangono per le operazioni critiche (publish, schedule, delete); il CLI gestisce `GET /analytics/*` e `GET /integrations`.

### Acceptance criteria

- [ ] CLI Postiz generato da spec `/api-json`; `get analytics` non fa chiamate di rete se i dati sono in cache (< 1h)
- [ ] `services/postiz_analytics.py` usa CLI per pull analytics; `postiz_publisher.py` mantiene httpx diretto per publish/delete
- [ ] MCP Postiz avviabile come sidecar e raggiungibile dall'agent runtime
- [ ] `POSTIZ_API_KEY` e `POSTIZ_API_URL` iniettati via env al CLI e al MCP

---

## Phase 5: Credential Vault multi-brand

**User stories**: ogni brand ha le proprie credenziali per ogni servizio (Postiz account, chiavi API, etc.); un singolo deployment serve N brand in isolamento

### What to build

**Schema**: nuova migrazione Supabase con tabella `brand_service_credentials` — `brand_id` (FK → `brands`), `service_name` (text: `postiz`, `serper`, `resend`, etc.), `encrypted_credentials` (jsonb cifrato via `pgcrypto`). RLS: un brand può leggere solo le proprie credenziali.

**Vault service**: `services/credential_vault.py` — `get_credentials(brand_id, service_name) -> dict` che decifra e ritorna le credenziali. Usato dal `CLIRunner` per iniettare le env vars corrette per brand a runtime.

**Config promotion**: il resolver di credenziali prova nell'ordine: 1) vault per-brand dal DB, 2) env globale da `.env`. Nessun comportamento esistente si rompe se il vault è vuoto.

**API + UI**: endpoint CRUD `/api/brands/{id}/credentials/{service}` (JWT + RLS). Pagina nel dashboard per gestire le credenziali per brand (form per ogni servizio supportato, mascheramento valori sensibili).

### Acceptance criteria

- [ ] Migrazione Supabase applicata: tabella `brand_service_credentials` con RLS attiva
- [ ] `get_credentials(brand_id, service)` ritorna credenziali decifrate; ritorna `None` se non presenti (fallback a env globale)
- [ ] `CLIRunner` inietta le credenziali del brand corrente nelle env vars al momento dell'esecuzione subprocess
- [ ] Due brand con `POSTIZ_API_KEY` diversi eseguono research/publish senza interferire
- [ ] API CRUD `/api/brands/{id}/credentials/{service}` funzionante con auth JWT + RLS
- [ ] UI dashboard: form per inserire/aggiornare credenziali per brand, valori mascherati dopo salvataggio
- [ ] Nessun brand può leggere le credenziali di un altro brand (test RLS esplicito)
