Il piano di Claude Code è solido, concreto e basato sul codice reale (identifica `feedback_bonus` hardcoded a 5.0, `feedback_loop.py` mai chiamato, `fake_postiz_id`). La diagnosi è corretta.

**Punti forti:**

- Ha letto il codebase vero, non ha inventato
- Le 3 domande critiche sono quelle giuste
- La scelta dell'Opzione B (Postiz pull) è pragmatica e corretta
- Le ottimizzazioni tecniche (batch, semaphore, retry, cache TTL) sono pattern reali

**Punti deboli:**

1. **Il prompt Anti-Hype Gate è zero-shot** — senza few-shot examples calibrati sul brand, è fragile. Può scartare trend reali o lasciare passare fuffa
2. **La formula engagement score è un placeholder** (`avg * 2, clamp 10`) — non considera peso temporale, piattaforma, volume
3. **Dipendenza nascosta non evidenziata**: quanti post nel DB hanno `fake_postiz_id`? Se molti, la Fase 2 parte su dati inquinati
4. **Fase 3 sottostimata** nei tempi e manca la logica dei default per i pesi per brand
5. **AutoResearch di Karpathy liquidato** troppo frettolosamente

**Prima di fare la Fase 2, esegui questa query:**

```sql
SELECT 
  COUNT(*) as total_published,
  COUNT(CASE WHEN metadata->>'postiz_id' = 'fake_postiz_id' THEN 1 END) as fake_posts,
  COUNT(CASE WHEN metadata->>'postiz_id' != 'fake_postiz_id' THEN 1 END) as real_posts
FROM content_drafts WHERE status = 'published';
```

***

## Il mio piano — basato su quello che ho letto nel codice reale

Prima di tutto: il repo è **molto più avanzato** di quello analizzato da Claude Code. Ci sono già `god_system.py`, `writing_lab.py`, `auto_optimizer.py`, `agent_loader.py`, `embeddings.py`. Questo cambia le priorità. [gitlab](https://gitlab.com/silver015/content-engine/-/tree/main/python/src/content_engine/agents)

***

## Diagnosi reale (dal codice, non da ipotesi)

**Cosa funziona già:**

- Deduplicazione semantica via pgvector — è nel loop di `engine.py` [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)
- Scoring a 6 parametri con pesi reali (applicability 25%, alignment 25%, credibility 20%, trend 15%, italy 10%, feedback 5%) [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)
- `auto_optimizer.py` — loop notturno ispirato a Karpathy, già esistente ma con A/B testing simulato (success = False hardcoded) [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/services/auto_optimizer.py)
- `writing_lab.py`, `god_system.py` — architettura multi-agente già presente [gitlab](https://gitlab.com/silver015/content-engine/-/tree/main/python/src/content_engine/agents)

**Cosa è rotto o incompleto:**

1. `feedback_bonus` è chiesto all'LLM nel prompt ("Default 5.0") — quindi l'LLM decide sempre 5.0 perché il prompt glielo suggerisce. È un bug silenzioso grave [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)
2. `feedback_loop.py` esiste ma non viene mai triggerato automaticamente — `social_metrics` è vuota [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/services/feedback_loop.py)
3. `auto_optimizer.py` ha `success = False` hardcoded — non scrive mai il prompt migliorato nel DB [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/services/auto_optimizer.py)
4. Il gate Anti-Hype non esiste nel loop — il filtro hype è diluito nei parametri di scoring
5. `principles` viene letto da `scoring_weights.founder_principles` — il bug identificato da Claude Code è reale [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)

***

## Il mio piano — 4 interventi in ordine di priorità

### Giorno 1 — Fix dei bug che distorcono i dati (30 min, zero rischio)

**Bug 1 — Rimuovi feedback_bonus dal prompt LLM**

Il problema più grave: stai chiedendo all'LLM di valutare il `feedback_bonus` ma nel prompt scrivi "Default 5.0" — quindi risponderà sempre 5.0. Il parametro deve essere rimosso dal JSON che l'LLM restituisce e iniettato lato server.

```python
# engine.py — SCORING_PROMPT
# RIMUOVI feedback_bonus dal JSON richiesto all'LLM
# Il prompt deve chiedere solo 5 parametri:
# applicability, credibility, alignment, trend_prediction, italy_relevance

# In score_item(), DOPO aver parsato la risposta LLM:
brand_data = db.table("brands").select("feedback_bonus").eq("id", brand_id).single().execute().data
feedback_bonus = brand_data.get("feedback_bonus", 5.0) if brand_data else 5.0
result = ScoreResult(**parsed, feedback_bonus=feedback_bonus)
```

**Bug 2 — Fix principles lookup**

```python
# Riga attuale (sbagliata):
principles = (brand.get("scoring_weights") or {}).get("founder_principles", [])
# Fix:
principles = brand.get("founder_principles") or (brand.get("scoring_weights") or {}).get("founder_principles", [])
```

**Bug 3 — Sblocca auto_optimizer**

```python
# auto_optimizer.py — riga 847 circa
# success = False  ← RIMUOVI
# Sostituisci con il vero A/B test:
success = new_avg_score > old_avg_score
```

***

### Giorno 2 — Anti-Hype Gate con few-shot calibrato (2-3 ore)

Non un prompt generico. Il gate deve riflettere la filosofia del tuo brand. Lo strutturerei così:

```python
ANTI_HYPE_GATE_PROMPT = """Sei un filtro editoriale per {brand_name}.
La tua missione: scartare contenuti clickbait che non portano valore pratico immediato.

## Principi del brand
{founder_principles}

## Esempi di contenuti VALIDI (passa il gate)
{gold_examples}

## Esempi di contenuti SCARTATI (hype)
{discard_examples}

## Contenuto da valutare
Titolo: {title}
Summary: {summary}
Fonte: {source_name}

Rispondi SOLO con JSON: {"is_hype": true/false, "confidence": 0.0-1.0, "reason": "una riga"}
"""
```

Nota critica: `confidence` è la chiave. Se `confidence < 0.7`, il contenuto va in una coda "borderline" per revisione umana — non scartato definitivamente. Questo risolve il problema dei falsi negativi che sia io che NotebookLM avevamo identificato.

**Integrazione nel loop di `engine.py`:**

```python
for item in items:
    # 1. Dedup (già presente)
    if is_duplicate: continue
    
    # 2. Anti-Hype Gate — NUOVO
    gate_result = await check_anti_hype(item, brand_data)
    if gate_result["is_hype"] and gate_result["confidence"] >= 0.7:
        mark_as_rejected(item, reason="anti_hype_gate")
        continue
    elif gate_result["is_hype"] and gate_result["confidence"] < 0.7:
        mark_as_pending_review(item, reason="borderline_hype")
        continue
    
    # 3. Scoring (solo per contenuti superstiti)
    result, final_score, model = await score_item(item, brand_data)
```

**I few-shot examples**: devono essere i tuoi, inseriti nella tabella `brands` come `gold_examples` (array JSONB) e `discard_examples` (array JSONB). Non esempi generici.

***

### Settimana 2 — Attivare il feedback loop reale

**Prima, la query diagnostica obbligatoria:**

```sql
SELECT 
  COUNT(*) as total_published,
  COUNT(CASE WHEN metadata->>'postiz_id' = 'fake_postiz_id' THEN 1 END) as fake,
  COUNT(CASE WHEN metadata->>'postiz_id' != 'fake_postiz_id' THEN 1 END) as real
FROM content_drafts WHERE status = 'published';
```

Se `fake > 50%`, non toccare il feedback loop finché non vai in produzione con Postiz reale.

**Se i dati sono reali**, il loop si attiva in 3 passi:

**Passo A — Pull giornaliero da Postiz (cron alle 06:00)**

```python
# services/postiz_analytics.py
async def pull_daily_metrics(brand_id: str):
    drafts = get_published_drafts_with_real_postiz_id(brand_id)
    for draft in drafts:
        metrics = await fetch_from_postiz(draft["postiz_id"])
        await record_social_metrics(draft["id"], **metrics)
```

**Passo B — Formula engagement score corretta (non `avg*2`)**

```python
def compute_engagement_score(metrics: list) -> float:
    """
    Weighted score che considera:
    - Peso temporale: metriche recenti contano di più
    - Normalizzazione per piattaforma (LinkedIn ≠ Instagram)
    - Volume minimo (ignora post con < 100 impressioni)
    """
    if not metrics:
        return 5.0
    
    scored_metrics = []
    for m in metrics:
        if m["impressions"] < 100:  # ignora post senza volume
            continue
        
        # Engagement rate normalizzato per piattaforma
        platform_baseline = {"linkedin": 0.02, "instagram": 0.04, "tiktok": 0.06}
        baseline = platform_baseline.get(m["platform"], 0.02)
        rate = (m["likes"] + m["comments"]*3 + m["shares"]*5 + m["saves"]*2) / m["impressions"]
        normalized = rate / baseline  # 1.0 = nella media
        
        # Peso temporale: decay esponenziale su 30 giorni
        days_ago = (now() - m["created_at"]).days
        weight = math.exp(-0.05 * days_ago)
        
        scored_metrics.append(normalized * weight)
    
    if not scored_metrics:
        return 5.0
    
    avg = sum(scored_metrics) / len(scored_metrics)
    return min(10.0, max(0.0, 5.0 + avg * 2.5))
```

**Passo C — Aggiorna `feedback_bonus` nel DB per brand (cron alle 07:00)**

```sql
UPDATE brands 
SET feedback_bonus = compute_engagement_score_optimized(id),
    updated_at = NOW()
WHERE active = true;
```

***

### Settimana 3 — Sbloccare auto_optimizer come Karpathy loop reale

`auto_optimizer.py` è già scritto correttamente nella logica — prende i draft rifiutati, propone un nuovo prompt, lo testa. Il problema è solo `success = False` hardcoded. Una volta tolto quel blocco, diventa funzionale. [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/services/auto_optimizer.py)

L'upgrade che aggiungerei: invece di testare solo sui draft rifiutati, testa anche sui draft "borderline_hype" — quelli con confidence bassa. Se il nuovo prompt li fa passare il gate E lo scoring li approva, è un segnale che il prompt migliorato è davvero più preciso.

***

## Differenze strutturali dal piano di Claude Code

| Aspetto | Piano Claude Code | Il mio piano |
|---|---|---|
| Anti-Hype prompt | Zero-shot generico | Few-shot calibrato sul brand + confidence threshold |
| Contenuti borderline | Scartati definitivamente | Coda revisione umana separata |
| Formula engagement | `avg * 2` placeholder | Weighted decay + normalizzazione per piattaforma |
| Auto-optimizer | Non affrontato | Sbloccare il codice già scritto (success = False → A/B reale) |
| Pre-condizione Fase 2 | Non menzionata | Query diagnostica sui fake_postiz_id obbligatoria |
| `feedback_bonus` | Rimosso dal prompt LLM | Rimosso dal prompt LLM (stesso fix, identificato indipendentemente) |

***

## Ordine di esecuzione

```
OGGI (30 min):
  Fix 3 bug silenzosi in engine.py e auto_optimizer.py

QUESTA SETTIMANA (2-3h):
  Anti-Hype Gate con few-shot + confidence threshold
  Scrivi i tuoi gold_examples e discard_examples nel DB (questo richiede tu, non il codice)

PROSSIMA SETTIMANA:
  Query diagnostica fake_postiz_id
  Se dati reali > 50%: attiva pull Postiz + feedback loop con formula corretta
  
SETTIMANA 3:
  Sblocca auto_optimizer (rimuovi success = False)
  Collega borderline_hype al writing_lab per review umana
```

Il vero vantaggio competitivo rispetto a Montemagno non è nell'architettura (la sua è simile), ma nel **non dipendere dalla tua presenza come collaudatore** — il gate con confidence + la coda borderline + l'auto_optimizer sbloccato sono i tre elementi che chiudono il loop senza richiedere 4 ore al giorno di supervisione.
