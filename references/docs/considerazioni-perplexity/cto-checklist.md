# CTO Checklist — Content Engine

*Basata su lettura completa del codebase GitLab + NotebookLM*

***

## 🔴 P0 — Bloccante per andare live (sistema non funziona senza)

- [ ] **Social Publisher reale** — `social_publisher.py` segna solo `status: published` nel DB ma non posta da nessuna parte. Integrare almeno LinkedIn API e/o Buffer/Zapier webhook per il primo brand
- [ ] **Newsletter delivery reale** — `newsletter_delivery.py` esiste ma senza integrazione ESP (Brevo/Beehiiv/Mailchimp). Senza questo la newsletter non parte
- [ ] **Cron trigger per `daily_research_pipeline()`** — lo scheduler è pronto ma non viene mai chiamato. Aggiungere cron job su Railway/Render (es. `0 7 * * *`)
- [ ] **Error handling nel GOD System** — se uno degli agenti fallisce, il draft si blocca con status `god_mode` per sempre. Aggiungere try/except per ogni step + status `god_mode_failed`

***

## 🟠 P1 — Importante per qualità del prodotto (funziona male senza)

- [ ] **Parallelizzare i primi 3 agenti GOD Mode** — Advocate, FactCheck e Creative sono indipendenti, possono girare in `asyncio.gather()`. Il Synthesizer aspetta tutti e tre. Risparmio stimato: ~60% del tempo GOD Mode
- [ ] **Semantic dedup con pgvector** — il codice ha il TODO esplicito: `"Semantic dedup (pgvector) will be done post-insert via SQL"`. Con più brand e volumi alti, duplicati semantici (stesso articolo, fonti diverse) passano il filtro URL-based
- [ ] **Feedback loop su dati reali** — `feedback_bonus` è aggiornato internamente ma senza dati di engagement reali (LinkedIn impressions, open rate newsletter). Integrare almeno una fonte esterna (LinkedIn Analytics API o UTM tracking via Supabase)
- [ ] **Brand Voice Document strutturato** — `writer.py` legge `tone_of_voice.rules` e `founder_principles` dal DB, ma non c'è un onboarding guidato per compilarli. Aggiungere UI per brand setup con esempi e preview output
- [ ] **Versioning immutabile dei draft** — il GOD System sovrascrive il body del draft. Spostare la versione originale in una tabella `content_draft_versions` prima di ogni modifica

***

## 🟡 P2 — Nice to have per scalabilità e UX

- [ ] **Separare repo frontend/backend** (o almeno due Dockerfile distinti con docker-compose) — attualmente Next.js in root e Python in `/python/` complicano CI/CD
- [ ] **Rate limiting sulle API routes** — nessun limite sulle chiamate a `/research/trigger`, `/scoring/run`, `/god-mode` — un bug nel frontend può bruciare centinaia di dollari in LLM calls
- [ ] **Dashboard metriche reali** — il frontend ha `(dashboard)` folder ma senza dati di engagement real-time è solo un contatore di status
- [ ] **Webhook Supabase per notifiche realtime** — quando un draft diventa `approved` notificare via Telegram/Slack al content manager invece di polling
- [ ] **Test suite** — zero test nel repo. Almeno unit test su `_compute_final_score()`, `_deduplicate()`, e `_parse_json()` che sono le funzioni più critiche in produzione
