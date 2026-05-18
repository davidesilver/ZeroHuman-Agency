# PRD — AI Capability Stack Expansion (v2)

**Versione:** 0.2 (merged)
**Data:** 2026-05-15
**Approccio:** plug-and-play first, custom solo se necessario

Full PRD: [docs/plans/2026-05-15-capability-expansion-prd-v2.md](../2026-05-15-capability-expansion-prd-v2.md)
Triage: [docs/plans/2026-05-15-integration-candidates-triage.md](../2026-05-15-integration-candidates-triage.md)

---

## Problema

ZeroHuman Agency è operativa con Postiz, Next.js 16, Python/FastAPI, Supabase. Pipeline testo + immagini coperta. Mancano cinque capability di prodotto e due gap operativi.

**Gap prodotto:**
1. Video di qualità dall'idea al file finale, senza intervento manuale
2. Ricerca trend/competitor/brief automatizzata e profonda
3. Distribuzione email marketing & automation (oggi solo transazionale via Resend)
4. Orchestrazione di agenti specializzati per ruolo
5. Animazione asset web e video con standard pro

**Gap operativi:**
6. Lock-in implicito su OpenRouter senza confronto economico misurato
7. Skills Claude dev-time minime

## Obiettivo

Aggiungere capability stack modulare combinando componenti open-source, API in abbonamento e skill Claude. Per ogni componente: modalità d'integrazione esplicita (Root / Esterno / Codice / Skill Claude).

## Stack priorità

| Fase | Componente | Modalità |
|------|-----------|----------|
| **P0** | agency-agents (subset 7 categorie) | Root |
| **P0** | Brevo API (contatti + campaign) | Esterno + Codice |
| **P0** | Foundation: feature_flags + brand_integrations | Root |
| **P0** | Dev skills bundle (superpowers/claude-mem/repomix/taste-skill) | Skill Claude |
| **P1** | Provider abstraction + telemetria LLM | Codice |
| **P1** | HyperFrames + GSAP (motion graphics) | Codice + Skill |
| **P1** | Heygen talking-head | Esterno |
| **P1** | local-deep-research (Docker) | Esterno |
| **P1** | Scrapling (competitor monitoring) | Codice |
| **P1** | Brevo automations | Codice |
| **P2** | Video templates customization | Codice |
| **P2** | ViMax full pipeline | Esterno |
| **P2** | OpenClaw POC + A/B | Esterno |
| **P3** | WeClone | Esterno (on-demand) |

## Decisioni architetturali durabili

- Routes: `api/video/`, `api/email-marketing/`, `api/research/deep`, `api/llm/providers`, `api/agents/`
- Schema Supabase: `videos`, `video_templates`, `brevo_contacts`, `brevo_campaigns`, `email_automations`, `deep_research_jobs`, `llm_provider_metrics`, `feature_flags`, `brand_integrations` — tutte con RLS per `brand_id`
- Multi-tenancy: chiavi API per-brand cifrate in `brand_integrations`
- Feature flags per-brand
- Video boundary: HyperFrames in-process Node sidecar v1, API compatibile con migrazione Lambda v2
- Brevo affianca Resend, non sostituisce
- Skills: `skills-lock.json` committato per dev-time, `/agents` e `/skills` cartelle root per prodotto

## Metriche di successo (90gg)

- Tempo brief → post pubblicato: **< 15 min**
- Ore umane per campagna mensile: **< 2h**
- Costo per contenuto: **riduzione > 60%**
- Qualità video output: **approvazione cliente senza revisioni > 70%**

## Out of scope

AutoHedge, Open-Generative-AI, WeClone v1, context-mode come dipendenza, sostituzione Resend, Remotion v1, ViMax v1.

---

Vedi il file completo per: 12 componenti dettagliati, architettura target, rischi, domande aperte.

**Issue figli**: tracciati nei commenti sotto man mano che vengono creati.
