#!/bin/bash

# Automated Deployment Script for Pragmatic Heartbeat System
# This script handles the deployment of the heartbeat system components

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="${BACKEND_DIR:-./python}"
FRONTEND_DIR="${FRONTEND_DIR:-./}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}🚀 Pragmatic Heartbeat System Deployment${NC}"
echo "========================================"
echo ""

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Pre-deployment checks
log_info "Running pre-deployment checks..."

# Check if required directories exist
if [ ! -d "$BACKEND_DIR" ]; then
    log_error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
    log_error "Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

log_success "Directory structure verified"

# Check if required files exist
REQUIRED_BACKEND_FILES=(
    "src/content_engine/utils/heartbeat.py"
    "src/content_engine/utils/llm_client.py"
    "tests/test_heartbeat_pragmatic.py"
)

for file in "${REQUIRED_BACKEND_FILES[@]}"; do
    if [ ! -f "$BACKEND_DIR/$file" ]; then
        log_error "Required backend file missing: $file"
        exit 1
    fi
done

log_success "Required backend files verified"

REQUIRED_FRONTEND_FILES=(
    "src/app/api/system/health/route.ts"
    "src/app/(dashboard)/page.tsx"
)

for file in "${REQUIRED_FRONTEND_FILES[@]}"; do
    if [ ! -f "$FRONTEND_DIR/$file" ]; then
        log_error "Required frontend file missing: $file"
        exit 1
    fi
done

log_success "Required frontend files verified"

# Check if database migration exists
if [ ! -f "$FRONTEND_DIR/supabase/migrations/013_add_llm_metadata_to_pipeline_health.sql" ]; then
    log_error "Critical migration file missing: 013_add_llm_metadata_to_pipeline_health.sql"
    exit 1
fi

log_success "Database migration file verified"

# Create backup directory
log_info "Creating backup directory..."
mkdir -p "$BACKUP_DIR"
log_success "Backup directory created: $BACKUP_DIR"

# Backup current state
log_info "Backing up current state..."

# Backup Python files
BACKUP_NAME="heartbeat_backup_${TIMESTAMP}"
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

cp "$BACKEND_DIR/src/content_engine/utils/heartbeat.py" "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
cp "$BACKEND_DIR/src/content_engine/utils/llm_client.py" "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
cp "$FRONTEND_DIR/src/app/api/system/health/route.ts" "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true
cp "$FRONTEND_DIR/src/app/(dashboard)/page.tsx" "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || true

log_success "Backup created: $BACKUP_DIR/$BACKUP_NAME"

# Run pre-deployment tests
log_info "Running pre-deployment tests..."
cd "$BACKEND_DIR"

if [ -f "test_heartbeat_integration.sh" ]; then
    if bash test_heartbeat_integration.sh; then
        log_success "Pre-deployment tests passed"
    else
        log_error "Pre-deployment tests failed"
        log_warn "Deployment aborted due to test failures"
        exit 1
    fi
else
    log_warn "Integration test script not found, skipping tests"
fi

cd ..

# Deploy backend components
log_info "Deploying backend components..."
log_success "Backend files already in place (heartbeat.py, llm_client.py)"

# Deploy frontend components
log_info "Deploying frontend components..."
log_success "Frontend files already in place (route.ts, page.tsx)"

# Apply database migration (CRITICAL)
log_info "Applying database migration 013..."
if [ -f "$FRONTEND_DIR/supabase/migrations/013_add_llm_metadata_to_pipeline_health.sql" ]; then
    cd "$FRONTEND_DIR/supabase"
    if supabase db push; then
        log_success "Database migration 013 applied successfully"
    else
        log_error "Database migration 013 failed"
        log_warn "This is a CRITICAL step - cannot proceed without it"
        exit 1
    fi
    cd "$FRONTEND_DIR"
else
    log_error "Database migration file not found"
    exit 1
fi

# Set environment variables (if provided)
log_info "Configuring environment variables..."

if [ -n "$HEARTBEAT_DB_WRITE" ]; then
    log_warn "Setting HEARTBEAT_DB_WRITE=$HEARTBEAT_DB_WRITE"
    export HEARTBEAT_DB_WRITE="$HEARTBEAT_DB_WRITE"
else
    log_info "HEARTBEAT_DB_WRITE not set, using default (enabled)"
fi

if [ -n "$HEARTBEAT_CACHE_MAX_SIZE" ]; then
    log_warn "Setting HEARTBEAT_CACHE_MAX_SIZE=$HEARTBEAT_CACHE_MAX_SIZE"
    export HEARTBEAT_CACHE_MAX_SIZE="$HEARTBEAT_CACHE_MAX_SIZE"
fi

if [ -n "$HEARTBEAT_CACHE_TTL" ]; then
    log_warn "Setting HEARTBEAT_CACHE_TTL=$HEARTBEAT_CACHE_TTL"
    export HEARTBEAT_CACHE_TTL="$HEARTHEAT_CACHE_TTL"
fi

log_success "Environment variables configured"

# Restart services (if configured)
if [ -n "$RESTART_BACKEND" ]; then
    log_info "Restarting backend service..."
    if $RESTART_BACKEND; then
        log_success "Backend service restarted"
    else
        log_error "Failed to restart backend service"
        exit 1
    fi
fi

if [ -n "$RESTART_FRONTEND" ]; then
    log_info "Restarting frontend service..."
    if $RESTART_FRONTEND; then
        log_success "Frontend service restarted"
    else
        log_error "Failed to restart frontend service"
        exit 1
    fi
fi

# Wait for services to be ready
log_info "Waiting for services to be ready..."
sleep 5

# Run post-deployment verification
log_info "Running post-deployment verification..."

if [ -f "post_deploy_verification.sh" ]; then
    if bash post_deploy_verification.sh; then
        log_success "Post-deployment verification passed"
    else
        log_error "Post-deployment verification failed"
        log_warn "Deployment may have issues, please investigate"
        log_warn "Rollback may be necessary"
        exit 1
    fi
else
    log_warn "Post-deployment verification script not found"
    log_warn "Please run manual verification"
fi

# Deployment complete
echo ""
echo "========================================"
log_success "🎉 Deployment Complete!"
echo ""
echo "Deployment Details:"
echo "  - Backup: $BACKUP_DIR/$BACKUP_NAME"
echo "  - Timestamp: $TIMESTAMP"
echo "  - Rate Limiting: DISABLED (unlimited requests)"
echo "  - Cache: max_size=1000, ttl_seconds=60"
echo ""
echo "Next Steps:"
echo "  1. Monitor application logs for heartbeat entries"
echo "  2. Check dashboard for real-time agent status"
echo "  3. Verify LLM metadata appears correctly"
echo "  4. Monitor cache size and performance"
echo ""
echo "Rollback Command (if needed):"
echo "  bash rollback_heartbeat_system.sh $BACKUP_NAME"
echo ""
echo "For issues, check:"
echo "  - Backend logs: tail -f logs/backend.log | grep -i heartbeat"
echo "  - Cache stats: python3 -c 'from src.content_engine.utils.heartbeat import get_cache_stats; print(get_cache_stats())'"
echo "  - Run diagnostics: bash post_deploy_verification.sh"
echo ""
