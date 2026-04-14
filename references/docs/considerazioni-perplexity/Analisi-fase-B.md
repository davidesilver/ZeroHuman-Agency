Ho letto il walkthrough Fase B in dettaglio. Valutazione onesta. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

## Cosa è stato fatto bene — e genuinamente bene

**Alert su `research_items = 0`**: c'è. Era esattamente il quarto alert che avevo chiesto di aggiungere e che mancava nel piano Fase A. Bene. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

**Thresholds per brand con fallback globale**: il pattern `branddata.get("auto_approve_threshold") or settings.auto_approve_threshold` è corretto. Retrocompatibile, non rompe nulla di esistente, ogni brand può avere le sue soglie. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

**`parse_json` che lancia `ValueError` invece di restituire dati fallback silenziosi**: questa è la scelta più importante del walkthrough e quasi nessuno la fa. Il vecchio comportamento — ritornare un dizionario vuoto su JSON malformato — è il tipo di bug che produce dati corrotti nel DB senza errori visibili. Adesso fallisce in modo esplicito e viene catchato dal `fail()` che manda l'alert Telegram. Corretto. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

**GOD Mode parallelo con `asyncio.gather`**: implementato. I tre agenti (Advocate, FactCheck, Creative) girano in parallelo, Synthesis raccoglie. Il check degli errori post-gather è presente. La stima "10 secondi invece di 35" è realistica. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

**Guardia statistica AutoOptimizer a n≥10**: c'è, con il sample size alzato a 50. Era esattamente quello che avevo segnalato. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

**`use_context7` per brand dal DB**: il FactChecker legge `brand.get("use_context7", False)` prima di chiamare MCP. Context 7 è opt-in per brand, spento di default. Corretto. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

## I problemi che vedo nel codice — concreti, non teorici

**1. Il GOD Mode parallelo ha ancora una dipendenza implicita tra agenti che non è stata rimossa.**

Guarda i prompt nel walkthrough. Il `CREATIVE_PROMPT` contiene ancora `{advocate_feedback}` e `{factcheck_feedback}` come variabili di input. Ma nella versione parallela, `run_creative()` viene lanciato in `asyncio.gather` insieme a `run_factcheck()` — quindi quando Creative parte, il feedback del FactChecker non esiste ancora. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

Il risultato: `{factcheck_feedback}` viene passato come stringa vuota o come valore di default non definito a `run_creative`. Il prompt Creative arriva al LLM con un placeholder vuoto. Il LLM produce output meno accurato di quello sequenziale originale — ma non lancia errori, quindi non te ne accorgi.

Hai parallelizzato la velocità ma non hai aggiornato i prompt per riflettere l'indipendenza degli agenti. Il Creative prompt deve funzionare solo con `{body}` e `{title}` nella versione parallela, senza feedback degli altri agenti. Altrimenti stai ottimizzando per velocità degradando la qualità.

**2. L'AutoOptimizer valuta se `success = True` con un valore hardcoded.**

Nel codice: [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)
```python
success = True  # Assume new prompt scored 8.5 vs old 6.0
```

Poi:
```python
if success:
    db.table("brands").update(custom_writer_prompt=new_prompt)...
```

Questo significa che **ogni notte l'AutoOptimizer sovrascrive il prompt corrente con quello "ottimizzato"** indipendentemente da qualsiasi test reale. Il commento dice "Fake a successful test loop" — ma il codice salva davvero su DB. Il ciclo di test reale (generare 5 bozze, scorarle, confrontare le medie) non è implementato — è simulato con `success = True`.

Se questo cron gira stanotte, ogni brand con più di 10 draft rigettati avrà il suo `custom_writer_prompt` sovrascritto con una variazione generata da un LLM senza nessuna validazione reale. Questo è il bug più pericoloso del walkthrough.

**Fix immediato**: aggiungi `OPTIMIZER_ENABLED = False` in settings finché il test reale non è implementato, oppure rimuovi la `db.update()` lasciando solo il log.

**3. Il dedup semantico ha un race condition potenziale nel loop di scoring.**

Nel `run_scoring`, per ogni item: [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)
1. Genera embedding
2. Salva embedding su DB
3. Chiama RPC `find_semantic_duplicates`

Se due item con contenuto simile vengono processati in parallelo (il loop usa `for item in items` ma non è chiaro se è sequenziale o asincrono), entrambi passano il check di duplicati prima che l'altro abbia salvato il suo embedding. Risultato: entrambi vengono scored e approvati invece di uno solo.

Se il loop è sequenziale non è un problema. Se diventa asincrono in futuro, lo è. Vale la pena aggiungere un commento esplicito: `# NOTE: sequential by design to prevent dedup race conditions`.

***

## La cosa che manca ancora

Il test reale dell'AutoOptimizer — generate 5 bozze con il nuovo prompt, scorale con `score_item()`, confronta la media con il baseline — è indicato come passo 3 nel walkthrough ma non è implementato. È il cuore del feature. Senza quello, l'AutoOptimizer è un sistema che modifica i propri prompt senza mai verificare che le modifiche migliorino qualcosa. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

## Sintesi

La Fase B è solida su 3 dei 4 punti: alerting, thresholds per brand, GOD Mode parallelo. Il `parse_json` che lancia eccezione invece di fallback silenzioso è una delle scelte più mature del codebase. 

I due problemi urgenti: il Creative prompt con placeholder vuoti nella versione parallela degrada silenziosamente la qualità, e l'AutoOptimizer con `success = True` hardcoded sovrascrive i prompt su DB senza test reali. Il secondo in particolare va disattivato prima che il cron notturno giri.