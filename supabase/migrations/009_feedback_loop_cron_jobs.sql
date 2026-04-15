-- ============================================================================
-- AI Content Engine - Feedback Loop Cron Jobs
-- Migration: 009_feedback_loop_cron_jobs.sql
-- Purpose: Schedule automated daily Postiz analytics and feedback loop
-- ============================================================================
--
-- This migration creates cron jobs that call the Python backend API
-- to perform daily analytics pulling and feedback bonus updates.
--
-- IMPORTANT: Requires the backend API to be deployed and accessible
-- The cron service_key should match the project's Supabase cron service key
-- ============================================================================

-- Ensure pg_cron is available
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- ----------------------------------------------------------------------------
-- 1. Daily Postiz Analytics Pull (06:00 UTC)
-- Pulls engagement metrics for all published posts from the last 7 days
-- ----------------------------------------------------------------------------
SELECT cron.schedule(
  'pull-postiz-metrics-daily',
  '0 6 * * *',  -- Runs daily at 06:00 UTC
  $$
  SELECT net.http_post(
    url := 'https://your-backend-url.com/api/analytics/pull-metrics',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Scheduler-Secret', 'your-scheduler-secret-here'
    ),
    body := jsonb_build_object('action', 'pull_daily')
  );
  $$
);


-- ----------------------------------------------------------------------------
-- 2. Update Feedback Bonus (07:00 UTC)
-- Computes and updates the feedback_bonus for all active brands
-- ----------------------------------------------------------------------------
SELECT cron.schedule(
  'update-feedback-bonus-daily',
  '0 7 * * *',  -- Runs daily at 07:00 UTC
  $$
  SELECT net.http_post(
    url := 'https://your-backend-url.com/api/analytics/feedback-loop',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Scheduler-Secret', 'your-scheduler-secret-here'
    ),
    body := jsonb_build_object('action', 'update_bonus')
  );
  $$
);


-- ----------------------------------------------------------------------------
-- 3. Alternative: Full Analytics Cycle (08:00 UTC)
-- Runs both pull metrics and update feedback in a single job
-- Use this instead of jobs 1 & 2 if you prefer a single consolidated job
-- ----------------------------------------------------------------------------
-- NOTE: Commented out by default. To use this, uncomment it and comment out jobs 1 & 2

-- SELECT cron.schedule(
--   'full-analytics-cycle-daily',
--   '0 8 * * *',  -- Runs daily at 08:00 UTC
--   $$
--   SELECT net.http_post(
--     url := 'https://your-backend-url.com/api/analytics/pull-metrics',
--     headers := jsonb_build_object(
--       'Content-Type', 'application/json',
--       'X-Scheduler-Secret', 'your-scheduler-secret-here'
--     ),
--     body := jsonb_build_object('action', 'full_cycle')
--   );
--   $$
-- );


-- ============================================================================
-- Configuration Instructions
-- ============================================================================
--
-- Before activating these cron jobs, you MUST:
--
-- 1. Deploy your Python backend to a public URL
--    - Replace 'https://your-backend-url.com' with your actual backend URL
--    - Ensure the /api/analytics/pull-metrics endpoint is accessible
--    - Ensure the /api/analytics/feedback-loop endpoint is accessible
--
-- 2. Set SCHEDULER_SECRET in your backend environment
--    - Generate a secure random string (e.g., openssl rand -hex 32)
--    - Set it as SCHEDULER_SECRET env var in your backend
--    - Replace 'your-scheduler-secret-here' with this value
--
-- 3. Verify SCHEDULER_BRAND_ID is set (for multi-brand environments)
--    - Set SCHEDULER_BRAND_ID env var in your backend
--    - This determines which brand the cron jobs operate on
--
-- 4. Test the endpoints manually first
--    curl -X POST https://your-backend-url.com/api/analytics/pull-metrics \
--      -H "X-Scheduler-Secret: your-scheduler-secret-here"
--    curl -X POST https://your-backend-url.com/api/analytics/feedback-loop \
--      -H "X-Scheduler-Secret: your-scheduler-secret-here"
--
-- 5. Activate the cron jobs
--    - In Supabase dashboard: Database > Cron Jobs
--    - You should see the 3 cron jobs defined above
--    - Click "Activate" for the jobs you want to run
--    - Monitor execution in the "History" tab
--
-- ============================================================================
-- Schedule Strategy Options
-- ============================================================================
--
-- Option A: Separate Jobs (Recommended for Production)
--   - Job 1: Pull metrics at 06:00 UTC
--   - Job 2: Update feedback at 07:00 UTC
--   - Advantage: More granular control, easier to debug partial failures
--   - Disadvantage: Two separate API calls
--
-- Option B: Single Consolidated Job
--   - Job 3: Full cycle at 08:00 UTC
--   - Advantage: Single API call, simpler to monitor
--   - Disadvantage: Less granular, harder to isolate issues
--
-- Recommendation: Start with Option A (separate jobs) for production,
--                switch to Option B if you prefer simplicity.
-- ============================================================================
