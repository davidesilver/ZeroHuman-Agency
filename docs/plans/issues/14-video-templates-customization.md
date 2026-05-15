## Parent PRD

#{{PARENT}}

## What to build

Permettere agli agency-owner di definire template video per-brand (loghi, colori, font, asset, props custom).

Riferimento PRD §6 + US-V4.

## Acceptance criteria

- [ ] UI Settings → Brand → Video templates: lista template attivi, "New template"
- [ ] Form template: nome, kind (recap | carousel-reel | custom), props_schema editor, upload asset (logo, brand colors)
- [ ] Asset salvati in Supabase Storage per-brand
- [ ] Template `weekly-recap` e `carousel-to-reel` leggono asset/colori brand quando presenti
- [ ] Anteprima 1° frame del template prima del render (snapshot)
- [ ] Test: brand X definisce template "client-recap" con suoi colori → render usa quei colori

## Blocked by

- Blocked by #{{11}}

## User stories addressed

- US-V4 (template per-brand customization)
