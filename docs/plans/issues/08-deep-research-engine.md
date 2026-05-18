## Parent PRD

#{{PARENT}}

## What to build

Wrappare `local-deep-research` come retriever avanzato. Microservizio Docker + wrapper Python. Job asincroni, status pollabili, risultati strutturati.

Riferimento PRD §3.6.

## Acceptance criteria

- [ ] Container `local-deep-research` aggiunto a `docker-compose.yaml` (porta 5000 mappata, env config)
- [ ] `retrievers/deep_research.py` con `start_job(topic, depth, brand_id)` e `get_status(job_id)`
- [ ] Tabella `deep_research_jobs` con RLS
- [ ] Worker async per esecuzione job (usa pattern già esistente in `orchestrator/`)
- [ ] Endpoint `POST /api/research/deep`, `GET /status/:id`, `GET /results/:id`
- [ ] UI Research → "Deep research" tab: form (topic, depth slider 1-5), lista job con stato, view risultato con summary + sources
- [ ] Feature flag `deep_research_enabled` e cap `deep_research_depth_cap` (default 3) per controllare costi
- [ ] Test: job depth=2 completa in < 5min su topic noto, sources > 5

## Blocked by

- Blocked by #{{1}}

## User stories addressed

- US-R1 (deep research)
