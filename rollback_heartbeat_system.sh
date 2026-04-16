#!/bin/bash

# Rollback Script for Pragmatic Heartbeat System
# This script rolls back the heartbeat system to a previous backup

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

if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Backup name required${NC}"
    echo "Usage: $0 <backup_name>"
    echo "Example: $0 heartbeat_backup_20260416_143022"
    echo ""
    echo "Available backups:"
    ls -la "$BACKUP_DIR/" 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_NAME="$1"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

echo -e "${YELLOW}🔄 Rollback: Pragmatic Heartbeat System${NC}"
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

# Verify backup exists
log_info "Verifying backup exists..."

if [ ! -d "$BACKUP_PATH" ]; then
    log_error "Backup not found: $BACKUP_PATH"
    exit 1
fi

log_success "Backup found: $BACKUP_PATH"

# Show backup contents
log_info "Backup contents:"
ls -la "$BACKUP_PATH/"
echo ""

# Confirm rollback
log_warn "This will rollback to: $BACKUP_NAME"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    log_info "Rollback cancelled"
    exit 0
fi

# Create pre-rollback backup
log_info "Creating pre-rollback backup..."
PRE_ROLLBACK_BACKUP="pre_rollback_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR/$PRE_ROLLBACK_BACKUP"

cp "$BACKEND_DIR/src/content_engine/utils/heartbeat.py" "$BACKUP_DIR/$PRE_ROLLBACK_BACKUP/" 2>/dev/null || true
cp "$BACKEND_DIR/src/content_engine/utils/llm_client.py" "$BACKUP_DIR/$PRE_ROLLBACK_BACKUP/" 2>/dev/null || true
cp "$FRONTEND_DIR/src/app/api/system/health/route.ts" "$BACKUP_DIR/$PRE_ROLLBACK_BACKUP/" 2>/dev/null || true
cp "$FRONTEND_DIR/src/app/(dashboard)/page.tsx" "$BACKUP_DIR/$PRE_ROLLBACK_BACKUP/" 2>/dev/null || true

log_success "Pre-rollback backup created: $PRE_ROLLBACK_BACKUP"

# Rollback backend files
log_info "Rolling back backend files..."

if [ -f "$BACKUP_PATH/heartbeat.py" ]; then
    cp "$BACKUP_PATH/heartbeat.py" "$BACKEND_DIR/src/content_engine/utils/heartbeat.py"
    log_success "Rolled back: heartbeat.py"
else
    log_warn "heartbeat.py not found in backup, skipping"
fi

if [ -f "$BACKUP_PATH/llm_client.py" ]; then
    cp "$BACKUP_PATH/llm_client.py" "$BACKEND_DIR/src/content_engine/utils/llm_client.py"
    log_success "Rolled back: llm_client.py"
else
    log_warn "llm_client.py not found in backup, skipping"
fi

# Rollback frontend files
log_info "Rolling back frontend files..."

if [ -f "$BACKUP_PATH/route.ts" ]; then
    cp "$BACKUP_PATH/route.ts" "$FRONTEND_DIR/src/app/api/system/health/route.ts"
    log_success "Rolled back: route.ts"
else
    log_warn "route.ts not found in backup, skipping"
fi

if [ -f "$BACKUP_PATH/page.tsx" ]; then
    cp "$BACKUP_PATH/page.tsx" "$FRONTEND_DIR/src/app/(dashboard)/page.tsx"
    log_success "Rolled back: page.tsx"
else
    log_warn "page.tsx not found in backup, skipping"
fi

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

# Rollback complete
echo ""
echo "========================================"
log_success "🎉 Rollback Complete!"
echo ""
echo "Rollback Details:"
echo "  - From backup: $BACKUP_NAME"
echo "  - Pre-rollback backup: $PRE_ROLLBACK_BACKUP"
echo "  - Timestamp: $(date +%Y%m%d_%H%M%S)"
echo ""
echo "Next Steps:"
echo "  1. Verify application is working correctly"
echo "  2. Check logs for any errors"
echo "  3. Monitor system performance"
echo "  4. Investigate issues that caused rollback"
echo ""
echo "To re-deploy (if issues are resolved):"
echo "  bash deploy_heartbeat_system.sh"
echo ""
echo "For issues, check:"
echo "  - Application logs"
echo "  - System metrics"
echo "  - Error reports"
echo ""
