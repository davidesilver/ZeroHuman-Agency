Hai ragione, mi sono perso sui modelli. Rileggendo il piano concentrandomi sulla parte tecnica e funzionale, questi sono i punti che contano: [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

**Cosa è corretto e va approvato**

L'unificazione su un singolo gateway `llm_client.py` è la scelta più importante della Fase C e risolve un problema reale. Con 4 implementazioni clonate di `call_llm`, il cost tracking su Supabase è parziale — traccia solo le chiamate che passano dal client nuovo, non quelle di writer.py, editor.py, scoring e writing lab. Questo significa che la dashboard `costi-api` mostra dati incompleti da subito. Eliminare i cloni risolve questo a monte. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

Il parametro `task_type` come interfaccia è corretto come astrazione — disaccoppia chi chiama dall'implementazione del routing. Qualunque modello metti sotto, l'interfaccia resta stabile.

***

**I problemi tecnici reali**

**1. Il `CAUTION` del piano è il punto più importante ed è sepolto in fondo.** [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

Il vecchio `scoring/engine.py` aveva la logica `if anthropic_api_key → usa Anthropic SDK, else → OpenRouter`. Con l'unificazione sul gateway, questa priorità viene rimossa e tutta la logica di fallback diventa responsabilità esclusiva di `llm_client.py`. Se il gateway non implementa correttamente questo fallback chain — ovvero: prova Anthropic SDK prima, poi OpenRouter, poi errore esplicito — perdi la capacità di usare la chiave Anthropic direttamente. Il piano non mostra il codice del gateway aggiornato con questa logica. Prima di cancellare i cloni, verifica che `llm_client.py` abbia:

```python
if settings.anthropic_api_key:
    # usa SDK Anthropic nativo
elif settings.openrouter_api_key:
    # usa OpenRouter
else:
    raise RuntimeError("No API key configured")
```

**2. Il `track_cost` nei cloni esistenti usa parametri diversi.**

Guarda il codice di `scoring/engine.py` dalla Fase B — chiama `track_cost(brand_id, "scoring_agent", "claude-sonnet-4-20250514", ...)` con il nome modello hardcoded. Quando migri al gateway unificato, il nome del modello viene deciso dentro `llm_client.py` in base al `task_type`. Questo significa che `track_cost` dentro il gateway non sa quale modello è stato effettivamente chiamato finché non torna la risposta. Controlla che il gateway passi il modello realmente usato a `track_cost`, non il `task_type` come stringa.

**3. `writer.py` e `editor.py` usano parsing ad-hoc del JSON oltre a `call_llm`.** [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

La migrazione non è solo sostituire l'import — c'è parsing personalizzato del raw response in ogni file. Se il formato della response del gateway è diverso da quello che i file si aspettano (`message.content[0].text` vs `choices[0].message.content`), rompi silenziosamente il parsing dei draft. Il verification plan dice "compila e controlla le importazioni" ma non verifica che i draft prodotti da writer.py dopo la migrazione abbiano ancora `title`, `body`, `hooks`, `cta` nel JSON. Aggiungi un test su questo prima di deployare. [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

***

**Risposta alla domanda aperta** [notebooklm.google](https://notebooklm.google.com/notebook/9d94ed2c-3409-48ba-8285-80e9696fff40?authuser=2)

Sì, approva l'eliminazione dei cloni e il passaggio globale al gateway. Ma condizionato a: verificare il fallback chain Anthropic→OpenRouter nel gateway, e verificare che il parsing JSON di writer.py/editor.py funzioni con il nuovo formato di response prima di cancellare i vecchi file.
