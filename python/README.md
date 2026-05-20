# Backend

The FastAPI backend powering the Content Engine research, scoring, and generation pipeline.

## Running the backend

```bash
uv sync
uv run uvicorn src.content_engine.main:app --reload --port 8000
# → http://localhost:8000
```

## Documentation

- [Setup Guide](../docs/SETUP.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [API Guide](../docs/API.md)
- [Deployment](../docs/DEPLOYMENT.md)

## Entrypoint

[`src/content_engine/main.py`](src/content_engine/main.py)
