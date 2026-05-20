# PRD — LLM Provider Hub (Strategy C: Hybrid BYOK + Gateway)

> Status: Draft 2026-05-18
> Owner: Davide Silvestri
> Supersedes: `docs/plans/issues/05-llm-provider-abstraction.md` (Phase 4), `docs/plans/issues/15-openclaw-poc.md` (Phase 14)
> Architecture: `docs/plans/2026-05-18-llm-provider-hub-architecture.md`
> Compliance: `docs/plans/2026-05-18-llm-provider-hub-compliance.md`

---

## 1. Problema

Oggi le API key LLM sono env var globali impostate dall'admin. L'utente finale non puo':

1. **Portare le proprie chiavi** (BYOK) — bloccato su qualunque provider l'admin abbia configurato
2. **Scegliere provider o modello** per il proprio brand
3. **Usare gateway locali** (Ollama, OpenClaw, LM Studio) per costo zero e privacy totale
4. **Usare provider in abbonamento** che espongono API key (Kimi Code subscription, OpenClaw plans, OpenRouter prepaid)
5. **Confrontare costi e latenza** tra provider in modo actionable

Il wizard di setup (Step 1 "LLM") e' read-only: mostra solo se le env var sono presenti e dice "edit .env.local". Zero self-service.

## 2. Per chi

| Stakeholder | Bisogno |
|-------------|---------|
| Utente self-hosted | Configurare provider LLM dalla UI senza toccare env var |
| Utente con abbonamento | Riusare la propria key Kimi Code / OpenClaw / OpenRouter prepaid |
| Utente privacy-first | Puntare a Ollama/LM Studio locale, zero dati a terzi |
| Power user | Scegliere modello specifico per capability (creative → Opus, editing → Haiku) |
| Admin/owner | Mantenere un fallback globale e controllare il budget |

## 3. Obiettivo

Dare all'utente un'esperienza simile a `openclaw configure` (45+ provider, auth method multipli, gateway locali) ma integrata nella UI web di ZeroHuman, con tre categorie:

- **Direct BYOK** — l'utente incolla la propria API key per un provider specifico
- **Gateway** — l'utente connette un gateway locale (OpenClaw, Ollama, LM Studio, LiteLLM, vLLM) che gestisce auth/subscription/routing
- **Meta-router** — l'utente connette OpenRouter per accedere a 200+ modelli con una sola key

## 4. Strategia: Hybrid C

```
Direct BYOK (top provider)       l'utente porta la sua API key
         +
Gateway (OpenClaw, Ollama, ...)   il gateway gestisce auth/subscription
         +
Meta-router (OpenRouter)          accesso a 200+ modelli con 1 key
         +
System fallback (env var)         l'admin garantisce un fallback globale
```

### Perche' non A o B

- **A (solo OpenClaw gateway)**: dipendenza esterna, non tutti lo installano
- **B (replicare 45 provider nativamente)**: lavoro enorme, maintenance impossibile
- **C (ibrido)**: BYOK diretto per i top 10, gateway per chi vuole 45+, OpenRouter come catch-all

## 5. Provider Catalog

### 5.1 Direct BYOK (built-in, OpenAI-compatible + Anthropic)

| Provider | API type | Auth | Billing model | Priority |
|----------|----------|------|---------------|----------|
| Anthropic | anthropic SDK | api_key | pay-per-use | P0 |
| OpenAI | openai-compatible | api_key | pay-per-use | P0 |
| Google AI (Gemini) | openai-compatible | api_key | pay-per-use | P0 |
| Groq | openai-compatible | api_key | free tier + pay | P0 |
| DeepSeek | openai-compatible | api_key | pay-per-use | P1 |
| Mistral AI | openai-compatible | api_key | pay-per-use | P1 |
| xAI (Grok) | openai-compatible | api_key | pay-per-use | P1 |
| Together AI | openai-compatible | api_key | pay-per-use | P1 |
| Fireworks | openai-compatible | api_key | pay-per-use | P2 |
| NVIDIA NIM | openai-compatible | api_key | pay-per-use | P2 |
| Perplexity | openai-compatible | api_key | pay-per-use + search | P2 |
| Moonshot (Kimi) | openai-compatible | api_key / subscription | pay-per-use + subscription | P2 |
| Cerebras | openai-compatible | api_key | free tier | P2 |
| SambaNova | openai-compatible | api_key | free tier | P2 |
| Qwen Cloud | openai-compatible | api_key | pay-per-use | P2 |

### 5.2 Gateway (local/self-hosted, OpenAI-compatible)

| Gateway | Auth | URL editabile | Note |
|---------|------|---------------|------|
| Ollama | none | si (default localhost:11434) | Modelli locali, costo zero |
| OpenClaw | api_key o none | si (default localhost:18789) | 45+ provider, subscription auth |
| LM Studio | none | si (default localhost:1234) | GUI per modelli locali |
| vLLM | api_key o none | si | Self-hosted inference server |
| LiteLLM | api_key o none | si | Unified proxy, 100+ provider |
| Cloudflare AI Gateway | api_key | si | Edge inference |

### 5.3 Meta-router

| Router | Auth | Note |
|--------|------|------|
| OpenRouter | api_key | 200+ modelli, prepaid credits, free tier |

### 5.4 Subscription vs API key — chiarimento per l'utente

I "provider in abbonamento" consumer (ChatGPT Plus $20/mo, Claude Pro $20/mo, Gemini Advanced) **non espongono API**. Sono prodotti web-only.

Provider che hanno **sia abbonamento sia API key** (e quindi funzionano con ZeroHuman):
- Moonshot/Kimi → "Kimi Code API key (subscription)" = abbonamento con API access
- OpenClaw → piani subscription con API key inclusa
- OpenRouter → prepaid credits (ricarichi, non abbonamento mensile)
- Together.ai → committed spend tiers

La UI deve spiegare questa differenza con un banner informativo.

## 6. Scope

### 6.1 In scope

1. **Provider Catalog** — registro statico dei provider supportati con metadata (P0-P2)
2. **DB: `brand_llm_config`** — preferenze LLM per-brand (provider, model, fallback strategy, budget)
3. **BYOK API routes** — CRUD API key criptata + validazione + config preferenze
4. **Enhanced Registrar** — routing per-brand basato su config utente + BYOK keys + system fallback
5. **`GenericOpenAIProvider`** — singola implementazione che copre tutti i provider OpenAI-compatible
6. **`AnthropicDirectProvider`** — provider nativo per Anthropic SDK (non OpenAI-compatible)
7. **Gateway detection** — auto-discovery di Ollama/LM Studio/OpenClaw su localhost
8. **Frontend: Provider Hub** — pagina settings interattiva per gestire provider e preferenze
9. **Wizard Step "LLM" refactor** — da read-only a interattivo: l'utente configura il provider durante il setup
10. **Cost dashboard** — chart comparativo per-provider (estensione di ProviderStatsCard esistente)

### 6.2 Out of scope (esplicito)

- OAuth flow per provider (Google OAuth, Copilot) — solo API key per ora
- CLI login reuse (es. "Reuse Claude CLI login") — richiede accesso al filesystem dell'utente
- Streaming responses — il sistema oggi e' batch, lo streaming e' un progetto separato
- Model fine-tuning / LoRA management
- Provider marketplace / community plugins
- Automatic model selection via benchmarking

## 7. User Stories

### US-1: BYOK per provider diretto
> Come utente, voglio inserire la mia API key Anthropic/OpenAI/Groq dalla UI e che il sistema la usi per le chiamate del mio brand, cosi' non dipendo dall'admin.

**AC:**
- [ ] La pagina Settings > AI Providers mostra una card per ogni provider P0
- [ ] Posso inserire, validare (test call), e rimuovere una API key
- [ ] La key e' criptata con Fernet e salvata in `brand_integrations`
- [ ] Le chiamate LLM del mio brand usano la mia key se configurata
- [ ] Se la mia key fallisce, il sistema ricade sul fallback globale

### US-2: Gateway locale
> Come utente privacy-first, voglio connettere Ollama sul mio PC e che ZeroHuman lo usi, senza mandare dati a terzi.

**AC:**
- [ ] Sezione "Gateways" mostra Ollama/OpenClaw/LM Studio
- [ ] Posso specificare URL custom (default: localhost:11434 per Ollama)
- [ ] Il sistema fa un health check (GET /v1/models) e mostra i modelli disponibili
- [ ] Posso selezionare Ollama come provider preferito per il mio brand
- [ ] Se Ollama e' offline, fallback automatico a provider cloud

### US-3: OpenClaw gateway con subscription
> Come utente con abbonamento OpenClaw/Kimi, voglio connettere il gateway OpenClaw e che il sistema usi i miei modelli subscription.

**AC:**
- [ ] OpenClaw appare nella sezione Gateways
- [ ] Posso configurare URL + API key (opzionale per auth subscription)
- [ ] Il sistema lista i modelli disponibili dal gateway
- [ ] Le chiamate passano attraverso OpenClaw che gestisce auth/subscription

### US-4: Preferenze modello per-brand
> Come power user, voglio scegliere quale provider e modello usare per ogni tipo di task (creative, research, scoring).

**AC:**
- [ ] Sezione "Model Routing" mostra le 7 capability con i modelli assegnati
- [ ] Posso overridare il modello per ogni capability (dropdown con modelli disponibili)
- [ ] Default: "Auto" (il sistema sceglie in base a priority)
- [ ] Le preferenze sono per-brand, salvate in `brand_llm_config`

### US-5: Wizard setup interattivo
> Come nuovo utente, voglio configurare il mio provider LLM durante il wizard di setup, non dopo.

**AC:**
- [ ] Step "LLM" del wizard mostra il Provider Hub in versione compatta
- [ ] Posso inserire una API key direttamente nel wizard
- [ ] Posso connettere un gateway locale direttamente nel wizard
- [ ] Posso saltare (skip) — il sistema usa il fallback globale se disponibile
- [ ] Lo step blocca se nessun LLM e' disponibile (ne' BYOK ne' env var ne' gateway)

### US-6: Cost comparison
> Come owner, voglio vedere quanto costa ogni provider e confrontarli per prendere decisioni informate.

**AC:**
- [ ] Dashboard costi mostra: calls, latency, cost/1k tokens, error rate per provider
- [ ] Filtro temporale: 24h, 7d, 30d
- [ ] Chart comparativo (bar chart) per cost e latency
- [ ] Alert se il budget giornaliero e' al 80% o superato

## 8. UI/UX

### 8.1 Settings > AI Providers (pagina dedicata)

```
┌────────────────────────────────────────────────────────────┐
│  AI Providers                                    [Docs ↗]  │
│                                                             │
│  ┌─ System fallback ────────────────────────────────────┐  │
│  │ ⚡ Anthropic (env)    ✓ configured                   │  │
│  │ ⚡ OpenRouter (env)   ✓ configured                   │  │
│  │ Set by admin via .env — used when no BYOK is set     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ Your API Keys (BYOK) ──────────────────────────────┐  │
│  │                                                       │  │
│  │ [Anthropic logo] Anthropic           [Add key]       │  │
│  │ [OpenAI logo]    OpenAI              [sk-***] ✓ [✕]  │  │
│  │ [Google logo]    Google AI (Gemini)  [Add key]       │  │
│  │ [Groq logo]      Groq               [gsk-***] ✓ [✕] │  │
│  │ [DeepSeek logo]  DeepSeek           [Add key]       │  │
│  │ [Mistral logo]   Mistral AI         [Add key]       │  │
│  │                              [Show more providers ▾]  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ Local Gateways ────────────────────────────────────┐  │
│  │                                                       │  │
│  │ 🦙 Ollama     localhost:11434   ✓ 3 models  [Config] │  │
│  │ 🔌 OpenClaw   localhost:18789   ✓ connected  [Config] │  │
│  │ 📦 LM Studio  localhost:1234    ○ offline            │  │
│  │ ⚡ LiteLLM    — not configured  [Add gateway]        │  │
│  │                                                       │  │
│  │ ℹ️  Gateways run on your machine. They can use       │  │
│  │    subscription auth (Kimi Code, OpenClaw plans).    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ Meta-router ───────────────────────────────────────┐  │
│  │ 🌐 OpenRouter  [sk-or-***] ✓  200+ models           │  │
│  │    Credits: $12.34 remaining                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ Routing Preferences ───────────────────────────────┐  │
│  │ Preferred provider: [Auto ▾]                         │  │
│  │ Fallback strategy:  [Auto (priority-based) ▾]        │  │
│  │ Daily AI budget:    [$5.00 ▾]                        │  │
│  │                                                       │  │
│  │ Per-capability overrides:          [Show advanced ▾]  │  │
│  │   Creative:  [claude-opus-4 ▾]                       │  │
│  │   Research:  [Auto ▾]                                │  │
│  │   Scoring:   [gpt-4o-mini ▾]                         │  │
│  │   ...                                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ Provider Stats (last 7d) ──────────────────────────┐  │
│  │ [24h] [7d] [30d]                                     │  │
│  │                                                       │  │
│  │ anthropic   142 calls  820ms avg  $0.0034/1k  0.7%  │  │
│  │ groq         58 calls  180ms avg  $0.0000/1k  1.2%  │  │
│  │ ollama       23 calls  340ms avg  $0.0000/1k  0.0%  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ ℹ️  About subscription providers ──────────────────┐  │
│  │ ChatGPT Plus, Claude Pro, and Gemini Advanced are    │  │
│  │ consumer products without API access.                │  │
│  │                                                       │  │
│  │ To use AI models in ZeroHuman, you need an API key   │  │
│  │ from the provider (different from the subscription).  │  │
│  │                                                       │  │
│  │ Some providers offer subscription plans WITH API      │  │
│  │ access: Kimi Code, OpenClaw, OpenRouter prepaid.     │  │
│  │ Connect these via the Gateway or BYOK sections above.│  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### 8.2 Wizard Step "LLM" (refactored)

```
┌─────────────────────────────────────────────────────────┐
│ ● ● ○ ○ ○ ○   LLM                                       │
│                                                           │
│ Configure your AI provider                                │
│ At least one provider is needed to run the pipeline.      │
│                                                           │
│ ┌─ Quick setup (choose one) ────────────────────────┐    │
│ │                                                     │    │
│ │  ○ I have an API key                                │    │
│ │    [Select provider ▾] [paste key here___] [Test]   │    │
│ │                                                     │    │
│ │  ○ I use Ollama / local models                      │    │
│ │    [localhost:11434___]  [Test connection]           │    │
│ │                                                     │    │
│ │  ○ I use OpenClaw gateway                           │    │
│ │    [localhost:18789___]  [Test connection]           │    │
│ │                                                     │    │
│ │  ○ My admin already configured it (env vars)        │    │
│ │    ✓ Anthropic configured   ✓ OpenRouter configured │    │
│ │                                                     │    │
│ └─────────────────────────────────────────────────────┘    │
│                                                           │
│ [← Back]                              [Next →]            │
└─────────────────────────────────────────────────────────┘
```

## 9. Routing Logic (enhanced)

La selezione del provider per una chiamata LLM segue questa cascata:

```
1. brand_llm_config.preferred_provider?     → usa quello (se ha key/gateway valido)
2. brand_llm_config.capability_overrides?    → per-capability model override
3. brand ha BYOK key per un provider?        → usa la BYOK key (priority order)
4. brand ha gateway connesso?                → usa gateway (OpenClaw/Ollama)
5. system env var configurata?               → usa env var (admin fallback)
6. OpenRouter free tier disponibile?         → usa free tier (emergency)
7. nessuno disponibile                       → errore con messaggio actionable
```

## 10. Fasi di implementazione

### Fase 1 — Foundation (P0)
- Provider catalog (dataclass/registry statico)
- DB: `brand_llm_config` migration
- `GenericOpenAIProvider` (copre 80% provider)
- `AnthropicDirectProvider` (Anthropic SDK nativo)
- BYOK API routes (CRUD + validate)
- Enhanced registrar routing

### Fase 2 — UI (P0)
- Provider Hub component (settings page)
- Wizard Step "LLM" refactor
- Gateway connection UI (Ollama, OpenClaw, LM Studio)
- Gateway auto-discovery (health check localhost ports)

### Fase 3 — Preferences & Cost (P1)
- Per-capability model override UI
- Routing preferences (provider, strategy, budget)
- Cost comparison dashboard (estensione ProviderStatsCard)
- Budget alerts

### Fase 4 — Extended catalog (P2)
- Aggiunta provider P1 e P2 al catalogo
- Provider-specific features (Perplexity search, NVIDIA NIM)
- OpenRouter credit balance display
- Gateway model listing (GET /v1/models)

## 11. Metriche di successo

| Metrica | Target | Come misurare |
|---------|--------|---------------|
| % brand con BYOK configurato | >50% entro 30d dal deploy | count brand_integrations where provider in llm_providers |
| Chiamate su BYOK vs system fallback | >70% su BYOK | llm_provider_metrics.is_fallback ratio |
| Wizard completion rate step LLM | >90% (oggi blocca) | wizard state tracking |
| Costo medio ridotto | -20% vs baseline | llm_provider_metrics.cost_usd trend |
| Gateway locali connessi | >10% brand | brand_llm_config where preferred_provider in gateways |

## 12. Rischi e mitigazioni

| Rischio | Impatto | Mitigazione |
|---------|---------|-------------|
| API key utente scaduta/invalida | Chiamate falliscono | Validation on save + periodic health check + fallback chain |
| Ollama offline durante pipeline | Content non generato | Fallback automatico a cloud provider |
| Rate limit su free tier (Groq, Cerebras) | Rallentamento | Rate limiter gia' implementato in llm_client.py, rispetta 429 |
| Utente incolla key sbagliata | UX frustrazione | Validation call prima di salvare + error message chiaro |
| Costi imprevisti con BYOK | Sorpresa in bolletta | Budget cap per-brand + alert a 80% |
| Gateway locale non OpenAI-compatible | Errori parsing | Strict health check su GET /v1/models prima di attivare |
