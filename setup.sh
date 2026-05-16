#!/usr/bin/env bash
# ZeroHuman-Agency — Setup Wizard
# Guides you from a fresh clone to a running stack in ~5 minutes.
#
# Usage (interactive):
#   ./setup.sh
#
# Usage (non-interactive / CI):
#   ./setup.sh \
#     --supabase-url=https://xxx.supabase.co \
#     --supabase-anon-key=eyJ... \
#     --supabase-service-key=eyJ... \
#     --anthropic-key=sk-ant-... \
#     [--openrouter-key=sk-or-...] \
#     [--serper-key=...] \
#     [--tavily-key=...] \
#     [--youtube-key=...] \
#     [--resend-key=...] \
#     [--postiz-mode=disabled|self_hosted|cloud] \
#     [--postiz-url=...] \
#     [--postiz-key=...] \
#     [--no-docker] \
#     [--no-migrations]

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET} $*"; }
info() { echo -e "${BLUE}→${RESET} $*"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $*"; }
err()  { echo -e "${RED}✗${RESET} $*" >&2; }
step() { echo -e "\n${BOLD}${CYAN}$*${RESET}"; }
hr()   { echo -e "${CYAN}──────────────────────────────────────────────${RESET}"; }

# ── Non-interactive flag parsing ──────────────────────────────────────────────
SUPABASE_URL=""
SUPABASE_ANON_KEY=""
SUPABASE_SERVICE_KEY=""
ANTHROPIC_KEY=""
OPENROUTER_KEY=""
SERPER_KEY=""
TAVILY_KEY=""
YOUTUBE_KEY=""
RESEND_KEY=""
POSTIZ_MODE="disabled"
POSTIZ_URL=""
POSTIZ_KEY=""
USE_DOCKER=true
RUN_MIGRATIONS=true
NON_INTERACTIVE=false

for arg in "$@"; do
  case $arg in
    --supabase-url=*)        SUPABASE_URL="${arg#*=}"; NON_INTERACTIVE=true ;;
    --supabase-anon-key=*)   SUPABASE_ANON_KEY="${arg#*=}"; NON_INTERACTIVE=true ;;
    --supabase-service-key=*)SUPABASE_SERVICE_KEY="${arg#*=}"; NON_INTERACTIVE=true ;;
    --anthropic-key=*)       ANTHROPIC_KEY="${arg#*=}"; NON_INTERACTIVE=true ;;
    --openrouter-key=*)      OPENROUTER_KEY="${arg#*=}"; NON_INTERACTIVE=true ;;
    --serper-key=*)          SERPER_KEY="${arg#*=}"; NON_INTERACTIVE=true ;;
    --tavily-key=*)          TAVILY_KEY="${arg#*=}"; NON_INTERACTIVE=true ;;
    --youtube-key=*)         YOUTUBE_KEY="${arg#*=}"; NON_INTERACTIVE=true ;;
    --resend-key=*)          RESEND_KEY="${arg#*=}"; NON_INTERACTIVE=true ;;
    --postiz-mode=*)         POSTIZ_MODE="${arg#*=}"; NON_INTERACTIVE=true ;;
    --postiz-url=*)          POSTIZ_URL="${arg#*=}"; NON_INTERACTIVE=true ;;
    --postiz-key=*)          POSTIZ_KEY="${arg#*=}"; NON_INTERACTIVE=true ;;
    --no-social)             POSTIZ_MODE="disabled"; NON_INTERACTIVE=true ;;
    --no-newsletter)         RESEND_KEY=""; NON_INTERACTIVE=true ;;
    --no-docker)             USE_DOCKER=false; NON_INTERACTIVE=true ;;
    --no-migrations)         RUN_MIGRATIONS=false; NON_INTERACTIVE=true ;;
    --help|-h)
      grep '^#' "$0" | head -20 | sed 's/^# \?//'
      exit 0 ;;
    *) warn "Unknown flag: $arg" ;;
  esac
done

# ── Helper: prompt with default ───────────────────────────────────────────────
ask() {
  local prompt="$1" default="${2:-}" var_name="$3"
  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    return
  fi
  if [[ -n "$default" ]]; then
    read -rp "$(echo -e "${BOLD}$prompt${RESET} [${default}]: ")" val
    val="${val:-$default}"
  else
    read -rp "$(echo -e "${BOLD}$prompt${RESET}: ")" val
  fi
  printf -v "$var_name" '%s' "$val"
}

ask_yn() {
  local prompt="$1" default="${2:-y}" var_name="$3"
  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    printf -v "$var_name" '%s' "$default"
    return
  fi
  local hint="[Y/n]"
  [[ "$default" == "n" ]] && hint="[y/N]"
  read -rp "$(echo -e "${BOLD}$prompt${RESET} $hint: ")" val
  val="${val:-$default}"
  printf -v "$var_name" '%s' "${val,,}"
}

# ── Banner ────────────────────────────────────────────────────────────────────
clear
echo -e "${BOLD}${CYAN}"
cat <<'EOF'
  ______              _   _
 |___  /             | | | |
    / / ___ _ __ ___ | |_| |_   _ _ __ ___   __ _ _ __
   / / / _ \ '__/ _ \| __| | | | | '_ ` _ \ / _` | '_ \
  / /_|  __/ | | (_) | |_| | |_| | | | | | | (_| | | | |
 /_____\___|_|  \___/ \__|_|\__,_|_| |_| |_|\__,_|_| |_|

  Agency — Setup Wizard
EOF
echo -e "${RESET}"
hr
echo "  This wizard will guide you from a fresh clone to a running stack."
echo "  Estimated time: 3–5 minutes"
hr
echo ""

# ── Step 1: Environment check ─────────────────────────────────────────────────
step "Step 1/7 — Checking environment"

MISSING_TOOLS=()

if command -v docker &>/dev/null; then
  DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
  ok "Docker $DOCKER_VERSION found"
else
  warn "Docker not found — cannot use Docker setup"
  USE_DOCKER=false
  MISSING_TOOLS+=("Docker (https://docs.docker.com/get-docker/)")
fi

if command -v node &>/dev/null; then
  NODE_VERSION=$(node --version | tr -d 'v')
  NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
  if [[ "$NODE_MAJOR" -ge 20 ]]; then
    ok "Node.js $NODE_VERSION found"
  else
    warn "Node.js $NODE_VERSION found — recommend 20+"
  fi
else
  MISSING_TOOLS+=("Node.js 20+ (https://nodejs.org)")
fi

if command -v python3 &>/dev/null; then
  PYTHON_VERSION=$(python3 --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
  ok "Python $PYTHON_VERSION found"
elif command -v python &>/dev/null; then
  ok "Python found"
else
  MISSING_TOOLS+=("Python 3.11+ (https://python.org)")
fi

if command -v supabase &>/dev/null; then
  ok "Supabase CLI found"
  HAS_SUPABASE_CLI=true
else
  warn "Supabase CLI not found — migrations will need to be applied manually or via dashboard"
  HAS_SUPABASE_CLI=false
fi

if [[ ${#MISSING_TOOLS[@]} -gt 0 ]]; then
  echo ""
  warn "Missing tools:"
  for t in "${MISSING_TOOLS[@]}"; do
    echo "  • $t"
  done
  if [[ "$USE_DOCKER" == "false" ]]; then
    echo ""
    err "Cannot continue without Docker and Node.js. Please install them first."
    exit 1
  fi
fi

# ── Step 2: Setup mode ────────────────────────────────────────────────────────
step "Step 2/7 — Setup mode"

if [[ "$USE_DOCKER" == "true" ]] && [[ "$NON_INTERACTIVE" == "false" ]]; then
  echo "How do you want to run ZeroHuman-Agency?"
  echo "  1) Docker (recommended — zero local dependencies)"
  echo "  2) Manual (npm + uv — for development)"
  read -rp "$(echo -e "${BOLD}Choice${RESET} [1]: ")" SETUP_MODE
  SETUP_MODE="${SETUP_MODE:-1}"
  [[ "$SETUP_MODE" == "2" ]] && USE_DOCKER=false
fi

if [[ "$USE_DOCKER" == "true" ]]; then
  info "Using Docker setup"
else
  info "Using manual setup"
fi

# ── Step 3: Supabase credentials ──────────────────────────────────────────────
step "Step 3/7 — Supabase credentials"
echo "Create a free Supabase project at https://supabase.com if you haven't already."
echo "Find your credentials at: Project Settings → API"
echo ""

if [[ -z "$SUPABASE_URL" ]]; then
  ask "Supabase Project URL (e.g. https://xxx.supabase.co)" "" SUPABASE_URL
fi
if [[ -z "$SUPABASE_URL" ]]; then
  err "Supabase URL is required."
  exit 1
fi
ok "Supabase URL: $SUPABASE_URL"

if [[ -z "$SUPABASE_ANON_KEY" ]]; then
  ask "Supabase Anon Key (eyJ...)" "" SUPABASE_ANON_KEY
fi
if [[ -z "$SUPABASE_ANON_KEY" ]]; then
  err "Supabase Anon Key is required."
  exit 1
fi
ok "Supabase Anon Key: ${SUPABASE_ANON_KEY:0:12}..."

if [[ -z "$SUPABASE_SERVICE_KEY" ]]; then
  ask "Supabase Service Role Key (eyJ...)" "" SUPABASE_SERVICE_KEY
fi
if [[ -z "$SUPABASE_SERVICE_KEY" ]]; then
  err "Supabase Service Role Key is required."
  exit 1
fi
ok "Service Role Key: ${SUPABASE_SERVICE_KEY:0:12}..."

# Extract project ref from URL
SUPABASE_PROJECT_REF=$(echo "$SUPABASE_URL" | sed -E 's|https://([^.]+)\.supabase\.co.*|\1|')
ok "Project ref: $SUPABASE_PROJECT_REF"

# ── Step 4: LLM provider ──────────────────────────────────────────────────────
step "Step 4/7 — LLM provider (required)"
echo "At least one LLM API key is required for content generation."
echo ""

if [[ -z "$ANTHROPIC_KEY" ]]; then
  ask "Anthropic API key (sk-ant-... | leave blank to skip)" "" ANTHROPIC_KEY
fi
if [[ -z "$OPENROUTER_KEY" ]]; then
  ask "OpenRouter API key (sk-or-... | leave blank to skip)" "" OPENROUTER_KEY
fi

if [[ -z "$ANTHROPIC_KEY" && -z "$OPENROUTER_KEY" ]]; then
  err "At least one LLM key (Anthropic or OpenRouter) is required."
  exit 1
fi

[[ -n "$ANTHROPIC_KEY" ]]   && ok "Anthropic API key configured"
[[ -n "$OPENROUTER_KEY" ]]  && ok "OpenRouter API key configured"

# ── Step 5: Optional services ─────────────────────────────────────────────────
step "Step 5/7 — Optional services"
echo "Research APIs (leave blank to use free DuckDuckGo + RSS fallback):"
echo ""

if [[ -z "$SERPER_KEY" ]]; then
  ask "Serper API key for Google Search (serper.dev | blank = free DDG)" "" SERPER_KEY
fi
if [[ -z "$TAVILY_KEY" ]]; then
  ask "Tavily API key (tavily.com | 1000 free/month | blank = skip)" "" TAVILY_KEY
fi
if [[ -z "$YOUTUBE_KEY" ]]; then
  ask "YouTube Data API key (blank = disable trend research)" "" YOUTUBE_KEY
fi

echo ""
echo "Email newsletter:"
if [[ -z "$RESEND_KEY" ]]; then
  ask "Resend API key (resend.com | blank = disable newsletter)" "" RESEND_KEY
fi

echo ""
echo "Social publishing:"
if [[ "$NON_INTERACTIVE" == "false" ]]; then
  echo "  1) Disabled (default — skip for now)"
  echo "  2) Self-hosted Postiz (Docker, OAuth setup required)"
  echo "  3) Cloud Postiz (postiz.com or custom instance)"
  read -rp "$(echo -e "${BOLD}Postiz mode${RESET} [1]: ")" POSTIZ_CHOICE
  case "${POSTIZ_CHOICE:-1}" in
    2) POSTIZ_MODE="self_hosted" ;;
    3) POSTIZ_MODE="cloud"
       ask "Postiz API URL (e.g. https://api.postiz.com)" "" POSTIZ_URL
       ask "Postiz API key" "" POSTIZ_KEY
       ;;
    *) POSTIZ_MODE="disabled" ;;
  esac
fi
ok "Postiz mode: $POSTIZ_MODE"

# ── Step 6: Generate config ───────────────────────────────────────────────────
step "Step 6/7 — Generating configuration"

if [[ -f ".env.local" ]]; then
  warn ".env.local already exists — backing up to .env.local.bak"
  cp .env.local .env.local.bak
fi

SCHEDULER_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")

if [[ "$USE_DOCKER" == "true" ]]; then
  BACKEND_URL="http://backend:8000"
else
  BACKEND_URL="http://localhost:8000"
fi

cat > .env.local <<EOF
# ============================================================
# Generated by setup.sh on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# DO NOT commit this file to version control
# ============================================================

# ── Supabase ──────────────────────────────────────────────────
NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_KEY}

# ── Python Backend ─────────────────────────────────────────────
PYTHON_BACKEND_URL=${BACKEND_URL}

# ── Security ───────────────────────────────────────────────────
SCHEDULER_SECRET=${SCHEDULER_SECRET}
ALLOWED_ORIGINS=http://localhost:3000

# ── AI / LLM ──────────────────────────────────────────────────
ANTHROPIC_API_KEY=${ANTHROPIC_KEY}
OPENROUTER_API_KEY=${OPENROUTER_KEY}

# ── Research APIs (optional — free fallback active) ────────────
SERPER_API_KEY=${SERPER_KEY}
TAVILY_API_KEY=${TAVILY_KEY}
YOUTUBE_API_KEY=${YOUTUBE_KEY}

# ── Email ──────────────────────────────────────────────────────
RESEND_API_KEY=${RESEND_KEY}
NEWSLETTER_FROM_EMAIL=newsletter@yourdomain.com
NEWSLETTER_FROM_NAME=ZeroHuman Agency

# ── Image Generation ───────────────────────────────────────────
DEFAULT_IMAGE_BACKEND=mock
DEFAULT_IMAGE_MODEL=mock-v1

# ── Social Publishing ──────────────────────────────────────────
POSTIZ_MODE=${POSTIZ_MODE}
POSTIZ_API_URL=${POSTIZ_URL:-http://localhost:3001}
POSTIZ_API_KEY=${POSTIZ_KEY}

# ── Scheduler ──────────────────────────────────────────────────
SCHEDULER_BRAND_ID=
EOF

ok ".env.local generated"
ok "SCHEDULER_SECRET auto-generated"

# ── Step 7: Migrations ────────────────────────────────────────────────────────
step "Step 7/7 — Applying database migrations"

if [[ "$RUN_MIGRATIONS" == "false" ]]; then
  warn "Skipping migrations (--no-migrations flag)"
elif [[ "$HAS_SUPABASE_CLI" == "true" ]]; then
  info "Linking Supabase project..."
  if supabase link --project-ref "$SUPABASE_PROJECT_REF" 2>&1 | grep -q "Error\|error\|failed"; then
    warn "Supabase link may have failed — you may need to run: supabase link --project-ref $SUPABASE_PROJECT_REF"
  else
    info "Pushing migrations..."
    if supabase db push; then
      ok "All migrations applied successfully"
    else
      warn "Migration push failed. Run manually: supabase db push"
    fi
  fi
else
  warn "Supabase CLI not found — apply migrations manually:"
  echo "  Option A: supabase db push (after installing Supabase CLI)"
  echo "  Option B: Run SQL from supabase/schema_complete.sql in your Supabase dashboard"
fi

# ── Start services ────────────────────────────────────────────────────────────
echo ""
hr
step "Starting services"

if [[ "$USE_DOCKER" == "true" ]]; then
  DOCKER_ARGS="-f docker-compose.full.yaml"
  if [[ "$POSTIZ_MODE" == "self_hosted" ]]; then
    DOCKER_ARGS="$DOCKER_ARGS --profile social"
    info "Postiz profile enabled — starting full social stack"
  fi

  info "Building and starting Docker services..."
  DOCKER_BUILD=1 docker compose $DOCKER_ARGS up -d --build

  # Health check
  echo ""
  info "Waiting for services to be ready..."
  RETRIES=12
  for i in $(seq 1 $RETRIES); do
    sleep 5
    BACKEND_OK=false
    FRONTEND_OK=false

    if curl -sf http://localhost:8000/health &>/dev/null; then
      BACKEND_OK=true
    fi
    if curl -sf http://localhost:3000/api/health &>/dev/null 2>/dev/null; then
      FRONTEND_OK=true
    fi

    if [[ "$BACKEND_OK" == "true" && "$FRONTEND_OK" == "true" ]]; then
      break
    fi

    if [[ "$i" == "$RETRIES" ]]; then
      warn "Health check timed out. Services may still be starting."
      warn "Check status with: docker compose -f docker-compose.full.yaml ps"
    fi
  done

  # Final status
  BACKEND_STATUS=$(curl -sf http://localhost:8000/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null || echo "starting...")
  echo ""

else
  info "Manual start — run these commands in separate terminals:"
  echo ""
  echo "  Terminal 1 (backend):"
  echo "    cd python && uv run uvicorn src.content_engine.main:app --reload --port 8000"
  echo ""
  echo "  Terminal 2 (frontend):"
  echo "    npm install && npm run dev"
  echo ""
  BACKEND_STATUS="(not started)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
hr
echo -e "${BOLD}${GREEN}  Setup complete!${RESET}"
hr
echo ""
echo -e "  ${BOLD}Dashboard:${RESET}   http://localhost:3000"
echo -e "  ${BOLD}Backend:${RESET}     http://localhost:8000/health"
echo ""
echo -e "  ${BOLD}Configured services:${RESET}"
[[ -n "$ANTHROPIC_KEY" ]]   && echo -e "    ${GREEN}✓${RESET} Anthropic (Claude)"
[[ -n "$OPENROUTER_KEY" ]]  && echo -e "    ${GREEN}✓${RESET} OpenRouter"
[[ -n "$SERPER_KEY" ]]      && echo -e "    ${GREEN}✓${RESET} Serper (Google Search)" || echo -e "    ${YELLOW}~${RESET} Research: DuckDuckGo (free fallback)"
[[ -n "$TAVILY_KEY" ]]      && echo -e "    ${GREEN}✓${RESET} Tavily (enhanced search)"
[[ -n "$YOUTUBE_KEY" ]]     && echo -e "    ${GREEN}✓${RESET} YouTube API"
[[ -n "$RESEND_KEY" ]]      && echo -e "    ${GREEN}✓${RESET} Resend (newsletter)" || echo -e "    ${YELLOW}~${RESET} Newsletter: disabled"
[[ "$POSTIZ_MODE" != "disabled" ]] && echo -e "    ${GREEN}✓${RESET} Postiz ($POSTIZ_MODE)" || echo -e "    ${YELLOW}~${RESET} Social publishing: disabled"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo "    1. Open http://localhost:3000 and create your first brand"
echo "    2. Use Brand Auto-Discovery to set up your brand voice from your website"
echo "    3. Trigger a research run to start generating content"
echo ""
if [[ -f ".env.local.bak" ]]; then
  echo -e "  ${YELLOW}Note:${RESET} Previous .env.local backed up to .env.local.bak"
  echo ""
fi
hr
