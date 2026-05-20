# Triage candidati di integrazione — ZeroHuman-Agency

> Data: 2026-05-15
> Scopo: valutare ~17 candidati eterogenei (repo GitHub, MCP server, API, skills, plugin marketplace) per stabilire **se**, **come** e **dove** integrarli nel Content Engine. Questo documento NON è un piano di implementazione: è la base decisionale che precede il PRD.
> Output successivi: (1) capability map → (2) shortlist → (3) PRD sui gruppi sopravvissuti → (4) plan via `/prd-to-plan`.

---

## Contesto attuale del repo

ZeroHuman-Agency (a.k.a. **Content Engine**) è una piattaforma multi-tenant per operazioni di contenuto AI: research → ideation → generation → multi-agent review → publishing.

Stack:
- Frontend: Next.js 16, React 19, TS, Tailwind 4, Supabase
- Backend: Python 3.14 + FastAPI, moduli `agents/retrievers/scoring/orchestrator/memory/services/prompts`
- LLM: Anthropic (preferito), OpenAI, OpenRouter
- Integrazioni vive: Postiz (satellite), Resend, Replicate/OpenAI/Pillo (immagini), Serper, YouTube, Firecrawl, MCP, Telegram
- Skills system in `skills-lock.json` (oggi: solo Supabase best practices)

<<<<<<< HEAD
Possible integration modes (important to distinguish them):

| Mode | What it means | When to use it |
|------|---------------|----------------|
| **Skill / Claude plugin** | Added to `.claude/skills/` or `skills-lock.json` or `/plugin marketplace add`. Available only to the Claude Code agent in dev | Knowledge / workflow for us as developers, not for end users |
| **MCP server** | Exposed as an MCP tool to Claude (and theoretically to the Python backend via `mcp>=1.0.0` already present) | Runtime capability that the agentic system must use (e.g. scraping, research) |
| **Python/Node dependency in code** | `pip add` / `npm add` and direct import | Product functionality that becomes part of the Content Engine |
| **External satellite (like Postiz)** | Separate container, communicates via HTTP API | Heavy system with its own UI, independent release cycle, laterally multi-tenant |
| **Reference / pattern** | Study only, no code imported | Educational repos (e.g. awesome-lists, prompt guides) |
=======
Modalità di integrazione possibili (importante distinguerle):

| Modalità | Cosa significa | Quando usarla |
|----------|----------------|---------------|
| **Skill / plugin Claude** | Aggiunto a `.claude/skills/` o `skills-lock.json` o `/plugin marketplace add`. Disponibile solo all'agente Claude Code in dev | Knowledge / workflow per noi sviluppatori, non per gli utenti finali |
| **MCP server** | Esposto come tool MCP a Claude (e teoricamente al backend Python via `mcp>=1.0.0` già presente) | Capability runtime che il sistema agentico deve usare (es. scraping, ricerca) |
| **Dipendenza Python/Node nel codice** | `pip add` / `npm add` e import diretto | Funzionalità di prodotto che diventa parte del Content Engine |
| **Satellite esterno (come Postiz)** | Container separato, comunica via HTTP API | Sistema pesante con UI propria, ciclo di rilascio indipendente, multi-tenant lateralmente |
| **Riferimento / pattern** | Solo studio, niente codice importato | Repo educativi (es. awesome-lists, prompt guides) |
>>>>>>> claude/magical-newton-4dd601

---

## Triage per candidato

Legenda colonne:
- **Fit**: ★ = scarso, ★★ = marginale, ★★★ = forte, ★★★★ = strategico
- **Modalità**: come l'integreremmo (vedi tabella sopra)
- **Sovrap.**: cosa nel repo lo rende ridondante o lo completa

### Gruppo A — Generazione video AI

#### A1. `HKUDS/ViMax`
- **Cosa**: framework di video generation accademico (Hong Kong University Data Science). Tipicamente research-grade, pesante su GPU.
- **Fit**: ★★ — il Content Engine non genera video oggi, ma potrebbe. Però è research, non production-ready.
- **Modalità**: nessuna diretta. Eventualmente API esterna se hostato altrove, altrimenti skip.
- **Sovrap.**: nessuna (nessun video oggi).
- **Rischio**: licenza accademica spesso non-commerciale, GPU cost, drift di manutenzione.
- **Verdetto**: **PARK** — segnare come opzione futura quando video diventa requisito.

#### A2. `AIDC-AI/Pixelle-Video`
- **Cosa**: text-to-video / image-to-video da Alibaba DAMO. Più production-friendly di ViMax di solito.
- **Fit**: ★★★ se aggiungiamo video alla pipeline di content.
- **Modalità**: API esterna (se disponibile via Replicate / fal.ai) → backend Python come retriever/generator.
- **Sovrap.**: complementare a Replicate già configurato.
- **Verdetto**: **CANDIDATO SHORTLIST** condizionale a "video è una capability del prodotto".

#### A3. `heygen-com/hyperframes`
- **Cosa**: SDK Heygen per video con avatar AI (talking head, lip sync).
- **Fit**: ★★★★ se vogliamo "personaggi del brand" che parlano (e.g. founder video LinkedIn auto-generati). Caso d'uso preciso e differenziante.
- **Modalità**: dipendenza Node/Python nel codice, API key Heygen, nuovo modulo `python/.../generators/video_avatar.py`.
- **Sovrap.**: complementare alle immagini esistenti — è il prossimo livello.
- **Costo**: Heygen è a consumo, da contabilizzare per tenant.
- **Verdetto**: **CANDIDATO SHORTLIST** se video-avatar è strategico per il GTM.

#### A4. `remotion-dev/remotion`
- **Cosa**: framework React per generare video programmaticamente (lo stack già lo supporta: React 19 ✅).
- **Fit**: ★★★★ — è il match più naturale dello stack. Permette composition di video da dati (es. carousel → reel, analytics → recap video).
- **Modalità**: dipendenza Node in monorepo, modulo `src/lib/video/` o servizio renderer separato (Remotion Lambda).
- **Sovrap.**: complementa Pillo (carousel) e immagini Replicate.
- **Verdetto**: **SHORTLIST FORTE**. Se entra video nel prodotto, Remotion è il fondo dello stack.

#### A6 / Higgsfield (vedi sotto C2)

---

### Gruppo B — Animazione / motion

#### B1. `greensock/gsap-skills` (plugin marketplace)
- **Cosa**: skills Claude per usare GSAP (libreria animazione web).
- **Fit**: ★★ — animazioni dashboard / landing page, ma non è core business.
- **Modalità**: skill Claude (dev-time), zero impatto runtime.
- **Sovrap.**: nessuna (`tw-animate-css` è in `package.json` ma è altra cosa).
- **Verdetto**: **NICE-TO-HAVE** — installare quando si fa front-end polish. Zero rischio.

---

### Gruppo C — Generative AI / image / video orchestration

#### C1. `Anil-matcha/Open-Generative-AI`
- **Cosa**: tipicamente aggregatori open-source di generative AI providers.
- **Fit**: ★★ — già abbiamo provider abstraction (Anthropic / OpenAI / OpenRouter / Replicate / Pillo).
- **Sovrap.**: alta. Probabilmente reinventa quello che il backend Python fa già nei `services/`.
- **Verdetto**: **SKIP** salvo evidenza specifica di feature mancante.

#### C2. MCP Higgsfield
- **Cosa**: Higgsfield AI = video generation con motion control / cinematic.
- **Fit**: ★★★ — video con qualità "cinema", buon match per content premium.
- **Modalità**: MCP server → consumato da Claude in dev + backend Python via `mcp` (già dependency).
- **Sovrap.**: si sovrappone a A2/A3. Va scelto **uno** dei tre per categoria "video premium".
- **Verdetto**: **CANDIDATO** in competizione con Heygen e Pixelle. Probabilmente Higgsfield se "B-roll cinematic", Heygen se "talking head".

---

### Gruppo D — Email / outbound

#### D1. **Brevo API**
- **Cosa**: ESP completo (transazionali + marketing + automations + SMS + CRM lite). Forte in EU/IT (GDPR-friendly).
- **Fit**: ★★★★ — il Content Engine già usa Resend per transazionali (newsletter). Brevo aggiunge marketing automation e segmenti.
- **Modalità**: dipendenza Python (`sib-api-v3-sdk` o HTTP), nuovo modulo `services/brevo.py`, env `BREVO_API_KEY`. Affianca Resend, non lo sostituisce subito.
- **Sovrap.**: parziale con Resend → decidere se Brevo prende tutto o solo marketing.
- **Verdetto**: **SHORTLIST FORTE** — Brevo è il pezzo che oggi manca per chiudere il loop "content → distribuzione email targettizzata".

---

### Gruppo E — Context / memory engineering

#### E1. `mksglu/context-mode`
- **Cosa**: gestione modi di contesto / prompt routing.
- **Fit**: ★★ — `python/src/content_engine/memory/` e `prompts/` esistono già.
- **Sovrap.**: alta.
- **Verdetto**: **STUDIO** — leggere i pattern, eventualmente portarli nel modulo `memory` esistente. Non importare il pacchetto.

#### E2. `xming521/weclone`
- **Cosa**: clona uno "stile" personale (originariamente da WeChat) per generazione AI con voce/scrittura specifica.
- **Fit**: ★★★ — overlap forte con "brand voice intelligence" che è un differenziatore dichiarato del prodotto.
- **Modalità**: pattern → integrare nel modulo brand voice esistente (`Humanizer` citato in PROJECT_DESCRIPTION). NON importare codice intero: è poco manutenuto tipicamente.
- **Sovrap.**: la feature *esiste già* nel prodotto. WeClone serve come riferimento per migliorarla.
- **Verdetto**: **STUDIO / RIFERIMENTO** — non integrare come dipendenza.

---

### Gruppo F — Research

#### F1. `LearningCircuit/local-deep-research`
- **Cosa**: deep research locale (multi-step research agent senza dipendere da OpenAI Researcher).
- **Fit**: ★★★★ — il prodotto ha già `retrievers/` e research scoring. Local deep research aggiunge "research profondo agentico" che oggi è semplice retrieval.
- **Modalità**: dipendenza Python, nuovo `retrievers/deep_research.py`, opzionalmente come "GOD Mode research" parallelo al "GOD Mode review" esistente.
- **Sovrap.**: complementare (alza il livello dei retrievers attuali).
- **Verdetto**: **SHORTLIST** — bel match.

---

### Gruppo G — Scraping / extraction

#### G1. `D4Vinci/Scrapling`
- **Cosa**: scraping stealth con auto-healing selectors. Antibot-aware.
- **Fit**: ★★★ — Firecrawl è già configurato come premium, trafilatura come fallback. Scrapling è una terza opzione (open-source, controllo totale).
- **Modalità**: dipendenza Python, fallback layer in `retrievers/`.
- **Sovrap.**: alta con Firecrawl → ridondante salvo cost-sensitive use cases.
- **Verdetto**: **PARK** — utile se Firecrawl costi diventano un problema o se serve scraping su siti antibot-pesanti.

---

### Gruppo H — Trading agents (off-topic)

#### H1. `The-Swarm-Corporation/AutoHedge`
- **Cosa**: agenti per hedging finanziario.
- **Fit**: ★ — fuori dominio. Content Engine non è una piattaforma fintech.
- **Verdetto**: **SKIP**. Se ti interessa come pattern di multi-agent coordination, c'è già il "GOD Mode review" interno: studialo lì.

---

### Gruppo I — Agency / multi-agent patterns

#### I1. `msitarzewski/agency-agents`
- **Cosa**: pattern multi-agente per agenzie.
- **Fit**: ★★ — `agents/` già esiste con Critic/Fact-Checker/Creative/Synthesis.
- **Verdetto**: **STUDIO** — leggere, eventualmente assorbire pattern interessanti. Non importare.

---

### Gruppo J — Skills collection (dev-time per Claude Code)

#### J1. Top repo da [Image #1] (Instagram list)
Top 12 repo Claude Code (153k–17k stars):
1. `affaan-m/everything-claude-code` — collezione generica
2. `shanraisshan/claude-code-best-practice` — best practices
3. `obra/superpowers` — set di skills "potenziati"
4. `thedotmack/claude-mem` — memory layer
5. `forrestchang/andrej-karpathy-skills` — skill style Karpathy
6. `hesreallyhim/awesome-claude-code` — awesome list
7. `yamadashy/repomix` — repo flattening per LLM
8. `gsd-build/get-shit-done` — productivity workflow
9. `dair-ai/Prompt-Engineering-Guide` — pure docs
10. `anthropics/skills` — official (già parzialmente in uso)
11. `VoltAgent/awesome-claude-code-subagents` — awesome list subagent
12. `VoltAgent/awesome-design-md` — awesome list design markdown

⚠️ Nota dal commento `pnic7690` su quel post: "spesso vanno in conflitto se installate in contemporanea... bisogna selezionare quella giusta per ogni progetto." → **Non installare tutto**: cherry-picking guidato.

- **Modalità**: skills Claude / plugin marketplace, dev-time. Zero impatto runtime.
- **Verdetto per voce**:
  - `obra/superpowers` → **SHORTLIST** (alto valore segnalato in comment)
  - `thedotmack/claude-mem` → **SHORTLIST** (memory è core nel prodotto e nel workflow dev)
  - `yamadashy/repomix` → **INSTALL** (utile per dump repo a LLM, zero rischio)
  - `anthropics/skills` → **ALREADY** (parzialmente usato già)
  - tutti gli `awesome-*` e `Prompt-Engineering-Guide` → **REFERENCE** (bookmark, non installare)
  - altri → **VALUTARE caso-per-caso** dopo i 3 sopra

#### J2. `leonxlnx/taste-skill`
- **Cosa**: skill "taste" per giudizio estetico/qualitativo.
- **Fit**: ★★★ — utile per il modulo Critic / Creative del GOD Mode review.
- **Modalità**: skill Claude, prima sperimentale.
- **Verdetto**: **TRY** — basso costo di prova.

#### J3. `skills.sh` (best skills)
- **Cosa**: marketplace community.
- **Verdetto**: **AUDIT** — pescare 3-5 skill specifiche per esigenze nostre (brand voice, content review). Non bulk-install.

---

### Gruppo K — Model providers

#### K1. OpenClaw model providers (subscription)
- **Cosa**: OpenClaw espone connettori a molti modelli (anche premium) via abbonamento unificato.
- **Fit**: ★★★ — abbiamo già Anthropic + OpenAI + OpenRouter. OpenClaw può **sostituire** OpenRouter come hub se l'economia è migliore, o complementare per modelli non coperti.
- **Modalità**: nuovo provider in `services/llm/` del backend Python, env var, feature flag per A/B.
- **Sovrap.**: alta con OpenRouter — è un'alternativa, non un'aggiunta. Decisione **commerciale**, non tecnica.
- **Verdetto**: **VALUTAZIONE COMMERCIALE** — confronto costi vs OpenRouter su modelli realmente usati. Tecnicamente facile da aggiungere.

---

## Capability map (dopo triage)

Raggruppando per capability di prodotto:

| Capability | Stato oggi | Candidati | Decisione preliminare |
|------------|------------|-----------|------------------------|
| **Video generation programmatico** | Assente | Remotion, Pixelle, Heygen, Higgsfield, ViMax | **Remotion** come base + **uno** di {Heygen | Higgsfield} per AI generation |
| **Email marketing automation** | Solo transazionale (Resend) | Brevo | **Brevo** affianca Resend |
| **Deep research** | Retrievers semplici | local-deep-research | **Adottare** |
| **Brand voice clone** | Humanizer esistente | weclone | **Studiare**, non importare |
| **Animazione web (dashboard)** | tw-animate-css | gsap-skills | Nice-to-have, installare al bisogno |
| **Scraping antibot** | Firecrawl + trafilatura | Scrapling | Park (ridondante oggi) |
| **Multi-agent patterns** | GOD Mode review | agency-agents | Studio |
| **Model provider hub** | OpenRouter | OpenClaw | Decisione commerciale |
| **Dev-time Claude skills** | Solo Supabase | superpowers, claude-mem, repomix, taste-skill, skills.sh picks | Installazione mirata, NON bulk |
| **Context/prompt routing** | memory/prompts esistenti | context-mode | Studio |
| **Trading** | N/A | AutoHedge | Skip (off-topic) |
| **Generative AI aggregator** | services/ esistente | Open-Generative-AI | Skip (sovrapposto) |

---

## Shortlist proposta per il PRD

Da portare al passo successivo (PRD → poi `/prd-to-plan`), ordinata per impatto:

### Tier 1 — Strategico, alto ROI atteso
1. **Brevo integration** → email marketing & automations multi-tenant
2. **Remotion + (Heygen | Higgsfield)** → capability video AI (decisione single-pick tra Heygen e Higgsfield)
3. **local-deep-research** → research agent profondo, evoluzione naturale dei retrievers

### Tier 2 — Tattico, basso costo
4. **OpenClaw provider** → confronto economico vs OpenRouter (probabilmente solo POC)
5. **Skills mirate per Claude Code dev**: `obra/superpowers`, `thedotmack/claude-mem`, `yamadashy/repomix`, `leonxlnx/taste-skill`

### Tier 3 — Park / Studio
6. WeClone, context-mode, agency-agents — **leggere**, eventualmente assorbire pattern interni
7. ViMax, Pixelle, Scrapling, gsap-skills — **revisitare** quando emerge necessità specifica

### Skip definitivi
- AutoHedge (off-topic)
- Open-Generative-AI (sovrapposto)
- Awesome-lists e Prompt-Engineering-Guide come *installazioni* (vanno usati come bookmark)

---

## Domande aperte prima del PRD

1. **Video è davvero una capability che vogliamo aggiungere al Content Engine?** Se no, salta tutto il Gruppo A.
2. **Heygen vs Higgsfield**: vogliamo "talking head con avatar brand" o "B-roll cinematico"? Sono use case diversi.
3. **Brevo affianca o sostituisce Resend?** Influisce su quanto migrare.
4. **OpenClaw è una sostituzione di OpenRouter o un'aggiunta?** Influisce sulla scope del lavoro provider-side.
5. **Le skill Claude dev-time vanno in `skills-lock.json` (committed) o solo nel `.claude/` locale dello sviluppatore?** Affecta la portabilità del team.
