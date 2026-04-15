# Cron Jobs Quick Start — Postiz Analytics & Feedback Loop

**Status**: ✅ Ready for Setup  
**Migration**: `009_feedback_loop_cron_jobs.sql`

---

## What These Cron Jobs Do

### 1. Pull Postiz Analytics (06:00 UTC Daily)
- Fetches engagement metrics (likes, shares, comments, impressions) from Postiz API
- Stores metrics in `social_metrics` table
- Processes all published posts from last 7 days
- Runs for all active brands automatically

### 2. Update Feedback Bonus (07:00 UTC Daily)
- Computes weighted engagement scores from metrics
- Applies platform normalization (LinkedIn vs Instagram vs TikTok baselines)
- Uses temporal decay (recent metrics matter more)
- Updates `brands.feedback_bonus` for each brand
- Records audit trail in `feedback_loop_audit` table

---

## Setup Steps

### Step 1: Deploy Backend
Ensure your Python backend is deployed and accessible:
```
https://your-backend-domain.com
```

Required endpoints must be accessible:
- `/api/analytics/pull-metrics` — For metrics pulling
- `/api/analytics/feedback-loop` — For feedback updates

### Step 2: Generate Scheduler Secret

```bash
# Generate a secure random 32-character hex string
openssl rand -hex 32
```

Set this as environment variable in your backend:
```bash
SCHEDULER_SECRET=your-generated-secret-here
```

### Step 3: Update Migration File

Edit `/supabase/migrations/009_feedback_loop_cron_jobs.sql`:

Replace these placeholders with your actual values:
```sql
-- Replace with your actual backend URL
url := 'https://your-backend-domain.com/api/analytics/pull-metrics',

-- Replace with your actual scheduler secret
'X-Scheduler-Secret', 'your-generated-secret-here'
```

### Step 4: Apply Migration

```bash
# Push migration to Supabase
supabase db push --linked

# This will create the cron jobs in your Supabase project
```

### Step 5: Activate Cron Jobs

1. Go to Supabase Dashboard
2. Navigate to **Database** > **Cron Jobs**
3. You should see 3 new cron jobs:
   - `pull-postiz-metrics-daily` (06:00 UTC)
   - `update-feedback-bonus-daily` (07:00 UTC)
   - `full-analytics-cycle-daily` (08:00 UTC) — commented out
4. Click **Activate** on each job you want to run
5. Click **Pause** on any job you don't want to run

---

## Testing Before Activation

### Test Metrics Pull

```bash
curl -X POST https://your-backend-domain.com/api/analytics/pull-metrics \
  -H "Content-Type: application/json" \
  -H "X-Scheduler-Secret: your-generated-secret-here" \
  -d '{"action": "pull_daily"}'
```

Expected response:
```json
{
  "success": true,
  "data": {
    "brands_processed": 3,
    "total_posts_processed": 15,
    "total_metrics_fetched": 12,
    "brands_updated": 2
  }
}
```

### Test Feedback Loop

```bash
# First, get your JWT token from your app
curl -X POST https://your-backend-domain.com/api/analytics/feedback-loop \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Expected response:
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

## Verify Cron Job Execution

### 1. Wait for Scheduled Time
- Job 1: Runs at 06:00 UTC (next day)
- Job 2: Runs at 07:00 UTC (next day)
- Job 3: (optional) Runs at 08:00 UTC (next day)

### 2. Check Cron Job History

Go to Supabase Dashboard > Database > Cron Jobs > History tab:
- ✅ Green checkmark = successful execution
- ❌ Red X = failed execution
- Click on any failed job to see error details

### 3. Verify Database Updates

```sql
-- Check if metrics were pulled
SELECT COUNT(*), MAX(recorded_at) 
FROM social_metrics;

-- Check if feedback bonus was updated
SELECT brand_id, feedback_bonus, updated_at 
FROM brands 
WHERE updated_at > NOW() - INTERVAL '1 day';

-- Check audit trail
SELECT brand_id, previous_bonus, new_bonus, score_delta, executed_at
FROM feedback_loop_audit
ORDER BY executed_at DESC
LIMIT 10;
```

---

## Troubleshooting

### Issue: "Failed to connect to backend"

**Cause**: Backend URL is incorrect or backend is down

**Fix**:
```bash
# Test backend health
curl https://your-backend-domain.com/health/db

# Should return:
{
  "status": "ok",
  "db": "connected",
  "latency_ms": <number>
}
```

### Issue: "Invalid or missing scheduler secret"

**Cause**: SCHEDULER_SECRET doesn't match between backend and cron job

**Fix**:
- Verify SCHEDULER_SECRET is set in backend environment
- Verify migration file has the correct secret
- Update migration and re-apply if needed:
  ```bash
  supabase db reset --db DATABASE_NAME
  supabase db push --linked
  ```

### Issue: "No active brands found"

**Cause**: SCHEDULER_BRAND_ID is not set or brand doesn't exist

**Fix**:
- Set SCHEDULER_BRAND_ID env var in backend (for single-brand setups)
- Or verify brand exists in database:
  ```sql
  SELECT id, name, status FROM brands WHERE status = 'active';
  ```

### Issue: "No metrics found"

**Cause**: No published drafts with valid postiz_id in metadata

**Fix**:
- Publish some content via Postiz first
- Check draft metadata:
  ```sql
  SELECT id, status, metadata 
  FROM content_drafts 
  WHERE status = 'published';
  ```
- Ensure `postiz_id` exists in metadata JSON

### Issue: "Feedback bonus not updating"

**Cause**: No social_metrics records found in last 30 days

**Fix**:
- Verify Job 1 (pull metrics) is running successfully
- Check social_metrics table:
  ```sql
  SELECT COUNT(*) FROM social_metrics 
  WHERE recorded_at > NOW() - INTERVAL '30 days';
  ```
- Manually trigger feedback loop to test:
  ```bash
  curl -X POST https://your-backend-domain.com/api/analytics/feedback-loop \
    -H "Authorization: Bearer YOUR_JWT_TOKEN"
  ```

---

## Choosing a Schedule Strategy

### Option A: Separate Jobs (Recommended)
- Job 1: Pull metrics at 06:00 UTC
- Job 2: Update feedback at 07:00 UTC
- **Advantages**:
  - More granular control
  - Easier to debug partial failures
  - Can retry individual jobs
  - Better for production stability

### Option B: Single Consolidated Job
- Job 3: Full cycle at 08:00 UTC
- **Advantages**:
  - Single API call
  - Simpler to monitor
  - Less chance of partial failures
  - Good for smaller setups

**Recommendation**: Start with Option A for production, consider Option B for development.

---

## Monitoring Cron Jobs

### 1. Supabase Dashboard
- Go to Database > Cron Jobs > History
- Check execution status
- View error messages
- Monitor execution times

### 2. Database Queries
```sql
-- Cron job success rate
SELECT job_id, COUNT(*) as runs, 
       SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
FROM cron.job_run_details
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY job_id;

-- Metrics growth
SELECT DATE(recorded_at) as date, 
       COUNT(*) as records
FROM social_metrics
WHERE recorded_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(recorded_at)
ORDER BY date DESC;
```

### 3. Alerting Setup
Configure Supabase to send alerts for:
- Cron job failures (recommended)
- High error rates (>10% failures in 24h)
- Database disk usage approaching limits

---

## Maintenance Tasks

### Weekly
- Review cron job execution history
- Check for increasing error rates
- Verify feedback bonus trends look reasonable
- Monitor database growth (social_metrics table)

### Monthly
- Rotate SCHEDULER_SECRET (security best practice)
- Archive old metrics (older than 90 days)
- Archive old audit logs (older than 180 days)
- Review and update documentation if needed

### Quarterly
- Audit cron job permissions
- Review automation logic for optimization opportunities
- Evaluate if additional metrics should be tracked

---

## Security Best Practices

1. **Never commit secrets to version control**
2. **Use environment variables for all secrets**
3. **Rotate scheduler secret monthly**
4. **Different secrets for dev/staging/production**
5. **Monitor cron job logs for suspicious activity**
6. **Use HTTPS for all API calls**
7. **Implement rate limiting on backend endpoints**
8. **Audit cron job access logs**

---

## Performance Expectations

### Execution Times (per brand)
- Pull metrics: ~10-30 seconds (depends on published posts)
- Update feedback: ~5-15 seconds
- Full cycle: ~15-45 seconds

### Database Growth
- Social metrics: ~10 records per published post per platform
- Audit logs: 1 entry per brand per day
- Expect ~1-2MB growth per month per active brand

### API Rate Limits
- Postiz API: Respect 1000 req/min limit
- Backend: Configure rate limiting for scheduler endpoints
- Implement retry logic with exponential backoff

---

## Support

### Documentation
- **Cron Jobs Setup**: `/references/docs/cron-jobs.md` — Complete guide
- **Analytics Service**: `/python/src/content_engine/services/postiz_analytics.py`
- **Feedback Service**: `/python/src/content_engine/services/feedback_loop.py`
- **Migration**: `/supabase/migrations/009_feedback_loop_cron_jobs.sql`

### Common Commands

```bash
# Apply migration
supabase db push --linked

# Reset cron jobs (careful!)
supabase db reset --db DATABASE_NAME

# Test endpoint manually
curl -X POST https://your-backend.com/api/analytics/pull-metrics \
  -H "X-Scheduler-Secret: YOUR_SECRET" \
  -d '{"action": "pull_daily"}'
```

---

**Quick Start Status**: ✅ READY TO SETUP
**Next Steps**: Follow the 5 setup steps above
