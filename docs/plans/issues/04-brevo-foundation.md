## Parent PRD

#{{PARENT}}

## What to build

Connessione Brevo per-brand, sync contatti base (CSV → Brevo + mirror locale).

Riferimento PRD §3.2.

## Acceptance criteria

- [ ] `services/email/brevo_client.py` con: auth, list/create contatti, list/create liste
- [ ] Chiave API Brevo per-brand in `brand_integrations` (cifrata)
- [ ] Tabella `brevo_contacts` (mirror locale) con RLS
- [ ] Endpoint `POST /api/email-marketing/contacts` (sync da CSV o JSON)
- [ ] Endpoint `GET /api/email-marketing/lists`
- [ ] UI Settings → Brand → "Audience": connessione Brevo (test connection), upload CSV, vista lista contatti
- [ ] Feature flag `email_marketing_enabled` rispettato (UI nascosta se OFF)
- [ ] Rate limit + retry esponenziale nel client
- [ ] Test integrazione contro sandbox Brevo

## Blocked by

- Blocked by #{{1}}

## User stories addressed

- US-E1 (sync contatti)
