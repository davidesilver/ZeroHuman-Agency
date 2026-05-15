## Parent PRD

#{{PARENT}}

## What to build

Automation multi-step (welcome / nurture / win-back) collegate a trigger Brevo. v1 template-based, non drag-drop.

Riferimento PRD §3.2.

## Acceptance criteria

- [ ] Tabella `email_automations` con RLS
- [ ] 3 template predefiniti: welcome 3-step, nurture 5-step, win-back 2-step
- [ ] Endpoint `POST /api/email-marketing/automations` (create da template + override copy)
- [ ] UI Settings → Brand → Automations: lista, attiva/disattiva, edit copy step
- [ ] Mapping automation → Brevo workflow (se API espone workflow; altrimenti orchestrare via campagne + condizioni)
- [ ] Test: attivare welcome series → primo step inviato al contatto di test

## Blocked by

- Blocked by #{{6}}

## User stories addressed

- US-E3 (automations)
