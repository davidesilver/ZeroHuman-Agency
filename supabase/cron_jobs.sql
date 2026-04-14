-- Postiz Analytics Cron Jobs
-- Schedule: Daily pull of engagement metrics and feedback_bonus update

-- Cron Job 1: Pull Postiz Analytics (06:00 UTC)
-- Pull metrics for all published posts from the last 7 days
SELECT cron.schedule(
  'pull-postiz-analytics-0600',
  '0 6 * * *',
  $$
  SELECT net.http_post(
    url := 'https://bljtqkzmebbvzfwhcjvl.supabase.co/functions/v1/postiz-analytics',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || settings.service_role_key
    ),
    body := jsonb_build_object('action', 'pull_daily')
  );
  $$
);

-- Cron Job 2: Update Feedback Bonus (07:00 UTC)
-- Compute and update feedback_bonus for all active brands
SELECT cron.schedule(
  'update-feedback-bonus-0700',
  '0 7 * * *',
  $$
  SELECT net.http_post(
    url := 'https://bljtqkzmebbvzfwhcjvl.supabase.co/functions/v1/postiz-analytics',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || settings.service_role_key
    ),
    body := jsonb_build_object('action', 'update_bonus')
  );
  $$
);

-- Cron Job 3: Full Analytics Cycle (08:00 UTC)
-- Run complete cycle: pull metrics + update bonus in one job
SELECT cron.schedule(
  'run-daily-analytics-cycle-0800',
  '0 8 * * *',
  $$
  SELECT net.http_post(
    url := 'https://bljtqkzmebbvzfwhcjvl.supabase.co/functions/v1/postiz-analytics',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || settings.service_role_key
    ),
    body := jsonb_build_object('action', 'full_cycle')
  );
  $$
);

-- Note: Choose ONE schedule strategy:
-- Option A: Separate jobs (06:00 pull, 07:00 update) - gives more granular control
-- Option B: Single full cycle job (08:00) - simpler, less chance of partial failures

-- To use separate jobs, comment out the "full_cycle" job
-- To use single job, comment out the "pull" and "update" jobs
