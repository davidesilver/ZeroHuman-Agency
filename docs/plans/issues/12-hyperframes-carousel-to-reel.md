## Parent PRD

#{{PARENT}}

## What to build

Secondo template HyperFrames che monta un carousel approvato come reel video animato.

Riferimento PRD §3.3.

## Acceptance criteria

- [ ] Template "carousel-to-reel" in HyperFrames: legge slides di un carousel, anima transizioni con GSAP
- [ ] Bottone "Convert to reel" sulla view di un carousel pubblicato
- [ ] Endpoint usa `POST /api/video/render` con template="carousel-to-reel" e `source_carousel_id`
- [ ] Video risultante può essere inviato a Postiz per pubblicazione (riusa flow social esistente)
- [ ] Test e2e: carousel esistente → reel → pubblicato in Postiz dev

## Blocked by

- Blocked by #{{11}}

## User stories addressed

- US-V2 (carousel → reel)
