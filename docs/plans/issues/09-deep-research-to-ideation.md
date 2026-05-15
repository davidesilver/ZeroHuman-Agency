## Parent PRD

#{{PARENT}}

## What to build

Risultato deep research diventa input per il flow ideation esistente.

Riferimento PRD §3.6.

## Acceptance criteria

- [ ] Bottone "Generate content ideas" sulla view risultato deep research
- [ ] Endpoint che prende `deep_research_job_id` e crea N ideation entries collegati
- [ ] FK `ideation.source_research_id` aggiunta, nullable
- [ ] UI ideation mostra origine (manual / research / deep_research) come badge
- [ ] Test: completare un job → click → 5 idee popolate con riferimento al job

## Blocked by

- Blocked by #{{8}}

## User stories addressed

- US-R2 (research → ideation handoff)
