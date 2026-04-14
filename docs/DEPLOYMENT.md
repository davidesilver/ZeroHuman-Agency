# Deployment Guide 🚢

The platform dictates a split deployment. Frontend UI components belong on edge/serverless platforms (like Vercel), while the long-running Python orchestrator needs a continuous containerized environment like Railway, Render, or ECS.

## 1. Deploying the Python Backend (Railway/Render)

The backend handles heavy ML and LLM integrations. Serverless constraints (like 10-second timeouts) are not suitable. 
1. Push the `python/` folder to your continuous deployment provider using a standard Python `Dockerfile` or buildpack.
2. Set your Environment Variables:
   - `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
   - `SCHEDULER_SECRET` (crucial for protecting cron routes)
3. Ensure the port binds correctly (typically 8000).

## 2. Deploying Next.js (Vercel)

The frontend is a classic Next.js 15 App router. 
1. Link your git repo to Vercel.
2. Ensure the root directory is set correctly if using a monorepo setup.
3. Provide the Public Environment Keys:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `PYTHON_BACKEND_URL` (Point this to your deployed Railway/Render URL)

## 3. Database Migrations (Supabase)

You must initialize the target Supabase project using the built-in CLI:
```bash
supabase link --project-ref your-project-id
supabase db push
```
This guarantees all 20+ tables, RLS policies, and triggers are exact clones of your local environment.
