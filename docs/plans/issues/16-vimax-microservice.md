## Parent PRD

#{{PARENT}}

## What to build

**[HITL]** Microservizio Docker ViMax (pipeline multi-agente video: Director + Screenwriter + Producer + Generator). Si attiva quando Heygen talking-head + HyperFrames motion graphics non bastano per il caso d'uso.

**Gate HITL**: prima dell'implementazione, decisione su budget mensile per API video generation (Veo / Kling / altri backend ViMax richiede). Vedi PRD §9 domanda aperta #2.

Riferimento PRD §3.5.

## Acceptance criteria

- [ ] Decisione budget API video generation approvata e documentata in PRD update
- [ ] Backend video AI scelto (Veo / Kling / Pixelle / Higgsfield) documentato
- [ ] Container ViMax in `docker-compose.yaml` con env config
- [ ] `services/video/vimax_client.py` per orchestrazione job
- [ ] Tabella `videos` estesa con `type='vimax'` e `pipeline_metadata` jsonb
- [ ] Endpoint `POST /api/video/generate` con kind="full-pipeline", input=brief
- [ ] UI Settings → Brand → Video → "Full pipeline" sezione: budget cap, backend default
- [ ] Quota per-brand + alert Telegram come per Heygen
- [ ] Test e2e: brief breve → script → storyboard → clip → MP4 finale

## Blocked by

- Blocked by #{{11}}
- Blocked by #{{13}}

## User stories addressed

Gap PRD #1 (video di qualità dall'idea al file, full pipeline).
