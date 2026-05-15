# PRD — Capability Expansion: Video, Email Marketing, Deep Research, Provider Hub, Dev Skills

> Source triage: [2026-05-15-integration-candidates-triage.md](./2026-05-15-integration-candidates-triage.md)
> Status: Draft 2026-05-15
> Owner: Davide Silvestri
> Implementation plan target: `/prd-to-plan` → `docs/plans/<feature>.md`

---

## 1. Problema

ZeroHuman-Agency (Content Engine) oggi copre **research → ideation → generation → review → publishing testo + immagini**. Mancano tre capability che limitano il valore differenziante della piattaforma e tre asset di sviluppo che rallentano l'iterazione interna.

Gap di prodotto:

1. **Niente video in pipeline.** Tutto il content è testo o immagine. La piattaforma non genera reel, talking-head, recap video.
2. **Email solo transazionale.** Resend invia la newsletter ma non c'è marketing automation, segmentazione, drip campaign o behavior trigger.
3. **Research troppo superficiale.** I `retrievers/` raccolgono e segnano sorgenti, ma non c'è un agente di deep research che indaga un topic in più step.

Gap operativi:

4. **Lock-in implicito a OpenRouter** per i modelli, senza un confronto economico misurato.
5. **Skills Claude dev-time minime** (solo `supabase-postgres-best-practices`) — il team usa workflow ad-hoc e perde tempo.

## 2. Per chi

| Stakeholder | Bisogno specifico |
|-------------|-------------------|
| Content team (utenti finali) | Produrre video brand + automazioni email senza uscire dalla piattaforma |
| Agency users | Distribuire campaign multi-canale (email marketing + video) per i loro client |
| Developer team interno | Skills Claude condivise per ridurre tempo di sviluppo |
| Owner | Visibilità su costi LLM reali via A/B provider |

## 3. Scope

### In scope

- **Video pipeline**: Remotion come renderer programmatico + Heygen come generatore talking-head avatar
- **Brevo integration**: marketing automation **affianca** Resend (non sostituisce)
- **Deep research agent**: integrazione `local-deep-research` come retriever avanzato
- **Provider abstraction + OpenClaw POC**: feature-flagged accanto a OpenRouter, telemetria comparativa
- **Dev skills**: aggiunta a `skills-lock.json` di `obra/superpowers`, `thedotmack/claude-mem`, `yamadashy/repomix`, `leonxlnx/taste-skill`

### Out of scope (esplicito)

- Generazione video puramente AI text-to-video (ViMax, Pixelle, Higgsfield) — postponed, video AI = solo Heygen avatar
- Voice cloning (WeClone) — solo studio di pattern per migliorare l'Humanizer esistente, niente codice
- Sostituzione di Resend con Brevo
- Scrapling (Firecrawl resta primario)
- AutoHedge, Open-Generative-AI, context-mode, agency-agents, gsap-skills (vedi triage)
- Mobile app, SSO, advanced collaboration (già nel roadmap futuro del prodotto)

## 4. Decisioni architetturali durabili

Decisioni che valgono per tutte le fasi. Da congelare prima dell'implementazione.

### 4.1 Routes API

Nuovi endpoint Next.js (sotto `src/app/api/`):

- `api/video/` — POST `/render`, POST `/generate`, GET `/status/:id`, GET `/list`
- `api/email-marketing/` — POST `/contacts`, POST `/campaigns`, POST `/automations`, GET `/lists`
- `api/research/deep` — POST avvia deep research, GET `/status/:id`, GET `/results/:id`
- `api/llm/providers` — GET lista provider configurati, POST `/route` (manual override per test)

Tutti rispettano l'attuale pattern multi-tenant (header brand, RLS Supabase).

### 4.2 Schema (Supabase) — nuove tabelle

- `videos` — `id, brand_id, type (remotion|heygen), status, source_data jsonb, render_url, created_at, completed_at`
- `video_templates` — `id, brand_id, name, kind (recap|carousel-reel|talking-head|...), props_schema jsonb`
- `brevo_contacts` — `brand_id, brevo_contact_id, email, attributes jsonb, lists text[]` (mirror locale)
- `brevo_campaigns` — `id, brand_id, brevo_campaign_id, type, status, scheduled_at, metrics jsonb`
- `email_automations` — `id, brand_id, trigger jsonb, steps jsonb, status`
- `deep_research_jobs` — `id, brand_id, topic, depth int, status, started_at, completed_at, summary text, sources jsonb`
- `llm_provider_metrics` — `id, brand_id, provider, model, prompt_hash, latency_ms, input_tokens, output_tokens, cost_usd, ts`

Tutti hanno RLS per `brand_id` come il resto del prodotto.

### 4.3 Modelli Python (`python/src/content_engine/`)

- `services/video/` — `remotion_renderer.py`, `heygen_client.py`, `video_orchestrator.py`
- `services/email/brevo_client.py` — affianca `resend_client.py`
- `retrievers/deep_research.py` — wrappa local-deep-research
- `services/llm/providers/openclaw.py` — nuovo provider; refactor `services/llm/` per registrar pattern
- `monitoring/llm_metrics.py` — emette righe in `llm_provider_metrics`

### 4.4 Skill management

`skills-lock.json` resta single source of truth. Aggiunte committate, hash-pinned come oggi.

### 4.5 Feature flags

Tabella `feature_flags` (per-brand) con almeno:
- `video_enabled` (default false)
- `email_marketing_enabled` (default false)
- `deep_research_enabled` (default false)
- `llm_provider_openclaw_share` (0..1, default 0 — POC traffic split)

### 4.6 Auth / multi-tenancy

Tutte le nuove integrazioni sono **per-brand**:
- API key Heygen / Brevo / OpenClaw in tabella `brand_integrations` (cifrata) — non env globali
- Env globale = solo fallback / default

### 4.7 Boundary di servizio video

Remotion render è **pesante** (CPU/IO bound). Due opzioni — congelare ora:
- **Locale**: rendering nel container Python con `@remotion/renderer` via Node sidecar
- **Lambda**: Remotion Lambda (AWS) come servizio remoto

→ **Decisione**: partire **locale** con Node sidecar (semplice, dev-friendly), schema/API già compatibili con migrazione a Lambda in fase successiva senza breaking change.

## 5. User stories

### Video

- **US-V1**: Come content manager, voglio generare un video recap programmatico dalle analytics settimanali del brand, così posso pubblicarlo come reel.
- **US-V2**: Come content manager, voglio convertire un carousel approvato in un reel video con animazioni del brand.
- **US-V3**: Come content manager, voglio generare un talking-head con avatar brand a partire da uno script generato dal Content Engine.
- **US-V4**: Come agency owner, voglio definire template video per-brand riutilizzabili.
- **US-V5**: Come utente, voglio vedere lo stato dei render in corso e accedere ai video completati dalla dashboard.

### Email marketing

- **US-E1**: Come content manager, voglio sincronizzare i contatti del brand su Brevo da una lista CSV o dal CRM esistente.
- **US-E2**: Come content manager, voglio creare campagne email a partire dai draft già esistenti nel Content Engine (riuso del contenuto).
- **US-E3**: Come content manager, voglio definire automation (welcome series, nurture, win-back) collegate a eventi del brand.
- **US-E4**: Come owner, voglio metriche di apertura/click delle campagne Brevo nel dashboard del Content Engine.

### Deep research

- **US-R1**: Come content manager, voglio richiedere un "deep research" su un topic con livello di profondità configurabile, e ricevere un report sintetico con fonti.
- **US-R2**: Come content manager, voglio che il risultato di un deep research alimenti automaticamente l'ideation di nuovi contenuti.

### Provider hub

- **US-P1**: Come owner, voglio dirigere una percentuale del traffico LLM verso OpenClaw e confrontare costi/latenza vs OpenRouter sui medesimi prompt.
- **US-P2**: Come dev, voglio aggiungere un provider LLM senza toccare gli orchestrator (registrar pattern).

### Dev skills

- **US-S1**: Come dev, quando clono il repo, ho automaticamente disponibili le skills Claude condivise del team (superpowers, claude-mem, repomix, taste-skill).

## 6. Requisiti non-funzionali

- **Multi-tenancy**: ogni nuova capability è per-brand. RLS attiva.
- **Cost observability**: costi Heygen, Brevo, OpenClaw, LLM provider tracciati per-brand in tabelle dedicate.
- **Backward compat**: chi non abilita il flag non vede UI nuovo. Brevo non interferisce con Resend.
- **Latency**: video render asincrono (job + webhook/polling), deep research idem. UI non blocca mai > 2s su POST.
- **Security**: chiavi API per-brand cifrate at-rest (Supabase Vault o `pgcrypto`).
- **Telemetria**: ogni chiamata LLM popola `llm_provider_metrics` per il POC OpenClaw.

## 7. Success metrics

| Capability | Metrica | Target a 90gg |
|------------|---------|---------------|
| Video | # brand con almeno 1 video renderizzato | ≥ 30% dei brand attivi |
| Video | Tempo medio script→video pubblicato | < 15 min |
| Email mkt | # campagne Brevo create via Content Engine | ≥ 3 / brand attivo / mese |
| Email mkt | Open rate medio campagne via piattaforma | ≥ benchmark Brevo per industry |
| Deep research | # job completati con successo | ≥ 95% |
| Deep research | Riuso research → content generato | ≥ 50% dei job |
| Provider hub | Decisione data-driven OpenClaw vs OpenRouter | Report con almeno 1000 request comparabili |
| Dev skills | Tempo medio di onboarding nuovo dev | -30% vs baseline |

## 8. Rischi & mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Costo Heygen per-minuto fuori controllo | M | A | Quota per-brand, hard cap configurabile, alert Telegram |
| Render Remotion locale satura risorse Python | A | M | Queue + concorrenza max, fallback "Lambda mode" già nel design |
| Brevo API rate limit | M | M | Backoff esponenziale, batch in modulo client |
| Deep research costoso in token | A | M | Limite "depth" max per-brand, cache risultati su `deep_research_jobs` |
| OpenClaw provider instabile in POC | M | B | Traffic share configurabile, rollback istantaneo via feature flag |
| Skills Claude conflict (warning del commento Instagram) | M | B | Selezione mirata 4 skills, niente bulk install |
| Schema migration multi-tenant rotta | B | A | Migrations atomiche + test su branch Supabase prima di main |

## 9. Open questions per le fasi successive

1. Quota giornaliera Heygen di default per nuovo brand?
2. Brevo: importare contatti esistenti automaticamente dal DB del prodotto o richiedere sync manuale per consenso GDPR?
3. Deep research: pubblicare summary in `research_findings` esistente o tabella separata?
4. Provider metrics: ritenzione 90gg sufficiente?
5. Per le 4 skills da committare: pinniamo versione `main` o un commit specifico per stabilità?

---

## Note operative sull'integrazione

Triage chiarisce che NON tutto va "nella root". Per ciascun blocco:

| Capability | Modalità | Dove vive |
|------------|----------|-----------|
| Video (Remotion) | Codice prodotto | `python/.../services/video/` + Node sidecar in monorepo |
| Video (Heygen) | API esterna | client in `services/video/heygen_client.py`, chiavi per-brand |
| Brevo | API esterna | `services/email/brevo_client.py`, mirror tabelle locali |
| Deep research | Dipendenza Python | `retrievers/deep_research.py` |
| OpenClaw | API esterna | `services/llm/providers/openclaw.py` |
| Skills Claude | Dev-time | `skills-lock.json` committato — zero impact runtime |

Niente nuovi satelliti tipo Postiz: l'unico satellite resta Postiz, perché è l'unico con UI propria e ciclo di rilascio indipendente che lo giustifica.

---

**Prossimo passo**: invocare `/prd-to-plan` su questo documento per generare il piano a fasi (vertical slices).
