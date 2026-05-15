## Parent PRD

#{{PARENT}}

## What to build

**[HITL]** Installazione subset di `msitarzewski/agency-agents` (142+ agenti) nella cartella `/agents` del repo. Richiede decisione umana sul subset preciso da committare (vedi PRD §3.1).

Subset proposto come default (modificabile in review):
- `marketing-content-creator.md`
- `marketing-tiktok-strategist.md`
- `marketing-social-media-strategist.md`
- `paid-media-ppc-strategist.md`
- `design-brand-guardian.md`
- `design-image-prompt-engineer.md`
- categoria `strategy/` (analytics, trend research)

## Acceptance criteria

- [ ] Submodule `git submodule add https://github.com/msitarzewski/agency-agents .vendor/agency-agents` pinnato a commit
- [ ] Script `scripts/install-agents.sh` che copia categorie selezionate in `/agents`
- [ ] Subset di agenti approvato e committato in `/agents`
- [ ] Endpoint `GET /api/agents/` lista agents disponibili (read da filesystem)
- [ ] Endpoint `POST /api/agents/:slug/invoke` proxy verso Claude/OpenRouter con system prompt = contenuto dell'agente
- [ ] UI Settings → Agents tab: lista agenti, click per dettagli
- [ ] Doc in `docs/AGENTS.md`: come aggiungere/aggiornare un agente

## Blocked by

None - can start immediately (subset selection è la HITL gate)

## User stories addressed

Gap PRD #4 (orchestrazione agenti specializzati).
