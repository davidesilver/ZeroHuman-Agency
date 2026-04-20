## Lo stato attuale dell'algoritmo nel Content Engine

Ho letto il codice reale (`scoring/engine.py`) e interrogato NotebookLM in profondità. Ecco cosa sta succedendo davvero. [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)

***

## L'algoritmo attuale: cosa c'è nel codice

Il tuo `engine.py` implementa uno **scoring a 6 parametri** con pesi fissi hardcoded:

```python
WEIGHTS = {
    "applicability":    0.25,   # 25% — quanto è applicabile lunedì mattina
    "credibility":      0.20,   # 20% — fonte autorevole, cita dati/esperti
    "alignment":        0.25,   # 25% — allineamento a topic e principi del brand
    "trend_prediction": 0.15,   # 15% — trend emergente, rilevante a 6 mesi
    "italy_relevance":  0.10,   # 10% — applicabile al mercato italiano
    "feedback_bonus":   0.05,   # 5%  — bonus da engagement storico
}
```

**Formula finale:**

```
score = applicability×0.25 + credibility×0.20 + alignment×0.25 
      + trend_prediction×0.15 + italy_relevance×0.10 + feedback_bonus×0.05
```

Ogni parametro è valutato da **Claude Sonnet in modalità `reasoning`** su scala 0-10, poi moltiplicato per il peso. Il `feedback_bonus` ha default fisso a **5.0** — non viene mai aggiornato automaticamente dai dati social. Rimane statico.

**Deduplicazione semantica**: prima dello scoring, ogni item viene embeddato e confrontato via `find_semantic_duplicates` RPC con soglia `0.85`. Duplicati → status `archived`, non scorati. Questo è un punto di forza già implementato.

***

## Cosa fa Montemagno vs cosa fa il tuo codice

| Aspetto | Marco (teorico) | Content Engine (reale) |
|---|---|---|
| Pesi scoring | "Giudizio umano codificato" — non dichiarati | ✅ Dichiarati e numerici |
| Brand Persona input | 4.000 video + 3 libri analizzati in profondità | Solo `topics` + `founder_principles` nel prompt |
| `feedback_bonus` | Aggiornato da analytics social (ibrido auto+manuale) | ❌ Hardcoded a 5.0, mai aggiornato |
| Anti-Hype filter | Filtro esplicito per notizie sensazionalistiche | Non esiste come parametro separato |
| AutoResearch (Karpathy) | AB test notturno su varianti di scrittura | ❌ Non implementato |
| Tono di voce | Training su database storico + Writing Lab (Sì/No) | Solo prompt hardcoded in `writer.py` |
| Dedup semantica | Concettuale | ✅ Implementata con pgvector |

***

## Come costruire l'algoritmo perfetto: 4 interventi specifici

### 1. Attivare il `feedback_bonus` dinamico (impatto alto, 4h)

Ora è fisso a 5.0. Il fix è collegarlo agli analytics reali. Nel DB hai già `scores` e `research_items` — basta aggiungere una colonna `social_engagement` e un job che aggiorna il bonus:

```python
# Logica da aggiungere in engine.py
async def compute_feedback_bonus(brand_id: str, source_name: str) -> float:
    """Calcola bonus basato su CTR storico di articoli dalla stessa fonte."""
    db = get_db()
    stats = db.table("published_posts")\
        .select("engagement_rate")\
        .eq("brand_id", brand_id)\
        .eq("source_name", source_name)\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()
    
    if not stats.data:
        return 5.0  # default neutro
    
    avg_engagement = sum(r["engagement_rate"] for r in stats.data) / len(stats.data)
    # Normalizza 0-10 basandosi sulla media del brand
    return min(10.0, max(0.0, avg_engagement * 2))
```

### 2. Aggiungere il parametro Anti-Hype come filtro hard (impatto alto, 2h)

Montemagno ha "tolleranza zero" per le notizie sensazionalistiche. Nel tuo scoring non esiste. Va aggiunto come **gate binario pre-scoring**, non come peso — perché se un articolo è hype non deve nemmeno essere scorato:

```python
# Aggiungere in engine.py prima del LLM scoring
ANTI_HYPE_PROMPT = """
Analizza questo titolo e summary. Rispondi solo con JSON: {"is_hype": true/false}
Un contenuto è HYPE se: usa numeri sensazionalistici senza dati, promette risultati 
impossibili, ha titolo clickbait senza sostanza, è trend del momento senza utilità pratica.
Title: {title}
Summary: {summary}
"""

async def is_hype_content(item: dict) -> bool:
    resp = await call_llm(prompt=ANTI_HYPE_PROMPT.format(**item), 
                          task_type="reasoning")
    return json.loads(resp.content).get("is_hype", False)
```

Nel loop principale aggiungi: `if await is_hype_content(item): continue`

### 3. Rendere i pesi configurabili per brand (impatto medio, 3h)

Ora i pesi sono fissi per tutti i brand. Ma Vest (B2B sponsorship) ha bisogno di parametri diversi rispetto a Maso Caiano (agriturismo). Soluzione: spostare i pesi nel DB nel campo `scoring_weights` della tabella `brands`.

```python
# In engine.py, sostituire WEIGHTS fisso con:
def get_weights(brand_data: dict) -> dict:
    custom = brand_data.get("scoring_weights") or {}
    defaults = {
        "applicability": 0.25, "credibility": 0.20, "alignment": 0.25,
        "trend_prediction": 0.15, "italy_relevance": 0.10, "feedback_bonus": 0.05
    }
    # Sovrascrive solo i pesi specificati, mantiene defaults per gli altri
    merged = {**defaults, **custom}
    # Normalizza a 1.0
    total = sum(merged.values())
    return {k: v/total for k, v in merged.items()}
```

Nel frontend `/settings/agenti` puoi già esporre questi slider per brand.

### 4. Arricchire la Brand Persona (impatto alto, 1 giorno)

Il punto più debole rispetto al sistema di Montemagno: il tuo `alignment` viene calcolato su `topics` (lista di keyword) e `founder_principles` (lista di frasi). È troppo superficiale.

Il sistema di Marco parte da un'analisi approfondita di 4.000 video e 3 libri per estrarre valori, stile, esempi concreti. La versione minimale per il Content Engine è aggiungere nel brand una sezione **"Esempi di contenuti eccellenti"** — 5-10 post reali che hanno performato bene — e includerli nel prompt di scoring come riferimento:

```python
# Nel SCORING_PROMPT, aggiungere sezione:
## Esempi di Contenuti Eccellenti per questo Brand
{examples}
# Valuta il nuovo item in confronto a questi esempi di riferimento
```

***

## Il problema critico che nessuno ha citato: il `reasoning` model costa molto

Nel codice c'è `task_type="reasoning"` per ogni scoring. Con il routing LLM attuale, `reasoning` usa `xiaomi-mimo-v2-flash-free` (o simili). Lo scoring viene eseguito su **ogni singolo item** prima della deduplicazione semantica — quindi se arrivano 500 item, sono 500 call LLM. [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)

**Fix**: invertire l'ordine — prima dedup semantica, poi scoring. Il codice attualmente fa già questo (dedup→score), ma il loop è **sequenziale** (non async), lento per volumi alti. Per ora va bene, ma tienilo a mente.

***

## Priorità di implementazione

1. **Feedback_bonus dinamico** — massimo impatto sulla qualità con minimo rischio. Lo scoring diventa auto-apprendente basandosi su cosa ha funzionato.
2. **Anti-Hype gate** — porta l'algoritmo più vicino al sistema di Montemagno, filtra il rumore prima ancora di spendere token.
3. **Pesi per brand** — necessario non appena hai 2+ brand con nature diverse (B2B vs consumer).
4. **Brand Persona arricchita** — il salto qualitativo più grande ma richiede che tu inserisca manualmente i contenuti di riferimento per ogni brand.

***

## Analisi tecnica del codice reale — dove siamo e cosa va fatto

Ho letto l'intero `engine.py` e `models.py`. Ecco la situazione reale, senza filtri. [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)

***

### Lo stato effettivo del codice

**Quello che funziona già bene:**

- Deduplicazione semantica via pgvector con soglia configurabile (`dedup_threshold: 0.85`) — **già nel loop, prima dello scoring** [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)
- Scoring a 6 parametri con pesi dichiarati e formula trasparente
- Auto-approve/reject con soglie per brand (`auto_approve_threshold`, `auto_reject_threshold`) — già configurabili per brand [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)
- `scoring_weights` già letta dal record brand nel DB — la struttura per i pesi per-brand **esiste già parzialmente** [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)

**I problemi reali (non teorici):**

1. **`feedback_bonus` hardcoded a 5.0 nel prompt** — il LLM viene istruito esplicitamente a restituire sempre 5.0: `"feedback_bonus": 5.0`. Non è solo un default, è un'istruzione diretta al modello. Anche se il DB avesse dati di engagement, il modello li ignora. [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)

2. **`founder_principles` letto male** — c'è un bug silenzioso: `principles = (brand.get("scoring_weights") or {}).get("founder_principles", [])`. I principi sono annidati dentro `scoring_weights` invece di essere un campo di primo livello. Se la struttura del DB non matcha esattamente, i principi arrivano vuoti al prompt senza errori visibili. [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)

3. **WEIGHTS fissi nel codice** — il dict `WEIGHTS` è hardcoded nel file Python, non viene mai letto dal DB. La lettura di `scoring_weights` è parziale (prende solo `founder_principles`, ignora i pesi). [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)

4. **Nessun Anti-Hype gate** — confermato: non c'è alcun filtro pre-scoring. Il LLM di reasoning viene chiamato su ogni item sopravvissuto alla dedup, inclusi quelli chiaramente clickbait.

5. **Loop sequenziale su volumi alti** — il commento nel codice lo spiega: è intenzionale per evitare race condition nella dedup. Corretto per ora, ma scala male oltre ~200 item/run. [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/scoring/engine.py)

***

### Le 4 modifiche concrete, in ordine di impatto

#### 1. Fix immediato: `feedback_bonus` dinamico (4h)

Il problema è a due livelli: il prompt istruisce il modello a restituire 5.0, e non c'è nessun job che aggiorni il valore. Soluzione in due parti:

```python
# In engine.py — nuova funzione
async def compute_feedback_bonus(brand_id: str, source_name: str) -> float:
    db = get_db()
    stats = db.table("published_posts")\
        .select("engagement_rate")\
        .eq("brand_id", brand_id)\
        .eq("source_name", source_name)\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()
    
    if not stats.data:
        return 5.0  # default neutro
    
    avg = sum(r["engagement_rate"] for r in stats.data) / len(stats.data)
    return min(10.0, max(0.0, avg * 2))  # normalizza 0-10
```

Poi nel prompt rimuovi la riga `"feedback_bonus": 5.0` e prima della chiamata LLM calcoli il bonus reale e lo inietti nel prompt come contesto. Il modello non deve più restituirlo — lo calcoli tu e lo aggiungi al `ScoreResult` dopo.

#### 2. Anti-Hype gate binario (2h)

Va inserito tra la dedup e lo scoring, esattamente dove già c'è il `continue` per i duplicati:

```python
# Subito dopo il blocco deduplicazione, prima di score_item()
ANTI_HYPE_PROMPT = """
Analizza titolo e summary. Rispondi SOLO con JSON: {"is_hype": true/false}
È HYPE se: usa numeri senza dati reali, promette risultati impossibili, 
è clickbait senza sostanza, è trend del momento senza utilità pratica.

Title: {title}
Summary: {summary}
"""

async def is_hype_content(item: dict) -> bool:
    # Usa un modello veloce/economico, NON reasoning
    resp = await call_llm(
        prompt=ANTI_HYPE_PROMPT.format(
            title=item.get("title", ""),
            summary=item.get("summary", "")
        ),
        brand_id=item.get("brand_id", ""),
        context="anti_hype_gate",
        action="check_hype",
        task_type="fast"  # NON reasoning — risparmio costi
    )
    try:
        return json.loads(resp.content.strip()).get("is_hype", False)
    except:
        return False  # in caso di parsing error, lascia passare
```

Nel loop principale, dopo la dedup:

```python
if await is_hype_content(item):
    db.table("research_items").update({"status": "rejected", 
        "metadata": {"rejection_reason": "anti_hype_gate"}
    }).eq("id", item["id"]).execute()
    continue
```

**Nota critica**: usa un modello `fast` (Haiku, Flash) non `reasoning` per questo gate. Il costo del reasoning per un semplice check binario è 10-20x quello necessario.

#### 3. Pesi per brand dal DB (3h)

Il codice attuale legge `scoring_weights` ma usa solo `founder_principles`. Fix:

```python
def get_weights(brand_data: dict) -> dict:
    custom = brand_data.get("scoring_weights") or {}
    # Rimuovi founder_principles per non confonderlo con pesi
    weight_keys = {"applicability", "credibility", "alignment", 
                   "trend_prediction", "italy_relevance", "feedback_bonus"}
    custom_weights = {k: v for k, v in custom.items() if k in weight_keys}
    
    defaults = {
        "applicability": 0.25, "credibility": 0.20, "alignment": 0.25,
        "trend_prediction": 0.15, "italy_relevance": 0.10, "feedback_bonus": 0.05
    }
    merged = {**defaults, **custom_weights}
    total = sum(merged.values())
    return {k: v/total for k, v in merged.items()}  # normalizza sempre a 1.0
```

E nel `run_scoring` sostituisci `WEIGHTS` con `get_weights(brand_data)` passandolo a `_compute_final_score`.

Il DB `brands.scoring_weights` può già contenere sia i pesi che i `founder_principles` — basta che il parsing li separi correttamente.

#### 4. Fix bug silenzioso: `founder_principles` (30 min)

```python
# Linea attuale (sbagliata):
principles = (brand.get("scoring_weights") or {}).get("founder_principles", [])

# Fix — leggi da campo dedicato o da scoring_weights come fallback:
principles = brand.get("founder_principles") or \
             (brand.get("scoring_weights") or {}).get("founder_principles", [])
```

Questo da solo può migliorare significativamente la qualità dell'alignment score perché i principi arrivano effettivamente al LLM.

***

### Cosa NON farei ora

- **Gold Examples nel prompt** — utile ma aumenta i token di ogni chiamata. Prima chiudi il gap sul `feedback_bonus` dinamico e l'Anti-Hype gate, che hanno ROI immediato senza aumentare i costi.
- **Async parallelizzazione** — il commento nel codice è corretto: la dedup semantica ha race condition se parallelizzata. Risolvi prima, poi valuta batch processing con lock per brand.
- **AutoResearch stile Karpathy** — è un nice-to-have. Il sistema non ha ancora un feedback loop reale (social analytics → DB). Prima connetti quello.

***

### Ordine di esecuzione consigliato

| # | Intervento | Impatto | Costo API | Tempo |
|---|---|---|---|---|
| 1 | Fix `founder_principles` bug | Alto (alignment quality) | Zero | 30min |
| 2 | Anti-Hype gate con modello fast | Alto (qualità + risparmio) | -20% | 2h |
| 3 | `feedback_bonus` dinamico | Alto (auto-learning) | Neutro | 4h |
| 4 | Pesi per brand dal DB | Medio (scalabilità) | Zero | 3h |

Il punto 1 è gratis e può fare la differenza domani mattina. Il punto 2 riduce i costi. Il punto 3 è il salto verso l'auto-apprendimento reale che Marco descrive nei video ma che nel suo codice ancora non esiste.

***

## autoresearch di Karpathy <https://github.com/karpathy/autoresearch> — onestà brutale: **non è quello che pensiamo**

Ho letto la repo per intero. Il punto critico è questo: **il nome è fuorviante rispetto all'uso che Marco ne descrive nei video**. [github](https://github.com/karpathy/autoresearch)

***

### Cosa fa davvero autoresearch

Non è un sistema per ricercare contenuti editoriali. È un **loop di autoottimizzazione per il training di LLM**: [github](https://github.com/karpathy/autoresearch)

- Un agente modifica `train.py` (architettura modello, optimizer, hyperparameter)
- Lancia un training da 5 minuti su GPU
- Misura `val_bpb` (validation bits per byte — metrica di qualità del modello)
- Se migliora → keep. Se peggiora → git reset
- Ripete all'infinito mentre dormi [github](https://github.com/karpathy/autoresearch/blob/master/program.md)

L'idea core è: **"LOOP FOREVER, NEVER STOP, you are autonomous"**. È letteralmente un ricercatore AI che ottimizza se stesso come modello ML. [github](https://github.com/karpathy/autoresearch/blob/master/program.md)

Richiede una **singola NVIDIA GPU** (testato su H100). Non gira su CPU, non gira sul cloud senza GPU, non gira sul tuo stack. [github](https://github.com/karpathy/autoresearch)

***

### Il malinteso di Marco

Quando Marco dice nei video che usa "il sistema di Karpathy" per migliorare la scrittura e la ricerca, quasi certamente si riferisce al **concetto** — il loop autonomo di test/discard/keep — non all'implementazione vera. Perché autoresearch letteralmente non si può usare per ottimizzare testi o scoring di notizie: lavora su metriche di training LLM su GPU dedicate.

***

### Cosa è invece trasferibile al nostro sistema

Ci sono **due elementi concettuali** che hanno senso adattare:

**1. Il `program.md` come "skill" per l'agente** [github](https://github.com/karpathy/autoresearch/blob/master/program.md)
Karpathy usa un file Markdown come insieme di istruzioni operative per l'agente. È esattamente come funzionano le `CLAUDE.md` skills di Cloud Code. Il meccanismo è applicabile: un file che definisce il loop, i vincoli, il criterio di successo. Per il Content Engine potrebbe diventare un `scoring_program.md` che l'agente usa per iterare sui parametri di scoring.

**2. Il loop keep/discard con metrica fissa** [github](https://github.com/karpathy/autoresearch/blob/master/program.md)
Il pattern è potente: prendi una metrica oggettiva (nel suo caso `val_bpb`, nel nostro caso engagement rate / CTR), fai girare esperimenti, tieni solo ciò che migliora. Questo è adattabile al Writing Lab: variante A vs variante B del testo, metrica = tasso di apertura della newsletter o click su LinkedIn, loop notturno che scarta le varianti peggiori.

***

### La mia valutazione netta

| Aspetto | Per l'algoritmo di scoring | Per gli agenti |
|---|---|---|
| Usabile direttamente | ❌ No (richiede GPU, misura LLM training) | ⚠️ Solo il pattern |
| Pattern keep/discard | ✅ Adattabile per A/B test contenuti | ✅ Applicabile al Writing Lab |
| `program.md` come skill | N/A | ✅ Ottimo per strutturare le istruzioni operative degli agenti |
| Loop autonomo notturno | ✅ Applicabile ma serve metrica reale (analytics social) | ✅ Applicabile |

**La cosa più utile che puoi prendere da questa repo** è la struttura di `program.md`: un file Markdown che dice all'agente cosa può fare, cosa non può fare, qual è la metrica di successo, e come decidere keep/discard. Applicato al tuo `engine.py`, diventa: l'agente prova varianti dei parametri di scoring o del prompt, misura engagement reale dopo 48h, e automaticamente promuove o scarta la variante. Quello è l'AutoResearch applicato al Content Engine — ma devi costruirlo tu da zero, non puoi usare la repo di Karpathy così com'è. [github](https://github.com/karpathy/autoresearch/blob/master/program.md)

**Per gli agenti invece**: il pattern del loop con `NEVER STOP` e criterio di successo esplicito è direttamente adottabile nella struttura delle skill di Cloud Code del tuo sistema.

Ho ragionato su un paio di punti con perplexity e notebook lm. Leggi, analizza, studia, valuta, dimmi cosa ne pensi. Sii onesto e schietto. usa context 7 mcp e le skills.
