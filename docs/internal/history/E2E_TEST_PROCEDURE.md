# E2E Integration Test Procedure - Manual Testing Guide

## Priority: HIGH - Must be completed before production deployment

This guide provides step-by-step instructions for manual end-to-end testing of the heartbeat system.

## Prerequisites

- ✅ Backend running (Python/FastAPI) on `http://localhost:8000`
- ✅ Frontend running (Next.js) on `http://localhost:3000`
- ✅ Database (Supabase) connected and accessible
- ✅ At least one brand configured in the database
- ✅ Authentication token for API calls

## Test Environment Setup

### 1. Verify System Status

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend accessibility
curl http://localhost:3000

# Check database connection
# (Use your preferred DB client or Supabase dashboard)
```

### 2. Get Authentication Token

```bash
# Login to get JWT token
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com", "password": "your-password"}'

# Save the token for subsequent requests
export AUTH_TOKEN="your-jwt-token-here"
```

### 3. Get Brand ID

```bash
# Get your brand ID
curl http://localhost:3000/api/brands \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq

# Save your brand ID
export BRAND_ID="your-brand-id-here"
```

---

## Test Case 1: Complete Heartbeat Loop

### Objective
Verify the complete data flow: `call_llm → heartbeat → pipeline_health → /api/health → dashboard`

### Steps

#### 1.1 Generate Test Content

```bash
# Create a test research item first
curl -X POST http://localhost:8000/api/research/create \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "E2E Test Research",
    "url": "https://example.com/test-article",
    "platform": "linkedin"
  }'

# Save the research item ID
export RESEARCH_ITEM_ID="returned-id-here"
```

#### 1.2 Generate Content

```bash
# Generate content (this will trigger heartbeats)
curl -X POST http://localhost:8000/api/content/generate \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"research_item_id\": \"$RESEARCH_ITEM_ID\",
    \"platform\": \"linkedin\",
    \"run_god\": true,
    \"run_humanizer\": false
  }"

# Save the draft ID
export DRAFT_ID="returned-draft-id-here"
```

#### 1.3 Verify Heartbeat in Logs

```bash
# Check backend logs for heartbeat entries
tail -f logs/backend.log | grep -i "Heartbeat:"

# You should see entries like:
# Heartbeat: brand=xxx agent=writer context=writer_initial action=generate_content status=healthy model=claude-3-5-haiku-20241022 engine=anthropic latency_ms=1234
```

#### 1.4 Verify Database Pipeline Health

```bash
# Check pipeline_health table directly
psql $DATABASE_URL -c "
SELECT agent_name, status, current_model, engine, last_latency_ms
FROM pipeline_health
WHERE brand_id = '$BRAND_ID'
ORDER BY last_seen DESC
LIMIT 10;
"

# Expected: Should see entries for agents that were just used
# - writer
# - editor
# - god_advocate, god_factcheck, god_creative, god_synthesis
```

#### 1.5 Verify Health API

```bash
# Call health API
curl http://localhost:3000/api/system/health \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq

# Verify:
# 1. "agents" array is not empty
# 2. Each agent has: agent_name, status, current_model, engine, last_latency_ms
# 3. "summary" contains: active_models, active_engines, emergency_fallbacks_24h
```

#### 1.6 Verify Dashboard

1. Open browser to `http://localhost:3000`
2. Navigate to Dashboard
3. Verify the following:

**KPI Cards:**
- "Active LLM Models" shows a number > 0
- "Engines Active" shows engine names (anthropic, openrouter)
- "Emergency Fallbacks 24h" shows a number (probably 0)

**Agent Status Section:**
- Should show agents that were just used
- Each agent shows:
  - Agent name (e.g., "writer", "god_advocate")
  - Status badge (Online/Offline)
  - Current model (e.g., "claude-3-5-haiku-20241022")
  - Engine badge (🔷 Anthropic or 🌐 OpenRouter)
  - Latency in ms (color-coded: green < 2s, yellow < 5s, red ≥ 5s)

### Expected Results

✅ All steps complete without errors
✅ Heartbeat entries appear in logs
✅ Pipeline_health table has new entries
✅ Health API returns agent data with LLM metadata
✅ Dashboard shows real-time agent status

---

## Test Case 2: God System Sub-Agent Tracking

### Objective
Verify that God System sub-agents are tracked separately

### Steps

#### 2.1 Generate Content with GOD Mode

```bash
curl -X POST http://localhost:8000/api/content/generate \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"research_item_id\": \"$RESEARCH_ITEM_ID\",
    \"platform\": \"linkedin\",
    \"run_god\": true,
    \"run_humanizer\": false
  }"
```

#### 2.2 Verify Sub-Agent Tracking

```bash
# Check database for God System sub-agents
psql $DATABASE_URL -c "
SELECT agent_name, status, current_model, engine
FROM pipeline_health
WHERE brand_id = '$BRAND_ID'
  AND agent_name LIKE 'god_%'
ORDER BY agent_name;
"

# Expected: Should see 4 separate entries:
# - god_advocate
# - god_factcheck
# - god_creative
# - god_synthesis
```

#### 2.3 Verify Dashboard Shows Sub-Agents

1. Refresh Dashboard
2. Look in Agent Status section
3. Verify you see separate entries for:
   - god_advocate
   - god_factcheck
   - god_creative
   - god_synthesis

### Expected Results

✅ Each God System sub-agent appears as separate entry
✅ Dashboard shows all 4 sub-agents with individual status
✅ Each sub-agent shows correct model and engine

---

## Test Case 3: Fallback Detection

### Objective
Verify that system detects and reports fallbacks

### Steps

#### 3.1 Simulate Anthropic API Failure

**Option A: Temporary configuration change**
```bash
# Temporarily break Anthropic API key
export ANTHROPIC_API_KEY="invalid-key"

# Restart backend service
```

**Option B: Use environment variable**
```bash
# Set USE_CLAUDE_SUBSCRIPTION=true with invalid key
export USE_CLAUDE_SUBSCRIPTION=true
export ANTHROPIC_API_KEY="invalid-key"

# Restart backend service
```

#### 3.2 Generate Content (Should Trigger Fallback)

```bash
curl -X POST http://localhost:8000/api/content/generate \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"research_item_id\": \"$RESEARCH_ITEM_ID\",
    \"platform\": \"linkedin\"
  }"
```

#### 3.3 Verify Fallback Logging

```bash
# Check logs for fallback messages
tail -f logs/backend.log | grep -i "fallback"

# Should see:
# - "Emergency fallback successful"
# - "Anthropic API failed"
# - Telegram alert (if configured)
```

#### 3.4 Verify Fallback in Database

```bash
# Check llm_fallback_log table
psql $DATABASE_URL -c "
SELECT *
FROM llm_fallback_log
WHERE brand_id = '$BRAND_ID'
  AND is_emergency = true
ORDER BY created_at DESC
LIMIT 5;
"
```

#### 3.5 Verify Dashboard Shows Fallback

1. Refresh Dashboard
2. Check "Emergency Fallbacks 24h" KPI card
3. Should show number > 0

4. Check Agent Status for agents that used fallback
5. Should see "Fallback" badge in red

#### 3.6 Restore Normal Configuration

```bash
# Restore valid Anthropic API key
export ANTHROPIC_API_KEY="your-valid-key"

# Restart backend service
```

### Expected Results

✅ System gracefully falls back to OpenRouter
✅ Fallback is logged in database
✅ Dashboard shows fallback count and badges
✅ Telegram alert is sent (if configured)
✅ System continues to function despite Anthropic API failure

---

## Test Case 4: Performance Under Load

### Objective
Verify system handles concurrent requests without degradation

### Steps

#### 4.1 Generate Multiple Concurrent Requests

```bash
# Create 10 concurrent content generation requests
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/content/generate \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"research_item_id\": \"$RESEARCH_ITEM_ID\",
      \"platform\": \"linkedin\"
    }" &
done

wait
echo "All requests completed"
```

#### 4.2 Monitor System Performance

```bash
# Monitor CPU and memory
top -p $(pgrep -f "python.*content_engine")

# Monitor response times
time curl http://localhost:8000/health

# Check cache size
python3 -c "
from python.src.content_engine.utils.heartbeat import get_cache_stats
import json
print(json.dumps(get_cache_stats(), indent=2))
"
```

#### 4.3 Verify No Performance Degradation

1. Check Dashboard - should still load quickly
2. Check Agent Status - should show real-time data
3. Check logs - no errors or warnings about cache issues

### Expected Results

✅ All 10 requests complete successfully
✅ No significant performance degradation (<20% slower)
✅ Cache stays bounded (<1000 entries)
✅ No errors in logs
✅ Dashboard remains responsive

---

## Test Case 5: Graceful Degradation

### Objective
Verify system continues to function if heartbeat fails

### Steps

#### 5.1 Temporarily Break Database Connection

```bash
# Stop Supabase or block database port
# (Method depends on your setup)

# OR modify connection string to invalid value
export DATABASE_URL="postgresql://invalid:invalid@localhost:5432/invalid"

# Restart backend service
```

#### 5.2 Generate Content

```bash
curl -X POST http://localhost:8000/api/content/generate \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"research_item_id\": \"$RESEARCH_ITEM_ID\",
    \"platform\": \"linkedin\"
  }"
```

#### 5.3 Verify System Still Functions

```bash
# Content should still be generated successfully
# Check logs - should see heartbeat errors but content generation should succeed

tail -f logs/backend.log | grep -E "(Heartbeat|content|draft)"

# Should see:
# - Heartbeat recording errors (expected)
# - Content generation success (critical)
```

#### 5.4 Restore Database Connection

```bash
# Restore valid DATABASE_URL
# Start Supabase or unblock port

# Restart backend service
```

### Expected Results

✅ Content generation continues despite heartbeat failures
✅ System does not crash
✅ Logs show heartbeat errors but content generation succeeds
✅ Graceful degradation working as designed

---

## Test Case 6: Rate Limiting Behavior

### Objective
Verify rate limiting behavior (currently disabled by default)

### Steps

#### 6.1 Check Current Rate Limiting Status

```bash
python3 -c "
from python.src.content_engine.utils.heartbeat import get_cache_stats
stats = get_cache_stats()
print('Rate Limiting Enabled:', stats['rate_limiting_enabled'])
"

# Expected: False (disabled)
```

#### 6.2 Generate High Volume Requests

```bash
# Generate 200 rapid requests
for i in {1..200}; do
  curl -s -X POST http://localhost:8000/api/content/generate \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"research_item_id\": \"$RESEARCH_ITEM_ID\", \"platform\": \"linkedin\"}" &
done

wait
echo "All 200 requests completed"
```

#### 6.3 Verify All Requests Succeeded

```bash
# All should have succeeded because rate limiting is disabled
# No "rate limited" messages in logs

tail -f logs/backend.log | grep -i "rate limited"

# Expected: No output (rate limiting disabled)
```

### Expected Results

✅ All 200 requests complete successfully
✅ No rate limiting messages in logs
✅ System handles high volume as expected

---

## Post-Test Verification

### 1. System Health Check

```bash
# Final system health verification
curl http://localhost:8000/health
curl http://localhost:3000/api/system/health -H "Authorization: Bearer $AUTH_TOKEN"
```

### 2. Data Consistency Check

```bash
# Verify database integrity
psql $DATABASE_URL -c "
SELECT COUNT(*) as total_agents,
       COUNT(CASE WHEN status = 'healthy' THEN 1 END) as healthy_agents,
       COUNT(CASE WHEN engine = 'anthropic' THEN 1 END) as anthropic_agents,
       COUNT(CASE WHEN engine = 'openrouter' THEN 1 END) as openrouter_agents
FROM pipeline_health
WHERE brand_id = '$BRAND_ID';
"
```

### 3. Performance Baseline

```bash
# Document current performance metrics
python3 -c "
from python.src.content_engine.utils.heartbeat import get_cache_stats
import json
stats = get_cache_stats()
print('Performance Baseline:')
print(json.dumps(stats, indent=2))
"
```

---

## Troubleshooting

### Issue: No heartbeat entries in logs

**Solution:**
```bash
# Check if heartbeat module is loaded
python3 -c "from python.src.content_engine.utils.heartbeat import record_agent_heartbeat; print('OK')"

# Check if heartbeat is being called
# Add debug logging to heartbeat.py
```

### Issue: Dashboard not showing agent data

**Solution:**
```bash
# Check Health API directly
curl http://localhost:3000/api/system/health -H "Authorization: Bearer $AUTH_TOKEN" | jq

# If API returns empty data, check database:
psql $DATABASE_URL -c "SELECT * FROM pipeline_health WHERE brand_id = '$BRAND_ID';"
```

### Issue: Cache growing unbounded

**Solution:**
```bash
# Check cache size
python3 -c "from python.src.content_engine.utils.heartbeat import get_cache_stats; print(get_cache_stats())"

# If approaching limit, consider:
# 1. Reducing cache max size
# 2. Increasing TTL to reduce churn
# 3. Investigating why so many unique agents
```

### Issue: Performance degradation

**Solution:**
```bash
# Check if DB writes are enabled
grep HEARTBEAT_DB_WRITE .env

# If causing issues, disable:
export HEARTBEAT_DB_WRITE=false
# Restart services
```

---

## Test Results Template

```markdown
## E2E Test Results

**Date:** ___________
**Tester:** ___________
**Environment:** ___________

### Test Case 1: Complete Heartbeat Loop
- [ ] Content generation successful
- [ ] Heartbeat entries in logs
- [ ] Database entries created
- [ ] Health API returns data
- [ ] Dashboard shows agents
- **Status:** ⬜ PASS ⬜ FAIL
- **Notes:** ___________

### Test Case 2: God System Sub-Agent Tracking
- [ ] All 4 sub-agents tracked
- [ ] Dashboard shows sub-agents
- [ ] Each sub-agent has correct metadata
- **Status:** ⬜ PASS ⬜ FAIL
- **Notes:** ___________

### Test Case 3: Fallback Detection
- [ ] Fallback triggered on API failure
- [ ] Fallback logged in database
- [ ] Dashboard shows fallback count
- [ ] Telegram alert sent (if configured)
- [ ] System continues to function
- **Status:** ⬜ PASS ⬜ FAIL
- **Notes:** ___________

### Test Case 4: Performance Under Load
- [ ] All concurrent requests successful
- [ ] No significant performance degradation
- [ ] Cache stays bounded
- [ ] No errors in logs
- **Status:** ⬜ PASS ⬜ FAIL
- **Notes:** ___________

### Test Case 5: Graceful Degradation
- [ ] Content generation succeeds despite heartbeat failures
- [ ] System does not crash
- [ ] Logs show appropriate errors
- **Status:** ⬜ PASS ⬜ FAIL
- **Notes:** ___________

### Test Case 6: Rate Limiting Behavior
- [ ] High volume requests succeed
- [ ] No rate limiting interference
- [ ] System handles load as expected
- **Status:** ⬜ PASS ⬜ FAIL
- **Notes:** ___________

## Overall Assessment

**Critical Issues:** ___________
**Non-Critical Issues:** ___________
**Recommendations:** ___________

**Go/No-Go for Production:** ⬜ GO ⬜ NO-GO

**Approved By:** ___________
**Date:** ___________
```

---

## Next Steps After Testing

### If All Tests Pass:
1. ✅ Document test results
2. ✅ Create performance baseline
3. ✅ Proceed to production deployment
4. ✅ Monitor system closely for first 24 hours

### If Tests Fail:
1. ❌ Document failures
2. ❌ Investigate root causes
3. ❌ Fix issues
4. ❌ Re-test failed scenarios
5. ❌ Only proceed to production after all critical tests pass

---

**Remember:** This E2E test is MANDATORY before production deployment. Do not skip any test cases.
