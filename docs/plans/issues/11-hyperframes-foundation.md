## Parent PRD

#{{PARENT}}

## What to build

Pipeline base per rendering video programmatico via HyperFrames (Apache 2.0). 1 template hard-coded: "weekly recap" da analytics di un brand.

Riferimento PRD §3.3.

## Acceptance criteria

- [ ] `@heygen/hyperframes` aggiunta a Next.js dependencies
- [ ] Node sidecar HyperFrames in `python/.../services/video/hyperframes_renderer/` invocato via subprocess dal backend Python
- [ ] Tabella `videos` e `video_templates` con RLS
- [ ] Template "weekly-recap" definito con props_schema (brand_id, week_start, metrics)
- [ ] GSAP integrato per transizioni (skill `npx skills add heygen-com/hyperframes`)
- [ ] Endpoint `POST /api/video/render` (template + props → job async)
- [ ] Endpoint `GET /api/video/status/:id`, `GET /api/video/list`
- [ ] UI "Videos" tab nella dashboard con lista video e stati
- [ ] Storage video su Supabase Storage, URL firmato per download
- [ ] Feature flag `video_enabled`
- [ ] Test: render del weekly-recap di un brand → MP4 valido < 60s

## Blocked by

- Blocked by #{{1}}

## User stories addressed

- US-V1 (recap programmatico)
- US-V5 (stato render visibile)
