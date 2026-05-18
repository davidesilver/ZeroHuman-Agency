#!/usr/bin/env bash
# Create child issues for PRD on davidesilver/ZeroHuman-Agency
# Parent PRD issue must already exist. Pass its number as $1.
# Usage: ./_create_issues.sh 1
set -eo pipefail

REPO="davidesilver/ZeroHuman-Agency"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT="${1:?Usage: $0 <parent-issue-number>}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

extract_number() {
  grep -oE '/[0-9]+$' | tr -d '/'
}

create_issue() {
  local title="$1" body_file="$2"; shift 2
  if [ $# -gt 0 ]; then
    local label_args=()
    for lbl in "$@"; do
      label_args+=(--label "$lbl")
    done
    gh issue create --repo "$REPO" --title "$title" --body-file "$body_file" "${label_args[@]}" 2>&1 | tee /dev/stderr | extract_number
  else
    gh issue create --repo "$REPO" --title "$title" --body-file "$body_file" 2>&1 | tee /dev/stderr | extract_number
  fi
}

subst_file() {
  local src="$1" dst="$2"; shift 2
  cp "$src" "$dst"
  while [ $# -gt 0 ]; do
    local k="${1%%=*}" v="${1#*=}"; shift
    sed -i.bak "s|{{${k}}}|${v}|g" "$dst" && rm -f "${dst}.bak"
  done
}

prep_and_create() {
  local base="$1" title="$2"; shift 2
  # remaining args before "--" are substitution pairs, after "--" are labels
  local in_labels=0
  local subs=()
  local labels=()
  for arg in "$@"; do
    if [ "$arg" = "--" ]; then
      in_labels=1; continue
    fi
    if [ "$in_labels" -eq 1 ]; then
      labels+=("$arg")
    else
      subs+=("$arg")
    fi
  done
  local out="$TMP/$base"
  if [ ${#subs[@]} -gt 0 ]; then
    subst_file "$DIR/$base" "$out" "PARENT=$PARENT" "${subs[@]}"
  else
    subst_file "$DIR/$base" "$out" "PARENT=$PARENT"
  fi
  if [ ${#labels[@]} -gt 0 ]; then
    create_issue "$title" "$out" "${labels[@]}"
  else
    create_issue "$title" "$out"
  fi
}

echo "Parent PRD: #$PARENT"
echo ""

# === P0: no dependencies (can start immediately) ===

echo "==> #1 Foundation"
N1=$(prep_and_create 01-foundation.md \
  "[P0] Foundation: feature_flags + brand_integrations + secrets helper" \
  -- P0 foundation backend)
echo "    -> #$N1"

echo "==> #2 Dev skills bundle"
N2=$(prep_and_create 02-dev-skills-bundle.md \
  "[P0] Dev skills bundle in skills-lock.json" \
  -- P0 dev-experience skills)
echo "    -> #$N2"

echo "==> #3 Agency agents [HITL]"
N3=$(prep_and_create 03-agency-agents-install.md \
  "[P0][HITL] Install agency-agents subset in /agents" \
  -- P0 HITL agents)
echo "    -> #$N3"

# === P0/P1: depend on #1 ===

echo "==> #5 LLM provider abstraction"
N5=$(prep_and_create 05-llm-provider-abstraction.md \
  "[P1] LLM provider abstraction + telemetria" \
  "1=$N1" -- P1 backend llm)
echo "    -> #$N5"

echo "==> #4 Brevo foundation"
N4=$(prep_and_create 04-brevo-foundation.md \
  "[P0] Brevo foundation: contacts + lists per-brand" \
  "1=$N1" -- P0 brevo email)
echo "    -> #$N4"

echo "==> #8 Deep research engine"
N8=$(prep_and_create 08-deep-research-engine.md \
  "[P1] Deep research engine (local-deep-research Docker)" \
  "1=$N1" -- P1 research backend)
echo "    -> #$N8"

echo "==> #10 Scrapling competitor monitoring"
N10=$(prep_and_create 10-scrapling-competitor.md \
  "[P1] Scrapling competitor monitoring" \
  "1=$N1" -- P1 research scraping)
echo "    -> #$N10"

echo "==> #11 HyperFrames foundation"
N11=$(prep_and_create 11-hyperframes-foundation.md \
  "[P1] HyperFrames motion graphics foundation" \
  "1=$N1" -- P1 video frontend)
echo "    -> #$N11"

# === P1: depend on other P0/P1 slices ===

echo "==> #6 Brevo campaigns"
N6=$(prep_and_create 06-brevo-campaigns.md \
  "[P1] Brevo campaigns from drafts + metrics" \
  "4=$N4" -- P1 brevo email)
echo "    -> #$N6"

echo "==> #7 Brevo automations"
N7=$(prep_and_create 07-brevo-automations.md \
  "[P1] Brevo automations (welcome / nurture / win-back)" \
  "6=$N6" -- P1 brevo email)
echo "    -> #$N7"

echo "==> #9 Deep research → ideation"
N9=$(prep_and_create 09-deep-research-to-ideation.md \
  "[P1] Deep research → ideation handoff" \
  "8=$N8" -- P1 research ideation)
echo "    -> #$N9"

echo "==> #12 Carousel → reel template"
N12=$(prep_and_create 12-hyperframes-carousel-to-reel.md \
  "[P1] HyperFrames carousel → reel template" \
  "11=$N11" -- P1 video)
echo "    -> #$N12"

echo "==> #13 Heygen talking-head"
N13=$(prep_and_create 13-heygen-talking-head.md \
  "[P1] Heygen talking-head integration" \
  "1=$N1" "11=$N11" -- P1 video heygen)
echo "    -> #$N13"

# === P2 ===

echo "==> #14 Video templates customization"
N14=$(prep_and_create 14-video-templates-customization.md \
  "[P2] Video templates customization per-brand" \
  "11=$N11" -- P2 video)
echo "    -> #$N14"

echo "==> #15 OpenClaw POC"
N15=$(prep_and_create 15-openclaw-poc.md \
  "[P2] OpenClaw POC + A/B vs OpenRouter" \
  "5=$N5" -- P2 llm)
echo "    -> #$N15"

echo "==> #16 ViMax microservice [HITL]"
N16=$(prep_and_create 16-vimax-microservice.md \
  "[P2][HITL] ViMax microservice (full pipeline video)" \
  "11=$N11" "13=$N13" -- P2 HITL video)
echo "    -> #$N16"

echo ""
echo "==================================="
echo "DONE. All 16 issues created."
echo "Parent PRD: #$PARENT"
echo "  1  Foundation        -> #$N1"
echo "  2  Dev skills        -> #$N2"
echo "  3  Agency agents     -> #$N3"
echo "  4  Brevo foundation  -> #$N4"
echo "  5  LLM provider      -> #$N5"
echo "  6  Brevo campaigns   -> #$N6"
echo "  7  Brevo automations -> #$N7"
echo "  8  Deep research     -> #$N8"
echo "  9  Research→ideation -> #$N9"
echo "  10 Scrapling         -> #$N10"
echo "  11 HyperFrames       -> #$N11"
echo "  12 Carousel→reel     -> #$N12"
echo "  13 Heygen            -> #$N13"
echo "  14 Video templates   -> #$N14"
echo "  15 OpenClaw POC      -> #$N15"
echo "  16 ViMax             -> #$N16"
