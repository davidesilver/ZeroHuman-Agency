## Humanizer: vale la pena?

**13.9k stelle, 1.2k fork, aggiornato 2 settimane fa.** Non è un progetto toy — ha trazione reale. [github](https://github.com/blader/humanizer)

### Cos'è esattamente

Una **Claude Code skill** (file `SKILL.md`) che insegna a Claude un set di 29 pattern per rilevare ed eliminare il "sapore AI" dal testo. Basato sulla guida Wikipedia "Signs of AI Writing", include anche un **secondo pass di audit** per catturare gli AI-ism sopravvissuti alla prima riscrittura. [github](https://github.com/blader/humanizer)

La feature più interessante è la **Voice Calibration**: puoi passare 2-3 paragrafi del tuo stile personale e la skill adatta la riscrittura a quel tono invece di produrre output genericamente "pulito". [github](https://github.com/blader/humanizer)

***

### È utile per il tuo Content Engine?

**Sì, ma in modo specifico — non generico.**

**Dove si inserisce perfettamente:**

- Come **post-processing step** dopo il God Mode / `god_synthesis`. Ora il God Mode produce testo di qualità, ma è ancora riconoscibilmente AI. L'Humanizer attacca esattamente quel problema.
- Come **Writing Lab automatizzato**: invece di far votare manualmente Marco Sì/No tra varianti stilistiche, potresti usare l'Humanizer come trasformazione deterministica con la voice calibration fissata sui principi stilistici del brand.

**Il punto critico però:** è una skill per Claude Code (tool interattivo), non una libreria Python importabile nel pipeline. Il `SKILL.md` è essenzialmente un mega-prompt strutturato. Questo significa che puoi:

1. **Usarlo direttamente** come Claude Code skill durante la fase di writing manuale
2. **Estrarre il contenuto di SKILL.md** e usarlo come system prompt aggiuntivo nel tuo agente `writer.py` o `god_synthesis` — questo è l'uso più interessante per te

***

### Come integrarlo concretamente nel tuo sistema

```python
# In writer.py o god_synthesis — aggiungi il contenuto di SKILL.md
# come istruzione aggiuntiva nel prompt di riscrittura finale

HUMANIZER_INSTRUCTIONS = open("prompts/humanizer_skill.md").read()

god_synthesis_prompt = f"""
{HUMANIZER_INSTRUCTIONS}

Sei god_synthesis. Prendi i feedback di tutti i modelli e produci
il testo finale. Applica le regole di umanizzazione sopra.

Voice reference: {brand.writing_sample}
"""
```

La **Voice Calibration** diventa la tua brand persona storica: passi i contenuti che hanno performato meglio (gold examples) come reference stilistica, e ogni output viene adattato a quel tono. [github](https://github.com/blader/humanizer)

***

### Cosa non fa

- Non è una libreria, non ha API, non ha CI/CD — è solo un file Markdown con istruzioni
- Non gestisce la **lingua italiana** nativamente (tutti i pattern sono in inglese); andrebbe testato e probabilmente adattato per l'italiano
- Non risolve il problema dell'accuratezza fattuale — umanizza la forma, non verifica il contenuto

***

### Verdetto

**Installalo subito come Claude Code skill** (`~/.claude/skills/humanizer`) — costa zero e ti torna utile immediatamente per i task manuali. [github](https://github.com/blader/humanizer)

**Per il pipeline automatico**: estrai `SKILL.md` e integralo come system prompt in `god_synthesis` nella Fase 5 (quella che NotebookLM aveva identificato come mancante — il God Mode di sintesi). Diventa il tuo Writing Lab automatico, riducendo il bisogno del feedback Sì/No manuale di Marco.

***

L'analisi di NotebookLM è corretta e supera la mia proposta precedente su un punto fondamentale: il principio di **Separation of Concerns**.

**Perché ha ragione:**

1. **Carico cognitivo**: un agente `writer` non dovrebbe portare anche 29 regole di humanization — produce testo forzato. Meglio lasciarlo scrivere liberamente e delegare la ripulitura a un agente dedicato.

2. **Doppio passaggio con autoriflessione**: il metodo di SKILL.md (scrivi → chiedi "cosa è ancora ovviamente AI?" → riscrivi) funziona meglio su testo già prodotto, non durante la prima stesura.

3. **Flessibilità e costi**: puoi usare un modello economico per scrivere (Haiku/Flash) e Sonnet solo per il raffinamento finale, e attivare l'humanizer solo per certi canali.

**L'architettura corretta per il tuo sistema:**

| Agente | Modello | Compito |
|--------|---------|---------|
| `writer.py` | Haiku/Flash | Genera contenuto grezzo |
| `god_system.py` | Sonnet/Opus | Critica, fact-check, sintesi |
| `editor_agent.py` | Sonnet | Humanizer — solo forma e stile |

L'`editor_agent` è già nella tua architettura documentata — questo è il suo ruolo naturale. Non serve un agente nuovo, serve cablare quello che esiste con il contenuto di SKILL.md come system prompt e la voice calibration del brand come reference stilistica.

***

L'integrazione si riduce a tre mosse concrete:

**1. Scarica SKILL.md nel progetto** (una riga di curl, nessuna dipendenza):

```bash
mkdir -p prompts/skills
curl -o prompts/skills/humanizer.md \
  https://raw.githubusercontent.com/blader/humanizer/main/SKILL.md
```

**2. Crea `agents/editor_agent.py`** — usa il contenuto del SKILL.md come system prompt e implementa il doppio passaggio nativo del file (draft → audit "cosa rende questo testo ovviamente AI?" → revisione finale). Usa Haiku perché l'editing non richiede reasoning pesante, solo pattern recognition e riscrittura.

**3. La Voice Calibration usa i `gold_examples` già nel DB** — gli stessi che stai aggiungendo alla tabella `brands` nella Fase 0 del piano diventano automaticamente il parametro di voice calibration. Zero lavoro aggiuntivo.

Il posto nel pipeline è dopo `god_synthesis` e prima di `publisher.py`, attivabile per canale (blog/newsletter sì, docs tecniche no).

Costo aggiuntivo stimato: ~$0.002 per item in Haiku — trascurabile rispetto al God System in Sonnet.
