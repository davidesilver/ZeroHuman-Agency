# Screenshot & GIF Guide — ZeroHuman Demo

## Fase 1: Popola il DB (10 min)

1. Vai su [Supabase Dashboard](https://supabase.com/dashboard) → il tuo progetto → SQL Editor
2. Apri `supabase/seed-demo.sql` da questo repo
3. Incolla e clicca **Run**
4. Dovresti vedere: `Demo seed completed successfully for brand: ZeroHuman Demo`

## Fase 2: Screenshot per social (20 min)

Lancia l'app:
```bash
npm run dev
```
Vai su `http://localhost:3080`, seleziona il brand "ZeroHuman Demo".

### Le 5 schermate più forti (in ordine di impatto)

| # | Pagina | URL | Cosa mostra | Perché funziona |
|---|--------|-----|-------------|-----------------|
| 1 | **Content Hub** | `/content-hub` | 6 draft cards con status colorati (published, scheduled, GOD mode, approved...) | Mostra lo stato del pipeline in un colpo solo |
| 2 | **GOD Mode review** | `/content-hub/[draft_4_id]` | Il feedback dei 4 agenti su draft_4, con score e azioni prioritarie | La feature più unica — non l'ha nessun competitor |
| 3 | **Research** | `/research` | 8 research items con titoli reali, score colorati, status tabs | Mostra la pipeline di ricerca attiva |
| 4 | **Dashboard home** | `/` | KPI cards (drafts, published, pipeline health, costs) | Overview potente in una schermata |
| 5 | **Calendar** | `/calendario` | 6 eventi pianificati su giorni diversi | Mostra la visione settimanale |

### Come fare uno screenshot perfetto per social

**Dimensioni:** 2560×1440 (retina, quello che hai già)

**Crop consigliato per LinkedIn/X:** 1200×628 (16:9 wide)

**Tool macOS:**
- `Cmd+Shift+4` → seleziona area → screenshot in /Desktop
- `Cmd+Shift+5` → finestra specifica (più pulito, include solo l'app)

**Tip:** Vai in Settings → metti il browser in full-screen (F11 in Chrome), poi screenshot dell'intera finestra. Elimina la barra del browser dal crop.

### Crop con Quick Look (zero tool)
1. Apri l'immagine con Preview
2. `Cmd+K` → inserisci dimensioni 1200×628
3. Salva come PNG

---

## Fase 3: GIF virale (30 min)

### Lo storyboard della GIF (sequenza di 8 movimenti)

Questo è il flow che vuoi registrare. Dura circa 60-90 secondi.

```
[1] Dashboard overview  →  3 sec pausa
[2] Click "Research"    →  scroll veloce sulla lista items  →  2 sec
[3] Click un item       →  "Generate Content" button  →  2 sec
[4] Loading animation   →  Draft appare  →  3 sec
[5] Click "GOD Mode"    →  Loading  →  GOD Mode result con 4 agenti  →  4 sec
[6] Click "Approve"     →  Status → APPROVED (verde)  →  2 sec
[7] Click "Schedule"    →  Calendar view con l'evento  →  2 sec
[8] Dashboard overview  →  counter updated  →  2 sec END
```

**Totale: ~20 secondi di GIF** (loop perfetto)

### Tool per registrare

**Opzione A — Loom (gratis, facile):**
1. Installa [Loom](https://www.loom.com)
2. Registra area dello schermo (solo il browser, senza barra)
3. Esporta come GIF (Loom lo fa nativo)

**Opzione B — Kap (macOS, open source, migliore qualità):**
```bash
brew install --cask kap
```
1. Seleziona area (solo il browser content, escludi chrome/barra url)
2. Registra il flow
3. Export → GIF, 800px width, 15fps (file size sotto 5MB)
4. Per LinkedIn: esporta anche MP4 (più nativo, più views)

**Opzione C — QuickTime + gifski (massima qualità):**
```bash
brew install gifski
# Registra con QuickTime → File → New Screen Recording → seleziona area
# Poi converti:
gifski --fps 15 --width 800 -o demo.gif recording.mov
```

### Dimensioni ottimali per piattaforma

| Piattaforma | Formato | Dimensione max | Consiglio |
|-------------|---------|----------------|-----------|
| LinkedIn | GIF o MP4 | 5MB GIF / 200MB MP4 | Preferisci MP4 — più views |
| X/Twitter | GIF | 15MB | GIF va bene |
| GitHub README | GIF | Nessun limite (hosted su Imgur/CDN) | Usa gifski per qualità |

### Upload GIF su GitHub README

```bash
# Metti la GIF in docs/assets/
mkdir -p docs/assets
mv demo.gif docs/assets/pipeline-demo.gif
git add docs/assets/
git commit -m "docs: add pipeline demo GIF"
git push

# Nel README, aggiungi sopra il testo:
# ![ZeroHuman Pipeline Demo](docs/assets/pipeline-demo.gif)
```

---

## Fase 4: Montaggio asset per ogni contenuto

| Contenuto | Screenshot da usare | GIF/Video? |
|-----------|--------------------|----|
| #3 Open source announcement | Dashboard overview (screenshot 4) | No — la GIF è troppo per un annuncio |
| #5 Pipeline overview | GIF completa del flow | Sì — questo è il post dove metti la GIF |
| #1 GOD Mode | Screenshot GOD Mode review (screenshot 2) | Clip dei 4 agenti (10 sec) |
| #2 Humanizer | N/A — non visibile nell'UI ancora | Usa un before/after testuale |
| #4 Multi-tenancy | Settings/Brands page | N/A |

---

## Note finali

- **Non nascondere che è vuoto nelle altre schermate.** Il seed popola solo le pagine key. Se finisci sulle metriche (placeholder), non fare screenshot di quella.
- **La GIF vale 10 screenshot.** Il movimento mostra che il software funziona davvero. GitHub README con GIF → +40% stars secondo le analisi dei top repos.
- **Aggiungi sempre l'URL del repo** in ogni immagine/video — nei contenuti social il link è nell'anchor text, ma nella GIF (che può girare staccata dal post) mettilo come watermark o come schermata finale.
