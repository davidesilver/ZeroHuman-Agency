# Deployment Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- A Supabase project (free tier is sufficient for single-brand)
- An OpenRouter API key
- A Serper API key (for web search)

## Local Development

```bash
# Clone the repository
git clone https://github.com/yourhandle/content-engine.git
cd content-engine

# Copy environment template
cp .env.example .env
# Fill in your API keys in .env

# Start the full local stack (API + DB)
docker-compose up -d

# Install Python dependencies
cd python
pip install -r requirements.txt

# Run database migrations
python -m content_engine.db.migrate

# Start the API server
uvicorn main:app --reload --port 8000

# In a separate terminal: start the frontend
cd ../
npm install
npm run dev
# Dashboard available at http://localhost:3000/dashboard
```

## First Pipeline Run

```bash
# Trigger a manual research run (does not publish — sets status to 'scored')
curl -X POST http://localhost:8000/pipeline/research \
  -H "Content-Type: application/json" \
  -d '{"vertical_id": "your_vertical_id"}'

# Check what was scored above threshold
curl http://localhost:8000/pipeline/queue?vertical_id=your_vertical_id

# Trigger writing for approved items
curl -X POST http://localhost:8000/pipeline/write \
  -H "Content-Type: application/json" \
  -d '{"vertical_id": "your_vertical_id"}'
```

## Railway Deployment (Recommended)

1. Push to GitHub
2. Create a new Railway project → "Deploy from GitHub repo"
3. Add environment variables in Railway dashboard (all keys from `.env`)
4. Railway auto-detects `Dockerfile` or `nixpacks` configuration
5. Add a Cron Job service:
   - Command: `python -m content_engine.core.scheduler trigger_daily --vertical YOUR_ID`
   - Schedule: `0 7 * * *`

## Supabase Setup

```sql
-- Enable pgvector extension (required for semantic deduplication)
create extension if not exists vector;

-- Run migrations from supabase/migrations/ in order
-- The migration files create all required tables and indexes
```

## Monitoring

Every pipeline run writes to `pipeline_runs` table. Query run health:

```sql
SELECT
  vertical_id,
  started_at,
  status,
  items_collected,
  items_scored,
  items_published,
  jsonb_array_length(errors) as error_count
FROM pipeline_runs
ORDER BY started_at DESC
LIMIT 10;
```
