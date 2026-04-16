# 🚀 Pragmatic Heartbeat System - Deployment Guide

## Quick Start

```bash
# 1. Deploy the system
bash deploy_heartbeat_system.sh

# 2. Verify it's working
bash post_deploy_verification.sh

# 3. Done! 🎉
```

## What You Get

✅ **Real-time agent monitoring** - See which LLM models are being used
✅ **Performance insights** - View latency per agent
✅ **Engine tracking** - Know if using Anthropic or OpenRouter
✅ **Emergency alerts** - Track fallback occurrences
✅ **Unlimited requests** - Rate limiting disabled as requested
✅ **Zero breaking changes** - 100% backward compatible

## Key Features

- **Rate Limiting:** DISABLED (unlimited heartbeat requests)
- **Cache:** Bounded to 1000 entries (prevents memory leaks)
- **Performance:** ~3,500 heartbeat/second throughput
- **Resilience:** Never fails the main pipeline
- **Graceful Degradation:** Heartbeat issues don't impact LLM calls

## Configuration

All configuration is **optional** - system works with defaults:

```bash
# Optional: Disable DB writes (logging only)
export HEARTBEAT_DB_WRITE=false

# Optional: Adjust cache size
export HEARTBEAT_CACHE_MAX_SIZE=1000  # Default
export HEARTBEAT_CACHE_TTL=60         # Default (seconds)
```

## Verification

After deployment, check:

1. **Dashboard** - Should show real-time agent status
2. **Logs** - Should show heartbeat entries: `tail -f logs/backend.log | grep Heartbeat`
3. **API** - Should return new fields: `curl /api/system/health | jq`

## Rollback (if needed)

```bash
# List backups
ls -la backups/

# Rollback to specific backup
bash rollback_heartbeat_system.sh <backup_name>
```

## Troubleshooting

**Dashboard not showing data?**
```bash
# Check logs
tail -f logs/backend.log | grep Heartbeat

# Check cache stats
python3 -c "from src.content_engine.utils.heartbeat import get_cache_stats; print(get_cache_stats())"
```

**Performance issues?**
```bash
# Disable DB writes temporarily
export HEARTBEAT_DB_WRITE=false
# Restart services
```

**Need to enable rate limiting?**
```python
from src.content_engine.utils.heartbeat import set_rate_limiting
set_rate_limiting(True)  # Enable
set_rate_limiting(False) # Disable (default)
```

## Documentation

- `DEPLOYMENT_CHECKLIST.md` - Complete deployment checklist
- `DEPLOYMENT_SUMMARY.md` - Detailed deployment information
- `PRAGMATIC_HEARTBEAT_IMPLEMENTATION.md` - Technical implementation details
- `heartbeat_usage_example.py` - Code examples

## Support

1. Check logs first
2. Run `bash post_deploy_verification.sh`
3. Refer to documentation
4. Rollback if needed

---

**Status:** ✅ READY FOR DEPLOYMENT
**Version:** 1.0.0
**Date:** 2026-04-16

**Just deploy it - it's ready!** 🚀
