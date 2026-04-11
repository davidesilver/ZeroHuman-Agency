# Piano di Implementazione

> Roadmap dettagliata per costruire il Content Engine "Empty Box" da zero.
> Prerequisito: leggere [ARCHITECTURE.md](architecture/ARCHITECTURE.md) e [TECH_STACK.md](architecture/TECH_STACK.md).

---

## Prerequisiti

Prima di iniziare:
- [ ] Account Supabase (progetto creato)
- [ ] Account OpenRouter (API key)
- [ ] Account Serper (API key)
- [ ] Account Firecrawl (API key)
- [ ] Repository Git (GitHub o GitLab)
- [ ] VPS Hostinger x2 (staging + production) o equivalente
- [ ] Dominio registrato
- [ ] Account Vercel (deploy frontend)
- [ ] Claude Code installato e configurato

---

## Fase 0 — Fondamenta (Settimana 1)

> Obiettivo: infrastruttura di base funzionante, database pronto, prima pagina visibile.

### 0.1 Setup Progetto
- [ ] Inizializzare repo Git
- [ ] Creare progetto Next.js 15 con App Router
- [ ] Installare dipendenze: `shadcn/ui`, `tailwindcss`, `@supabase/supabase-js`, `recharts`
- [ ] Configurare Tailwind con design tokens da [DESIGN_SYSTEM.md](design/DESIGN_SYSTEM.md)
- [ ] Creare struttura directory secondo [ARCHITECTURE.md](architecture/ARCHITECTURE.md)
- [ ] Setup `.env.local` con tutte le variabili (vedi [BRAND_CONFIG.md](config/BRAND_CONFIG.md))

### 0.2 Database
- [ ] Eseguire migration [001_initial_schema.sql](database/001_initial_schema.sql) su Supabase
- [ ] Abilitare RLS su tutte le tabelle
- [ ] Creare primo brand nel database (record in `brands`)
- [ ] Creare utente owner associato al brand
- [ ] Testare RLS: verificare che l'utente veda solo i dati del suo brand
- [ ] Generare tipi TypeScript: `supabase gen types typescript`

### 0.3 Autenticazione
- [ ] Configurare Supabase Auth (email + password)
- [ ] Creare pagina login
- [ ] Creare middleware Next.js per protezione route
- [ ] Testare login/logout/registrazione

### 0.4 Layout Dashboard
- [ ] Implementare sidebar con navigazione (tutti i menu)
- [ ] Implementare staging bar
- [ ] Implementare URL bar
- [ ] Implementare API spend row
- [ ] Creare pagina Dashboard (Home) con dati placeholder
- [ ] Verificare responsive base

### Deliverable Fase 0
- Dashboard accessibile dopo login con sidebar funzionante
- Database con schema completo e RLS attivo
- Brand configurato nel database

---

## Fase 1 — MVP Research (Settimane 2-3)

> Obiettivo: pipeline di ricerca funzionante che trova, valuta e presenta contenuti.

### 1.1 Research Pipeline (Python Backend)
- [ ] Setup progetto Python 3.12+ con poetry/uv
- [ ] Implementare `FeedParser` retriever (RSS)
  - Input: lista fonti RSS da brand config
  - Output: research_items normalizzati
- [ ] Implementare `Serper` retriever (search)
  - Query generate da topics e subtopics
  - Deduplicazione per URL
- [ ] Implementare `YouTube` retriever
  - Cerca nei canali configurati
- [ ] Implementare orchestratore che esegue tutti i retriever in parallelo
- [ ] Salvare risultati in tabella `research_items`
- [ ] Creare endpoint API: `POST /api/research/trigger`
- [ ] Creare endpoint API: `GET /api/research/items`
- [ ] Creare cron job (n8n o pg_cron) per esecuzione alle 07:00

### 1.2 Scoring Engine
- [ ] Implementare scoring agent con Claude Sonnet via OpenRouter
- [ ] Prompt di scoring con parametri da brand config (vedi [AGENTS.md](agents/AGENTS.md))
- [ ] Calcolo `final_score` pesato
- [ ] Salvare scores in tabella `scores`
- [ ] Auto-approve items con score > soglia
- [ ] Auto-reject items con score < soglia
- [ ] Endpoint: `POST /api/scoring/run`

### 1.3 Pagina Ricerca (Frontend)
- [ ] Implementare pagina `/ricerca` secondo [SCREENS.md](design/SCREENS.md)
- [ ] KPI tabs con conteggi per status
- [ ] Volume Report con barre colorate
- [ ] Tabella research items con filtri
- [ ] Sub-tabs TUTTE | SISTEMA | TOOL | MOSSA
- [ ] Bottoni azione: Approva, Top Pick, Archivia, Rifiuta
- [ ] Bottone "Lancia Ricerca" che triggera pipeline
- [ ] Real-time update via Supabase Realtime

### 1.4 Semantic Deduplication
- [ ] Abilitare pgvector su Supabase
- [ ] Generare embedding per ogni research item (modello: text-embedding-3-small)
- [ ] Implementare MMR rerank per deduplicazione semantica
- [ ] Filtrare duplicati prima dello scoring

### Deliverable Fase 1
- Pipeline ricerca che trova 50-200 contenuti da fonti configurate
- Scoring automatico su 6 parametri
- Dashboard Ricerca funzionante con approvazione manuale
- Deduplicazione semantica attiva

---

## Fase 2 — Content Generation (Settimane 4-5)

> Obiettivo: generare contenuti multi-formato da items approvati, con review GOD system.

### 2.1 Writer Agent
- [ ] Implementare writer agent con Claude Opus via OpenRouter
- [ ] Generazione per formato: post LinkedIn, thread X, carousel text, blog, newsletter section
- [ ] Prompt con tone of voice da brand config
- [ ] Salvare in `content_drafts` con reference a `research_item_id`
- [ ] Endpoint: `POST /api/content/generate`

### 2.2 Editor Agent
- [ ] Implementare editor agent (Claude Opus)
- [ ] Review e miglioramento bozza
- [ ] Aggiornamento `content_drafts` con nuova versione

### 2.3 Adapter Agent
- [ ] Implementare adapter (Claude Sonnet)
- [ ] Adattamento per piattaforma (char limit, hashtag, formato)
- [ ] Generazione versioni per ogni piattaforma target

### 2.4 GOD System
- [ ] Implementare god_advocate (Claude Sonnet) — critica
- [ ] Implementare god_factcheck (Claude Sonnet + Serper) — verifica fatti
- [ ] Implementare god_creative (Claude Sonnet) — angoli creativi
- [ ] Implementare god_synthesis (Claude Opus) — sintesi finale
- [ ] Pipeline sequenziale: advocate → factcheck → creative → synthesis
- [ ] Salvare risultati in `god_mode_reviews`
- [ ] Endpoint: `POST /api/content/drafts/:id/god-mode`

### 2.5 Content Hub (Frontend)
- [ ] Implementare pagina `/content-hub` secondo [SCREENS.md](design/SCREENS.md)
- [ ] Card contenuto con preview multi-piattaforma
- [ ] Workflow: DA APPROVARE → APPROVATI → SCHEDULATI → PUBBLICATI
- [ ] Bottone GOD Mode per attivare review
- [ ] Preview contenuto espanso con tutte le versioni piattaforma

### 2.6 Newsletter Composer
- [ ] Implementare selezione candidati per 3 slot (SISTEMA, STRUMENTO, MOSSA)
- [ ] 6 candidati per slot ordinati per score
- [ ] Generazione HTML newsletter con template
- [ ] Preview rendering
- [ ] Salvare in tabella `newsletters`
- [ ] Pagina `/newsletter` con tabella + generazione

### Deliverable Fase 2
- Contenuti generati automaticamente da items approvati
- GOD system funzionante con review multi-agente
- Content Hub con workflow approvazione
- Newsletter composer con 3 slot e preview

---

## Fase 3 — Distribution (Settimane 6-7)

> Obiettivo: pubblicare contenuti sui canali, inviare newsletter, tracciare metriche.

### 3.1 Newsletter Delivery
- [ ] Integrare Resend API per invio email
- [ ] Template HTML responsive per newsletter
- [ ] Workflow: genera → preview → approva → schedula → invia
- [ ] Tracking open rate e CTR (Resend webhooks)
- [ ] Salvare metriche in tabella `newsletters`

### 3.2 Social Publishing
- [ ] Integrare Postiz API (o LinkedIn API diretta per MVP)
- [ ] Pubblicazione post LinkedIn
- [ ] Queue system per scheduling multi-piattaforma
- [ ] Retry logic per fallimenti
- [ ] Salvare URL pubblicato in `content_drafts.published_url`

### 3.3 Calendario Editoriale (Frontend)
- [ ] Implementare pagina `/calendario` con vista mensile
- [ ] Drag & drop per spostare eventi (opzionale)
- [ ] Legenda colori per tipo contenuto
- [ ] Pannello "Prossimi eventi"
- [ ] KPI: programmati, in produzione, approvati

### 3.4 Metriche (Frontend)
- [ ] Implementare pagina `/metriche`
- [ ] Grafici: Open Rate Trend, Crescita Iscritti
- [ ] Heatmap orari ottimali
- [ ] Tabella ultimi invii
- [ ] Tabs: NEWSLETTER | SOCIAL | WEB | REVENUE

### 3.5 Analytics Feedback Loop
- [ ] Raccogliere metriche social (LinkedIn API)
- [ ] Salvare in `social_metrics`
- [ ] Integrare nel scoring: items che hanno generato engagement alto → bonus score
- [ ] Aggiornare scoring algorithm con feedback loop

### Deliverable Fase 3
- Newsletter inviate automaticamente via Resend
- Post pubblicati su LinkedIn (almeno)
- Calendario editoriale funzionante
- Metriche base con grafici
- Feedback loop attivo

---

## Fase 4 — Polish (Settimane 8-9)

> Obiettivo: completare tutte le schermate, ottimizzare, preparare per multi-brand.

### 4.1 Writing Lab
- [ ] Implementare sessioni A/B con 50 round
- [ ] UI side-by-side con votazione
- [ ] Tracking hook types e win rates
- [ ] GOD Mode inline per ogni versione

### 4.2 Blog Manager
- [ ] Pagina `/blog` con tabella articoli
- [ ] SEO score breakdown per articolo
- [ ] Integrazione geo-seo per keyword research
- [ ] Export blog post come MDX per Next.js blog

### 4.3 Revenue & Pipeline Health
- [ ] Pagina `/revenue` con KPI, deal, forecast
- [ ] Pipeline Health con status agenti
- [ ] Error tracking base con log

### 4.4 Costi API
- [ ] Pagina `/costi-api` con breakdown per agente
- [ ] Alert soglia budget
- [ ] Grafici trend costi giornalieri

### 4.5 Multi-Brand
- [ ] Testare con secondo brand
- [ ] Verificare RLS separazione dati
- [ ] Brand switcher nel frontend
- [ ] Validazione brand config all'avvio

### 4.6 Performance & Security
- [ ] Audit sicurezza: OWASP top 10
- [ ] GDPR: double opt-in newsletter, privacy policy link
- [ ] Rate limiting API
- [ ] Caching per query pesanti
- [ ] Error tracking con Sentry

### Deliverable Fase 4
- Tutte e 10 le schermate funzionanti
- Multi-brand funzionante
- Writing Lab con A/B testing
- Costi e revenue tracking
- Sicurezza base implementata

---

## Fase 5 — Scala (Settimane 10+)

> Obiettivo: espandere, automatizzare, monetizzare.

### Futuro
- [ ] Carousel generation con Remotion
- [ ] Video script + ElevenLabs voice
- [ ] TikTok / Instagram Reels automation
- [ ] Sponsorship automation (ricerca sponsor, pitch, contratto)
- [ ] Piattaforme social aggiuntive (Facebook, TikTok, Pinterest)
- [ ] AutoResearch notturno (Karpathy-inspired)
- [ ] Mobile responsive dashboard
- [ ] CI/CD con GitHub Actions
- [ ] Backup automatico su R2/S3

---

## Metriche di Successo per Fase

| Fase | Metrica | Target |
|------|---------|--------|
| 0 | Dashboard accessibile con login | Login funzionante |
| 1 | Items ricercati e scored | 50+ items/giorno |
| 2 | Contenuti generati e approvati | 10+ drafts/giorno |
| 3 | Newsletter inviata | 1/settimana con tracking |
| 4 | Tutte le schermate | 10/10 funzionanti |
| 5 | Multi-brand | 2+ brand attivi |

---

## Stima Effort

| Fase | Settimane | Dipendenze |
|------|-----------|------------|
| 0 - Fondamenta | 1 | Nessuna |
| 1 - Research | 2 | Fase 0 |
| 2 - Content Generation | 2 | Fase 1 |
| 3 - Distribution | 2 | Fase 2 |
| 4 - Polish | 2 | Fase 3 |
| 5 - Scala | Ongoing | Fase 4 |
| **Totale MVP** | **~9 settimane** | |

---

## Rischi e Mitigazioni

| Rischio | Probabilita' | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| API social bloccano posting | Alta | Alto | Iniziare con LinkedIn API (piu' permissiva) |
| Costi API superiori al previsto | Media | Medio | Budget alert + fallback su modelli piu' economici |
| Qualita' contenuti insufficiente | Media | Alto | GOD system + human review obbligatorio |
| Complessita' multi-brand | Bassa | Medio | RLS Supabase gestisce nativamente |
| VPS instabilita' | Bassa | Alto | Deploy frontend su Vercel (gestito), backend su VPS con monitoring |
