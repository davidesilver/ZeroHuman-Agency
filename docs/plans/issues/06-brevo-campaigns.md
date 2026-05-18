## Parent PRD

#{{PARENT}}

## What to build

Creare campagne Brevo da draft Content Engine esistenti. Mirror metriche aperture/click in dashboard.

Riferimento PRD §3.2.

## Acceptance criteria

- [ ] Tabella `brevo_campaigns` con RLS, FK opzionale al draft di origine
- [ ] Endpoint `POST /api/email-marketing/campaigns` (crea + schedule)
- [ ] Bottone "Send as Brevo campaign" in writing-lab per draft di tipo newsletter/email
- [ ] Webhook handler per metriche Brevo → update `brevo_campaigns.metrics`
- [ ] Card "Email performance" in dashboard analytics con open/click rate per campagna
- [ ] Test e2e: draft → campagna → invio test → metriche visualizzate

## Blocked by

- Blocked by #{{4}}

## User stories addressed

- US-E2 (campaign da draft)
- US-E4 (metriche email)
