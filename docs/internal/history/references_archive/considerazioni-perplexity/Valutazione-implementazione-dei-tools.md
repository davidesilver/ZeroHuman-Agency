## Valutazione: Implementation Plan + Walkthrough

### Quadro generale

Il piano è tecnicamente coerente nella direzione, ma ha un problema strutturale: **ha aggiunto 5 integrazioni contemporaneamente su una base che ha ancora zero test e il brand hardcoded**. È come installare un turbo su un motore non ancora collaudato. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

Il `walkthrough.md` presenta le modifiche come "validate" — ma "sintassi senza errori" ≠ "funziona in produzione". In un sistema multi-agente con cron notturni, quella distinzione è critica.

***

### Cosa è stato fatto bene (genuinamente)

**OpenRouter dynamic routing** — routing per `complexity` (Haiku/Sonnet/o3-mini) è esattamente la cosa giusta. Marco spende ~$500/mese usando Opus per tutto. Questo taglia il 40-60% dei costi LLM.

**Postiz come layer unificato** — corretto. Un'API key, 5 piattaforme. Non c'era alternativa sensata.

**Firecrawl al posto di BeautifulSoup/Trafilatura** — upgrade concreto di qualità per il Writer Agent. RSS + scraping classico rotto è uno dei colli di bottiglia reali di Marco.

**AutoResearch come service separato** — la scelta di salvare i prompt vincenti su Supabase invece di riscrivere i `.py` a runtime è la risposta corretta alla domanda aperta del piano. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

### I problemi reali

**1. Context 7 MCP nel backend: latenza non giustificata per il tuo caso d'uso**

Il piano inserisce un MCP client che chiama Context 7 per documentazione live prima di ogni scrittura. Il problema: il tuo Content Engine produce contenuti su AI, business, produttività per il mercato italiano — non è un technical writer per documentazione di framework. Context 7 aggiunge 300-800ms di latenza per ogni articolo, una dipendenza esterna in più con tier gratuita limitata, e valore reale vicino allo zero sul 95% dei contenuti che produrrai. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

Questa è **cargo cult di Marco** — lui la nomina, sembra avanzata, l'hai aggiunta. Ma Marco la userebbe per un pubblico developer. Il tuo audience è "il piccolino": freelance, partite IVA, imprenditori. Context 7 avrebbe senso per un blog tecnico su Next.js o Tailwind v4.

**Cosa avrei fatto**: configurabile per brand via `knowledge_base.use_context7: boolean` nella BrandConfig — opzionale, non nel core.

**2. AutoResearch senza guardrail: rischio di ottimizzazione locale verso un massimo sbagliato**

Il `autooptimizer.py` propone variazioni ai prompt, misura lo score LLM, propaga i vincenti come nuovi default. Ma manca il pezzo critico: chi valida che il prompt "vincente" secondo lo score LLM non stia ottimizzando verso qualcosa di sbagliato? Uno score LLM che valuta un LLM è un loop chiuso. Un prompt che migliora lo score interno di 1.5 punti può peggiorare l'open rate reale. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

Mancano: un ceiling sulla deviazione dal baseline (es. max 20% di modifica per ciclo), un flag `human_review_required` per variazioni oltre soglia, e il collegamento con le metriche reali di `social_metrics` come segnale di verità.

**3. Pillo/PostNitro per carousel: dipendenza esterna che fallisce silenziosamente**

La `visual_generator.py` aggiunge un'API esterna per carousel senza avere ancora un sistema di alerting. Se il carousel non viene generato, il draft va in produzione senza immagine e il post LinkedIn esce con solo testo. Non lo sai perché non hai ancora il webhook Telegram di monitoring.

**Ordine sbagliato**: prima l'alerting, poi le dipendenze esterne per feature visual.

**4. GOD System con Think-Plan-Build-QA: costo non documentato**

La ristrutturazione con fasi aggiuntive ispirate a gstack aggiunge chiamate LLM senza documentare quante. Se ogni draft passa da 4 a 6-7 chiamate, il costo per draft sale del 50-75%. Su 10 draft/giorno × 30 giorni è impatto reale — non è stata fatta l'analisi costo/beneficio prima di implementarla. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

### Risposta diretta alla domanda aperta del piano

"Postiz Cloud o self-hosting Docker?" — **Cloud, senza dubbi, adesso.** Self-hosting aggiunge un server da mantenere, aggiornamenti di sicurezza, monitoring del container. Il tuo vantaggio competitivo non è nell'infrastruttura Postiz. Paga i $29/mese. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

### Cosa avrei fatto io, in ordine diverso

**Fase A — Fondamenta prima di tutto**

1. Multi-brand middleware (sblocca tutto il resto)
2. 3 test critici (scoring, dedup, god mode failure)
3. Alert Telegram (visibilità sui fallimenti)
4. GOD Mode in parallelo (costo -60%)

**Fase B — Integrazioni, una alla volta**

1. Postiz
2. OpenRouter dynamic routing
3. Firecrawl
4. AutoResearch con guardrail definiti
5. pgvector dedup semantica

Context 7 MCP e Pillo → backlog "valuta per brand specifici".

***

### Sintesi

Hai buon fiuto sui tool giusti. Postiz, OpenRouter, Firecrawl, AutoResearch sono tutti nella direzione corretta. Il problema è l'ordine e la densità: 5 integrazioni in parallelo su fondamenta non consolidate, con una dipendenza (Context 7) che non serve il tuo caso d'uso attuale, e senza guardrail sulla feature (AutoResearch) che può degradare silenziosamente la qualità nel tempo. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

Non è un errore di visione — è un errore di sequ
