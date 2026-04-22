-- Migration 019: Weekly newsletter cron + daily pipeline cron
-- Adds pg_cron jobs for automated newsletter generation and daily research pipeline.
-- pg_cron syntax: cron.schedule(name, schedule, command)
-- All jobs use HTTP POST to the scheduler endpoint (via pg_net extension).

BEGIN;

-- ─── Weekly newsletter generation ────────────────────────────────────────────
-- Fires Monday 05:00 UTC → POST /api/scheduler/weekly-newsletter
-- Creates draft newsletters for every brand with ≥3 approved items in last 7 days.
DO $$
BEGIN
  PERFORM cron.unschedule('weekly-newsletter-generation');
EXCEPTION WHEN OTHERS THEN NULL;
END;
$$;

SELECT cron.schedule(
  'weekly-newsletter-generation',
  '0 5 * * 1',   -- Monday 05:00 UTC
  $$
  SELECT net.http_post(
    url := current_setting('app.python_backend_url', true) || '/api/scheduler/weekly-newsletter',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Scheduler-Secret', current_setting('app.scheduler_secret', true)
    ),
    body := '{}'::jsonb
  );
  $$
);

-- ─── Daily research pipeline ──────────────────────────────────────────────────
-- Already partially implemented in app; these crons ensure it runs even if
-- the Python process doesn't have an internal scheduler.
DO $$
BEGIN
  PERFORM cron.unschedule('daily-scoring-pipeline');
EXCEPTION WHEN OTHERS THEN NULL;
END;
$$;

SELECT cron.schedule(
  'daily-scoring-pipeline',
  '0 6 * * *',   -- Every day 06:00 UTC
  $$
  SELECT net.http_post(
    url := current_setting('app.python_backend_url', true) || '/api/scheduler/daily-pipeline',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Scheduler-Secret', current_setting('app.scheduler_secret', true)
    ),
    body := '{}'::jsonb
  );
  $$
);

-- ─── Comment on purpose ──────────────────────────────────────────────────────
COMMENT ON EXTENSION pg_cron IS
  'Scheduled jobs: weekly-newsletter-generation (Mon 05:00), daily-scoring-pipeline (06:00), '
  'memory-ttl-sweep (03:30 — see migration 018), memory-monthly-partition (1st of month — see 018).';

COMMIT;
