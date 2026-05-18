## Parent PRD

#{{PARENT}}

## What to build

Aggiunta committata di 4 skills Claude dev-time in `skills-lock.json`, hash-pinned come `supabase-postgres-best-practices` oggi:

- `obra/superpowers`
- `thedotmack/claude-mem`
- `yamadashy/repomix`
- `leonxlnx/taste-skill`

Più 2-3 righe per ognuna in `docs/ONBOARDING.md` su cosa fa e quando invocarla.

Riferimento PRD §3.8.

## Acceptance criteria

- [ ] `skills-lock.json` aggiornato con 4 skills, hash pinnati
- [ ] Per ogni skill: 2-3 righe in `docs/ONBOARDING.md` su cosa fa e quando invocarla
- [ ] Verifica su clone fresco: tutte e 4 le skills disponibili senza setup manuale
- [ ] Smoke test che le 4 non vadano in conflict reciproco (eseguire una task semplice che potrebbe attivarne più di una)

## Blocked by

None - can start immediately

## User stories addressed

- US-S1 (developer experience: skills condivise team)
