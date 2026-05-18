# Plan: Capability Expansion (Video + Email Marketing + Deep Research + Agents + Provider Hub + Dev Skills)

> Source PRD: [2026-05-15-capability-expansion-prd-v2.md](./2026-05-15-capability-expansion-prd-v2.md) (merged v2)
> Triage: [2026-05-15-integration-candidates-triage.md](./2026-05-15-integration-candidates-triage.md)
> Parent issue: [#1](https://github.com/davidesilver/ZeroHuman-Agency/issues/1)
> Created: 2026-05-15 — Updated: 2026-05-16

## Architectural decisions

Decisioni durevoli — valide per tutte le fasi.

- **Routes** (nuove sotto `src/app/api/`):
  - `api/video/` — POST `/render`, POST `/generate`, GET `/status/:id`, GET `/list`
  - `api/email-marketing/` — POST `/contacts`, POST `/campaigns`, POST `/automations`, GET `/lists`
  - `api/research/deep` — POST avvia, GET `/status/:id`, GET `/results/:id`
  - `api/research/competitor` — POST avvia spider, GET `/snapshots`
  - `api/llm/providers` — GET lista, GET `/metrics`
  - `api/agents/` — GET lista, POST `/:slug/invoke`
- **Schema (Supabase, tutte con RLS per `brand_id`)**:
  - `videos`, `video_templates`
  - `brevo_contacts`, `brevo_campaigns`, `email_automations`
  - `deep_research_jobs`
  - `competitor_snapshots`
  - `llm_provider_metrics`
  - `feature_flags` (per-brand)
  - `brand_integrations` (chiavi API per-brand, cifrate)
- **Key models / moduli Python**:
  - `services/video/` (HyperFrames renderer + Heygen client + orchestrator)
  - `services/email/brevo_client.py` (affianca `resend_client.py`)
  - `retrievers/deep_research.py`
  - `retrievers/competitor_spider.py`
  - `services/llm/` con registrar pattern + provider plugin (`openrouter.py`, `openclaw.py`)
  - `monitoring/llm_metrics.py`
- **Multi-tenancy**: ogni capability è per-brand. Chiavi API cifrate in `brand_integrations`, non env globali (env = solo fallback).
- **Feature flags**: per-brand, default OFF. Provider hub usa share 0..1.
- **Video renderer boundary**: HyperFrames **in-process** (Node sidecar) v1 — Apache 2.0. API/schema progettati per migrare a Remotion Lambda se necessario senza breaking change.
- **Email**: Brevo **affianca** Resend (non sostituisce). Resend resta default per transazionale newsletter.
- **Agent files**: cartella root `/agents` con subset da `msitarzewski/agency-agents` (submodule pinnato a commit).
- **Skills Claude dev-time**: aggiunte a `skills-lock.json` committato, hash-pinned.

---

## Phase 0: Foundation cross-cutting

> GitHub issue: [#2](https://github.com/davidesilver/ZeroHuman-Agency/issues/2) — P0

**User stories**: prerequisito tecnico per tutte (no US dirette)

### What to build

Setup minimo cross-cutting: tabelle `feature_flags` e `brand_integrations` con encryption, helper Python/TS per accesso, documentazione del pattern.

### Acceptance criteria

- [ ] Migration `feature_flags` applicata, RLS testata
- [ ] Migration `brand_integrations` applicata, RLS testata, encryption funzionante
- [ ] Helper Python `get_feature_flag(brand_id, key)` e TS equivalente in `src/lib/`
- [ ] Helper `get_brand_secret(brand_id, key)` con cache in-memory e invalidazione
- [ ] Test unit: encrypt/decrypt round-trip, RLS blocca cross-brand
- [ ] Sezione "Feature flags & brand secrets" aggiunta in `docs/ARCHITECTURE.md`

---

## Phase 1: Dev skills bundle

> GitHub issue: [#3](https://github.com/davidesilver/ZeroHuman-Agency/issues/3) — P0

**User stories**: US-S1 (developer experience)

### What to build

4 skills Claude committate in `skills-lock.json` per il team: `obra/superpowers`, `thedotmack/claude-mem`, `yamadashy/repomix`, `leonxlnx/taste-skill`.

### Acceptance criteria

- [ ] `skills-lock.json` aggiornato con 4 skills, hash pinnati
- [ ] Per ogni skill: 2-3 righe in `docs/ONBOARDING.md`
- [ ] Verifica su clone fresco: skills disponibili senza setup manuale
- [ ] Smoke test: nessun conflict reciproco

---

## Phase 2: Agency agents installation [HITL]

> GitHub issue: [#4](https://github.com/davidesilver/ZeroHuman-Agency/issues/4) — P0

**User stories**: gap PRD #4 (orchestrazione agenti specializzati)

### What to build

Installazione subset di `msitarzewski/agency-agents` (142+ agenti .md) nella cartella `/agents` del repo. Richiede decisione umana sul subset. Endpoint e UI per listarli e invocarli.

### Acceptance criteria

- [ ] Submodule `agency-agents` pinnato a commit in `.vendor/`
- [ ] Script `scripts/install-agents.sh` che copia categorie selezionate in `/agents`
- [ ] Subset approvato e committato (marketing, paid-media, design, strategy)
- [ ] Endpoint `GET /api/agents/` lista agents disponibili
- [ ] Endpoint `POST /api/agents/:slug/invoke` proxy verso LLM con system prompt = agente
- [ ] UI Settings → Agents tab: lista agenti, click per dettagli
- [ ] Doc in `docs/AGENTS.md`

---

## Phase 3: Brevo foundation (contacts + lists)

> GitHub issue: [#6](https://github.com/davidesilver/ZeroHuman-Agency/issues/6) — P0 — blocked by Phase 0

**User stories**: US-E1 (sync contatti)

### What to build

Connessione Brevo per-brand, sync contatti base (CSV → Brevo + mirror locale).

### Acceptance criteria

- [ ] Client Brevo Python con: auth, list/create contatti, list/create liste
- [ ] Chiave API Brevo per-brand in `brand_integrations` cifrata
- [ ] Tabella `brevo_contacts` (mirror locale) con RLS
- [ ] Endpoint `POST /api/email-marketing/contacts` (sync da CSV o JSON)
- [ ] Endpoint `GET /api/email-marketing/lists`
- [ ] UI Settings → Brand → "Audience": connessione, upload CSV, vista contatti
- [ ] Feature flag `email_marketing_enabled` rispettato
- [ ] Rate limit + retry esponenziale nel client
- [ ] Test integrazione contro sandbox Brevo

---

## Phase 4: LLM provider abstraction + telemetria

> GitHub issue: [#5](https://github.com/davidesilver/ZeroHuman-Agency/issues/5) — P1 — blocked by Phase 0

**User stories**: US-P2 (provider extensibility), prerequisito US-P1

### What to build

Registrar di provider LLM in `services/llm/`. OpenRouter resta default. Ogni chiamata emette telemetria comparabile.

### Acceptance criteria

- [ ] Interfaccia `LLMProvider` (chat, complete, embedding) + registrar
- [ ] OpenRouter convertito al nuovo pattern, zero regressioni
- [ ] Tabella `llm_provider_metrics` con RLS, indice su `(brand_id, ts)`
- [ ] Middleware emette riga per ogni chiamata
- [ ] Endpoint `GET /api/llm/providers` e `GET /api/llm/providers/metrics`
- [ ] Mini-card "Provider stats" in Settings → Integrations
- [ ] Test integrazione: chiamata reale → riga in `llm_provider_metrics`

---

## Phase 5: Brevo campaigns

> GitHub issue: [#10](https://github.com/davidesilver/ZeroHuman-Agency/issues/10) — P1 — blocked by Phase 3

**User stories**: US-E2 (campaign da draft), US-E4 (metriche email)

### What to build

Creare campagne Brevo da draft Content Engine. Mirror metriche aperture/click in dashboard.

### Acceptance criteria

- [ ] Tabella `brevo_campaigns` con RLS, FK opzionale al draft di origine
- [ ] Endpoint `POST /api/email-marketing/campaigns` (crea + schedule)
- [ ] Bottone "Send as Brevo campaign" in writing-lab per draft newsletter/email
- [ ] Webhook handler per metriche Brevo → update `brevo_campaigns.metrics`
- [ ] Card "Email performance" in dashboard analytics
- [ ] Test e2e: draft → campagna → invio test → metriche visualizzate

---

## Phase 6: Brevo automations

> GitHub issue: [#11](https://github.com/davidesilver/ZeroHuman-Agency/issues/11) — P1 — blocked by Phase 5

**User stories**: US-E3 (automations)

### What to build

Automation multi-step template-based (welcome / nurture / win-back). v1 senza drag-drop.

### Acceptance criteria

- [ ] Tabella `email_automations` con RLS
- [ ] 3 template predefiniti: welcome 3-step, nurture 5-step, win-back 2-step
- [ ] Endpoint `POST /api/email-marketing/automations`
- [ ] UI Settings → Brand → Automations: lista, attiva/disattiva, edit copy step
- [ ] Mapping automation → Brevo workflow
- [ ] Test: welcome series attivata → primo step inviato

---

## Phase 7: Deep research engine

> GitHub issue: [#7](https://github.com/davidesilver/ZeroHuman-Agency/issues/7) — P1 — blocked by Phase 0

**User stories**: US-R1 (deep research)

### What to build

`local-deep-research` come microservizio Docker + wrapper Python. Job asincroni, risultati strutturati.

### Acceptance criteria

- [ ] Container `local-deep-research` in `docker-compose.yaml` (porta 5000)
- [ ] Wrapper Python con `start_job(topic, depth, brand_id)` e `get_status(job_id)`
- [ ] Tabella `deep_research_jobs` con RLS
- [ ] Worker async per esecuzione job
- [ ] Endpoint `POST /api/research/deep`, `GET /status/:id`, `GET /results/:id`
- [ ] UI Research → "Deep research" tab: form (topic, depth 1-5), lista job, view risultati
- [ ] Feature flag `deep_research_enabled` + cap depth per-brand (default 3)
- [ ] Test: job depth=2 completa in < 5min, sources > 5

---

## Phase 8: Deep research → ideation handoff

> GitHub issue: [#12](https://github.com/davidesilver/ZeroHuman-Agency/issues/12) — P1 — blocked by Phase 7

**User stories**: US-R2 (research → ideation)

### What to build

Risultato deep research diventa input per il flow ideation esistente.

### Acceptance criteria

- [ ] Bottone "Generate content ideas" sulla view risultato deep research
- [ ] Endpoint che prende `deep_research_job_id` e crea N ideation entries
- [ ] FK `ideation.source_research_id` aggiunta, nullable
- [ ] UI ideation mostra origine come badge
- [ ] Test: job → click → 5 idee generate con riferimento al job

---

## Phase 9: Scrapling competitor monitoring

> GitHub issue: [#8](https://github.com/davidesilver/ZeroHuman-Agency/issues/8) — P1 — blocked by Phase 0

**User stories**: gap PRD #2 (ricerca competitor automatizzata)

### What to build

Scrapling come strumento per competitor monitoring e spider task dove serve stealth anti-Cloudflare. Complementare a Firecrawl.

### Acceptance criteria

- [ ] `scrapling` aggiunta a dipendenze Python
- [ ] Modulo retriever con `start_spider(target_urls, brand_id)` e pause/resume
- [ ] Scrapling MCP server configurato per dev-time
- [ ] Endpoint `POST /api/research/competitor`
- [ ] Tabella `competitor_snapshots` con RLS
- [ ] UI Research → "Competitor watch" tab: URL monitorati, snapshot history
- [ ] Test: spider su 3 URL (incluso 1 Cloudflare-protected) → contenuto estratto

---

## Phase 10: HyperFrames motion graphics foundation

> GitHub issue: [#9](https://github.com/davidesilver/ZeroHuman-Agency/issues/9) — P1 — blocked by Phase 0

**User stories**: US-V1 (recap programmatico), US-V5 (stato render visibile)

### What to build

Pipeline base per rendering video via HyperFrames (Apache 2.0). 1 template: "weekly recap" da analytics.

### Acceptance criteria

- [ ] `@heygen/hyperframes` aggiunta a Next.js dependencies
- [ ] Node sidecar HyperFrames invocato via subprocess dal backend Python
- [ ] Tabella `videos` e `video_templates` con RLS
- [ ] Template "weekly-recap" con props_schema (brand_id, week_start, metrics)
- [ ] GSAP integrato per transizioni (skill HyperFrames)
- [ ] Endpoint `POST /api/video/render`, `GET /status/:id`, `GET /list`
- [ ] UI "Videos" tab nella dashboard
- [ ] Storage video su Supabase Storage, URL firmato
- [ ] Feature flag `video_enabled`
- [ ] Test: render weekly-recap → MP4 valido < 60s

---

## Phase 11: Carousel → reel template

> GitHub issue: [#13](https://github.com/davidesilver/ZeroHuman-Agency/issues/13) — P1 — blocked by Phase 10

**User stories**: US-V2 (carousel → reel)

### What to build

Secondo template HyperFrames che monta un carousel approvato come reel video animato.

### Acceptance criteria

- [ ] Template "carousel-to-reel": legge slides, anima transizioni con GSAP
- [ ] Bottone "Convert to reel" sulla view carousel pubblicato
- [ ] Usa `POST /api/video/render` con template="carousel-to-reel"
- [ ] Risultante pubblicabile via Postiz
- [ ] Test e2e: carousel → reel → pubblicato in Postiz dev

---

## Phase 12: Heygen talking-head integration

> GitHub issue: [#14](https://github.com/davidesilver/ZeroHuman-Agency/issues/14) — P1 — blocked by Phase 0 + Phase 10

**User stories**: US-V3 (talking-head da script)

### What to build

Video talking-head con avatar brand da script generato dal Content Engine.

### Acceptance criteria

- [ ] Client Heygen Python (auth, list avatars, generate video, poll status)
- [ ] Chiave Heygen per-brand in `brand_integrations`
- [ ] UI Settings → Brand → Video → "Heygen avatar": select avatar default
- [ ] Endpoint `POST /api/video/generate` con kind="talking-head"
- [ ] Bottone "Generate talking-head" in writing-lab per draft "video script"
- [ ] Quota per-brand (`heygen_minutes_per_month`), counter mensile
- [ ] Alert Telegram a 80% quota
- [ ] Video completato → mirror in tabella `videos` (type='heygen')
- [ ] Test integrazione contro sandbox Heygen

---

## Phase 13: Video templates customization

> GitHub issue: [#15](https://github.com/davidesilver/ZeroHuman-Agency/issues/15) — P2 — blocked by Phase 10

**User stories**: US-V4 (template per-brand)

### What to build

Agency-owner definisce template HyperFrames per-brand (loghi, colori, font, asset, props custom).

### Acceptance criteria

- [ ] UI Settings → Brand → Video templates: lista, "New template"
- [ ] Form: nome, kind, props_schema editor, upload asset
- [ ] Asset in Supabase Storage per-brand
- [ ] Template weekly-recap e carousel-to-reel leggono asset/colori brand
- [ ] Anteprima 1° frame
- [ ] Test: template custom con colori brand → render li usa

---

## Phase 14: OpenClaw POC + A/B

> GitHub issue: [#16](https://github.com/davidesilver/ZeroHuman-Agency/issues/16) — P2 — blocked by Phase 4

**User stories**: US-P1 (A/B economico provider)

### What to build

Provider OpenClaw dietro il registrar di Phase 4. Traffic split configurabile per-brand. Confronto diretto.

### Acceptance criteria

- [ ] Provider OpenClaw implementa interfaccia `LLMProvider`
- [ ] Chiave API in `brand_integrations`
- [ ] Feature flag `llm_provider_openclaw_share` (0..1)
- [ ] Routing layer: split traffico secondo share
- [ ] UI Settings → Provider hub: slider share, credito residuo
- [ ] Dashboard "Provider compare": cost-per-1k-tokens e latenza media
- [ ] Smoke test: share=1.0 → 100% chiamate a OpenClaw
- [ ] Report con ≥ 1000 request comparate

---

## Phase 15: ViMax microservice [HITL]

> GitHub issue: [#17](https://github.com/davidesilver/ZeroHuman-Agency/issues/17) — P2 — blocked by Phase 10 + Phase 12

**User stories**: gap PRD #1 (video full pipeline)

### What to build

Microservizio Docker ViMax (pipeline multi-agente video). Gate HITL: decisione budget API video generation richiesta prima dell'implementazione.

### Acceptance criteria

- [ ] Decisione budget API video approvata e documentata
- [ ] Backend video AI scelto (Veo / Kling / Pixelle / Higgsfield) documentato
- [ ] Container ViMax in `docker-compose.yaml`
- [ ] Client Python per orchestrazione job
- [ ] Tabella `videos` estesa con `type='vimax'` e `pipeline_metadata`
- [ ] Endpoint `POST /api/video/generate` con kind="full-pipeline"
- [ ] UI Settings → Brand → Video → "Full pipeline" con budget cap
- [ ] Quota per-brand + alert Telegram
- [ ] Test e2e: brief → script → storyboard → clip → MP4 finale

---

## Dependency graph

```
Phase 0 (Foundation) ─────┬──── Phase 1 (Dev skills)
  [#2]                     │      [#3]
                           │
                           ├──── Phase 2 (Agency agents) [HITL]
                           │      [#4]
                           │
                           ├──── Phase 3 (Brevo contacts) ── Phase 5 (Campaigns) ── Phase 6 (Automations)
                           │      [#6]                         [#10]                  [#11]
                           │
                           ├──── Phase 4 (LLM providers) ── Phase 14 (OpenClaw POC)
                           │      [#5]                        [#16]
                           │
                           ├──── Phase 7 (Deep research) ── Phase 8 (Research→ideation)
                           │      [#7]                        [#12]
                           │
                           ├──── Phase 9 (Scrapling)
                           │      [#8]
                           │
                           └──── Phase 10 (HyperFrames) ─┬── Phase 11 (Carousel→reel)
                                  [#9]                    │    [#13]
                                                          │
                                                          ├── Phase 12 (Heygen) ── Phase 15 (ViMax) [HITL]
                                                          │    [#14]                 [#17]
                                                          │
                                                          └── Phase 13 (Video templates)
                                                               [#15]
```

Phases 1, 2 are independent of Phase 0 and can start immediately in parallel.
