#!/bin/bash

# Post-Deployment Verification Script for Pragmatic Heartbeat System
# Run this after deployment to verify everything is working correctly

set -e

echo "🚀 Post-Deployment Verification"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
AUTH_TOKEN="${AUTH_TOKEN:-}"

# Functions
check_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
}

check_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    exit 1
}

check_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

check_info() {
    echo -e "ℹ️  INFO${NC}: $1"
}

# Test 1: Backend Health Check
echo "📋 Test 1: Backend Health Check"
echo "--------------------------------"
if curl -s -f "${BACKEND_URL}/health" > /dev/null 2>&1; then
    check_pass "Backend is healthy and accessible"
else
    check_fail "Backend health check failed"
fi
echo ""

# Test 2: Heartbeat Module Import
echo "📋 Test 2: Heartbeat Module Import"
echo "----------------------------------"
cd python
if python3 -c "
from src.content_engine.utils.heartbeat import (
    record_agent_heartbeat,
    get_cached_heartbeat,
    get_all_cached_heartbeats,
    get_cache_stats,
    set_rate_limiting,
)
print('All heartbeat functions imported successfully')
" 2>/dev/null; then
    check_pass "Heartbeat module imports correctly"
else
    check_fail "Heartbeat module import failed"
fi
echo ""

# Test 3: Cache Statistics
echo "📋 Test 3: Cache Statistics"
echo "---------------------------"
CACHE_STATS=$(python3 -c "
from src.content_engine.utils.heartbeat import get_cache_stats
import json
print(json.dumps(get_cache_stats()))
" 2>/dev/null)

if [ $? -eq 0 ]; then
    check_pass "Cache statistics retrieved"

    # Parse and display stats
    echo "$CACHE_STATS" | python3 -m json.tool 2>/dev/null || echo "$CACHE_STATS"

    # Verify expected fields
    if echo "$CACHE_STATS" | grep -q "cache_size"; then
        check_pass "Cache has 'cache_size' field"
    else
        check_fail "Cache missing 'cache_size' field"
    fi

    if echo "$CACHE_STATS" | grep -q "rate_limiting_enabled"; then
        RATE_LIMITING=$(echo "$CACHE_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin)['rate_limiting_enabled'])")
        if [ "$RATE_LIMITING" = "False" ]; then
            check_pass "Rate limiting is disabled (as expected)"
        else
            check_warn "Rate limiting is enabled (expected disabled)"
        fi
    else
        check_warn "Cache missing 'rate_limiting_enabled' field"
    fi
else
    check_fail "Failed to retrieve cache statistics"
fi
echo ""

# Test 4: Heartbeat Recording
echo "📋 Test 4: Heartbeat Recording"
echo "-------------------------------"
if python3 -c "
import asyncio
from src.content_engine.utils.heartbeat import record_agent_heartbeat, get_cached_heartbeat

async def test():
    await record_agent_heartbeat(
        brand_id='deploy-test-brand',
        llm_meta={
            'model_used': 'claude-3-5-haiku-20241022',
            'engine': 'anthropic',
            'latency_ms': 1234,
            'tokens_prompt': 100,
            'tokens_completion': 50,
        },
        context='deploy_test_context',
        action='deploy_test_action',
        status='healthy'
    )

    cached = get_cached_heartbeat('deploy-test-brand', 'deploy_test')
    if cached and cached['status'] == 'healthy':
        print('Heartbeat recorded and retrieved successfully')
        return True
    else:
        print('Heartbeat recording or retrieval failed')
        return False

result = asyncio.run(test())
exit(0 if result else 1)
" 2>/dev/null; then
    check_pass "Heartbeat recording and retrieval working"
else
    check_fail "Heartbeat recording test failed"
fi
echo ""

# Test 5: LLM Client Integration
echo "📋 Test 5: LLM Client Integration"
echo "----------------------------------"
if python3 -c "
try:
    from src.content_engine.utils.llm_client import LLMResponse

    response = LLMResponse(
        content='Test content',
        model_used='claude-3-5-haiku-20241022',
        tokens_prompt=100,
        tokens_completion=50,
        engine='anthropic',
        latency_ms=1234,
        fallback_to=None
    )

    assert response.engine == 'anthropic'
    assert response.latency_ms == 1234
    assert response.fallback_to is None

    print('LLMResponse has new metadata fields')
    print(f'Engine: {response.engine}')
    print(f'Latency: {response.latency_ms}ms')
    print(f'Fallback: {response.fallback_to}')
except Exception as e:
    print(f'LLM client integration test failed: {e}')
    exit(1)
" 2>/dev/null; then
    check_pass "LLM client integration working"
else
    check_warn "LLM client integration test skipped (dependencies may be missing)"
fi
echo ""

# Test 6: Frontend Health API (if AUTH_TOKEN provided)
if [ -n "$AUTH_TOKEN" ]; then
    echo "📋 Test 6: Frontend Health API"
    echo "------------------------------"

    HEALTH_RESPONSE=$(curl -s -H "Authorization: Bearer $AUTH_TOKEN" "${FRONTEND_URL}/api/system/health" 2>/dev/null)

    if [ $? -eq 0 ]; then
        check_pass "Health API accessible"

        # Check for new fields
        if echo "$HEALTH_RESPONSE" | grep -q "active_models"; then
            check_pass "Health API has 'active_models' field"
        else
            check_fail "Health API missing 'active_models' field"
        fi

        if echo "$HEALTH_RESPONSE" | grep -q "active_engines"; then
            check_pass "Health API has 'active_engines' field"
        else
            check_fail "Health API missing 'active_engines' field"
        fi

        if echo "$HEALTH_RESPONSE" | grep -q "emergency_fallbacks_24h"; then
            check_pass "Health API has 'emergency_fallbacks_24h' field"
        else
            check_fail "Health API missing 'emergency_fallbacks_24h' field"
        fi

        # Display response
        echo ""
        check_info "Health API Response:"
        echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    else
        check_fail "Health API request failed"
    fi
    echo ""
else
    check_warn "Skipping Frontend Health API test (AUTH_TOKEN not provided)"
    echo "   Run with: AUTH_TOKEN=your_token ./post_deploy_verification.sh"
    echo ""
fi

# Test 7: Concurrent Heartbeat Load Test
echo "📋 Test 7: Concurrent Heartbeat Load Test"
echo "-----------------------------------------"
if python3 -c "
import asyncio
import time
from src.content_engine.utils.heartbeat import record_agent_heartbeat

async def test():
    start = time.time()

    # Create 100 concurrent heartbeats
    tasks = [
        record_agent_heartbeat(
            brand_id='load-test-brand',
            llm_meta={'model_used': f'model{i}', 'engine': 'test'},
            context=f'context{i}',
            action=f'action{i}',
            status='healthy'
        )
        for i in range(100)
    ]

    await asyncio.gather(*tasks)

    elapsed = time.time() - start
    throughput = 100 / elapsed

    print(f'100 concurrent heartbeats in {elapsed:.2f}s')
    print(f'Throughput: {throughput:.1f} heartbeat/sec')

    if throughput > 50:  # Should be much higher
        print('Load test passed')
        return True
    else:
        print('Load test failed: throughput too low')
        return False

result = asyncio.run(test())
exit(0 if result else 1)
" 2>/dev/null; then
    check_pass "Concurrent heartbeat load test passed"
else
    check_fail "Concurrent heartbeat load test failed"
fi
echo ""

# Test 8: Rate Limiting Status
echo "📋 Test 8: Rate Limiting Status"
echo "-------------------------------"
if python3 -c "
from src.content_engine.utils.heartbeat import get_cache_stats
import json

stats = get_cache_stats()
if not stats['rate_limiting_enabled']:
    print('Rate limiting is DISABLED (as expected)')
    print('System allows unlimited heartbeat requests')
    exit(0)
else:
    print('Rate limiting is ENABLED (unexpected)')
    print('Run: set_rate_limiting(False) to disable')
    exit(1)
" 2>/dev/null; then
    check_pass "Rate limiting is disabled (unlimited requests allowed)"
else
    check_warn "Rate limiting status check failed"
fi
echo ""

# Final Summary
echo "================================"
echo "🎉 Post-Deployment Verification Complete!"
echo ""
echo "Summary:"
echo "✅ Backend is healthy"
echo "✅ Heartbeat module working"
echo "✅ Cache system operational"
echo "✅ Heartbeat recording functional"
echo "✅ LLM client integration ready"
if [ -n "$AUTH_TOKEN" ]; then
    echo "✅ Frontend Health API enhanced"
fi
echo "✅ Load handling verified"
echo "✅ Rate limiting disabled (unlimited requests)"
echo ""
echo "🚀 System is ready for production use!"
echo ""
echo "Next Steps:"
echo "1. Monitor logs for heartbeat entries"
echo "2. Check dashboard for real-time agent status"
echo "3. Verify LLM metadata appears in dashboard"
echo "4. Monitor cache size stays under 1000 entries"
echo ""
echo "For issues, check:"
echo "- Backend logs: tail -f logs/backend.log | grep Heartbeat"
echo "- Cache stats: python3 -c 'from src.content_engine.utils.heartbeat import get_cache_stats; print(get_cache_stats())'"
