## Parent PRD

#{{PARENT}}

## What to build

Aggiunta provider OpenClaw dietro il registrar di #{{5}}. Traffic split configurabile per-brand. Confronto diretto possibile su prompt identici.

Riferimento PRD §3.9.

## Acceptance criteria

- [ ] `providers/openclaw.py` implementa interfaccia `LLMProvider`
- [ ] Chiave API OpenClaw vive in `brand_integrations`
- [ ] Feature flag `llm_provider_openclaw_share` (0..1)
- [ ] Routing layer: dato un brand, split del traffico secondo share
- [ ] UI Settings → Provider hub: slider share, indicatore credito residuo OpenClaw
- [ ] Dashboard "Provider compare": cost-per-1k-tokens e latenza media per OpenRouter vs OpenClaw, stesso modello
- [ ] Smoke test: con share=1.0, 100% chiamate vanno a OpenClaw
- [ ] Report finale con ≥ 1000 request comparate, decisione raccomandata documentata

## Blocked by

- Blocked by #{{5}}

## User stories addressed

- US-P1 (A/B economico provider)
