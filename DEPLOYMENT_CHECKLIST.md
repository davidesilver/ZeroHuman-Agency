# Deployment Checklist - Pragmatic Heartbeat System

## 🚀 Pre-Deployment Verification

### ✅ Code Readiness

- [x] **Backend Core**
  - [x] `heartbeat.py` implemented with resilience-first approach
  - [x] `llm_client.py` integrated with heartbeat recording
  - [x] LLMResponse enhanced with engine, latency_ms, fallback_to
  - [x] Rate limiting disabled by default (as requested)
  - [x] Graceful degradation implemented (never fails main pipeline)

- [x] **Frontend Enhancement**
  - [x] Health API updated with LLM metadata
  - [x] Dashboard shows active models, engines, emergency fallbacks
  - [x] Agent status displays model, engine, latency

- [x] **Testing**
  - [x] Unit tests created (`test_heartbeat_pragmatic.py`)
  - [x] Integration tests passing (`test_heartbeat_integration.sh`)
  - [x] Performance validated (3,500+ heartbeat/sec)
  - [x] Rate limiting verified disabled
  - [x] Concurrent operations tested

### ✅ Configuration

- [x] **Default Settings**
  - [x] Cache: max_size=1000, ttl_seconds=60
  - [x] Rate limiting: DISABLED by default
  - [x] DB writes: ENABLED (can be disabled via config)
  - [x] Logging: Structured logging always active

- [x] **Environment Variables** (Optional)
  ```bash
  # Disabilita DB writes se problematici
  HEARTBEAT_DB_WRITE=false

  # Configura cache (default values shown)
  HEARTBEAT_CACHE_MAX_SIZE=1000
  HEARTBEAT_CACHE_TTL=60
  ```

### ✅ Database Readiness

- [x] **Required Tables**
  - [x] `pipeline_health` exists (from previous migration)
  - [x] `llm_fallback_log` exists (from migration 012)
  - [x] Both tables have correct schema

- [x] **No New Migrations Required**
  - [x] Uses existing tables only
  - [x] No schema changes needed

## 📋 Deployment Steps

### Phase 1: Code Deployment

1. **Backend Deployment**
   ```bash
   cd python
   # Ensure new files are deployed
   - src/content_engine/utils/heartbeat.py
   - tests/test_heartbeat_pragmatic.py
   # Ensure modified files are deployed
   - src/content_engine/utils/llm_client.py
   ```

2. **Frontend Deployment**
   ```bash
   # Ensure modified files are deployed
   - src/app/api/system/health/route.ts
   - src/app/(dashboard)/page.tsx
   ```

3. **Restart Services**
   ```bash
   # Restart Python backend
   # Restart Next.js frontend
   ```

### Phase 2: Verification

1. **Health Check**
   ```bash
   # Verify backend is healthy
   curl http://localhost:8000/health

   # Verify frontend is accessible
   curl http://localhost:3000
   ```

2. **API Endpoints Test**
   ```bash
   # Test health API with new fields
   curl http://localhost:3000/api/system/health \
     -H "Authorization: Bearer YOUR_TOKEN" | jq

   # Should return:
   # - active_models: array of model names
   # - active_engines: array ["anthropic", "openrouter"]
   # - emergency_fallbacks_24h: number
   ```

3. **Dashboard Verification**
   - Navigate to dashboard
   - Verify "Active LLM Models" KPI card shows data
   - Verify "Engines Active" KPI card shows data
   - Verify "Emergency Fallbacks 24h" KPI card shows data
   - Click on Agent Status section
   - Verify agents show model, engine, latency

### Phase 3: Smoke Tests

1. **Generate Content**
   ```bash
   # Create a test content generation
   curl -X POST http://localhost:8000/api/content/generate \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"research_item_id": "test-id", "platform": "linkedin"}'
   ```

2. **Verify Heartbeat Recording**
   ```bash
   # Check logs for heartbeat entries
   # Should see: "Heartbeat: brand=... agent=... context=... action=..."

   # Check dashboard for new agents appearing
   ```

3. **Verify Dashboard Updates**
   - Refresh dashboard after content generation
   - Verify new agents appear in Agent Status
   - Verify model, engine, latency are displayed

## 🔍 Post-Deployment Monitoring

### Immediate Checks (First 5 minutes)

- [ ] **Error Logs**: No errors in backend logs
- [ ] **Dashboard Accessible**: Dashboard loads without errors
- [ ] **API Response**: Health API returns 200 with new fields
- [ ] **Heartbeat Logs**: Structured logs appearing in backend

### Short-term Monitoring (First hour)

- [ ] **Performance**: No degradation in LLM call latency
- [ ] **Memory**: No memory leaks (cache stays bounded)
- [ ] **Database**: No excessive write load
- [ ] **User Experience**: No reported issues

### Long-term Monitoring (First 24 hours)

- [ ] **Cache Size**: Stays under 1000 entries
- [ ] **Heartbeat Volume**: Consistent with LLM call volume
- [ ] **Error Rate**: No increase in error rate
- [ ] **Dashboard Accuracy**: Agent status reflects reality

## 🚨 Rollback Plan

### If Issues Detected

**Option 1: Disable Heartbeat DB Writes**
```bash
# Set environment variable
export HEARTBEAT_DB_WRITE=false

# Restart services
# System continues with logging only, no DB writes
```

**Option 2: Full Rollback**
```bash
# Revert code changes
git revert <commit-hash>

# Restart services
# System returns to previous state
```

### Rollback Triggers

- **Critical Issues**
  - System crashes or instability
  - Significant performance degradation (>50% slower)
  - Database connection issues

- **Non-Critical Issues** (Monitor, don't rollback)
  - Slight performance increase (<10%)
  - Cache hitting limit frequently
  - Dashboard showing stale data

## 📊 Success Criteria

### Technical Success

- [ ] ✅ Zero system crashes
- [ ] ✅ <5% performance overhead
- [ ] ✅ Cache stays bounded (<1000 entries)
- [ ] ✅ No database connection issues
- [ ] ✅ Dashboard shows real-time data

### Business Success

- [ ] ✅ Users can see which LLM models are being used
- [ ] ✅ Users can see engine (Anthropic/OpenRouter)
- [ ] ✅ Users can see latency for each agent
- [ ] ✅ Users can see emergency fallback count
- [ ] ✅ Improved debugging capability

## 📞 Contact & Support

### If Issues Arise

1. **Check Logs First**
   ```bash
   # Backend logs
   tail -f logs/backend.log | grep "Heartbeat"

   # Frontend logs
   # Check browser console for errors
   ```

2. **Run Diagnostics**
   ```bash
   # Run integration tests
   bash python/test_heartbeat_integration.sh

   # Check cache stats
   python3 -c "
   from src.content_engine.utils.heartbeat import get_cache_stats
   import json
   print(json.dumps(get_cache_stats(), indent=2))
   "
   ```

3. **Contact Information**
   - System Administrator: [Contact info]
   - Development Team: [Contact info]

## ✅ Final Pre-Deploy Checklist

- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Rollback plan prepared
- [ ] Monitoring configured
- [ ] Team notified
- [ ] Maintenance window scheduled
- [ ] Backup completed

---

## 🎯 Go/No-Go Decision

**Date:** ___________
**Time:** ___________

**Go Criteria:**
- [ ] All pre-deployment checks passed
- [ ] Team available for support
- [ ] Monitoring tools ready
- [ ] Rollback plan tested

**Decision:** ⬜ GO  ⬜ NO-GO

**Approved By:** ___________
**Comments:** ___________

---

**Deployment Status:** ⬜ PENDING  ⬜ IN PROGRESS  ⬜ COMPLETED  ⬜ ROLLED BACK

**Deployment Time:** ___________
**Completion Time:** ___________

**Issues Encountered:** ___________

**Final Status:** ⬜ SUCCESS  ⬜ PARTIAL  ⬜ FAILED
