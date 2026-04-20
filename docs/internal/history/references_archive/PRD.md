# Product Requirements Document (PRD)
# Content Engine "Empty Box"

> Versione: 1.0
> Data: 2026-04-11
> Autore: Davide Silvestri + Claude

---

## 1. Panoramica del Prodotto

### Il Problema

Creare contenuti di qualita' su piu' piattaforme (newsletter, LinkedIn, Instagram, X, blog, TikTok) richiede un team di 5-6 persone (content manager, copywriter, social media manager, researcher, designer, newsletter editor) con un costo di €9.000-14.000/mese. Per un imprenditore che gestisce piu' brand, questi costi si moltiplicano e il collo di bottiglia resta la produzione.

Il risultato: o si pubblica poco e si perde visibilita', oppure si pubblica contenuto mediocre e si perde credibilita'.

### La Soluzione

**Empty Box** e' un sistema autonomo di content automation che opera al **95% senza intervento umano**. Il sistema:

1. **Ricerca** contenuti rilevanti da 500+ fonti internazionali ogni giorno
2. **Valuta** ogni contenuto su 6 parametri (applicabilita', credibilita', allineamento, trend, rilevanza mercato, feedback storico)
3. **Genera automaticamente** contenuti multi-formato (post LinkedIn, thread X, carousel Instagram, blog, newsletter)
4. **Rivede** ogni contenuto con un sistema multi-agente (GOD System: critico, fact-checker, creativo, sintetizzatore)
5. **Approva automaticamente** i contenuti con score alto; presenta all'umano solo i casi dubbi
6. **Pubblica** su tutte le piattaforme secondo un calendario ottimizzato
7. **Impara** dai risultati: engagement social e feedback umano migliorano l'algoritmo nel tempo

L'umano **non deve fare niente** nella routine quotidiana. Il sistema opera autonomamente. L'umano interviene solo per:
- Approvare/rifiutare contenuti con score medio (zona grigia)
- Scegliere i contenuti newsletter settimanale (tra 6 candidati pre-selezionati per slot)
- Dare feedback binario occasionale (like/dislike) nel Writing Lab per affinare lo stile
- Decisioni strategiche: cambiare topic, aggiungere fonti, modificare tono

### Target

**Fase 1 — Uso interno:** Davide Silvestri per i propri brand (Vest, Silvestri Pallets, Silv Energia).

**Fase 2 — SaaS:** Creator, imprenditori digitali, agenzie, e media company che vogliono automatizzare la produzione contenuti mantenendo qualita' e voce personale.

### Riferimenti Prodotto
- **Marco Montemagno / Spiegamelo** — Reference architetturale principale. Sistema in produzione con 170k subscriber, 30+ contenuti/giorno, costi ~$500/mese
- **Postiz** — Open-source social scheduling con AI agent API
- **Pi.ai (Inflection)** — Reference per UX conversazionale e approccio AI-first
- **gstack (Y Combinator)** — AutoPlan mode per Claude Code, workflow di sviluppo
- **Typefully / Buffer** — UX di scheduling e preview social

---

## 2. Profili Utente

### 2.1 Owner (Founder / Creator)

**Chi e':** L'imprenditore che gestisce il brand. Decide la strategia, il tono di voce, i topic. Non vuole eseguire, vuole supervisionare.

**Bisogni:**
- Vedere un riepilogo giornaliero: "il sistema ha funzionato, ecco cosa ha prodotto"
- Approvare/rifiutare solo i contenuti in zona grigia (score 4-8)
- Comporre la newsletter settimanale in 5 minuti (scelta tra candidati pre-scorati)
- Monitorare costi API e ROI
- Dare feedback occasionale per migliorare la qualita'

**Frequenza d'uso:** 10-15 minuti/giorno, 30 minuti per newsletter settimanale

**Azione tipica giornaliera:**
1. Apre dashboard → vede "17 contenuti approvati automaticamente, 3 da approvare"
2. Rivede i 3 dubbi → approva 2, rifiuta 1
3. Chiude. Fine.

### 2.2 Editor (Collaboratore)

**Chi e':** Membro del team che aiuta nella supervisione contenuti. Ha accesso alla dashboard ma non puo' modificare la configurazione del brand.

**Bisogni:**
- Rivedere e approvare contenuti
- Modificare bozze prima della pubblicazione
- Vedere metriche e performance

**Frequenza d'uso:** 20-30 minuti/giorno

### 2.3 Viewer (Stakeholder / Cliente)

**Chi e':** Persona che ha accesso in sola lettura. Puo' essere un investitore, un partner, o un cliente (in modalita' SaaS futura).

**Bisogni:**
- Vedere metriche e performance
- Consultare il calendario editoriale
- Scaricare report

**Frequenza d'uso:** 1-2 volte/settimana

### 2.4 Sistema (AI Agents)

**Chi e':** L'insieme degli agenti AI che operano autonomamente 24/7.

**Bisogni:**
- Eseguire pipeline senza interruzioni
- Accedere a tutte le API (OpenRouter, Serper, Firecrawl, social)
- Loggare ogni azione per audit trail
- Rispettare budget giornaliero
- Auto-approvare contenuti con score > soglia configurata

**Frequenza d'uso:** Continuo, 24/7

---

## 3. Funzionalita' Core

### 3.1 MUST-HAVE (MVP — Lancio)

#### F1. Research Pipeline Automatica
- Scansione giornaliera (cron 07:00) di 500+ fonti: RSS, Serper search, YouTube API
- 5 retriever types: semantic, practitioner, trusted_source, keyword, trend
- Funnel progressivo: Discovery → Normalized → Screened → Scored → Final Pool
- Deduplicazione semantica (pgvector + MMR rerank)
- Risultato: ~20-50 contenuti rilevanti/giorno nel pool finale

#### F2. Scoring Engine AI
- Valutazione automatica su 6 parametri pesati (configurabili per brand):
  - Applicabilita'/Concretezza (quanto e' utilizzabile subito)
  - Credibilita' (track record dell'autore/fonte)
  - Allineamento (coerenza con principi del founder)
  - Predizione Trend (rilevanza nei prossimi 6 mesi)
  - Rilevanza Mercato Target (applicabilita' al mercato italiano)
  - Bonus Feedback (storico like/dislike del founder)
- Auto-approvazione: score > 8.0 → approvato automaticamente
- Auto-rifiuto: score < 3.0 → rifiutato automaticamente
- Zona grigia (3.0-8.0) → presentato all'umano

#### F3. Content Generation Multi-Formato
- **Writer Agent** (Claude Opus): genera contenuto principale dal research item
- **Editor Agent** (Claude Opus): rivede e migliora
- **Adapter Agent** (Claude Sonnet): adatta per ogni piattaforma
- Formati supportati: post LinkedIn, thread X, post Facebook, caption Instagram, script TikTok, articolo blog, sezione newsletter
- Ogni contenuto rispetta il tone of voice configurato nel brand

#### F4. GOD System (Multi-Agent Quality Review)
- Pipeline sequenziale di 4 agenti:
  1. **Advocate**: critica, trova punti deboli
  2. **Factchecker**: verifica fatti, elimina allucinazioni (con ricerca Serper)
  3. **Creative**: aggiunge angoli creativi e prospettive inaspettate
  4. **Synthesis**: raccoglie tutto, produce versione finale
- Verdetto: pass / needs_revision / reject
- Contenuti che passano → pronti per pubblicazione
- Contenuti "needs_revision" → ritornano al Writer con feedback

#### F5. Dashboard con Approvazione
- **Home**: riepilogo giornaliero (contenuti prodotti, approvati auto, da approvare, costi)
- **Content Hub**: vista contenuti con workflow DA APPROVARE → APPROVATI → SCHEDULATI → PUBBLICATI
- **Ricerca**: tabella research items con score, filtri, azioni (approva/rifiuta/top pick/archivia)
- Approvazione rapida: un click per approvare, un click per rifiutare
- Batch actions: approva/rifiuta multipli

#### F6. Newsletter Composer
- 3 slot fissi: SISTEMA (metodo replicabile), STRUMENTO LAMPO (tool rapido), MOSSA (azione applicabile)
- 6 candidati per slot, ordinati per score
- Owner seleziona 1 per slot → click "Genera Newsletter"
- Preview HTML prima dell'invio
- Invio via Resend API
- Tracking: open rate, CTR, unsubscribe

#### F7. Tracking Costi API
- Dashboard costi in tempo reale
- Breakdown per agente (search, scoring, writer, editor, GOD, etc.)
- Budget giornaliero con alert a 80% e pausa automatica a 100%
- Storico 30 giorni con trend

#### F8. Brand Configuration
- File `brand.config.ts` con tutti i parametri del brand
- Topics, tone of voice, fonti RSS, pesi scoring, soglie auto-approve
- Cambio brand = cambio configurazione, stesso motore

### 3.2 NICE-TO-HAVE (Post-Lancio, Mese 2-3)

#### F9. Calendario Editoriale
- Vista mensile con eventi colorati per tipo (newsletter, social, blog, sponsorship)
- Drag & drop per spostare
- Pannello "prossimi eventi"

#### F10. Writing Lab (A/B Testing)
- Sessioni da 50 round: Campione vs Challenger
- Feedback binario del founder (A/B/pari)
- Sistema impara stile nel tempo
- Tracking hook types e win rates

#### F11. Metriche & Analytics
- Grafici: Open Rate trend, crescita iscritti, CTR
- Heatmap orari ottimali di invio
- Metriche social per piattaforma
- Tabella ultimi invii con dettagli

#### F12. Blog Manager
- Tabella articoli con status e SEO score
- SEO score breakdown (keyword density, readability, meta tags, links, alt images)
- Export come MDX per blog Next.js

#### F13. Social Publishing Automatico
- Integrazione Postiz (open-source, self-hosted)
- Scheduling automatico basato su orari ottimali
- Multi-piattaforma: LinkedIn, X, Instagram, Facebook
- Retry logic per fallimenti

#### F14. Feedback Loop Analytics
- Social metrics alimentano scoring algorithm
- Contenuti con alto engagement → bonus score per topic simili
- AutoResearch notturno (ispirato a Karpathy)

### 3.3 FUTURE (Fase 2 — SaaS, Mese 6+)

#### F15. Revenue Tracker
- MRR, affiliati, sponsorship tracking
- Deal pipeline con status
- Forecast con banda di confidenza

#### F16. Pipeline Health Monitor
- Uptime agenti, latency, errori, queue size
- Barre salute per agente
- Alert automatici su degradazione

#### F17. Sponsorship Automation
- Ricerca automatica sponsor target
- Generazione pitch personalizzati
- Pipeline: prospect → pitch → negotiation → confirmed → active
- Inserimento automatico in newsletter

#### F18. Video/Audio Generation
- ElevenLabs voice cloning
- Remotion per video/carousel da dati
- Script → audio → video automatizzato

#### F19. Multi-Tenancy SaaS
- Onboarding self-service per nuovi brand
- Billing (Stripe)
- Admin panel per gestione clienti
- Isolamento dati con RLS

#### F20. Mobile Dashboard
- Responsive design completo
- Push notification per contenuti da approvare
- Approvazione rapida da mobile

---

## 4. Flusso Utente Principale

### Flusso Giornaliero dell'Owner (10-15 min)

```
[MATTINA — Il sistema ha gia' lavorato durante la notte]

1. APERTURA DASHBOARD
   └─→ Home: "Buongiorno. Hai 17 bozze da approvare."
   └─→ KPI: "14 approvate automaticamente | 3 da approvare | Spesa API: €4.20"
   └─→ Activity log: "ResearchBot: 602 fonti → 45 items → 20 nel pool finale"

2. REVIEW CONTENUTI (solo 3 in zona grigia)
   └─→ Content Hub → tab "DA APPROVARE" (3 items)
   └─→ Per ogni item:
       └─→ Vedi titolo, score (es. 6.8), piattaforme target
       └─→ Espandi → leggi contenuto + GOD Mode feedback
       └─→ Click [APPROVA] o [RIFIUTA]
   └─→ Tempo: ~5 minuti

3. FINE
   └─→ Il sistema schedule e pubblica automaticamente
   └─→ L'owner chiude la dashboard
```

### Flusso Settimanale Newsletter (30 min, es. Venerdi')

```
1. APERTURA NEWSLETTER
   └─→ Menu → Newsletter → "+ Genera Newsletter"

2. SELEZIONE SLOT
   └─→ SLOT 1 — SISTEMA: 6 candidati con score
       └─→ Leggi titoli e anteprima → seleziona il migliore
   └─→ SLOT 2 — STRUMENTO LAMPO: 6 candidati
       └─→ Seleziona
   └─→ SLOT 3 — MOSSA: 6 candidati
       └─→ Seleziona

3. GENERAZIONE
   └─→ Click "Genera Newsletter"
   └─→ GOD System processa (advocate → factcheck → creative → synthesis)
   └─→ Preview HTML generata

4. REVISIONE & INVIO
   └─→ Leggi preview → eventuali edit manuali
   └─→ Click "Invia" (con conferma)
   └─→ Newsletter inviata

5. POST-INVIO
   └─→ Metriche arrivano in 24h: open rate, CTR, unsubscribe
   └─→ Feedback loop aggiorna scoring
```

### Flusso Primo Setup (una tantum, 1-2 ore)

```
1. LOGIN
   └─→ Crea account con email

2. CONFIGURAZIONE BRAND
   └─→ Nome brand, tagline, descrizione
   └─→ Topics principali (es. "AI", "marketing digitale")
   └─→ Tone of voice: personalita', cose da evitare, regole
   └─→ Esempi di contenuto buono e cattivo
   └─→ Principi del founder (per scoring alignment)

3. CONFIGURAZIONE FONTI
   └─→ Aggiungi fonti RSS (o importa lista)
   └─→ Configura autori trusted
   └─→ Imposta query Serper personalizzate

4. CONFIGURAZIONE SOCIAL
   └─→ Collega account LinkedIn, X, Instagram
   └─→ Imposta orari pubblicazione preferiti
   └─→ Scegli formati contenuto per piattaforma

5. CONFIGURAZIONE NEWSLETTER
   └─→ Email mittente, nome, reply-to
   └─→ Frequenza (settimanale)
   └─→ Giorno e ora invio

6. PRIMA RICERCA
   └─→ Click "Lancia Ricerca" manualmente
   └─→ Attendi ~10 minuti
   └─→ Vedi primi risultati → approva/rifiuta per calibrare
   └─→ Sistema impara dalle prime scelte
```

---

## 5. Struttura Schermate

### Mappa Navigazione

```
SIDEBAR (sempre visibile)
├── Home (Dashboard)
├── Content Hub
├── PRODUZIONE
│   ├── Ricerca
│   ├── Calendario
│   ├── Newsletter
│   └── Blog
├── QUALITA'
│   ├── Writing Lab
│   ├── Metriche
│   └── Newsletter (analytics)
└── SISTEMA
    ├── Pipeline Health
    ├── Revenue
    ├── Costi API
    └── Research V2
```

### Dettaglio Schermate

#### S1. Home (Dashboard) — `/`
**Scopo:** Riepilogo rapido. L'owner capisce in 5 secondi se tutto funziona.

**Contenuto:**
- Messaggio di benvenuto: "Buongiorno. Hai X bozze da approvare."
- 4 KPI card: Fonti scansionate | Contenuti pronti | Newsletter mese | Open rate
- Mini content pipeline (quanti per status)
- AI Agent Status (online/offline per agente)
- Activity log (ultime 10 azioni degli agenti con timestamp)
- Spesa API oggi con barra progresso vs budget

#### S2. Content Hub — `/content-hub`
**Scopo:** Il centro operativo. Qui si approvano contenuti.

**Contenuto:**
- Status bar: "APPROVATI: X | DA APPROVARE: Y | +Z%"
- Tabs: TUTTI | DA APPROVARE | APPROVATI | USATI | ARCHIVIATI
- Card per ogni contenuto: titolo, score, piattaforme, preview, status
- Espansione card: testo completo, versioni per piattaforma, GOD mode feedback
- Azioni: [Approva] [Rifiuta] [GOD Mode] [Modifica] [Archivia]
- Batch select + batch approve/reject

#### S3. Ricerca — `/ricerca`
**Scopo:** Vedere cosa ha trovato la pipeline di ricerca.

**Contenuto:**
- KPI tabs con conteggi per status (Tutti, In Attesa, Approvati, Archiviato, Rifiutati)
- Volume Report: barre colorate per categoria (Finanza, Prodotto, Marketing, Tech, Business)
- Filtri: tipo contenuto, fonte, score range
- Sub-tabs: TUTTE | SISTEMA | TOOL | MOSSA
- Tag-tabs: VERIFICATO | CASO STUDIO | ESPERTO | COMMUNITY
- Tabella items: checkbox, tag, status, fonte, titolo, score, azioni
- Bottone "Lancia Ricerca" (trigger manuale)

#### S4. Newsletter — `/newsletter`
**Scopo:** Comporre e inviare la newsletter settimanale.

**Contenuto:**
- 4 KPI: Inviate mese | Open rate | Iscritti | CTR
- Bottone verde "+ Genera Newsletter"
- Tabella newsletter passate con metriche
- Vista composizione: 3 slot con 6 candidati ciascuno
- Preview HTML
- Bottone "Invia"

#### S5. Calendario — `/calendario`
**Scopo:** Vista d'insieme di cosa esce e quando.

**Contenuto:**
- Griglia mensile 7 colonne (Lun-Dom)
- Eventi colorati per tipo: Newsletter (verde), Social (blu), Blog (viola), Sponsorship (arancio)
- Pannello destro: prossimi 5 eventi + bottone "Aggiungi"
- KPI bottom: Programmati | In Produzione | Approvati

#### S6. Writing Lab — `/writing-lab`
**Scopo:** Affinare lo stile di scrittura con A/B testing.

**Contenuto:**
- Selezione topic/formato
- Panel A/B side-by-side: Campione vs Challenger
- Bottoni: [Scegli A] [Scegli B] [Pari]
- Badge "VINCITORE PREVISTO"
- GOD Mode inline (factcheck, advocate, synthesizer feedback)
- Stats: round X/50, hook type, win rate

#### S7. Blog — `/blog`
**Scopo:** Gestire articoli blog con SEO.

**Contenuto:**
- Tabs: Tutti | Bozze | Programmati | Pubblicati
- KPI: Pubblicati | In Bozza | Programmati | Visite totali
- Tabella articoli: titolo, autore, data, status, SEO score, visite
- Pannello SEO score breakdown per articolo selezionato

#### S8. Metriche — `/metriche`
**Scopo:** Analytics e performance.

**Contenuto:**
- Tabs: NEWSLETTER | SOCIAL | WEB | REVENUE
- 3 KPI card: Open Rate | Iscritti | CTR
- Grafico line: Open Rate trend 30 giorni
- Grafico area: Crescita iscritti
- Heatmap: finestra ottimale invio (7x12)
- Tabella ultimi 10 invii

#### S9. Revenue — `/revenue`
**Scopo:** Tracking entrate e pipeline salute.

**Contenuto:**
- 4 KPI: MRR | Affiliati | Sponsorship | Totale
- Bar chart 6 mesi per fonte revenue
- Tabella deal attivi con status
- Line chart forecast Q4
- Pipeline Health: uptime, latency, errori, queue, salute per agente

#### S10. Costi API — `/costi-api`
**Scopo:** Controllo spesa.

**Contenuto:**
- 3 KPI: Oggi | Settimana | Mese
- Stacked bar chart costi 30 giorni per agente
- Tabella breakdown: agente, modello, chiamate, token, costo, % budget
- Barra alert budget (verde/giallo/rosso)

---

## 6. Requisiti Tecnici

### Stack Tecnologico

| Layer | Tecnologia | Motivazione |
|-------|-----------|-------------|
| **Frontend** | Next.js 15 (App Router) | React, server components, API routes, deploy Vercel |
| **UI Components** | shadcn/ui + Tailwind CSS | Componenti accessibili, design system personalizzabile |
| **Database** | Supabase (PostgreSQL 15+) | Managed, pgvector, RLS, Auth, Realtime, Storage |
| **Backend Agents** | Python 3.12+ | Ecosistema AI/ML, async, librerie scraping |
| **Orchestrazione** | n8n self-hosted | Visual workflows, cron, webhook, self-hosted |
| **AI Models** | OpenRouter (hub) | Multi-model, fallback, billing unificato |
| **Scrittura** | Claude Opus 4.6 | Qualita' massima per output finale |
| **Scoring/Review** | Claude Sonnet 4.6 | Cost-effective per batch processing |
| **Ricerca** | Serper + Firecrawl + Feed Parser | Search + deep scraping + RSS |
| **Embeddings** | text-embedding-3-small + pgvector | Semantic dedup, MMR rerank |
| **Email** | Resend (MVP) → Beehiiv (scala) | API-first, affordable |
| **Social** | Postiz (open-source) | Self-hosted, 9 piattaforme, AI agent API |
| **Video/Visual** | Remotion | React → video, programmatico |
| **Deploy Frontend** | Vercel | Auto-deploy, edge, preview deploys |
| **Deploy Backend** | Hostinger VPS x2 | €10/mese ciascuno, staging + prod |
| **Networking** | Tailscale | VPN zero-config tra VPS |
| **Error Tracking** | Sentry | Free tier sufficiente per MVP |

### Database
- 18 tabelle (vedi [SCHEMA.md](database/SCHEMA.md))
- Migration SQL pronta ([001_initial_schema.sql](database/001_initial_schema.sql))
- pgvector per embeddings e deduplicazione semantica
- RLS per multi-tenancy (isolamento dati per brand)
- Realtime per aggiornamenti live dashboard

### Autenticazione
- Supabase Auth (email + password)
- JWT con claims custom (brand_id, role)
- 3 ruoli: owner, editor, viewer
- Middleware Next.js per protezione route

### API
- 50+ endpoint REST (vedi [API_SPECIFICATION.md](api/API_SPECIFICATION.md))
- WebSocket per aggiornamenti real-time (pipeline status, agent activity)
- Rate limiting per endpoint
- Validazione input con Zod

### Sicurezza
- GDPR compliance (double opt-in, diritto cancellazione)
- API keys in Supabase Vault
- HTTPS ovunque, security headers
- Vedi [SECURITY.md](SECURITY.md) per dettagli completi

### Costi Operativi
- ~€400-500/mese per 1 brand
- ~€230-320/mese per brand aggiuntivo
- Vedi [COSTS.md](COSTS.md) per breakdown completo

---

## 7. Metriche di Successo

### Metriche di Prodotto (il sistema funziona?)

| Metrica | Target MVP | Target 6 mesi | Come si misura |
|---------|-----------|---------------|----------------|
| Contenuti generati/giorno | 10+ | 30+ | Count `content_drafts` creati/giorno |
| Tasso auto-approvazione | 60%+ | 80%+ | Contenuti con score > soglia / totale |
| Tempo umano/giorno | < 15 min | < 5 min | Self-reported + session tracking |
| GOD System pass rate | 70%+ | 85%+ | `god_mode_reviews` con verdict = pass |
| Research items qualita' | 20+ items validi/giorno | 50+ | Items con score > 5.0 / totale |
| Pipeline uptime | 95% | 99% | `pipeline_health` monitoring |

### Metriche di Growth (il contenuto funziona?)

| Metrica | Target MVP | Target 6 mesi | Come si misura |
|---------|-----------|---------------|----------------|
| Newsletter open rate | 30%+ | 40%+ | Resend/Beehiiv analytics |
| Newsletter CTR | 3%+ | 5%+ | Resend/Beehiiv analytics |
| Subscriber growth | +100/mese | +500/mese | `newsletters.recipients_count` trend |
| LinkedIn engagement rate | 2%+ | 5%+ | `social_metrics` |
| Blog visite/mese | 1.000+ | 10.000+ | Analytics web |
| Contenuti pubblicati/settimana | 20+ | 100+ | Count `content_drafts` pubblicati |

### Metriche di Business (il sistema rende?)

| Metrica | Target MVP | Target 6 mesi | Come si misura |
|---------|-----------|---------------|----------------|
| Costo/contenuto | < €0.50 | < €0.20 | `api_costs` totale / contenuti pubblicati |
| ROI (ricavi/costi) | > 1x | > 5x | `revenue_deals` / costi operativi |
| Break-even | Mese 3 | — | Ricavi >= Costi |
| Costo vs team umano | 95% risparmio | 97% | €400 vs €9.000-14.000 |

### Metriche di Qualita' (i contenuti sono buoni?)

| Metrica | Target | Come si misura |
|---------|--------|----------------|
| Factcheck pass rate | 95%+ | `god_mode_reviews.factcheck_issues` vuoto |
| Zero allucinazioni pubblicate | 0/mese | Report manuale + factcheck |
| Tone of voice consistency | Nessun feedback "suona robotico" | Survey/feedback manuale |
| Contenuti rifiutati post-pubblicazione | < 2% | Contenuti rimossi dopo pubblicazione |

### Dashboard Metriche

Tutte queste metriche sono visibili nella dashboard:
- **Home**: KPI giornalieri principali
- **Metriche**: grafici dettagliati per newsletter, social, web
- **Revenue**: tracking business
- **Costi API**: monitoraggio spesa
- **Pipeline Health**: salute tecnica del sistema

---

## 8. Piano di Implementazione MVP

### Scope MVP (Fase 1 + 2 dalla roadmap)

Il MVP include le funzionalita' F1-F8:
- Research Pipeline automatica ✅
- Scoring Engine AI ✅
- Content Generation multi-formato ✅
- GOD System review ✅
- Dashboard con approvazione ✅
- Newsletter Composer ✅
- Tracking costi API ✅
- Brand Configuration ✅

### NON incluso nel MVP
- Calendario editoriale (F9)
- Writing Lab A/B (F10)
- Analytics avanzati (F11)
- Blog Manager con SEO (F12)
- Social publishing automatico (F13) — nel MVP si pubblica manualmente o con copia-incolla
- Feedback loop analytics (F14)
- Revenue tracker (F15)
- Sponsorship automation (F17)
- Video generation (F18)
- Multi-tenancy SaaS (F19)

### Timeline

| Settimana | Deliverable |
|-----------|------------|
| 1 | Infrastruttura: Next.js + Supabase + Auth + Layout dashboard |
| 2-3 | Research Pipeline + Scoring Engine + Pagina Ricerca |
| 4-5 | Content Generation + GOD System + Content Hub |
| 6 | Newsletter Composer + Invio + Tracking costi |
| 7 | Testing, bug fix, primo brand configurato e funzionante |

### Criterio di Successo MVP
Il MVP e' riuscito quando:
1. Il sistema ricerca e trova 20+ contenuti rilevanti/giorno senza intervento
2. I contenuti vengono generati automaticamente in multi-formato
3. Il GOD system filtra contenuti di bassa qualita'
4. L'owner spende massimo 15 minuti/giorno nella dashboard
5. La newsletter settimanale viene composta e inviata dalla dashboard
6. I costi API restano sotto €500/mese

---

## Appendice: Documenti di Riferimento

| Documento | Contenuto |
|-----------|-----------|
| [ARCHITECTURE.md](architecture/ARCHITECTURE.md) | Architettura sistema, flusso E2E, principi |
| [TECH_STACK.md](architecture/TECH_STACK.md) | Stack tecnologico con motivazioni |
| [SCHEMA.md](database/SCHEMA.md) | Schema database 18 tabelle |
| [001_initial_schema.sql](database/001_initial_schema.sql) | Migration SQL pronta |
| [API_SPECIFICATION.md](api/API_SPECIFICATION.md) | 50+ endpoint API |
| [AGENTS.md](agents/AGENTS.md) | 14+ agenti AI con specifiche |
| [PIPELINES.md](agents/PIPELINES.md) | 8 pipeline automazione |
| [BRAND_CONFIG.md](config/BRAND_CONFIG.md) | Configurazione brand |
| [DESIGN_SYSTEM.md](design/DESIGN_SYSTEM.md) | Design tokens e componenti |
| [SCREENS.md](design/SCREENS.md) | 10 schermate dettagliate |
| [SECURITY.md](SECURITY.md) | Sicurezza e GDPR |
| [COSTS.md](COSTS.md) | Costi e proiezioni |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Roadmap implementazione |
