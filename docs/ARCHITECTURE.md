# Architecture Deep Dive

## Principles

1. **Domain separation:** Core engine and vertical configs are never mixed. A change to `media_company/config.yaml` cannot break `industrial/` or the `core/`.
2. **Idempotency:** Every pipeline step can be safely retried. Scraping the same URL twice does not create duplicate DB entries. Publishing the same item twice is prevented by the audit trail.
3. **Graceful degradation:** If YouTube is unavailable, the pipeline continues with RSS and web search. If GOD Mode times out, the item falls back to Editor review. Nothing hard-crashes the full run.
4. **Observable by default:** Every pipeline run writes structured logs. Every agent call logs tokens used, latency, model, and outcome. Every publish action is immutable in `publish_log`.

## State Machine

Each `ResearchItem` progresses through a defined set of states:

```
raw → deduped → scored → approved | rejected | review
                              │
                           writing
                              │
                          god_mode (if threshold met)
                              │
                          scheduled
                              │
                          published | failed
```

State transitions are atomic (database transactions). No item can be in two states simultaneously. If a pipeline run is interrupted, items resume from their last committed state on the next run.

## Retry Policy

Each agent wraps its LLM call in a retry decorator:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True
)
async def call_llm(prompt: str, model: str) -> str:
    ...
```

- Attempt 1: immediate
- Attempt 2: 2 seconds
- Attempt 3: 4–30 seconds (exponential backoff)
- After 3 failures: item is flagged `error`, pipeline continues with next item

## Rate Limiting

API rate limits are enforced at two levels:
- **LLM provider level:** OpenRouter has per-model RPM limits. The engine uses a token bucket per model.
- **Dashboard API level:** FastAPI middleware limits UI calls to 60 requests/minute per IP, preventing runaway frontend loops from triggering LLM calls.

## Timeout Policy

All LLM calls have explicit timeouts:
- Pre-filter: 15 seconds
- Scoring: 30 seconds
- Writing: 60 seconds
- GOD Mode per sub-agent: 45 seconds
- Total GOD Mode: 3 minutes

A timed-out call is treated as a retryable error.
