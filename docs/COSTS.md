# Breakdown Costi e Proiezioni

> Analisi dettagliata dei costi operativi del Content Engine per brand.

---

## Costi Mensili Stimati (per 1 brand)

### Infrastruttura

| Servizio | Piano | Costo/mese | Note |
|----------|-------|-----------|------|
| Supabase | Pro | $25 | 8GB database, 250GB bandwidth, 100GB storage |
| Vercel | Pro | $20 | Deploy frontend, edge functions |
| VPS Hostinger (prod) | KVM 2 | ~€10 | 2 vCPU, 8GB RAM, Python backend |
| VPS Hostinger (staging) | KVM 1 | ~€10 | 1 vCPU, 4GB RAM |
| Tailscale | Free | $0 | fino a 100 dispositivi |
| Dominio | — | ~€1 | ammortizzato su 12 mesi |
| **Subtotale infrastruttura** | | **~€66/mese** | |

### API AI Models (via OpenRouter)

Basato sul sistema Montemagno (~$10/giorno = ~$300/mese):

| Agente | Modello | % Budget | Costo/mese |
|--------|---------|----------|-----------|
| search (Serper) | Serper API | 29.9% | ~$90 |
| scoring_spiegamelo | Claude Sonnet | 10.2% | ~$31 |
| opus_writer | Claude Opus | 7.5% | ~$23 |
| opus_editor | Claude Opus | 5.5% | ~$17 |
| scoring_aimedia | Claude Sonnet | 5.1% | ~$15 |
| sf_carousel_structure | Claude Sonnet | 3.6% | ~$11 |
| curation_social_* | Claude Sonnet | ~11% | ~$33 |
| content_trend_* | Claude Sonnet | ~6.5% | ~$20 |
| sonnet_adapter | Claude Sonnet | 2.7% | ~$8 |
| scoring_monty | Claude Sonnet | 2.6% | ~$8 |
| god_* (advocate/factcheck/creative) | Claude Sonnet | ~0.4% | ~$1 |
| god_synthesis | Claude Opus | 1.5% | ~$5 |
| script + combined_script | Claude Sonnet | 3.3% | ~$10 |
| newsletter_* | Claude Opus/Sonnet | ~2% | ~$6 |
| altri | Vari | ~8% | ~$24 |
| **Subtotale AI API** | | **100%** | **~$300/mese** |

### Research & Scraping

| Servizio | Piano | Costo/mese | Note |
|----------|-------|-----------|------|
| Serper | Developer | $50 | 10.000 ricerche/mese (incluso nel budget API sopra) |
| Firecrawl | Hobby | $19 | 3.000 pagine/mese |
| YouTube Data API | Free | $0 | 10.000 unita'/giorno (sufficiente) |
| Feed Parser (RSS) | Self-hosted | $0 | Libreria Python gratuita |
| **Subtotale research** | | **~$19/mese** | Serper gia' contato sopra |

### Content Distribution

| Servizio | Piano | Costo/mese | Note |
|----------|-------|-----------|------|
| Resend | Pro | $20 | 50.000 email/mese |
| Postiz | Self-hosted | $0 | Open-source, self-hosted su VPS |
| **Subtotale distribution** | | **~$20/mese** | |

### Monitoring

| Servizio | Piano | Costo/mese | Note |
|----------|-------|-----------|------|
| Sentry | Developer | $0 | 5.000 errori/mese (sufficiente per MVP) |
| UptimeRobot | Free | $0 | 50 monitor |
| **Subtotale monitoring** | | **$0/mese** | |

---

## Totale per 1 Brand

| Categoria | Costo/mese |
|-----------|-----------|
| Infrastruttura | ~€66 |
| AI API (OpenRouter) | ~€280 (~$300) |
| Research tools | ~€18 (~$19) |
| Distribution | ~€19 (~$20) |
| Monitoring | €0 |
| **TOTALE** | **~€383/mese** |
| **TOTALE (arrotondato)** | **~€400-500/mese** |

---

## Confronto con Team Umano Equivalente

Per produrre ~30 contenuti/giorno + newsletter settimanale + ricerca quotidiana:

| Ruolo | Ore/settimana | Costo/mese (Italia) |
|-------|---------------|---------------------|
| Content Manager | 40h | €2.500-3.500 |
| Copywriter | 30h | €2.000-3.000 |
| Social Media Manager | 20h | €1.500-2.500 |
| Data Analyst / Researcher | 15h | €1.500-2.000 |
| Graphic Designer (carousel) | 10h | €1.000-1.500 |
| Newsletter Editor | 10h | €800-1.200 |
| **TOTALE team umano** | | **€9.300-13.700/mese** |

**Risparmio:** 95-97% (€400 vs €9.300-13.700)

---

## Scaling: Costi per Multi-Brand

### Costi condivisi (pagati una volta)

| Servizio | Costo |
|----------|-------|
| VPS production | €10 |
| VPS staging | €10 |
| Vercel Pro | $20 |
| Tailscale | $0 |
| Sentry | $0 |

### Costi per brand aggiuntivo

| Servizio | Costo aggiuntivo |
|----------|-----------------|
| Supabase (stesso progetto, RLS) | $0 (fino a limiti piano) |
| AI API | +~$200-300/mese (proporzionale ai contenuti) |
| Serper | +~$30/mese (piu' query) |
| Resend | +~$10/mese (piu' email) |
| **Per brand aggiuntivo** | **~€230-320/mese** |

### Proiezione Multi-Brand

| # Brand | Costo totale/mese | Costo medio/brand |
|---------|-------------------|-------------------|
| 1 | ~€400 | €400 |
| 2 | ~€650 | €325 |
| 3 | ~€900 | €300 |
| 5 | ~€1.400 | €280 |
| 10 | ~€2.700 | €270 |

Economia di scala: il costo marginale per brand diminuisce perche' l'infrastruttura e' condivisa.

---

## Proiezione Ricavi vs Costi

### Scenario Conservativo (1 brand, primi 6 mesi)

| Mese | Costi | Ricavi Newsletter | Ricavi Affiliate | Ricavi Sponsor | Totale Ricavi | P/L |
|------|-------|-------------------|------------------|----------------|---------------|-----|
| 1 | €400 | €0 | €0 | €0 | €0 | -€400 |
| 2 | €400 | €0 | €50 | €0 | €50 | -€350 |
| 3 | €400 | €0 | €150 | €500 | €650 | +€250 |
| 4 | €400 | €0 | €200 | €800 | €1.000 | +€600 |
| 5 | €450 | €200 | €300 | €1.000 | €1.500 | +€1.050 |
| 6 | €450 | €300 | €400 | €1.200 | €1.900 | +€1.450 |

**Break-even stimato:** Mese 3

### Scenario Ottimistico (3 brand, mese 6+)

| Metrica | Valore |
|---------|--------|
| Costi totali (3 brand) | ~€900/mese |
| Ricavi newsletter (3 brand) | ~€1.500/mese |
| Ricavi affiliate | ~€800/mese |
| Ricavi sponsorship | ~€3.000/mese |
| **Ricavi totali** | **~€5.300/mese** |
| **Profitto** | **~€4.400/mese** |

---

## Ottimizzazione Costi

### Quick Wins
1. **Usare Sonnet dove possibile** — Opus solo per scrittura finale e synthesis. Sonnet costa ~10x meno.
2. **Caching risposte** — Se lo stesso contenuto viene richiesto piu' volte, servire da cache.
3. **Batch scoring** — Processare items in batch anziche' uno alla volta (meno overhead API).
4. **Ridurre frequenza ricerca** — 3 volte/settimana anziche' giornaliera se il volume e' basso.

### Alert e Guardrails
- **Budget giornaliero**: alert a 80% del budget, pausa agenti a 100%
- **Budget mensile**: alert a 90%, notifica owner
- **Modello fallback**: se Opus non disponibile/troppo caro → Sonnet per scrittura
- **Kill switch**: endpoint per disabilitare tutti gli agenti immediatamente

### Monitoraggio Costi
- Dashboard `/costi-api` con breakdown in tempo reale
- Grafico trend 30 giorni
- Tabella per agente con tokens e costo
- Confronto budget allocato vs speso

---

## Pricing Modelli AI (Riferimento Aprile 2026)

| Modello | Input ($/1M token) | Output ($/1M token) | Note |
|---------|---------------------|----------------------|------|
| Claude Opus 4.6 | $15.00 | $75.00 | Scrittura principale |
| Claude Sonnet 4.6 | $3.00 | $15.00 | Scoring, adapting, GOD |
| Claude Haiku 4.5 | $0.25 | $1.25 | Classificazione leggera |
| GPT-4o | $2.50 | $10.00 | Brainstorming alternativo |
| Gemini 2.5 Pro | $1.25 | $5.00 | Panel review |
| text-embedding-3-small | $0.02 | — | Embedding per dedup |

*Prezzi via OpenRouter, possono variare. Verificare pricing aggiornato su openrouter.ai.*
