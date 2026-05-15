## Parent PRD

#{{PARENT}}

## What to build

Setup foundation cross-cutting per tutte le capability successive:

- Tabella `feature_flags` per-brand con migration + RLS + helper Python/TS per check
- Tabella `brand_integrations` cifrata (chiavi API per-brand) + helper di accesso con cache + invalidazione
- Modulo `services/secrets.py` per encrypt/decrypt (Supabase Vault o `pgcrypto`)
- Pattern documentato in `docs/ARCHITECTURE.md`: come aggiungere un nuovo flag, come aggiungere una nuova integrazione per-brand

Riferimento PRD §6 "Decisioni architetturali durabili" → Multi-tenancy / Feature flags.

## Acceptance criteria

- [ ] Migration `feature_flags` applicata, RLS testata
- [ ] Migration `brand_integrations` applicata, RLS testata, encryption funzionante
- [ ] Helper Python `get_feature_flag(brand_id, key)` e TS equivalente in `src/lib/`
- [ ] Helper `get_brand_secret(brand_id, key)` con cache in-memory e invalidazione
- [ ] Test unit: encrypt/decrypt round-trip, RLS blocca cross-brand
- [ ] Sezione "Feature flags & brand secrets" aggiunta in `docs/ARCHITECTURE.md`

## Blocked by

None - can start immediately

## User stories addressed

Prerequisito tecnico — abilita tutte le user stories del PRD (US-V*, US-E*, US-R*, US-P*).
