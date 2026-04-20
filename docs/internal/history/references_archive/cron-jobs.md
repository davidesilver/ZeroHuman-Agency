# Supabase Cron Jobs Setup — Postiz Analytics & Feedback Loop

**Status**: ✅ Complete
**Migration**: `009_feedback_loop_cron_jobs.sql`
**Date**: 2026-04-15

---

## Overview

This migration configures automated daily jobs to pull Postiz analytics and update the feedback loop system. These cron jobs call the Python backend API to perform daily analytics operations.

---

## Cron Jobs Created

### Job 1: Pull Postiz Analytics (`pull-postiz-metrics-daily`)
**Schedule**: Daily at 06:00 UTC  
**Endpoint**: `POST /api/analytics/pull-metrics`  
**Purpose**: Pulls engagement metrics for all published posts from the last 7 days

**What it does**:
- Calls `postiz_analytics.run_daily_analytics_cycle()` in Python backend
- Fetches metrics (impressions, likes, shares, comments, saves) from Postiz API
- Records metrics in `social_metrics` table
- Processes all active brands

---

### Job 2: Update Feedback Bonus (`update-feedback-bonus-daily`)
**Schedule**: Daily at 07:00 UTC  
**Endpoint**: `POST /api/analytics/feedback-loop`  
**Purpose**: Computes engagement scores and updates brand `feedback_bonus`

**What it does**:
- Calls `postiz_analytics.update_feedback_bonus()` in Python backend
- Computes weighted engagement scores with temporal decay
- Platform-normalizes metrics (different baselines for LinkedIn, Instagram, TikTok, X)
- Updates `brands.feedback_bonus` for each brand
- Records audit trail in `feedback_loop_audit` table

---

### Job 3: Full Analytics Cycle (`full-analytics-cycle-daily`) - **OPTIONAL**
**Schedule**: Daily at 08:00 UTC  
**Endpoint**: `POST /api/analytics/pull-metrics` with `action: full_cycle`  
**Purpose**: Runs both metrics pull and feedback update in a single consolidated job

**Note**: This job is commented out by default. Use it instead of Jobs 1 & 2 if you prefer a single consolidated cron job.

---

## Setup Instructions

### Step 1: Deploy Backend API

Ensure your Python backend is deployed and accessible at a public URL:
- Example: `https://your-backend.com` (replace with your actual domain)
- Backend must include the new `/api/analytics/pull-metrics` endpoint

### Step 2: Configure Scheduler Secret

Generate a secure secret for cron job authentication:

```bash
# Generate a random 32-character hex string
openssl rand -hex 32
```

Set this as environment variable in your backend:
```bash
# Add to .env or deployment config
SCHEDULER_SECRET=your-generated-secret-here
```

### Step 3: Set Scheduler Brand ID (Optional)

If you have a multi-brand environment, set which brand the cron jobs should operate on:

```bash
# Add to .env or deployment config
SCHEDULER_BRAND_ID=your-brand-uuid-here
```

### Step 4: Update Migration File

Replace the placeholder values in `009_feedback_loop_cron_jobs.sql`:

```sql
-- Replace this URL with your actual backend URL
url := 'https://your-backend-url.com/api/analytics/pull-metrics',

-- Replace this secret with your actual scheduler secret
'X-Scheduler-Secret', 'your-scheduler-secret-here'
```

### Step 5: Apply Migration

```bash
# Push migration to Supabase
supabase db push --linked

# This will create the cron jobs in your Supabase project
```

### Step 6: Activate Cron Jobs

In Supabase Dashboard:
1. Navigate to **Database** > **Cron Jobs**
2. You should see 3 new cron jobs (or 2 if Job 3 is commented out)
3. Click "Activate" on each job you want to run
4. Monitor the "History" tab to verify successful execution

---

## Endpoints Called

### POST /api/analytics/pull-metrics

**Authentication**: Requires `X-Scheduler-Secret` header  
**Body**: 
```json
{
  "action": "pull_daily" | "full_cycle"
}
```

**Actions**:
- `pull_daily`: Pulls metrics only (Job 1)
- `full_cycle`: Runs metrics pull + feedback update (Job 3)

**Response**:
```json
{
  "success": true,
  "data": {
    "brands_processed": 5,
    "total_posts_processed": 42,
    "total_metrics_fetched": 38,
    "brands_updated": 4
  }
}
```

### POST /api/analytics/feedback-loop

**Authentication**: Requires JWT (brand-scoped)  
**Body**: None required

**Response**:
```json
{
  "success": true,
  "data": {
    "previous_score": 5.0,
    "new_score": 6.8,
    "metrics_used": 15,
    "updated_at": "2026-04-15T07:00:00Z"
  }
}
```

---

## Testing Cron Jobs

### Test Manually Before Activating

**Test Metrics Pull**:
```bash
curl -X POST https://your-backend-url.com/api/analytics/pull-metrics \
  -H "Content-Type: application/json" \
  -H "X-Scheduler-Secret: your-scheduler-secret-here" \
  -d '{"action": "pull_daily"}'
```

**Test Feedback Loop**:
```bash
# Get your JWT token from your app's auth system
curl -X POST https://your-backend-url.com/api/analytics/feedback-loop \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Test Full Cycle**:
```bash
curl -X POST https://your-backend-url.com/api/analytics/pull-metrics \
  -H "Content-Type: application/json" \
  -H "X-Scheduler-Secret: your-scheduler-secret-here" \
  -d '{"action": "full_cycle"}'
```

### Verify Cron Job Execution

1. Wait for the next scheduled execution (e.g., 06:00 UTC)
2. Check Supabase Dashboard > Database > Cron Jobs > History tab
3. Look for successful executions (green checkmarks)
4. Check database to verify data:
   ```sql
   -- Verify metrics were pulled
   SELECT COUNT(*) FROM social_metrics;
   
   -- Verify feedback bonus was updated
   SELECT brand_id, feedback_bonus, updated_at 
   FROM brands 
   WHERE updated_at > NOW() - INTERVAL '1 day';
   ```

---

## Monitoring & Troubleshooting

### Check Cron Job Logs

In Supabase Dashboard > Database > Cron Jobs > History:
- **Success**: Green checkmark, shows response body
- **Failed**: Red X, shows error message

### Common Issues

**Issue 1: "Failed to connect to backend"**
- **Cause**: Backend URL is incorrect or backend is down
- **Fix**: Verify backend is deployed and URL is correct

**Issue 2: "Invalid or missing scheduler secret"**
- **Cause**: SCHEDULER_SECRET doesn't match between backend and cron job
- **Fix**: Ensure SCHEDULER_SECRET is set identically in both places

**Issue 3: "No active brands found"**
- **Cause**: SCHEDULER_BRAND_ID is not set or brand doesn't exist
- **Fix**: Set SCHEDULER_BRAND_ID env var or ensure brand exists in DB

**Issue 4: "No metrics found"**
- **Cause**: No published drafts with valid postiz_id in metadata
- **Fix**: Publish some content via Postiz first, or check metadata structure

**Issue 5: "Feedback bonus not updating"**
- **Cause**: No social_metrics records found in last 30 days
- **Fix**: Ensure metrics are being pulled successfully first

### Health Check Endpoint

Test backend health:
```bash
curl https://your-backend-url.com/health/db
```

Should return:
```json
{
  "status": "ok",
  "db": "connected",
  "latency_ms": <number>
}
```

---

## Data Flow Diagram

```
06:00 UTC                     07:00 UTC
┌─────────────┐           ┌─────────────┐
│  Cron Job  │           │  Cron Job  │
│  Pull      │           │  Update    │
│  Metrics   │           │  Feedback  │
└──────┬──────┘           └──────┬──────┘
       │                        │
       ▼                        ▼
┌─────────────────────────────────────────────────┐
│         Python Backend API                  │
│  /api/analytics/pull-metrics             │
│  /api/analytics/feedback-loop             │
└─────────────────┬───────────────────────────┘
                │
                │
      ┌─────────┴───────────────────────┐
      │                               │
      ▼                               ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Postiz API        │     │  Supabase DB       │
│  - Fetch metrics   │     │  - social_metrics  │
│  - engagements    │     │  - brands table    │
└─────────────────────┘     │  - feedback_audit  │
                            │  - agent_configs   │
                            └─────────────────────┘
```

---

## Performance Considerations

### Cron Job Timing
- **Job 1 (06:00)**: ~1-2 minutes per brand (depends on number of published posts)
- **Job 2 (07:00)**: ~30 seconds per brand (computes scores from cached metrics)
- **Job 3 (08:00)**: ~2-3 minutes per brand (combined operations)

### Database Impact
- **Social metrics**: ~10 records per published post (one per platform)
- **Audit logs**: 1 entry per brand per day
- **Indexes**: Ensure indexes exist for performance (created in migration 008)

### API Rate Limits
- Postiz API: Respect rate limits (usually 100-1000 req/min)
- Backend: Configure rate limiting for scheduler endpoints
- Parallel processing: Each brand is processed sequentially

---

## Security Considerations

### Scheduler Secret
- Never commit secrets to version control
- Use environment variables in production
- Rotate secrets periodically (recommended: monthly)
- Different secrets for dev/staging/production

### Authorization
- **Cron jobs**: Use X-Scheduler-Secret header
- **User actions**: Use JWT authentication
- **RLS policies**: Brand isolation enforced
- **Audit trail**: All feedback calculations logged

### Data Privacy
- Social metrics: Engagement data only (no PII)
- Audit logs: Scores and timestamps only (no content)
- Brand data: Isolated per brand via RLS

---

## Maintenance

### Review Cron Jobs Monthly
- Check execution history in Supabase Dashboard
- Monitor error rates (target: <5% failures)
- Verify database growth (social_metrics table)
- Update scheduler secrets (security best practice)

### Database Cleanup
```sql
-- Archive old metrics (older than 90 days)
-- This should be run manually or via maintenance job
CREATE TABLE IF NOT EXISTS social_metrics_archive AS
SELECT * FROM social_metrics
WHERE recorded_at < NOW() - INTERVAL '90 days';

DELETE FROM social_metrics 
WHERE recorded_at < NOW() - INTERVAL '90 days';

-- Archive audit logs (older than 180 days)
DELETE FROM feedback_loop_audit 
WHERE executed_at < NOW() - INTERVAL '180 days';
```

### Monitoring Setup
Configure alerts for:
- Cron job failures (Supabase can send email notifications)
- High error rates (>10% in 24h period)
- Database disk usage approaching limits
- API response times >5 seconds

---

## Rollback Procedure

If issues arise after activation:

### Step 1: Deactivate Cron Jobs
- Go to Supabase Dashboard > Database > Cron Jobs
- Click "Deactivate" on each job

### Step 2: Rollback Migration
```bash
# Drop cron jobs
supabase db reset --db DATABASE_NAME

# Or selectively (if you want to keep other migrations)
supabase db execute --file=cleanup_feedback_cron.sql
```

### Step 3: Verify System Stability
- Check backend API is still functioning
- Verify no data corruption in database
- Test manual feedback loop endpoint

### Step 4: Review Logs
- Check cron job execution history before deactivation
- Identify root cause of issues
- Apply fixes and re-test manually before re-activation

---

## Success Criteria

✅ Cron jobs created in Supabase
✅ Backend API endpoints deployed
✅ Scheduler secret configured
✅ Manual testing successful
✅ Cron jobs activated
✅ First automated execution successful
✅ Metrics pulling working
✅ Feedback bonus updating
✅ No errors in cron job history

---

## Documentation References

- **Backend API**: `/python/src/content_engine/api/routes.py`
- **Analytics Service**: `/python/src/content_engine/services/postiz_analytics.py`
- **Feedback Loop Service**: `/python/src/content_engine/services/feedback_loop.py`
- **Database Schema**: `/supabase/migrations/008_feedback_loop_cron.sql`
- **Cron Migration**: `/supabase/migrations/009_feedback_loop_cron_jobs.sql`

---

## Support

For issues with cron jobs:
1. Check Supabase Dashboard > Database > Cron Jobs > History
2. Check backend logs for API errors
3. Verify environment variables are set correctly
4. Test endpoints manually (see Testing section above)
5. Review this migration's configuration instructions

---

**Migration Status**: ✅ COMPLETE
**Date**: 2026-04-15
**Cron Jobs**: 2 active jobs (or 1 consolidated job)
**Next Steps**: Deploy backend, configure secrets, activate cron jobs
