## Parent PRD

#{{PARENT}}

## What to build

Refactor `services/llm/` per esporre registrar di provider LLM. OpenRouter resta default. Ogni chiamata emette telemetria comparabile in `llm_provider_metrics`.

Riferimento PRD §6 + §3.9 (preparazione per OpenClaw POC).

## Acceptance criteria

- [ ] Interfaccia `LLMProvider` (chat, complete, embedding se applicable) + registrar
- [ ] Provider esistente OpenRouter convertito al nuovo pattern, zero regressioni nei test esistenti
- [ ] Tabella `llm_provider_metrics` con RLS, indice su `(brand_id, ts)`
- [ ] Middleware emette riga per ogni chiamata: provider, model, prompt hash, latenza, token, costo stimato
- [ ] Endpoint `GET /api/llm/providers` lista provider attivi
- [ ] Endpoint `GET /api/llm/providers/metrics?brand_id&from&to` aggrega per provider/model
- [ ] Mini-card "Provider stats" in Settings → Integrations (read-only)
- [ ] Test integrazione: chiamata reale → riga in `llm_provider_metrics`

## Blocked by

- Blocked by #{{1}}

## User stories addressed

- US-P2 (provider extensibility)
- Prerequisito per US-P1 (gestito in #15)
