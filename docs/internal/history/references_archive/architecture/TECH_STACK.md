# Empty Box - Stack Tecnologico

> Documentazione completa di tutte le scelte tecnologiche del progetto Empty Box, con motivazioni e alternative valutate.

---

## Indice

1. [Infrastruttura Core](#infrastruttura-core)
2. [Modelli AI](#modelli-ai)
3. [Research e Scraping](#research-e-scraping)
4. [Distribuzione Contenuti](#distribuzione-contenuti)
5. [Strumenti di Sviluppo](#strumenti-di-sviluppo)
6. [Monitoring e Sicurezza](#monitoring-e-sicurezza)
7. [Mappa delle Dipendenze](#mappa-delle-dipendenze)

---

## Infrastruttura Core

### Panoramica

Lo stack e progettato per massimizzare la velocita di sviluppo di un team piccolo (1-2 persone), minimizzare i costi operativi e mantenere la flessibilita necessaria per iterare rapidamente. La preferenza va a soluzioni managed dove possibile, self-hosted dove necessario per costi o controllo.

### Tabella Decisioni

| Tecnologia | Ruolo | Perche | Alternative scartate |
|------------|-------|--------|---------------------|
| **Supabase** | Database + Auth + Storage + Realtime | PostgreSQL managed con pgvector integrato per embedding, RLS (Row Level Security) nativo per multi-tenancy tra brand, Auth pronta all'uso, Realtime per aggiornamenti live della dashboard, Edge Functions per logica server-side leggera. Un unico servizio che copre 5 esigenze. | **Firebase**: no SQL, query complesse impossibili, vendor lock-in Google. **Self-hosted PostgreSQL**: piu manutenzione, niente Auth/Realtime/Storage integrati, costo DevOps maggiore. **PlanetScale**: ottimo ma MySQL (non PostgreSQL), no pgvector nativo. |
| **Next.js 15** | Frontend + API Routes | React con Server Components per performance, App Router per routing flessibile, API Routes integrate per logica backend leggera (webhook handler, proxy API), deploy nativo su Vercel con zero-config. L'ecosistema React e il piu grande: shadcn/ui, librerie, talento disponibile. | **Remix**: ottimo framework ma ecosistema piu piccolo, meno componenti pronti, community piu ristretta. **SvelteKit**: performance eccellente ma meno maturita, meno librerie, curva di apprendimento per chi conosce React. **Astro**: ottimo per siti statici ma meno adatto a dashboard interattive. |
| **Python 3.12+** | Backend agents | Ecosistema AI/ML imbattibile: LangChain, LlamaIndex, transformers, scikit-learn. Librerie mature per scraping (BeautifulSoup, Scrapy). Async nativo con asyncio per operazioni I/O-bound (chiamate API parallele). Tipizzazione opzionale con type hints per codice mantenibile. | **Node.js/TypeScript**: ecosistema AI piu limitato, meno librerie per scraping, meno strumenti ML. Un unico linguaggio frontend+backend sarebbe comodo ma non compensa le lacune nell'ecosistema AI. |
| **n8n self-hosted** | Orchestrazione workflow | Workflow visuali per orchestrare i pipeline (research → scoring → generation → publish). Self-hosted per controllo completo e nessun limite di esecuzioni. Webhook trigger nativi, cron scheduler integrato, nodi custom in JavaScript. Facile debug visuale dei workflow. | **LangGraph**: potente per orchestrare agenti AI ma overkill per orchestrazione generale, curva di apprendimento alta, meno adatto a cron/webhook. **Temporal**: troppo enterprise, complessita eccessiva per un team piccolo. **Make/Zapier**: limiti di esecuzioni nel piano gratuito, costi elevati a scala, meno controllo. |
| **OpenRouter** | Hub API modelli AI | Un singolo endpoint per accedere a tutti i modelli (Claude, GPT, Gemini, Grok, open-source). Fallback automatico: se un modello e down, switcha su un altro. Billing unificato con una sola fattura. Rate limiting e caching integrati. Permette di cambiare modello senza toccare il codice. | **API dirette (Anthropic, OpenAI, Google)**: 3+ integrazioni separate, 3+ fatture, nessun fallback automatico, piu codice da mantenere. **LiteLLM**: buona alternativa open-source ma richiede self-hosting e manutenzione. |
| **Remotion** | Generazione video/carousel | React-to-video: si scrive un componente React e si renderizza come video MP4. Programmatico e data-driven: i dati del contenuto alimentano direttamente le animazioni. Perfetto per carousel Instagram e video TikTok generati automaticamente. | **FFmpeg puro**: troppo low-level, richiede conoscenza profonda di codec e filtri. **Canva API**: limiti di personalizzazione, costi elevati. **Creatomate**: buono ma meno flessibile di un approccio programmatico. |
| **Tailscale** | Networking VPN | VPN zero-config che crea una rete privata tra i server (VPS staging, VPS production, macchina di sviluppo). Setup in 5 minuti, nessun port forwarding, nessun firewall da configurare. Permette al frontend su Vercel di comunicare con il backend su VPS tramite URL privati. | **WireGuard manuale**: stessa tecnologia sottostante ma setup e manutenzione manuali. **Cloudflare Tunnel**: buona alternativa ma piu orientata a esporre servizi pubblici che a networking privato. |
| **Vercel** | Deploy frontend | Deploy automatico da GitHub push: ogni commit crea un preview deploy, merge su main va in production. Edge Functions per logica server-side distribuita globalmente. Analytics integrati. Zero-config per Next.js (sono gli stessi sviluppatori). | **Netlify**: buono ma meno ottimizzato per Next.js. **Self-hosted su VPS**: piu controllo ma piu manutenzione, niente preview deploys automatici, niente edge functions. **Cloudflare Pages**: promettente ma ecosistema Next.js meno maturo. |
| **Hostinger VPS x2** | Backend servers | Due VPS a ~10 euro/mese ciascuno: uno per staging, uno per production. Separazione netta degli ambienti. Abbastanza potenti per n8n + agenti Python. Costo totale ~20 euro/mese per l'intero backend. | **AWS/GCP/Azure**: overkill per le esigenze attuali, costi imprevedibili, complessita eccessiva. **Railway/Render**: piu costosi per workload always-on. **Un solo VPS**: rischio di rompere production durante lo sviluppo. |

---

## Modelli AI

### Strategia Multi-modello

Empty Box utilizza una strategia **multi-modello** deliberata: ogni modello e scelto per il task in cui eccelle. OpenRouter rende trasparente lo switching tra modelli.

### Tabella Modelli

| Modello | Ruolo nel sistema | Perche questo modello | Costo stimato |
|---------|-------------------|----------------------|---------------|
| **Claude Opus 4.6** | Scrittura principale (Writer + Editor). Genera newsletter, articoli blog, post LinkedIn lunghi. | Qualita di scrittura superiore, capacita di mantenere tono di voce coerente su testi lunghi, ragionamento profondo per argomentazioni complesse. Il migliore per output editoriale di alta qualita. | ~$15/M input, ~$75/M output |
| **Claude Sonnet** | Adattamento piattaforma (Adapter). Prende il contenuto generato da Opus e lo riformatta per ogni piattaforma social. | Ottimo rapporto qualita/prezzo per task piu strutturati e ripetitivi. Abbastanza intelligente da adattare tono e formato, abbastanza economico per volumi alti. | ~$3/M input, ~$15/M output |
| **Claude Code** | Workbot terminale. Debugging, deploy, automazione task di sviluppo, generazione codice, review PR. | Integrazione nativa con terminale e codebase. Capacita di navigare repository complessi, eseguire comandi, e iterare su codice. Indispensabile per velocita di sviluppo. | Incluso in abbonamento |
| **Grok 4.2** | Brainstorming e analisi competitiva. Usato per generare idee, analizzare trend, esplorare angoli creativi. | Accesso a dati X (Twitter) in tempo reale, tono piu diretto e meno "corporate", buono per pensiero laterale e prospettive non convenzionali. | ~$3/M input, ~$15/M output |
| **GPT 5.2 / 5.4** | Brainstorming e panel review. Partecipa come voce nel GOD System per diversificare le prospettive. | Eccelle in task di ragionamento strutturato e analisi critica. Utile come "seconda opinione" rispetto a Claude per evitare bias di modello singolo. | ~$5/M input, ~$15/M output |
| **Gemini 3.1 Pro / 3.2** | Panel review e analisi multimodale. Partecipa al GOD System, analizza immagini e video. | Context window enorme per analizzare documenti lunghi. Capacita multimodale nativa per valutare contenuti visivi. Prospettiva diversa da Claude e GPT. | ~$2/M input, ~$10/M output |
| **ElevenLabs** | Voice cloning per audio/video. Genera voce sintetica per video TikTok, podcast, audio newsletter. | Qualita vocale leader di mercato, clonazione voce con pochi minuti di campione, supporto multilingua, API robuste. | ~$0.30/1000 caratteri |

### Nota sui costi

I costi indicati sono stime basate sui listini di aprile 2026 e possono variare. Il monitoraggio costi API nella dashboard (modulo "Costi API") tiene traccia della spesa effettiva in tempo reale. Budget mensile target per i modelli AI: **150-300 euro/mese** a regime per un singolo brand con ~30 post/giorno.

---

## Research e Scraping

### Tabella Strumenti

| Tecnologia | Ruolo | Dettagli | Costo |
|------------|-------|----------|-------|
| **Serper** | Search engine primario | API Google Search results: restituisce risultati organici, news, immagini. 2500 query/mese nel piano gratuito, scalabile. Veloce e affidabile, JSON pulito. | Gratuito (2500 query), poi ~$50/mese per 50K query |
| **Firecrawl** | Scraping profondo | Scraping di singoli siti con estrazione strutturata del contenuto. Gestisce JavaScript rendering, anti-bot, rate limiting. Ideale per estrarre il testo completo di articoli da fonti specifiche. | ~$20/mese (5000 pagine) |
| **YouTube Data API** | Discovery video | Cerca video per keyword, monitora canali specifici, estrae metadati (titolo, descrizione, trascrizione). Gratuito con quota generosa. | Gratuito (10.000 unita/giorno) |
| **Feed Parser** | Gestione RSS | Libreria Python (`feedparser`) per parsare feed RSS/Atom. Gestisce 1000+ feed con scheduling intelligente (feed attivi piu frequenti, feed lenti meno frequenti). | Gratuito (libreria open-source) |

### Perche Serper e non Tavily

Tavily e stato valutato inizialmente come search engine per la ricerca. La scelta e ricaduta su Serper per:

- **Costo**: Serper offre piu query per euro
- **Risultati**: output piu pulito e strutturato
- **Affidabilita**: uptime superiore e latenza inferiore
- **Flessibilita**: supporto per ricerche news, immagini, e risultati locali
- **Comunita**: piu usato in produzione, piu documentazione disponibile

---

## Distribuzione Contenuti

### Tabella Strumenti

| Tecnologia | Ruolo | Dettagli | Perche |
|------------|-------|----------|--------|
| **Postiz** | Scheduling social multi-platform | Piattaforma open-source per scheduling e pubblicazione su LinkedIn, Instagram, Facebook, X, TikTok. Self-hosted sul VPS. Dashboard propria per gestione post. | **Open-source**: nessun costo di licenza, nessun limite di account o post. **Self-hosted**: controllo completo sui dati. **API**: integrabile con il nostro pipeline. Alternative come Buffer/Hootsuite costano 50-100 euro/mese e hanno limiti di post. |
| **Resend** | Email transazionali (MVP) | Servizio email moderno con API developer-friendly. Usato nella fase MVP per inviare la newsletter settimanale. Template React per email HTML. | **Developer experience**: API semplice, SDK per Node.js e Python, template in React (si riusa la competenza frontend). **Pricing**: generoso piano gratuito (3000 email/mese). **Deliverability**: buona reputazione IP. |
| **Beehiiv** | Newsletter platform (scala) | Piattaforma newsletter completa con gestione iscritti, segmentazione, analytics, monetizzazione. Migrazione pianificata quando la lista supera i 5000 iscritti. | **Funzionalita**: gestione lista, segmentazione, referral program, monetizzazione nativa. **Scalabilita**: gestisce centinaia di migliaia di iscritti. **Migrazione**: import facile da Resend. Usato nella fase di scala, non nell'MVP per semplicita. |

### Strategia di Migrazione Email

```
Fase 1 (MVP):     Resend → invio diretto, lista gestita su Supabase
Fase 2 (Crescita): Beehiiv → migrazione lista, gestione iscritti dedicata
Fase 3 (Scala):    Beehiiv + Resend → Beehiiv per newsletter, Resend per email transazionali
```

---

## Strumenti di Sviluppo

### Coding e AI Assistants

| Strumento | Ruolo | Perche |
|-----------|-------|--------|
| **Claude Code** | AI coding assistant primario | Integrazione terminale nativa, comprensione profonda del codebase, capacita di eseguire comandi e iterare. Usato per: scaffolding componenti, debugging, deploy, review PR, generazione test. Accelera lo sviluppo di 3-5x. |
| **gstack (Y Combinator)** | AutoPlan mode | Strumento Y Combinator per pianificazione automatica di task di sviluppo. Prende un obiettivo ad alto livello e genera un piano di esecuzione dettagliato con step e dipendenze. Utile per sessioni di sviluppo lunghe e strutturate. |
| **PIE (Daniel Messler)** | Personal assistant per sessioni Claude Code | Framework di Daniel Messler per gestire sessioni di sviluppo con AI. Organizza contesto, mantiene stato tra sessioni, gestisce prompt engineering per task complessi. |

### UI e Design

| Strumento | Ruolo | Perche |
|-----------|-------|--------|
| **shadcn/ui** | Component library | Componenti React accessibili, personalizzabili, non opinati. Non e una libreria (niente `node_modules`): si copia il codice del componente nel progetto e si personalizza. Perfetto per dashboard con design custom. Basato su Radix UI primitives. |
| **Tailwind CSS** | Utility-first CSS | Sviluppo UI velocissimo con classi utility. Nessun CSS custom da scrivere e mantenere. Ottima integrazione con shadcn/ui. Design system consistente con configurazione centralizzata (`tailwind.config`). |

### Perche questa combinazione

La scelta di **shadcn/ui + Tailwind** anziche una libreria UI completa (Material UI, Ant Design, Chakra) e deliberata:

- **Controllo**: il codice dei componenti e nel progetto, si puo modificare qualsiasi cosa
- **Performance**: nessuna dipendenza runtime pesante
- **Consistenza**: Tailwind forza un design system coerente
- **Velocita**: Claude Code genera componenti shadcn/ui + Tailwind in modo eccellente
- **Manutenibilita**: aggiornamenti indipendenti per ogni componente

---

## Monitoring e Sicurezza

### Tabella Strumenti

| Tecnologia | Ruolo | Dettagli | Perche |
|------------|-------|----------|--------|
| **Sentry** | Error tracking | Monitoraggio errori in tempo reale per frontend (Next.js) e backend (Python). Stack trace, breadcrumbs, performance monitoring. Alert su Slack/email per errori critici. | **Industry standard**: il piu usato per error tracking. **SDK**: integrazione nativa con Next.js e Python. **Piano gratuito**: generoso per volumi contenuti. **Source maps**: debugging preciso anche in produzione. |
| **Supabase Vault** | Secrets management | Gestione sicura delle chiavi API e credenziali. Integrato nativamente con Supabase, accessibile via SQL e API. Crittografia at-rest. | **Integrazione nativa**: nessun servizio esterno da gestire. **Semplicita**: accesso diretto dal backend tramite Supabase client. **Sicurezza**: crittografia AES-256, audit log. Alternative come HashiCorp Vault sono overkill per la scala attuale. |
| **GitHub Actions** | CI/CD | Pipeline di continuous integration e deployment. Test automatici su ogni PR, deploy automatico su merge in main. Workflow per: linting, type checking, test unitari, deploy frontend (Vercel), deploy backend (VPS via SSH). | **Integrazione GitHub**: zero setup aggiuntivo. **Gratuito**: 2000 minuti/mese per repo privati. **Ecosistema**: migliaia di action preconfigurate. Alternative come GitLab CI o CircleCI richiederebbero setup e integrazione aggiuntivi. |

### Pipeline CI/CD

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Push/PR su  │────▶│  GitHub      │────▶│  Test +      │
│  GitHub      │     │  Actions     │     │  Lint +      │
│              │     │  trigger     │     │  Type Check  │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                    ┌─────────────┴─────────────┐
                                    │                           │
                              ┌─────▼─────┐              ┌─────▼─────┐
                              │  Frontend  │              │  Backend   │
                              │  → Vercel  │              │  → VPS     │
                              │  (auto)    │              │  (SSH)     │
                              └───────────┘              └───────────┘
```

### Strategia di Sicurezza

| Livello | Misura | Implementazione |
|---------|--------|-----------------|
| **Autenticazione** | Auth multi-provider | Supabase Auth con email/password + OAuth (Google, GitHub) |
| **Autorizzazione** | Row Level Security | RLS PostgreSQL: ogni brand vede solo i propri dati |
| **Secrets** | Crittografia at-rest | Supabase Vault per API keys, mai nel codice o in `.env` committati |
| **Network** | VPN privata | Tailscale tra VPS e servizi interni, nessuna porta esposta |
| **Codice** | Review automatica | GitHub Actions: linting, type checking, dependency audit |
| **Errori** | Monitoraggio real-time | Sentry con alert immediati per errori critici |
| **Backup** | Backup automatici | Supabase backup giornalieri + script custom settimanale su storage esterno |

---

## Mappa delle Dipendenze

Visualizzazione di come le tecnologie si connettono tra loro nel sistema.

```
                    ┌──────────────────────┐
                    │     UTENTE/UMANO     │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Next.js 15         │
                    │   (Vercel)           │
                    │   + shadcn/ui        │
                    │   + Tailwind         │
                    └──┬───────────────┬───┘
                       │               │
            ┌──────────▼──┐    ┌───────▼────────┐
            │  Supabase   │    │  Python 3.12+  │
            │  - PostgreSQL│    │  (Hostinger    │
            │  - Auth     │    │   VPS x2)      │
            │  - Storage  │    └───┬────┬───┬───┘
            │  - Realtime │        │    │   │
            │  - Vault    │    ┌───▼┐ ┌─▼─┐ │
            └─────────────┘    │n8n │ │   │ │
                               └──┬─┘ │   │ │
                 ┌────────────────┘    │   │ │
                 │    ┌────────────────┘   │ │
                 │    │    ┌───────────────┘ │
                 │    │    │    ┌────────────┘
           ┌─────▼────▼────▼────▼──────────────┐
           │         OpenRouter                 │
           │  ┌────────┐ ┌─────┐ ┌──────┐     │
           │  │Claude  │ │ GPT │ │Gemini│     │
           │  │Opus/   │ │5.2/ │ │3.1/  │     │
           │  │Sonnet  │ │5.4  │ │3.2   │     │
           │  └────────┘ └─────┘ └──────┘     │
           │  ┌────────┐                       │
           │  │ Grok   │                       │
           │  │ 4.2    │                       │
           │  └────────┘                       │
           └───────────────────────────────────┘

           ┌───────────────────────────────────┐
           │         SERVIZI ESTERNI           │
           │  ┌────────┐ ┌─────────┐           │
           │  │ Serper │ │Firecrawl│           │
           │  └────────┘ └─────────┘           │
           │  ┌────────┐ ┌─────────┐           │
           │  │YouTube │ │Eleven   │           │
           │  │Data API│ │Labs     │           │
           │  └────────┘ └─────────┘           │
           │  ┌────────┐ ┌─────────┐           │
           │  │ Postiz │ │ Resend/ │           │
           │  │        │ │ Beehiiv │           │
           │  └────────┘ └─────────┘           │
           └───────────────────────────────────┘

           ┌───────────────────────────────────┐
           │         DEVOPS                    │
           │  ┌────────┐ ┌─────────┐           │
           │  │GitHub  │ │ Sentry  │           │
           │  │Actions │ │         │           │
           │  └────────┘ └─────────┘           │
           │  ┌──────────┐                     │
           │  │Tailscale │                     │
           │  └──────────┘                     │
           └───────────────────────────────────┘
```

---

## Stima Costi Mensili (Per Brand)

| Voce | Costo stimato | Note |
|------|---------------|------|
| **Supabase** | €0-25 | Piano gratuito sufficiente per MVP, Pro a ~€25/mese |
| **Vercel** | €0-20 | Piano gratuito per hobby, Pro a ~€20/mese |
| **Hostinger VPS x2** | €20 | ~€10/mese ciascuno, staging + production |
| **OpenRouter (modelli AI)** | €150-300 | Variabile in base al volume di contenuti |
| **Serper** | €0-50 | Gratuito fino a 2500 query, poi €50/mese |
| **Firecrawl** | €20 | Piano base 5000 pagine/mese |
| **ElevenLabs** | €5-30 | Variabile in base ai minuti di audio generati |
| **Postiz** | €0 | Open-source, self-hosted |
| **Resend** | €0-20 | Gratuito fino a 3000 email/mese |
| **Sentry** | €0 | Piano gratuito sufficiente |
| **Tailscale** | €0 | Piano gratuito per uso personale |
| **GitHub Actions** | €0 | 2000 minuti/mese gratuiti |
| **Dominio + DNS** | €10-15 | Costo annuale ripartito |
| **TOTALE** | **€200-500/mese** | Variabile, ~€300/mese atteso a regime |

### Nota sulla Scalabilita dei Costi

Il costo dominante e quello dei modelli AI via OpenRouter. Strategie di ottimizzazione:

- **Caching**: risposte simili vengono cachate per evitare chiamate duplicate
- **Modello giusto per il task giusto**: Sonnet (economico) per task ripetitivi, Opus (costoso) solo per scrittura di alta qualita
- **Batching**: raggruppare le chiamate API dove possibile
- **Prompt optimization**: prompt piu corti e mirati riducono i token di input

---

*Ultimo aggiornamento: Aprile 2026*
*Progetto: Empty Box Content Engine*
