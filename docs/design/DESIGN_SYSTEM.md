# Design System — Chromatic Grid

> Specifiche del design system estratte dal progetto Google Stitch per la dashboard del Content Engine.

---

## Panoramica

Il design system "Chromatic Grid" e' la versione finale del sistema visivo per la dashboard interna. Sostituisce il precedente "Cortex Carbon" (tema scuro neon). E' ottimizzato per la leggibilita' e l'uso prolungato da parte di content manager.

**Filosofia:** Light mode pulito, data-dense, azione rapida.

---

## Implementazione Tecnica

Il design viene implementato con:
- **shadcn/ui** — Component library basata su Radix UI
- **Tailwind CSS** — Utility-first CSS
- **Next.js App Router** — Layout con sidebar persistente

NON usare l'HTML/CSS esportato da Stitch: e' solo un reference visuale.

---

## Design Tokens

### Colori

```css
:root {
  /* Background */
  --bg-primary: #FFFFFF;
  --bg-secondary: #F9FAFB;
  --bg-tertiary: #F3F4F6;
  --bg-sidebar: #1F2937;

  /* Testo */
  --text-primary: #111827;
  --text-secondary: #6B7280;
  --text-muted: #9CA3AF;
  --text-inverse: #FFFFFF;

  /* Brand */
  --brand-primary: #3B82F6;       /* Blu principale */
  --brand-primary-hover: #2563EB;
  --brand-secondary: #10B981;     /* Verde */
  --brand-accent: #F59E0B;        /* Giallo/Ambra */

  /* Status */
  --status-success: #10B981;      /* Verde — approvato, attivo */
  --status-warning: #F59E0B;      /* Arancio — in attesa, in trattativa */
  --status-error: #EF4444;        /* Rosso — rifiutato, errore */
  --status-info: #3B82F6;         /* Blu — programmato, info */

  /* Badge specifici */
  --badge-tutti: #6B7280;
  --badge-approvato: #10B981;
  --badge-in-attesa: #F59E0B;
  --badge-rifiutato: #EF4444;
  --badge-archiviato: #9CA3AF;
  --badge-bozza: #D1D5DB;
  --badge-inviata: #10B981;
  --badge-programmata: #3B82F6;

  /* Grafici */
  --chart-1: #3B82F6;             /* Blu — newsletter/revenue */
  --chart-2: #10B981;             /* Verde — social/open rate */
  --chart-3: #8B5CF6;             /* Viola — blog/video */
  --chart-4: #F59E0B;             /* Arancio — sponsorship */
  --chart-5: #EF4444;             /* Rosso — finanza */

  /* Categorie contenuto (Volume Report bars) */
  --cat-finanza: #EF4444;
  --cat-prodotto: #3B82F6;
  --cat-marketing: #10B981;
  --cat-tech: #8B5CF6;
  --cat-business: #F59E0B;

  /* Bordi */
  --border-default: #E5E7EB;
  --border-focus: #3B82F6;

  /* Staging bar */
  --staging-bg: #10B981;
  --staging-text: #FFFFFF;
}
```

### Tipografia

```css
:root {
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* Dimensioni */
  --text-xs: 0.75rem;     /* 12px — label, badge */
  --text-sm: 0.875rem;    /* 14px — body secondario, tabelle */
  --text-base: 1rem;      /* 16px — body principale */
  --text-lg: 1.125rem;    /* 18px — heading sezione */
  --text-xl: 1.25rem;     /* 20px — heading pagina */
  --text-2xl: 1.5rem;     /* 24px — titolo principale */
  --text-3xl: 1.875rem;   /* 30px — KPI numeri grandi */

  /* Pesi */
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
}
```

### Spacing

```css
:root {
  --space-1: 0.25rem;    /* 4px */
  --space-2: 0.5rem;     /* 8px */
  --space-3: 0.75rem;    /* 12px */
  --space-4: 1rem;       /* 16px */
  --space-5: 1.25rem;    /* 20px */
  --space-6: 1.5rem;     /* 24px */
  --space-8: 2rem;       /* 32px */
  --space-10: 2.5rem;    /* 40px */
  --space-12: 3rem;      /* 48px */
}
```

### Border Radius

```css
:root {
  --radius-sm: 0.25rem;   /* 4px — badge, tag */
  --radius-md: 0.375rem;  /* 6px — input, card */
  --radius-lg: 0.5rem;    /* 8px — card, modal */
  --radius-xl: 0.75rem;   /* 12px — card grande */
  --radius-full: 9999px;  /* Pill shape */
}
```

---

## Componenti Principali

### Layout

```
+------------------------------------------------------------------+
| [STAGING BAR] verde - "STAGING // CONTENT ENGINE"                 |
+------------------------------------------------------------------+
| SIDEBAR (240px)  |  MAIN CONTENT                                  |
| bg-sidebar       |  bg-primary                                    |
|                  |  +------------------------------------------+  |
| [Logo] Brand     |  | [URL BAR] giallo - "Incolla URL..."      |  |
|                  |  +------------------------------------------+  |
| Quick URL bar    |  | [API SPEND] "Spesa API oggi: €X.XX"      |  |
| API spend line   |  +------------------------------------------+  |
|                  |  |                                          |  |
| NAV:             |  |  [CONTENUTO PAGINA]                     |  |
| Home             |  |                                          |  |
| Content Hub      |  |  KPI Cards → Tabelle → Grafici          |  |
|                  |  |                                          |  |
| -- PRODUZIONE -- |  |                                          |  |
| Ricerca          |  |                                          |  |
| Calendario       |  |                                          |  |
| Newsletter       |  |                                          |  |
| Blog             |  |                                          |  |
|                  |  |                                          |  |
| -- QUALITA' --   |  |                                          |  |
| Writing Lab      |  |                                          |  |
| Metriche         |  |                                          |  |
| Newsletter       |  |                                          |  |
|                  |  |                                          |  |
| -- SISTEMA --    |  |                                          |  |
| Pipeline Health  |  |                                          |  |
| Revenue          |  |                                          |  |
| Costi API        |  |                                          |  |
| Research V2      |  |                                          |  |
+------------------+--+------------------------------------------+--+
```

### Sidebar
- Larghezza: 240px fisso
- Background: `--bg-sidebar` (#1F2937)
- Testo: bianco con opacita' per inattivi
- Item attivo: highlight blu con barra laterale
- Sezioni separate da label grigia (PRODUZIONE, QUALITA', SISTEMA)
- Logo + brand name in alto
- URL bar gialla sotto il logo
- Linea spesa API verde sotto URL bar

### KPI Card
- Background bianco con bordo `--border-default`
- Numero grande (`--text-3xl`, `--font-bold`)
- Label sotto (`--text-sm`, `--text-secondary`)
- Variazione percentuale colorata (verde = positivo, rosso = negativo)
- Icona in alto a sinistra opzionale
- Border-radius: `--radius-lg`
- Padding: `--space-6`

### Tabella Dati
- Header: background `--bg-secondary`, testo `--text-secondary`, `--text-xs` uppercase
- Righe: alternating white / `--bg-secondary` (subtle)
- Hover: `--bg-tertiary`
- Checkbox in prima colonna per selezione multipla
- Badge stato con colori specifici (vedi badge sotto)
- Azioni inline: bottoni ghost a destra (Approva, Top Pick, Archivia, Rifiuta)

### Badge / Tag
- Padding: `--space-1` x `--space-2`
- Border-radius: `--radius-sm`
- Font: `--text-xs`, `--font-medium`
- Varianti:
  - APPROVATO: bg verde chiaro, testo verde scuro
  - IN ATTESA: bg arancio chiaro, testo arancio scuro
  - RIFIUTATO: bg rosso chiaro, testo rosso scuro
  - BOZZA: bg grigio chiaro, testo grigio scuro
  - INVIATA: bg verde chiaro, testo verde scuro
  - PROGRAMMATA: bg blu chiaro, testo blu scuro
  - CONFERMATO: bg verde chiaro, testo verde scuro
  - ATTIVO: bg verde chiaro, testo verde scuro
  - IN TRATTATIVA: bg giallo chiaro, testo giallo scuro
  - PROPOSTA INVIATA: bg blu chiaro, testo blu scuro

### Tab Navigation
- Tabs: `--text-sm`, `--font-medium`
- Attivo: testo `--brand-primary`, border-bottom 2px `--brand-primary`
- Inattivo: testo `--text-secondary`
- Sub-tabs (es. TUTTE | SISTEMA | TOOL | MOSSA): pill-shaped, bg attivo `--brand-primary`, testo bianco

### Bottoni
- Primary: bg `--brand-primary`, testo bianco, hover `--brand-primary-hover`
- Secondary: bg `--bg-secondary`, testo `--text-primary`, bordo `--border-default`
- Ghost: trasparente, testo `--text-secondary`, hover `--bg-secondary`
- Danger: bg `--status-error`, testo bianco
- Success: bg `--status-success`, testo bianco (es. "Genera Newsletter", "Approva")
- Dimensioni: sm (28px h), md (36px h), lg (44px h)

### Grafici
- Line chart: linea 2px, area sotto con opacita' 10%
- Bar chart: radius top `--radius-sm`, gap 4px
- Heatmap: griglia 7 colonne (giorni) x N righe (ore), gradiente grigio → verde
- Colori: usare `--chart-1` attraverso `--chart-5`
- Background: bianco, griglia leggera `--border-default`

### Volume Report (barre orizzontali)
- 5 barre colorate per categoria (FINANZA, PRODOTTO, MARKETING, TECH, BUSINESS)
- Ogni barra ha label a sinistra e numero a destra
- Colori: vedi `--cat-*` tokens

---

## Componenti shadcn/ui da Usare

| Componente | Uso nel progetto |
|-----------|------------------|
| `Card` | KPI cards, contenitori sezioni |
| `Table` | Tabelle dati (ricerca, newsletter, blog, deal) |
| `Tabs` | Navigazione sezioni (TUTTI/DA APPROVARE/APPROVATI...) |
| `Badge` | Status badge (APPROVATO, BOZZA, INVIATA...) |
| `Button` | Azioni (Approva, Genera, Invia...) |
| `Input` | URL bar, form fields |
| `Select` | Filtri (Score, Piattaforma...) |
| `Dialog` | Preview newsletter, conferme |
| `Sheet` | Pannelli laterali dettaglio |
| `Calendar` | Calendario editoriale |
| `Checkbox` | Selezione multipla in tabelle |
| `Progress` | Pipeline health bars |
| `Tooltip` | Info aggiuntive su hover |
| `DropdownMenu` | Menu azioni (Approva/Top Pick/Archivia/Rifiuta) |
| `Separator` | Divisori sezioni sidebar |
| `ScrollArea` | Scroll contenuto lungo |
| `Chart` (recharts) | Grafici (line, bar, area, heatmap) |

---

## Responsive Breakpoints

La dashboard e' ottimizzata per desktop. Breakpoints di base per future iterazioni:

| Breakpoint | Larghezza | Comportamento |
|-----------|-----------|---------------|
| Desktop | >= 1280px | Layout completo, sidebar visibile |
| Tablet | 768-1279px | Sidebar collassabile, tabelle scrollabili |
| Mobile | < 768px | Non prioritario — dashboard interna |

---

## Accessibilita'

- Contrasto minimo WCAG AA (4.5:1 per testo, 3:1 per elementi grandi)
- Tutti i bottoni con focus ring visibile
- Tabelle con header `scope="col"` e `aria-sort`
- Badge con `aria-label` per screen reader
- Grafici con `aria-label` e tabella dati alternativa
