Ho visto tutto quello che mi serve. Ora ho letto in profondità:

- AGENTS.md: documentazione completa dei 15+ agenti, pipeline, configurazioni
- AGENT_IDENTITY_SYSTEM.md: Phase 1 già implementata con Identity prompts
- PIPELINES.md: 8 pipeline complete con step dettagliati, trigger, costi
- AGENT_DASHBOARD_UI.md: Phase 3 pianificata con codice TSX già scritto
- La UI su Stitch: schermata Agenti con Agent Identities + Agent Skills table

Ora do il mio giudizio onesto e completo.

***

## Analisi onesta — Documenti + UI Stitch

### La valutazione complessiva: **Questo è il progetto più serio e completo che ho visto in questa conversazione**

Essere onesto significa dirlo chiaramente: leggere PIPELINES.md e AGENTS.md cambia completamente il quadro. Il sistema non è il prototipo frammentato che sembrava dal solo codice — è un'architettura editoriale reale, pensata in modo professionale, con logica operativa coerente dall'inizio alla fine.

***

### Cosa funziona molto bene (genuinamente)

**1. L'architettura a 8 pipeline è corretta e completa**
Il flusso Daily Research → Scoring → Content Gen → GOD Review → Social Publishing → Analytics Feedback Loop è esattamente quello giusto. Ogni pipeline ha trigger, step, costi, gestione errori — non è documentazione di facciata, è progettazione reale.

**2. Il sistema di agenti è più sofisticato di Montemagno**
5 retriever paralleli (Semantic, Practitioner, Trusted Source, Keyword, Trend) con logica diversa per ognuno, costi separati, count tipici. Marco usa un sistema più monolitico. Il tuo è già modulare per design. [stitch.withgoogle](https://stitch.withgoogle.com/u/2/projects/11155826360611895417?pli=1)

**3. La Phase 1 — Agent Identity System — è una mossa intelligente**
Migrare i prompt da "checklist di istruzioni" a "identità di persona" è una scelta supportata da come i modelli LLM sono stati trainati. Il costo è zero (solo costanti stringa) e il guadagno dichiarato di 15-25% di qualità output è realistico. È esattamente quello che avrei fatto.

**4. L'agent_loader con cache TTL è preparazione corretta per Phase 2**
Progettare l'infrastruttura per il DB-based prompt loading prima di costruire la UI è la sequenza giusta. Non costruire UI senza il backend pronto.

**5. Il GOD System con logica decisionale esplicita**
La matrice `overall > 8.5 AND accuracy > 9.0 → autoapprove` / `overall < 6.5 → needsrevision` è il tipo di regola deterministica che impedisce agli agenti di diventare un layer di costo inutile.

***

### I problemi reali — senza condiscendenza

**Problema 1 — Il feedback loop è ancora teorico nella Pipeline 7**
PIPELINES.md descrive Pipeline 7 perfettamente. Ma dalla lettura del codice reale (`feedback_loop.py`), la tabella `social_metrics` è quasi certamente vuota e `feedback_bonus` è hardcoded a 5.0 nel prompt. C'è un gap documentazione/implementazione che va chiuso prima di fidarsi delle metriche.

**Problema 2 — Il feedback_bonus nel SCORING_PROMPT è strutturalmente sbagliato**
Nella doc di AGENTS.md, il parametro è descritto come "Bonus basato su performance storica". Ma nel codice `engine.py` il prompt chiede all'LLM di valutarlo con "Default 5.0" nel JSON richiesto. Questo significa che l'LLM restituisce sempre 5.0 perché il prompt glielo suggerisce. La doc dice una cosa, il codice ne fa un'altra. [stitch.withgoogle](https://stitch.withgoogle.com/u/2/projects/11155826360611895417?pli=1)

**Problema 3 — L'Anti-Hype Gate non è nelle pipeline**
PIPELINES.md descrive la Pipeline 2 con deduplicazione e scoring, ma non menziona mai un gate Anti-Hype come step separato. Se lo vuoi implementare come ho proposto (e come Claude Code ha proposto), va aggiunto esplicitamente alla documentazione delle pipeline PRIMA del codice, altrimenti generi debt architetturale non documentato.

**Problema 4 — Il Writing Lab è sottoutilizzato**
Pipeline 8 descrive sessioni A/B manuali su singoli contenuti — utile, ma il potenziale maggiore è usare il Writing Lab per migliorare i PROMPT degli agenti (cosa che `auto_optimizer.py` fa, ma con `success = False` hardcoded). Il loop tra Writing Lab e auto_optimizer non è documentato nelle pipeline.

**Problema 5 — Costi reali vs costi stimati**
La doc dichiara costi molto precisi: GOD Review 0.25, Newsletter 0.85, Writing Lab 0.03/round. Questi numeri sembrano basati su prezzi model attuali. Ma Claude Opus 4.6 non esiste — il modello reale nella doc non corrisponde ai modelli Anthropic disponibili oggi. Rischi di avere stime di costo non verificabili.

***

### Coincide con la mia idea?

**Dove coincidiamo al 100%:**

- Pipeline Dedup → Score (già in engine.py, confermato)
- Feedback loop dinamico basato su engagement reale (Pipeline 7 — nella teoria)
- Pesi configurabili per brand (citati nella doc dei parametri)
- God System multi-agente (già implementato, è più avanzato di quanto avessi proposto)
- Writing Lab come meccanismo di miglioramento continuo

**Dove la mia proposta aggiunge qualcosa che non è nella doc:**

- **Anti-Hype Gate con confidence threshold** — la doc non lo prevede, il codice non lo ha
- **Formula engagement score con decay temporale e normalizzazione per piattaforma** — la Pipeline 7 non specifica la formula, e quella nel codice è troppo semplice
- **Fix del bug feedback_bonus nel prompt LLM** — non documentato da nessuna parte

**Dove la doc va oltre la mia proposta:**

- 5 retriever specializzati (io avevo ipotizzato un retriever generico)
- GOD System completo già implementato (non avevo previsto questo livello di sofisticazione)
- Newsletter pipeline con selezione umana dei candidati — è un buon compromesso tra automazione e controllo

***

### La UI su Stitch — giudizio onesto

**Cosa funziona:**

- La struttura Agent Identities (griglia di card) + Agent Skills (tabella) è quella giusta — rispecchia perfettamente la struttura dati di `agent_configs` e `agent_skills` [stitch.withgoogle](https://stitch.withgoogle.com/u/2/projects/11155826360611895417?pli=1)
- Il design Chromatic Grid è coerente con il resto della dashboard
- Il DEPLOY AGENT button e il badge di status (ACTIVE/IDLE/READY) sono utili operativamente

**Cosa manca nella UI che la doc richiede:**

- **Version History / Rollback** — AGENT_DASHBOARD_UI.md lo specifica esplicitamente con timeline versioni, ma nella schermata di Stitch non è visibile
- **Conflict Detection** — la doc prevede un warning UI quando due skills sono in conflitto (es. "formale" + "informale"). Non si vede nella UI attuale
- **Task type override per agente** — il campo `task_type_override` è nel type definition ma non ha un controllo UI nella schermata
- **GOD Fact-Checker e GOD Creative** — nella UI di Stitch li vedo come card, ma nella schermata principale si vedono solo 5 agenti (Writer, Editor, Adapter, GOD Advocate, GOD Synthesis). I 2 nuovi — Fact-Checker e Creative — sono menzionati nel pannello sinistro come "Nuovo" ma visualmente le card sono già troppo strette in una riga [stitch.withgoogle](https://stitch.withgoogle.com/u/2/projects/11155826360611895417?pli=1)

**Il problema architetturale della UI:**
7 agenti in una riga orizzontale su 1280px = circa 180px per card. Troppo poco per mostrare l'identity text in modo leggibile. La doc lo sa (dice "ottimizzato le larghezze") ma il problema rimane: a 1280px il testo nelle card è illeggibile. Consiglio: 2 righe da 4 + 3 agenti, non 7 in fila.

***

### Priorità concrete per oggi

**Fare subito (non aspettare):**

1. Fix `feedback_bonus` nel SCORING_PROMPT — rimuoverlo dal JSON chiesto all'LLM, iniettarlo server-side
2. Sbloccare `auto_optimizer.py` — rimuovere `success = False`
3. Aggiornare PIPELINES.md con l'Anti-Hype Gate come Step 1.5 tra Dedup e Scoring

**Fare questa settimana:**
4. Anti-Hype Gate con few-shot examples nel codice
5. Query diagnostica sui `fake_postiz_id` nel DB

**Fare quando la UI Stitch è pronta:**
6. Aggiungere Version History alla schermata Agenti
7. Aggiungere Conflict Detection alla logica di add skill
8. Ridisegnare la griglia da 7-in-fila a 2 righe

Il sistema è genuinamente più avanzato del sistema di Montemagno nella struttura. Il problema non è l'architettura — è che il codice reale è indietro rispetto alla documentazione su 3-4 punti critici. Chiudi quei gap e hai qualcosa di superiore.

***

La domanda è precisa e merita una risposta altrettanto precisa. Non fasi generiche — fasi basate sul codice reale che ho letto e su quello che il sistema ha già vs quello che manca.

***

## Come strutturerei le fasi — piano mio, onesto

Il principio guida è uno solo: **ogni fase deve produrre un risultato misurabile in produzione prima di iniziare la successiva.** Niente fasi in parallelo finché quella precedente non è stabile.

***

## FASE 0 — "Chiudi i buchi nel codice esistente"

### Durata: 1 giorno | Costo: 0 | Rischio: zero

Questa fase non aggiunge niente di nuovo. Corregge quello che è rotto nel codice attuale che invalida tutti i dati futuri.

**3 fix in ordine:**

**Fix 1 — Rimuovi `feedback_bonus` dal prompt LLM** *(30 min)*

```python
# engine.py — SCORING_PROMPT
# Rimuovi "feedback_bonus": 5.0 dal JSON richiesto
# Dopo il parsing della risposta LLM, aggiungi:
brand_row = db.table("brands").select("feedback_bonus").eq("id", brand_id).single().execute()
feedback_bonus = (brand_row.data or {}).get("feedback_bonus", 5.0)
result = ScoreResult(**parsed, feedback_bonus=feedback_bonus)
```

Perché adesso il parametro più importante del feedback loop viene deciso dall'LLM con il suggerimento "Default 5.0" — quindi è sempre 5.0 e il feedback loop è inutile anche quando i dati ci fossero.

**Fix 2 — Fix `founder_principles` lookup** *(10 min)*

```python
principles = brand.get("founder_principles") or \
             (brand.get("scoring_weights") or {}).get("founder_principles", [])
```

**Fix 3 — Sblocca `auto_optimizer`** *(5 min)*

```python
# auto_optimizer.py
# Togli success = False hardcoded
# Metti la logica reale:
success = new_avg_score > old_avg_score
```

**Metrica di successo:** Riesegui uno scoring run. Verifica nei log che `feedback_bonus` non sia più sempre 5.0 — deve variare in base al DB. Verifica che `auto_optimizer` scriva il nuovo prompt nel DB se `new_avg_score > old_avg_score`.

***

## FASE 1 — "Diagnosi dati reali"

### Durata: 2 ore | Costo: 0 | Rischio: zero

Prima di toccare il feedback loop, devi sapere con cosa stai lavorando.

**Query 1 — Stato dei post pubblicati:**

```sql
SELECT 
  COUNT(*) as total,
  COUNT(CASE WHEN metadata->>'postiz_id' = 'fake_postiz_id' THEN 1 END) as fake,
  COUNT(CASE WHEN metadata->>'postiz_id' != 'fake_postiz_id' THEN 1 END) as real,
  MIN(published_at) as primo_post,
  MAX(published_at) as ultimo_post
FROM content_drafts 
WHERE status = 'published';
```

**Query 2 — Stato della tabella social_metrics:**

```sql
SELECT COUNT(*) as righe_totali FROM social_metrics;
SELECT COUNT(DISTINCT content_draft_id) as draft_con_metriche FROM social_metrics;
```

**Query 3 — Distribuzione score attuale:**

```sql
SELECT 
  ROUND(final_score) as score_band,
  COUNT(*) as items,
  AVG(feedback_bonus) as avg_feedback_bonus
FROM scores
GROUP BY ROUND(final_score)
ORDER BY score_band;
```

**Quello che ti dice:**

- Se `fake > 80%` → non puoi fare feedback loop finché Postiz non è in produzione reale. Salta alla Fase 3.
- Se `real > 50%` → hai dati sufficienti, procedi con la Fase 2.
- Se `social_metrics = 0` → il feedback loop è architetturalmente pronto ma operativamente morto. Vai alla Fase 2 ma con priorità al pull.
- Se `avg_feedback_bonus ≈ 5.0` ovunque → Fix 1 della Fase 0 non è stato fatto, o il DB non ha ancora il campo.

**Metrica di successo:** Hai un quadro numerico chiaro. Decidi il path in base ai dati, non a ipotesi.

***

## FASE 2 — "Anti-Hype Gate"

### Durata: 3-4 ore | Costo: ~0.001$/item filtrato | Rischio: medio

Questo è il cambio di qualità più immediato. Non dipende dal feedback loop, non dipende da Postiz. Si aggiunge al loop esistente con un singolo file nuovo.

**Step 1 — Crea `scoring/anti_hype.py`:**

```python
ANTI_HYPE_PROMPT = """Sei il filtro editoriale di {brand_name}.
Il tuo unico compito: proteggere il brand dalla "fuffa mediatica".

## Principi del brand
{founder_principles}

## Esempi di contenuti che PASSANO (valore reale)
{gold_examples}

## Esempi di contenuti BLOCCATI (hype senza sostanza)
{discard_examples}

## Contenuto da valutare
Titolo: {title}
Fonte: {source_name}
Summary: {summary}

Rispondi SOLO con JSON valido:
{{"is_hype": true/false, "confidence": 0.0-1.0, "reason": "una riga max"}}
"""

async def check_anti_hype(item: dict, brand: dict) -> dict:
    # Carica gold_examples e discard_examples dal DB (campo brand)
    gold = brand.get("gold_examples") or []
    discards = brand.get("discard_examples") or []
    
    prompt = ANTI_HYPE_PROMPT.format(
        brand_name=brand.get("name", ""),
        founder_principles="\n".join(brand.get("founder_principles") or []),
        gold_examples="\n".join(f"- {e}" for e in gold[:5]),
        discard_examples="\n".join(f"- {e}" for e in discards[:5]),
        title=item.get("title", ""),
        source_name=item.get("source_name", ""),
        summary=item.get("summary", ""),
    )
    resp = await call_llm(prompt=prompt, brand_id=brand["id"],
                          context="anti_hype_gate", action="check",
                          task_type="fast")  # NON reasoning — risparmio costi
    try:
        return json.loads(resp.content.strip())
    except:
        return {"is_hype": False, "confidence": 0.0, "reason": "parse_error"}
```

**Step 2 — Inserisci nel loop di `engine.py`:**

```python
for item in items:
    # 1. Dedup (già presente)
    if await is_duplicate(item): continue
    
    # 2. Anti-Hype Gate — NUOVO
    gate = await check_anti_hype(item, brand_data)
    if gate["is_hype"]:
        if gate["confidence"] >= 0.75:
            # Alta confidence → scarta definitivamente
            update_status(item, "rejected", {"reason": "anti_hype_gate", 
                                              "confidence": gate["confidence"],
                                              "gate_reason": gate["reason"]})
            anti_hype_discarded += 1
            continue
        else:
            # Bassa confidence → metti in revisione umana, non scartare
            update_status(item, "pending_review", {"reason": "borderline_hype",
                                                    "confidence": gate["confidence"]})
            continue
    
    # 3. Scoring (solo per i superstiti)
    result, final_score, model = await score_item(item, brand_data)
```

**Step 3 — Prima di deployare: popola `gold_examples` e `discard_examples` nel DB**
Questo lo fai tu manualmente — 5-10 titoli reali di contenuti buoni e brutti per ogni brand. Senza questo, il gate è zero-shot e fragile.

**Metrica di successo:** Monitora per 3 giorni. Target: 15-30% di discard rate. Se < 10% → prompt troppo permissivo. Se > 40% → prompt troppo aggressivo, rivedi examples.

***

## FASE 3 — "Feedback Loop reale"

### Durata: 1 settimana | Costo: infrastruttura Supabase | Dipende da: Fase 1

**Questa fase si fa SOLO se la Fase 1 ha dimostrato che hai post reali con Postiz IDs reali.**

**Architettura in 3 componenti:**

**Componente A — Pull giornaliero Postiz** *(2h)*

```python
# services/postiz_analytics.py
async def pull_brand_metrics(brand_id: str):
    drafts = db.table("content_drafts")\
        .select("id, metadata")\
        .eq("brand_id", brand_id)\
        .eq("status", "published")\
        .not_.like("metadata", "%fake_postiz_id%")\
        .execute().data
    
    for draft in drafts:
        postiz_id = draft["metadata"].get("postiz_id")
        resp = await httpx_client.get(
            f"{settings.postiz_base_url}/public/v1/analytics/post/{postiz_id}",
            headers={"Authorization": f"Bearer {settings.postiz_api_key}"},
            params={"date": 7}
        )
        if resp.status_code == 200:
            data = resp.json()
            await record_social_metrics(
                draft_id=draft["id"],
                platform=data.get("platform"),
                impressions=data.get("impressions", 0),
                likes=data.get("likes", 0),
                shares=data.get("shares", 0),
                comments=data.get("comments", 0),
            )
```

**Componente B — Formula engagement score corretta** *(1h)*

```python
def compute_engagement_score(metrics: list) -> float:
    """
    Non avg*2. Formula con:
    - Peso temporale (recente > vecchio)
    - Normalizzazione per piattaforma
    - Volume minimo (ignora post con < 100 impression)
    """
    PLATFORM_BASELINE = {"linkedin": 0.02, "instagram": 0.04, "tiktok": 0.06}
    
    weighted = []
    for m in metrics:
        if m.get("impressions", 0) < 100:
            continue
        platform = m.get("platform", "linkedin")
        baseline = PLATFORM_BASELINE.get(platform, 0.02)
        
        # Engagement rate pesato per tipo di azione
        eng = (m.get("likes",0) + m.get("comments",0)*3 + 
               m.get("shares",0)*5) / m["impressions"]
        normalized = eng / baseline  # 1.0 = nella media della piattaforma
        
        # Decay esponenziale: metriche di 30 giorni fa pesano 22% di quelle di oggi
        days_ago = (datetime.utcnow() - m["created_at"]).days
        weight = math.exp(-0.05 * days_ago)
        
        weighted.append(normalized * weight)
    
    if not weighted:
        return 5.0
    
    avg = sum(weighted) / len(weighted)
    return min(10.0, max(0.0, round(5.0 + avg * 2.5, 2)))
```

**Componente C — Cron job Supabase** *(1h)*

```sql
-- 06:00 — pull metriche
SELECT cron.schedule('pull-postiz-metrics', '0 6 * * *', 
  $$ SELECT net.http_post(url := 'https://...supabase.co/functions/v1/pull-analytics') $$);

-- 07:00 — aggiorna feedback_bonus nel DB brands
SELECT cron.schedule('update-feedback-bonus', '0 7 * * *',
  $$ SELECT net.http_post(url := 'https://...supabase.co/functions/v1/aggregate-scores') $$);
```

**Metrica di successo:** `feedback_bonus` nella tabella `brands` cambia ogni giorno. I post con score > 7.5 mostrano correlazione con engagement rate > media.

***

## FASE 4 — "Pesi configurabili per brand + UI Agenti"

### Durata: 3-4 giorni | Dipende da: sistema stabile

Solo quando le fasi 0-3 sono stabili e i dati hanno senso, ha senso costruire la UI per configurarli.

**Backend:**

```sql
ALTER TABLE brands ADD COLUMN IF NOT EXISTS scoring_weights_config JSONB DEFAULT '{
  "applicability": 0.25,
  "credibility": 0.20,
  "alignment": 0.25,
  "trend_prediction": 0.15,
  "italy_relevance": 0.10,
  "feedback_bonus": 0.05
}'::jsonb;
```

**UI — Aggiornamento della schermata Agenti su Stitch:**
La schermata attuale ha Agent Identities + Agent Skills. Va bene come struttura. Aggiungo: [stitch.withgoogle](https://stitch.withgoogle.com/u/2/projects/11155826360611895417?pli=1)

- **Scoring Weights** come terza sezione (sliders 0-100% con validazione che sommano a 100%)
- **Gold/Discard Examples** come quarta sezione (lista editabile per l'Anti-Hype Gate)
- **Version History** con rollback su ogni agente (come da AGENT_DASHBOARD_UI.md)
- **Ridisegno griglia** da 7-in-fila a 2 righe: prima riga [Writer, Editor, Adapter, Adapter], seconda riga [GOD Advocate, GOD Factchecker, GOD Creative, GOD Synthesis]

***

## La tabella riassuntiva

| Fase | Cosa | Durata | Dipendenze | Output misurabile |
|------|------|--------|------------|-------------------|
| **0** | Fix 3 bug critici | 1 giorno | Nessuna | `feedback_bonus` ≠ 5.0 sempre |
| **1** | Diagnosi dati DB | 2 ore | Fase 0 | Sai quanti post reali hai |
| **2** | Anti-Hype Gate | 3-4 ore | Fase 0 + gold_examples tuoi | 15-30% discard rate |
| **3** | Feedback loop reale | 1 settimana | Fase 1 (post reali > 50%) | `feedback_bonus` cambia ogni giorno |
| **4** | UI Agenti + pesi brand | 3-4 giorni | Fasi 0-3 stabili | Dashboard funzionante end-to-end |

**Regola di avanzamento:** non si passa alla fase successiva se quella precedente non ha una metrica di successo verde per almeno 3 giorni consecutivi

***
