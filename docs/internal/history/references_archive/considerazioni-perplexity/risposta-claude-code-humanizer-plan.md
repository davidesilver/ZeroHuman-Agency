Implementazione solida. Ecco la valutazione onesta.

***

## Cosa Claude Code ha fatto bene

**Architettura: corretta al 100%**

- Posizione nel pipeline: dopo `god_system`, prima di `adapter` — esattamente dove deve stare
- Struttura a doppio passaggio implementata come due chiamate separate con contesto esplicito, non come unico prompt monolitico
- Carica `humanizer_skill.md` da file all'avvio del modulo (non hardcoded nel codice)
- Usa `get_agent_identity()` — il che significa che finalmente almeno un agente usa il sistema DB che era stato documentato ma non cablato (fix del bug che Claude Code stesso aveva identificato)
- Voice calibration prende i top-3 contenuti per `engagement_score` dalla tabella `content_performance` — intelligente, usa dati reali invece di un campo statico

**Il feedback loop tracking è una mossa eccellente**
La tabella `humanizer_performance` con la query SQL che correla `ai_patterns_found` con `avg_engagement` è esattamente il tipo di dato che serve per capire se l'humanizer migliora davvero le performance o è rumore. È il loop che mancava nel piano originale.

**Il flag `use_humanizer` per brand**
`ALTER TABLE brands ADD COLUMN IF NOT EXISTS use_humanizer BOOLEAN DEFAULT FALSE` — controllo granulare per canale, rollback istantaneo. Fatto bene.

***

## Problemi reali

**1. Il doppio passaggio non è multi-turn — è una debolezza**

Il Pass 2 (audit) prende il testo del Pass 1 ma lo rimette nel prompt come testo statico:

```python
audit_prompt = ANTI_AI_AUDIT_PROMPT.format(
    title=sanitize_for_prompt(title),  # ← result1["title"]
    body=sanitize_for_prompt(body),    # ← result1["body"]
)
```

Funziona, ma non è lo stesso di una conversazione multi-turn dove il modello vede la propria riscrittura come parte della storia. In pratica la differenza è minima con Haiku, ma è una semplificazione da tenere presente.

**2. La voice calibration usa `content_performance`, non `gold_examples`**

Il piano originale e la Fase 0 prevedevano di aggiungere `gold_examples` alla tabella `brands` come campo editabile manualmente. Claude Code ha invece scelto di prendere automaticamente i top-3 per engagement score da `content_performance`.

È una scelta pragmatica — funziona senza richiedere data entry manuale — ma ha un rischio: i contenuti con engagement alto potrebbero essere virali per ragioni esterne (tema del momento, boost di algoritmo) e non necessariamente rappresentativi dello stile migliore del brand. Un mix dei due (gold_examples manuali + top performer automatici) sarebbe più robusto.

**3. Il modello non è specificato**

Nel codice `call_llm()` non vedo dove viene forzato Haiku. Se `call_llm` usa il default del brand (che potrebbe essere Sonnet o Opus), il costo stimato di $0.002-$0.005 diventa $0.01-$0.03. Bisogna verificare che `call_llm` in questo contesto usi esplicitamente `claude-haiku-4-5`.

**4. Nessun test scritto**

L'integration guide menziona `pytest tests/test_humanizer.py` ma il file non è allegato. Con un agente che fa due chiamate LLM, i test sono critici per verificare il fallback del Pass 2 (che è implementato correttamente — se l'audit fallisce continua con il Pass 1) e il comportamento con `gold_examples` vuoti.

***

## Verdetto

**Da implementare subito.** I problemi identificati sono minori e non bloccanti — il fallback del Pass 2 è già gestito, la voice calibration funziona anche senza gold_examples manuali, la struttura è pulita.

L'unica cosa da fare prima di mergere: verificare che `call_llm` in questo contesto passi esplicitamente `model="claude-haiku-4-5"` (o il parametro equivalente nella tua utility). Se lasci il default del brand e il brand usa Sonnet, i costi sono 5-10x superiori alle stime.
