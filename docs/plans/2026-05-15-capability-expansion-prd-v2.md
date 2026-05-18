# PRD v2 — ZeroHuman Agency: AI Capability Stack Expansion

> Versione: 0.2 (merged)
> Data: 2026-05-15 (rev. 2026-05-16)
> Repo: davidesilver/ZeroHuman-Agency
> Sources: [v1 PRD interno](./2026-05-15-capability-expansion-prd.md) + PRD esterno (`~/Downloads/ZeroHuman_Agency_PRD.md`) + [triage](./2026-05-15-integration-candidates-triage.md)
> Approccio: **plug-and-play first, custom solo se necessario**

---

## 1. Problema

ZeroHuman Agency è operativa con Postiz, Next.js 16, Python/FastAPI, Supabase. Pipeline testo + immagini coperta. Mancano cinque capability:

1. **Video di qualità** dall'idea al file finale, senza intervento manuale
2. **Ricerca** trend / competitor / brief automatizzata e profonda
3. **Distribuzione** email marketing & automation (oggi solo transazionale via Resend)
4. **Orchestrazione** di agenti specializzati per ruolo (copywriter, media buyer, brand guardian, ecc.)
5. **Animazione** asset web e video con standard pro (motion graphics)

Più due gap operativi:
6. Lock-in implicito su OpenRouter senza confronto economico misurato
7. Skills Claude dev-time minime → team perde tempo su workflow ad-hoc

## 2. Obiettivo

Aggiungere a ZeroHuman Agency una **capability stack modulare** combinando componenti open-source esistenti, API in abbonamento e skill Claude. Per ogni componente: valutare modalità d'integrazione esplicita.

| Modalità | Significato |
|----------|-------------|
| **Root** | Codice/asset committato nel repo `ZeroHuman-Agency` (es. cartelle `/agents`, `/skills`) |
| **Esterno** | Servizio separato collegato via API/MCP (come Postiz oggi) |
| **Codice** | Libreria/SDK importato in Next.js o Python backend |
| **Skill Claude** | Skill committate in `skills-lock.json`, dev-time, zero runtime |

## 3. Componenti & decisioni

### 3.1 Agenti AI specializzati — **P0 Root**

**Componente**: [`msitarzewski/agency-agents`](https://github.com/msitarzewski/agency-agents) (142+ agenti .md formato Claude Code/Cursor/OpenClaw/Gemini CLI)

**Cosa fanno**: agenti con personalità definita per content creation, paid media, strategy, design. Compatibili con Claude Code via Skills.

**Modalità**: **Root** (cartella `/agents` nel repo) + installazione script

**Subset prioritario per agenzia marketing**:
- `marketing-content-creator.md`
- `marketing-tiktok-strategist.md`
- `marketing-social-media-strategist.md`
- `paid-media-ppc-strategist.md`
- `design-brand-guardian.md`
- `design-image-prompt-engineer.md`
- categoria `strategy/` (analytics, trend research)

**Install**:
```bash
git submodule add https://github.com/msitarzewski/agency-agents .vendor/agency-agents
./scripts/install-agents.sh marketing paid-media design strategy
```

---

### 3.2 Brevo — Email Marketing & CRM — **P0 Esterno**

**Componente**: Brevo API (ex Sendinblue) — `@getbrevo/brevo` npm + Python httpx

**Decisione architetturale**: **Brevo affianca Resend**. Resend resta default transazionale (newsletter). Brevo gestisce: marketing campaigns, automations, segmenti, CRM lead/clienti agenzia.

**Modalità**: **Esterno** API + **Codice** SDK lato Next.js. Chiave API **per-brand cifrata** in `brand_integrations` (non env globale).

**Capabilities portate in v1**:
- Sync contatti (CSV upload + mirror locale)
- Campaign da draft Content Engine
- Automations template (welcome, nurture, win-back)
- Webhook metriche → dashboard

---

### 3.3 Animazione & motion graphics — **P1 Codice**

**Componente primario**: [`heygen-com/hyperframes`](https://github.com/heygen-com/hyperframes) — rendering video da HTML/CSS/GSAP, Apache 2.0, 18k+ stars. Include skill `/gsap`.

**Componente complementare**: [`greensock/gsap-skills`](https://github.com/greensock/gsap-skills) (plugin marketplace Claude)

**Componente alternativo (gated)**: [`remotion-dev/remotion`](https://github.com/remotion-dev/remotion) — solo se serve rendering Lambda distribuito a volumi alti (licenza commerciale sopra soglie). **Decisione**: HyperFrames primario in v1; Remotion riconsiderato se HyperFrames non scala.

**Modalità**: **Codice** (HyperFrames SDK in Next.js + Node sidecar dal backend Python) + **Skill Claude** (GSAP skills dev-time)

**Install**:
```bash
npx skills add heygen-com/hyperframes
npm install @heygen/hyperframes
```

---

### 3.4 Video AI — talking-head — **P1 Esterno**

**Componente**: Heygen Hyperframes API per **talking-head con avatar brand**

**Caso d'uso scelto**: founder o portavoce AI parla. Match con LinkedIn / video personali. (Confermato in revisione triage.)

**Modalità**: **Esterno** API Heygen + **Codice** client Python in `services/video/heygen_client.py`. Chiave per-brand cifrata.

**Quota di costo**: cap per-brand in `feature_flags` (es. `heygen_minutes_per_month`), alert Telegram a 80%.

---

### 3.5 Video pipeline full — **P2 Esterno**

**Componente**: [`HKUDS/ViMax`](https://github.com/HKUDS/ViMax) — pipeline multi-agente (Director + Screenwriter + Producer + Generator). Combinabile con [`AIDC-AI/Pixelle-Video`](https://github.com/AIDC-AI/Pixelle-Video) e/o MCP Higgsfield come backend di clip raw.

**Modalità**: **Esterno** — microservizio Docker on-demand, NON in v1. Si attiva quando talking-head + motion graphics non bastano.

**Flusso target**:
```
Brief cliente → ViMax (script+storyboard) → Pixelle/Higgsfield (raw clips)
→ HyperFrames (compositing+motion) → MP4 → Postiz (scheduling)
```

**Domanda aperta**: budget mensile API video generation (Veo/Kling) — da chiarire prima di P2.

---

### 3.6 Deep research — **P1 Esterno**

**Componente**: [`LearningCircuit/local-deep-research`](https://github.com/LearningCircuit/local-deep-research) (~95% SimpleQA su Qwen3.6-27B, 10+ motori, Docker-ready, zero telemetria)

**Modalità**: **Esterno** Docker (`docker run -d -p 5000:5000 localdeepresearch/local-deep-research`) + **Codice** wrapper Python `retrievers/deep_research.py`.

**Capability v1**:
- Job asincrono con depth configurabile (cap per-brand)
- Tabella `deep_research_jobs` per cache risultati
- Handoff verso ideation (research → idee)

---

### 3.7 Scraping competitor — **P1 Codice**

**Componente**: [`D4Vinci/Scrapling`](https://github.com/D4Vinci/Scrapling) (49k+ stars, anti-Cloudflare, MCP server integrato)

**Decisione**: Scrapling **complementare** a Firecrawl, non sostituisce. Firecrawl resta per content extraction generale; Scrapling per **monitoraggio competitor / spider task** dove serve stealth + MCP.

**Modalità**: **Codice** Python dependency + **Esterno** MCP per uso da Claude in dev.

---

### 3.8 Skills aggiuntive — **P1 Root + Skills Claude**

**Componenti**:
- [`leonxlnx/taste-skill`](https://github.com/leonxlnx/taste-skill) — valutazione estetica/culturale per direzione creativa
- Skills selezionate da [skills.sh](https://www.skills.sh/)
- Dev-time bundle (da v1 PRD): `obra/superpowers`, `thedotmack/claude-mem`, `yamadashy/repomix`

**Modalità**:
- **Root** cartella `/skills` per skill di prodotto (taste-skill etc. — usate dagli agenti runtime)
- **Skill Claude** committate in `skills-lock.json` per dev-time (superpowers/claude-mem/repomix)

---

### 3.9 Multi-model AI access — **P2 Esterno**

**Componente**: [OpenClaw model providers](https://docs.openclaw.ai/it/concepts/model-providers) — gateway unificato a Claude, GPT-4o, Gemini, Mistral, DeepSeek, Qwen, ecc.

**Decisione (da v1)**: **POC** dietro feature flag, NON sostituzione di OpenRouter. Tabella `llm_provider_metrics` per A/B costo/latenza prima di decidere.

**Modalità**: **Esterno** gateway + provider plugin in `services/llm/providers/openclaw.py` (registrar pattern).

---

### 3.10 WeClone — **P3 Esterno**

**Componente**: [`xming521/weclone`](https://github.com/xming521/weclone) — digital clone da conversazioni

**Decisione**: **NON in v1**. Solo P3 on-demand se un cliente lo richiede (AI con voce specifica). Pattern utile per migliorare l'Humanizer esistente — studio interno senza importare codice.

---

### 3.11 context-mode — **P3 Studio**

**Componente**: [`mksglu/context-mode`](https://github.com/mksglu/context-mode)

**Decisione**: studio dei pattern, non importare. Modulo `memory/` + `prompts/` Python già esistenti.

---

### 3.12 AutoHedge — **NON INTEGRARE**

[`The-Swarm-Corporation/AutoHedge`](https://github.com/The-Swarm-Corporation/AutoHedge) — pattern multi-agent finance. **Off-topic** per marketing. Pattern di orchestrazione utile come riferimento ma il "GOD Mode review" interno copre già il caso.

---

## 4. Stack di priorità

| Fase | Componente | Modalità | Effort | Impatto |
|------|-----------|----------|--------|---------|
| **P0** | agency-agents (subset 7 categorie) | Root | Basso | Alto |
| **P0** | Brevo API (contatti + campaign) | Esterno + Codice | Basso | Alto |
| **P0** | Foundation: feature_flags + brand_integrations | Root | Basso | Alto |
| **P0** | Dev skills bundle (superpowers/claude-mem/repomix/taste-skill) | Skill Claude | Basso | Medio |
| **P1** | Provider abstraction + telemetria LLM | Codice | Medio | Medio |
| **P1** | HyperFrames + GSAP (motion graphics) | Codice + Skill | Medio | Alto |
| **P1** | Heygen talking-head | Esterno | Medio | Alto |
| **P1** | local-deep-research (Docker) | Esterno | Basso | Alto |
| **P1** | Scrapling (competitor monitoring) | Codice | Basso | Medio |
| **P1** | Brevo automations | Codice | Medio | Medio |
| **P2** | Video templates customization | Codice | Medio | Medio |
| **P2** | ViMax full pipeline | Esterno | Alto | Medio |
| **P2** | OpenClaw POC + A/B | Esterno | Medio | Medio |
| **P3** | WeClone | Esterno | Alto | Basso |
| **P3** | context-mode (study only) | — | — | Basso |

---

## 5. Architettura target

```
ZeroHuman Agency (Next.js 16 + Supabase + Python/FastAPI)
│
├── /agents                  ← agency-agents .md (Root)
├── /skills                  ← taste-skill + skills.sh picks (Root)
├── skills-lock.json         ← dev-time skills committed (Root)
│
├── API esterni
│   ├── Brevo                ← email marketing/CRM
│   ├── Heygen               ← talking-head video
│   ├── OpenClaw (P2)        ← model gateway
│   └── Postiz               ← scheduling (esistente)
│
├── Microservizi Docker
│   ├── local-deep-research :5000
│   └── ViMax (P2)
│
├── Backend Python (services/)
│   ├── video/heygen_client.py
│   ├── video/hyperframes_renderer.py
│   ├── email/brevo_client.py     ← affianca resend_client.py
│   ├── llm/providers/             ← registrar: openrouter, openclaw
│   └── monitoring/llm_metrics.py
│
└── Next.js dependencies
    ├── @heygen/hyperframes  ← motion graphics
    ├── @getbrevo/brevo      ← email SDK
    └── @gsap/...            ← animazioni
```

---

## 6. Decisioni architetturali durabili

### Routes API (nuove sotto `src/app/api/`)
- `api/video/` — POST `/render`, POST `/generate`, GET `/status/:id`, GET `/list`
- `api/email-marketing/` — POST `/contacts`, POST `/campaigns`, POST `/automations`, GET `/lists`
- `api/research/deep` — POST avvia, GET `/status/:id`, GET `/results/:id`
- `api/llm/providers` — GET lista, GET `/metrics`
- `api/agents/` — GET lista agency-agents installati, POST `/invoke`

### Schema Supabase (tutte con RLS per `brand_id`)
- `videos`, `video_templates`
- `brevo_contacts`, `brevo_campaigns`, `email_automations`
- `deep_research_jobs`
- `llm_provider_metrics`
- `feature_flags`
- `brand_integrations` (chiavi API cifrate)

### Multi-tenancy
Tutte le chiavi API esterne (Heygen, Brevo, OpenClaw) per-brand cifrate. Env globale = solo fallback dev.

### Feature flags per-brand
`video_enabled`, `email_marketing_enabled`, `deep_research_enabled`, `llm_provider_openclaw_share` (0..1), `heygen_minutes_per_month`, `deep_research_depth_cap`.

### Video boundary
HyperFrames in-process Node sidecar v1. Lambda/Remotion solo se v1 non scala (API/schema già compatibili).

### Skill management
- Dev-time: `skills-lock.json` committato (hash pin)
- Prodotto: `/agents` e `/skills` cartelle root committate

---

## 7. Metriche di successo

Da PRD esterno (target di prodotto a 90gg):

- Tempo brief → post pubblicato: **< 15 min** (da ~90 min attuali)
- Ore umane per campagna mensile: **< 2h** (supervisione + approvazione)
- Costo per contenuto: **riduzione > 60%** vs produzione tradizionale
- Qualità video output: **approvazione cliente senza revisioni > 70%**

Metriche tecniche (da v1):
- % brand con almeno 1 video renderizzato: ≥ 30%
- # campagne Brevo / brand attivo / mese: ≥ 3
- Deep research success rate: ≥ 95%
- Provider POC: report con ≥ 1000 request comparabili

---

## 8. Rischi & mitigazioni

| Rischio | Prob | Impatto | Mitigazione |
|---------|------|---------|-------------|
| Costo Heygen fuori controllo | M | A | Quota per-brand, alert 80%, hard cap |
| HyperFrames non scala oltre N video/giorno | M | M | API compatibile con migrazione Remotion Lambda |
| Brevo rate limit | M | M | Backoff esponenziale nel client |
| Deep research costoso in token | A | M | Depth cap, cache su `deep_research_jobs` |
| OpenClaw instabile in POC | M | B | Share configurabile, rollback istantaneo |
| agency-agents .md vanno stale upstream | M | B | Submodule pinnato a commit, update review periodico |
| Compliance GDPR per deep research + WeClone su dati EU | M | A | Storage locale, DPA con vendor, audit dedicato |
| Conflict tra skills Claude | M | B | Selezione mirata 4 skills, no bulk |

---

## 9. Domande aperte

1. Higgsfield MCP — disponibilità e costi produzione?
2. Budget mensile per API video generation (Veo/Kling) per ViMax P2?
3. Microservizi Docker su VPS dedicato o integrati nel deploy Vercel/Railway esistente?
4. agency-agents: subset esatto da committare in `/agents` — quante categorie ora vs incrementale?
5. Brevo: import contatti da DB esistente automatico o sync manuale (consenso GDPR)?
6. Heygen avatars: avatar generico per-brand o avatar custom (richiede training)?
7. Skills `/skills` cartella root: convivenza con `skills-lock.json` — singolo formato o doppio?

---

## 10. Out of scope (esplicito)

- AutoHedge (off-topic)
- Open-Generative-AI (sovrapposto a services LLM esistenti)
- WeClone in v1 (P3 on-demand)
- context-mode come dipendenza (solo studio)
- Sostituzione di Resend (Brevo affianca, non sostituisce)
- Remotion in v1 (HyperFrames primario; riconsiderare se non scala)
- ViMax in v1 (P2, attivato solo se Heygen+HyperFrames non bastano)
- Mobile app, SSO, advanced collaboration (roadmap futuro prodotto)

---

**Prossimo passo**: invocare `/prd-to-issues` su questo documento per creare gli issue GitHub.
