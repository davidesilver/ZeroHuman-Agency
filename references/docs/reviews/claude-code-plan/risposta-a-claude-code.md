## Le 3 domande: risposta dal codice reale

### 1. I post pubblicati sono già nel DB?

**Sì, parzialmente.** Il `social_publisher.py` salva lo status `published` e `published_url` nella tabella `content_drafts`. Il draft viene aggiornato quando viene pubblicato via Postiz. Esiste anche la tabella `calendar_events` per i post schedulati. Però c'è una condizione critica: **se `postiz_api_key` non è configurato**, il sistema simula la pubblicazione con `post_id = "fake_postiz_id"` e comunque scrive "published" nel DB — quindi potresti avere record "published" che non sono mai stati effettivamente postati su nessun social. [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/services/social_publisher.py)

### 2. L'engagement tracking è già funzionante?

**No.** Il `feedback_loop.py` è **completamente implementato lato codice** — ha `record_social_metrics()`, `compute_engagement_score()`, e `update_feedback_bonus()` — ma **non viene mai chiamato automaticamente**. La funzione `record_social_metrics()` aspetta che qualcuno le passi i dati di impressions/likes/shares, ma non c'è nessun cron job, nessun webhook, nessuna chiamata API ai social che popoli la tabella `social_metrics`. La tabella esiste nello schema ma è quasi certamente vuota. Quindi `compute_engagement_score()` restituisce sempre `5.0` (il default neutro) perché `if not metrics: return 5.0`. [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/services/feedback_loop.py)

Il feedback loop è architetturalmente pronto ma operativamente inattivo. È come avere un motore montato senza carburante.

### 3. Qual è la fonte dati dei social analytics?

**Non c'è.** Il sistema pubblica via **Postiz** (`publish_to_postiz`) ma non legge mai indietro le metriche da Postiz. Non ci sono chiamate alle API native di LinkedIn, Instagram o TikTok per raccogliere engagement. La struttura di `social_accounts` in `brands` contiene OAuth tokens per piattaforma, ma non vengono usati per pull di analytics — solo potenzialmente per publish diretto futuro. [gitlab](https://gitlab.com/silver015/content-engine/-/raw/main/python/src/content_engine/services/social_publisher.py)

***

## Cosa significa concretamente

Prima di qualsiasi intervento sull'algoritmo, il prerequisite reale è questo:

**Devi scegliere come entra l'engagement nel sistema.** Hai tre opzioni concrete, dal più semplice al più completo:

| Opzione | Come funziona | Complessità | Tempo |
|---|---|---|---|
| **A. Postiz Webhooks** | Postiz invia metriche al tuo endpoint quando un post riceve engagement | Bassa — aggiungi un endpoint API + chiami `record_social_metrics()` | 1-2h |
| **B. Pull da API Postiz** | Cron job giornaliero che chiede a Postiz le stats dei post pubblicati degli ultimi 7 giorni | Media — dipende da cosa espone Postiz nella sua API | 3-4h |
| **C. Pull da API native** | Chiami direttamente LinkedIn/Instagram con i token OAuth già nel DB | Alta — ogni piattaforma ha API diverse, rate limits, permission scope | 1-2 giorni |

**L'opzione A è quella giusta adesso.** Postiz è già il tuo intermediario di pubblicazione — se espone webhook sugli eventi di engagement (molti scheduler lo fanno), è il canale più diretto. Il codice per riceverli e salvarli in `social_metrics` esiste già in `feedback_loop.py`, basta chiamarlo.

Quindi la risposta alla domanda implicita di Claude Code è: **il `feedback_bonus` dinamico non richiede 4h, richiede prima una decisione su da dove arrivano i dati**. Fatto quello, il codice del loop è già scritto e funzionante — ironicamente è la parte più completa dell'intero sistema.

***

## Come procederei, step by step, con quali tool

Premessa: ho verificato la documentazione di Postiz. Ha un'**API pubblica per le analytics per post** (`GET /public/v1/analytics/{integration}`) che restituisce impressions, likes, engagement. I **webhook non esistono ancora** — sono una issue aperta su GitHub. Quindi niente webhook: il meccanismo giusto è il **pull giornaliero**. [docs.postiz](https://docs.postiz.com/public-api/analytics/platform)

***

### Fase 0 — Oggi, 30 min: Fix founder_principles (gratis, zero rischio)

**Tool: Claude Code direttamente su `engine.py`**

Una riga. Nessuna implicazione di schema, nessun rischio.

```python
# Prima (bug silenzioso):
principles = (brand.get("scoring_weights") or {}).get("founder_principles", [])

# Dopo:
principles = brand.get("founder_principles") or \
             (brand.get("scoring_weights") or {}).get("founder_principles", [])
```

Poi verifica nel DB Supabase che la colonna `founder_principles` esista come campo di primo livello nella tabella `brands`. Se non esiste, aggiungila con una migration SQL semplice. Non toccare altro.

***

### Fase 1 — Questa settimana: Anti-Hype Gate (2h)

**Tool: Claude Code su `engine.py`**

Aggiungi la funzione `is_hype_content()` con modello **fast** (non reasoning), e nel loop subito dopo la dedup:

```python
if await is_hype_content(item):
    db.table("research_items").update({
        "status": "rejected",
        "metadata": {**item.get("metadata", {}), 
                     "rejection_reason": "anti_hype_gate",
                     "gate_checked_at": datetime.utcnow().isoformat()}
    }).eq("id", item["id"]).execute()
    continue
```

**Cosa aggiungere obbligatoriamente**: un contatore nel return del `run_scoring` — `"anti_hype_discarded": N` — e loggarlo in `pipeline_health` o simile. Senza questo non sai mai se il gate sta funzionando o sta scartando troppo.

***

### Fase 2 — Settimana prossima: Feedback loop reale (il cuore)

Qui il tool principale è **Postiz Public API** + **Claude Code** + un **cron job Supabase**.

**Step 2a — Scrivi il puller Postiz (3h)**

Crea `services/postiz_analytics.py`:

```python
async def pull_post_analytics(brand_id: str) -> dict:
    """
    Chiama Postiz API per ogni post pubblicato negli ultimi 7 giorni,
    salva i metrics in social_metrics, poi chiama update_feedback_bonus().
    """
    db = get_db()
    
    # Prendi i draft pubblicati con postiz_post_id
    drafts = db.table("content_drafts")\
        .select("id, research_item_id, metadata")\
        .eq("brand_id", brand_id)\
        .eq("status", "published")\
        .not_.is_("research_item_id", "null")\
        .execute().data
    
    for draft in (drafts or []):
        postiz_id = (draft.get("metadata") or {}).get("postiz_id")
        if not postiz_id:
            continue
        
        # Chiama Postiz analytics per questo post
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.postiz_base_url}/public/v1/analytics/post/{postiz_id}",
                headers={"Authorization": f"Bearer {settings.postiz_api_key}"}
            )
        if resp.status_code != 200:
            continue
        
        data = resp.json()
        # Mappa i campi Postiz → social_metrics
        await record_social_metrics(
            draft_id=draft["id"],
            platform=data.get("platform", "unknown"),
            impressions=data.get("impressions", 0),
            likes=data.get("likes", 0),
            shares=data.get("shares", 0),
            comments=data.get("comments", 0),
        )
    
    # Ora aggiorna il feedback_bonus — il codice esiste già
    return await update_feedback_bonus(brand_id)
```

**Nota**: devi verificare che `publish_to_postiz()` salvi il `postiz_id` restituito nel campo `metadata` del draft. Guardando il codice attuale, salva `published_url` ma non sempre il `post_id` nei metadata. Aggiusta anche quello. [docs.postiz](https://docs.postiz.com/howitworks)

**Step 2b — Cron job (1h)**

**Tool: Supabase Edge Functions** (già nel tuo stack — vedi cartella `supabase/` nella repo).

Crea una Edge Function schedulata che chiama `pull_post_analytics` una volta al giorno per ogni brand attivo. Supabase ha i cron job nativi via `pg_cron` o via Edge Function scheduler. Non serve infrastruttura aggiuntiva.

```sql
-- In Supabase: cron job giornaliero alle 06:00
select cron.schedule(
  'pull-postiz-analytics',
  '0 6 * * *',
  $$
  select net.http_post(
    url := 'https://tuo-progetto.supabase.co/functions/v1/pull-analytics',
    headers := '{"Authorization": "Bearer SERVICE_KEY"}'::jsonb
  );
  $$
);
```

***

### Fase 3 — Quando hai 2+ brand: Pesi per brand (3h)

**Tool: Claude Code + migration Supabase**

Migration SQL su `brands`:

```sql
ALTER TABLE brands 
  ADD COLUMN IF NOT EXISTS scoring_weights_config JSONB DEFAULT '{
    "applicability": 0.25,
    "credibility": 0.20,
    "alignment": 0.25,
    "trend_prediction": 0.15,
    "italy_relevance": 0.10,
    "feedback_bonus": 0.05
  }'::jsonb;
```

Separa definitivamente i pesi da `founder_principles` usando una colonna dedicata. In `engine.py` sostituisci `WEIGHTS` con `get_weights(brand_data)` che legge da `scoring_weights_config`.

***

### Stack complessivo: cosa usi e perché

| Tool | Perché |
|---|---|
| **Claude Code** | Modifica `engine.py`, `feedback_loop.py`, `social_publisher.py` — è già il tuo workbot principale |
| **Postiz Public API** | Pull analytics giornaliero — esiste, documentata, non serve nulla di nuovo [docs.postiz](https://docs.postiz.com/public-api/analytics/platform) |
| **Supabase pg_cron** | Cron job — già nel tuo stack, zero infrastruttura aggiuntiva |
| **Supabase Edge Functions** | Trigger del puller analytics — già nella repo (`supabase/` folder) |
| **Nessun nuovo servizio** | Non aggiungi Postproxy, non integri API native LinkedIn/Instagram — Postiz è già il tuo intermediario |

L'unica dipendenza esterna nuova è la Postiz Analytics API, che hai già il token per usarla.

***

## NotebookLM è d'accordo — con sfumature importanti

Ecco la sintesi della risposta di NotebookLM e la mia analisi critica integrata.

***

### Verdetto di NotebookLM sull'approccio Dedup → Anti-Hype → Score

L'approccio proposto da Claude Code è giudicato **"estremamente valido"** e coerente con le criticità emerse nell'esperimento di 14 giorni di Montemagno. NotebookLM lo conferma su tre fronti: [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

1. **Costi**: Lo scoring è la seconda voce di costo più alta del sistema. Filtrare con un modello economico (Gemini Flash, GPT-4o-mini) prima di chiamare i reasoning model pesanti ottimizza drasticamente il budget API [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)
2. **Zero Tolleranza**: Un gate binario è più coerente con la filosofia "roba pratica, zero fuffa" rispetto alla media pesata dove un contenuto hype può comunque passare con un voto mediocre [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)
3. **Riduzione del babysitteraggio**: Marco ammette ancora 4 ore al giorno di supervisione manuale. Automatizzare lo scarto dell'hype riduce il carico cognitivo, avvicinando all'obiettivo Zero Human Company [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

### I Rischi che NotebookLM identifica (e io condivido)

Qui la risposta diventa più interessante:

**1. Falsi Negativi (il rischio più serio)**
Un modello veloce/economico potrebbe non distinguere tra "oggetto luccicante inutile" e "tecnologia pionieristica da monitorare". Il gate troppo severo rischia di eliminare il vantaggio competitivo del "pionierizzare" — che è esattamente il core value di Montemagno. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

**2. Mancanza di sfumature**
Un contenuto etichettato come "hype" potrebbe contenere un'idea utile se rielaborata. Il gate binario taglia tutto, senza possibilità di recupero parziale. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

**3. Dipendenza dalla qualità del prompt**
Se il `is_hype_content` non è tarato con precisione sui principi del brand, scarterà contenuti che l'umano avrebbe approvato. Questo è il punto più critico: il gate è forte quanto il suo prompt. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

### Cosa suggerisce di fare in più (le ottimizzazioni)

NotebookLM propone tre upgrade rispetto al piano base di Claude Code:

**A) Few-Shot Prompting nel Gate** (critico)
Invece di un semplice "Sì/No" con istruzioni astratte, il gate deve avere nel prompt **5-10 esempi di contenuti eccellenti** e **5-10 esempi di fuffa** come riferimento. Questo allinea la decisione binaria al "giudizio umano codificato" del brand in modo molto più preciso — ed è la differenza tra un gate che funziona e uno che butta via roba buona. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

**B) Feedback Loop Dinamico sul Gate stesso**
Il `feedback_bonus` attuale è **hardcoded a 5.0** — statico, non si aggiorna mai. Se un contenuto simile a uno già scartato performa bene su LinkedIn, il gate dovrebbe allentarsi leggermente in modo dinamico. Questo è il vero upgrade rispetto a Montemagno. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

**C) L'ordine rimane confermato**: Dedup prima del gate (non dopo) è la scelta tecnicamente più efficiente — non ha senso classificare come hype qualcosa già archiviato come duplicato. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

### La mia lettura critica integrata

**Cosa ha ragione Claude Code:**

- L'ordine delle tre fasi è corretto e ben motivato
- Il gate binario è superiore alla media pesata per i motivi citati
- Il risparmio sui costi API è reale e misurabile

**Dove Claude Code si è fermato troppo presto:**

- Non ha specificato che il prompt del gate deve essere few-shot (non zero-shot) — senza esempi concreti il gate è fragile
- Non ha affrontato il feedback loop dinamico sul gate: se il `feedback_bonus` rimane statico, il sistema non impara davvero
- Non ha previsto una modalità di "revisione borderline" — contenuti con una valutazione incerta (es. confidence bassa del gate) potrebbero finire in una coda umana invece di essere scartati definitivamente

**La formula ottimale consigliata da NotebookLM (con cui concordo):**

```
Score = [(Σ Parametri Configurabili × Pesi Brand) + Feedback Dinamico] × Anti-Hype Multiplier (0 o 1)
```

Il multiplier 0/1 garantisce che nessuna somma di parametri positivi possa "salvare" un contenuto hype — è architetturalmente più robusto di qualsiasi media pesata. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

### Conclusione operativa

**Sì, implementa Dedup → Anti-Hype → Score.** NotebookLM è d'accordo con l'architettura. Ma non partire con un gate zero-shot: prima di mettere in produzione `is_hype_content`, costruisci un set di 10-15 esempi reali (buoni e scarti) del tuo brand specifico e usali come few-shot nel prompt. Senza questa calibrazione, il gate sarà troppo generico e non rifletterà la filosofia reale del brand — che è esattamente il problema che stai cercando di risolvere rispetto a Montemagno.
