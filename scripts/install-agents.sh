#!/usr/bin/env bash
# install-agents.sh — copy selected agent categories from the agency-agents
# submodule into /agents for runtime use.
#
# Usage:
#   ./scripts/install-agents.sh [--all] [--categories cat1,cat2,...]
#
# The submodule must be initialised first:
#   git submodule update --init --recursive
#
# HITL gate: run `git diff --stat agents/` after this script and commit only
# the subset you approve.
#
set -euo pipefail

VENDOR_DIR=".vendor/agency-agents"
AGENTS_DIR="agents"

# Default categories — covers the PRD scope (marketing, paid-media, design, strategy).
# Extend by passing --categories or editing DEFAULT_CATEGORIES below.
DEFAULT_CATEGORIES=(
  "marketing"
  "paid-media"
  "design"
  "sales"
  "product"
)

usage() {
  echo "Usage: $0 [--all] [--categories cat1,cat2,...]"
  echo ""
  echo "Options:"
  echo "  --all                  Copy every agent from the submodule"
  echo "  --categories cat1,...  Comma-separated list of categories to install"
  echo ""
  echo "Available categories (run without args to see):"
  ls "${VENDOR_DIR}/" 2>/dev/null || echo "  (submodule not initialised — run: git submodule update --init)"
  exit 0
}

main() {
  if [ ! -d "${VENDOR_DIR}" ]; then
    echo "ERROR: ${VENDOR_DIR} not found. Initialise the submodule first:"
    echo "  git submodule update --init --recursive"
    exit 1
  fi

  local install_all=0
  local categories=("${DEFAULT_CATEGORIES[@]}")

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --all) install_all=1 ;;
      --categories)
        shift
        IFS=',' read -ra categories <<< "$1"
        ;;
      --help|-h) usage ;;
      *) echo "Unknown option: $1"; usage ;;
    esac
    shift
  done

  mkdir -p "${AGENTS_DIR}"

  if [[ ${install_all} -eq 1 ]]; then
    echo "Installing ALL agents from ${VENDOR_DIR}/"
    cp -r "${VENDOR_DIR}/"*.md "${AGENTS_DIR}/" 2>/dev/null || true
    find "${VENDOR_DIR}" -name "*.md" -not -path "*/.git/*" | while read -r f; do
      cp "$f" "${AGENTS_DIR}/"
    done
  else
    local installed=0
    for cat in "${categories[@]}"; do
      local src="${VENDOR_DIR}/${cat}"
      if [ -d "${src}" ]; then
        echo "Installing category: ${cat}"
        mkdir -p "${AGENTS_DIR}/${cat}"
        cp -r "${src}/"* "${AGENTS_DIR}/${cat}/"
        installed=$((installed + 1))
      else
        echo "WARNING: category not found: ${cat} (skipping)"
      fi
    done
    if [[ ${installed} -eq 0 ]]; then
      echo "No categories matched. Available:"
      ls "${VENDOR_DIR}/"
      exit 1
    fi
    echo "Installed ${installed} categories → ${AGENTS_DIR}/"
  fi

  echo ""
  echo "HITL review required:"
  echo "  git diff --stat ${AGENTS_DIR}/"
  echo "  git add ${AGENTS_DIR}/ && git commit -m 'feat: install agency-agents subset'"
}

main "$@"
