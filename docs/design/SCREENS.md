# Specifiche Schermate Dashboard

> Dettaglio delle 10 schermate della dashboard con dati necessari, componenti, e endpoint collegati.

---

## Struttura Comune a Tutte le Schermate

Ogni schermata include:
1. **Staging Bar** (verde, top) — "STAGING // [NOME SEZIONE]"
2. **Sidebar** (sinistra, 240px) — navigazione con sezioni PRODUZIONE / QUALITA' / SISTEMA
3. **URL Bar** (giallo, sotto header) — "Incolla URL per analisi rapida..." + bottone Play
4. **API Spend Row** (verde, sotto URL bar) — "Spesa API oggi: €X.XX — soglia €5.00 Dettagli →"
5. **Contenuto principale** — specifico per ogni schermata

---

## 1. Dashboard (Home)

**Route:** `/`
**Endpoint:** `GET /api/system/activity`, `GET /api/system/costs`, `GET /api/content/drafts?status=approved&limit=5`

### Layout
```
[URL Bar + API Spend]
[4 KPI Cards in riga]
[Content Pipeline (mini) | AI Agent Status]
[Ultime Attivita' — Activity Log]
```

### KPI Cards
| KPI | Dato | Endpoint |
|-----|------|----------|
| Fonti questa settimana | 602 | `GET /api/research/runs?week=current` |
| Contenuti pronti | 23 | `GET /api/content/drafts?status=approved` (count) |
| Newsletter | 4/mese | `GET /api/newsletter?month=current` (count) |
| Open rate | 68% | `GET /api/metrics/newsletter` (media) |

### Ultime Attivita'
Lista cronologica delle ultime 10 azioni degli agenti:
- "ResearchBot ha completato la scansione — 602 fonti analizzate" — 5 min fa
- "ScoringAgent ha valutato 45 nuovi articoli" — 12 min fa
- "WriterAgent ha generato 3 bozze LinkedIn" — 1 ora fa

---

## 2. Ricerca

**Route:** `/ricerca`
**Endpoint:** `GET /api/research/items`, `POST /api/research/trigger`

### Layout
```
[URL Bar + API Spend]
[KPI Tabs: 32 TUTTI | 6 IN ATTESA | 17 APPROVATI | 0 ARCHIVIATO | 6 RIFIUTATI]
[Volume Report 602 — 5 barre colorate orizzontali]
[Filter Row: Lancia Ricerca | Newsletter | Link AI | Pipeline | Approvati | Score ▼]
[Sub-tabs: TUTTE | SISTEMA | TOOL | MOSSA]
[Tag-tabs: TUTTE | VERIFICATO | CASO STUDIO | ESPERTO | COMMUNITY | NON VERIFICATO]
[Tabella news items]
```

### Tabella Research Items
| Colonna | Tipo | Note |
|---------|------|------|
| Checkbox | `<Checkbox>` | Selezione multipla |
| Tag | `<Badge>` | SISTEMA / TOOL / MOSSA |
| Status | `<Badge>` | VERIFICATO / NON VERIFICATO |
| Fonte | Testo | Nome fonte |
| Titolo | Testo + link | Titolo articolo |
| Score | Numero | Score finale con colore |
| Azioni | Bottoni | [Approva] [Top Pick] [Archivia] [Rifiuta] |

### Azioni Speciali
- **Lancia Ricerca** — `POST /api/research/trigger` — bottone primario verde
- **Filtro Score** — dropdown per ordinare per score decrescente
- **Filtro per categoria** — tabs SISTEMA/TOOL/MOSSA

---

## 3. Content Hub

**Route:** `/content-hub`
**Endpoint:** `GET /api/content/drafts`

### Layout
```
[URL Bar + API Spend]
[Status bar: "APPROVATI: X | 3 DA APPROVARE | +2.9%"]
[Tabs: TUTTI | DA APPROVARE | APPROVATI | USATI | ARCHIVIATI]
[Griglia contenuti con preview per piattaforma]
```

### Card Contenuto
Ogni contenuto mostra:
- Titolo e anteprima testo (troncato)
- Piattaforme target con icone (LinkedIn, X, Instagram, ecc.)
- Score badge
- Status badge
- Preview thumbnail (se carousel/video)
- Bottoni: [Approva] [Modifica] [GOD Mode] [Archivia]

### Flusso Approvazione
DA APPROVARE → APPROVATI → SCHEDULATI → PUBBLICATI

---

## 4. Newsletter

**Route:** `/newsletter`
**Endpoint:** `GET /api/newsletter`, `POST /api/newsletter/generate`

### Layout
```
[URL Bar + API Spend]
[4 KPI Cards: Inviate mese | Open Rate | Iscritti | CTR medio]
[Bottone verde: "+ Genera Newsletter"]
[Tabella newsletter]
```

### KPI Cards
| KPI | Esempio | Colore |
|-----|---------|--------|
| Inviate questo mese | 4 | Blu |
| Open rate medio | 68.3% | Verde |
| Iscritti | 47.832 | Blu |
| CTR medio | 4.2% | Arancio |

### Tabella Newsletter
| # | Titolo | Data | Iscritti | Open Rate | CTR | Stato |
|---|--------|------|----------|-----------|-----|-------|
| 64 | "3 aree AI che..." | 5 Apr | 47.832 | 72.1% | 5.1% | INVIATA |
| 63 | "Tool flash: Claude" | 29 Mar | 47.420 | 65.8% | 3.9% | INVIATA |
| 65 | "Mossa della sett..." | 12 Apr | — | — | — | BOZZA |

### Vista Dettaglio Newsletter
- 3 slot con 6 candidati ciascuno ordinati per score
- Bottone "Seleziona" per ogni candidato
- Preview HTML con rendering completo
- Bottone "Genera Newsletter" → "Invia" (con conferma)

---

## 5. Calendario Editoriale

**Route:** `/calendario`
**Endpoint:** `GET /api/calendar/events`

### Layout
```
[URL Bar + API Spend]
[Mese/Anno selector: ◀ Ottobre 2024 ▶]
[Griglia mensile 7 colonne (Lun-Dom)]
[Legenda: NEWSLETTER (verde) | SOCIAL (blu) | BLOG/VIDEO (viola) | SPONSORSHIP (arancio)]
[Pannello destro: PROSSIMI EVENTI + bottone AGGIUNGI]
[KPI bottom: PROGRAMMATI: 12 | IN PRODUZIONE: 8 | APPROVATI: 3]
```

### Evento nel Calendario
- Cella giorno con fino a 3 eventi visibili
- Ogni evento: colore per tipo + titolo troncato
- Click su evento: pannello dettaglio laterale
- Drag & drop per spostare eventi (futuro)

---

## 6. Writing Lab

**Route:** `/writing-lab`
**Endpoint:** `GET /api/writing-lab/sessions`, `POST /api/writing-lab/sessions/:id/vote`

### Layout
```
[URL Bar + API Spend]
[Dropdown selettori: Newsletter ▼ | Social ▼ | Blog ▼ | LinkedIn ▼]
[Toolbar: B | I | Genera AI | Riscrivi | Accorcia]
[A/B Panel side-by-side]
  [Pannello A: "CAMPIONE ATTUALE" + testo] [Pannello B: "NUOVA VERSIONE" + testo]
  [Badge: "VINCITORE PREVISTO" su pannello A]
  [Bottoni: Scegli A | Scegli B | Pari]
[GOD MODE section]
  [FactChecker feedback] [Advocate feedback] [Synthesizer feedback]
[Stats sessione: Round 23/50 | Hook type: "Attacco numerico" | Win rate: 67%]
```

### Flusso
1. Utente seleziona un topic dalla lista
2. Sistema genera round 1: Campione vs Challenger
3. Utente vota (A/B/pari) — `POST /api/writing-lab/sessions/:id/vote`
4. Sistema genera round successivo con campione aggiornato
5. Dopo 50 round: stile appreso, campione finale salvato

---

## 7. Blog Manager

**Route:** `/blog`
**Endpoint:** `GET /api/content/drafts?content_type=blog`

### Layout
```
[URL Bar + API Spend]
[Header: "BLOG" + tabs TUTTI | BOZZE | PROGRAMMATI | PUBBLICATI]
[KPI row: Pubblicati: 24 | In Bozza: 6 | Programmati: 3 | Visite totali: 48.2k]
[Tabella articoli blog]
[Pannello destro: SEO SCORE BREAKDOWN (per articolo selezionato)]
```

### Tabella Blog
| # | Titolo | Autore | Data | Status | Score SEO | Visite | Azioni |
|---|--------|--------|------|--------|-----------|--------|--------|
| 1 | "L'evoluzione dell'AI..." | Marco | 24 Oct | PUBBLICATO | 94 | 12.4k | [Modifica] [Analizza] |

### SEO Score Breakdown (pannello destro)
- Score totale: 94/100
- Barre progresso per:
  - Keyword density: 92%
  - Readability: 88%
  - Meta tags: 100%
  - Internal links: 85%
  - Image alt: 90%

---

## 8. Metriche / Analytics

**Route:** `/metriche`
**Endpoint:** `GET /api/metrics/newsletter`, `GET /api/metrics/social`, `GET /api/metrics/heatmap`

### Layout
```
[URL Bar + API Spend]
[Tabs: NEWSLETTER | SOCIAL | WEB | REVENUE]
[3 KPI Cards: Open Rate Medio | Iscritti Totali | CTR Medio]
[Grafico principale (60%): Open Rate Trend 30 giorni (line chart verde)]
[Grafico secondario (40%): Crescita Iscritti (area chart blu)]
[Heatmap: Finestra Ottimale di Invio (7x12 griglia)]
[Tabella: Ultimi 10 Invii con metriche dettagliate]
```

### Heatmap
- 7 colonne: Lun, Mar, Mer, Gio, Ven, Sab, Dom
- 12 righe: ore 6:00 → 22:00 (step 1h)
- Colore: grigio (basso) → verde (alto engagement)
- Picchi attesi: Mar 8-9, Gio 8-9, Mar 11-12

---

## 9. Revenue & Pipeline Health

**Route:** `/revenue`
**Endpoint:** `GET /api/revenue/summary`, `GET /api/revenue/deals`, `GET /api/system/health`

### Layout
```
[URL Bar + API Spend]
[4 KPI Cards: MRR | Affiliati MTD | Sponsorship | Totale MTD]
[Bar chart 6 mesi: Newsletter (verde) | Affiliati (blu) | Sponsorship (viola)]
[Tabella Deal Attivi]
[Line chart: Forecast Revenue Q4 (con banda di confidenza)]
[Pannello destro: Pipeline Health]
```

### Tabella Deal
| Partner | Tipo | Importo | Scadenza | Status | Azioni |
|---------|------|---------|----------|--------|--------|
| BrandX Agency | Sponsorship | €1.200 | 31 Oct | CONFERMATO | [Dettagli] |
| TechTools Pro | Affiliato | €450/mese | ongoing | ATTIVO | [Dettagli] |

### Pipeline Health (pannello destro)
- UPTIME AGENTI: 98.7%
- API LATENCY: 142ms
- ERRORI OGGI: 2
- QUEUE SIZE: 47 items
- Barre salute per agente: ResearchBot 98% | NewsletterAI 95% | FactChecker 100%

---

## 10. Costi API

**Route:** `/costi-api`
**Endpoint:** `GET /api/system/costs`, `GET /api/system/costs/breakdown`

### Layout
```
[URL Bar + API Spend]
[3 KPI Cards: Spesa Oggi | Spesa Settimana | Spesa Mese]
[Stacked bar chart: costi giornalieri ultimi 30 giorni per agente]
[Tabella breakdown per agente]
[Alert: soglia budget con indicatore visivo]
```

### Tabella Breakdown
| Agente | Modello | Chiamate oggi | Token In | Token Out | Costo | % Budget |
|--------|---------|---------------|----------|-----------|-------|----------|
| search | Serper | 45 | — | — | $1.35 | 9% |
| scoring_spiegamelo | Sonnet | 120 | 240k | 48k | $1.52 | 10.1% |
| opus_writer | Opus | 8 | 32k | 16k | $1.12 | 7.5% |

### Alert Budget
- Barra progresso: verde (< 80%) → giallo (80-100%) → rosso (> 100%)
- Notifica quando si supera `alert_threshold_usd` dalla brand config

---

## Navigazione e Routing

```
/                     → Dashboard (Home)
/content-hub          → Content Hub
/ricerca              → Ricerca
/calendario           → Calendario Editoriale
/newsletter           → Newsletter
/blog                 → Blog Manager
/writing-lab          → Writing Lab
/metriche             → Metriche / Analytics
/revenue              → Revenue & Pipeline Health
/costi-api            → Costi API
/impostazioni         → Settings (brand config) [futuro]
```
