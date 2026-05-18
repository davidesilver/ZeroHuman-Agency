## Parent PRD

#{{PARENT}}

## What to build

Scrapling come strumento per competitor monitoring e spider task dove serve stealth anti-Cloudflare. Complementare a Firecrawl (non sostituisce).

Riferimento PRD §3.7.

## Acceptance criteria

- [ ] `scrapling` aggiunta a `python/pyproject.toml`
- [ ] Modulo `retrievers/competitor_spider.py` con `start_spider(target_urls, brand_id)` e pause/resume
- [ ] Scrapling MCP server configurato in `.mcp.json` (dev-time)
- [ ] Endpoint `POST /api/research/competitor` per avviare spider
- [ ] Risultati salvati in tabella `competitor_snapshots` (URL, title, content, scraped_at, brand_id) con RLS
- [ ] UI Research → "Competitor watch" tab: lista URL monitorati, snapshot history
- [ ] Test: spider su 3 URL pubblici (incluso almeno 1 Cloudflare-protected) → contenuto estratto

## Blocked by

- Blocked by #{{1}}

## User stories addressed

Gap PRD #2 (ricerca competitor automatizzata).
