#!/bin/bash
# instructions_on_start.sh — session-start health checks for ADMESH-Domains
#
# USAGE: bash "$(git rev-parse --show-toplevel)"/scripts/instructions_on_start.sh
#
# WHAT THIS RUNS (in order):
#   1. DomI drift check (HARD STOP if behind upstream domattioli/DomI@main)
#   2. CLAUDE.md presence audit
#   3. Git hygiene snapshot (current branch, dirty files)
#
# DomI sync contract: see CLAUDE.md → "DomI Sync Contract" section.
# Hook source: ~/.claude/plugins/cache/DomI/sync-from-domi/<version>/skills/sync-from-domi/templates/downstream_startup_hook.sh

set -euo pipefail

# ============================================================================
# DomI drift check (pasted from sync-from-domi skill template)
# ============================================================================
# --- locate sync-from-domi ---
DOMI_SKILL_PATH="${DOMI_SKILL_PATH:-}"
if [ -z "$DOMI_SKILL_PATH" ]; then
  for cached in "${HOME}"/.claude/plugins/cache/DomI/sync-from-domi/*/skills/sync-from-domi; do
    if [ -f "${cached}/scripts/check_pin.sh" ]; then
      DOMI_SKILL_PATH="$cached"
      break
    fi
  done
fi
if [ -z "$DOMI_SKILL_PATH" ]; then
  for candidate in \
    "${HOME}/.claude/plugins/marketplaces/domattioli/DomI/plugins/sync-from-domi/skills/sync-from-domi" \
    "./plugins/sync-from-domi/skills/sync-from-domi" \
    "./skills/sync-from-domi" \
    "${HOME}/.claude/skills/sync-from-domi"; do
    if [ -f "${candidate}/scripts/check_pin.sh" ]; then
      DOMI_SKILL_PATH="$candidate"
      break
    fi
  done
fi

if [ -z "$DOMI_SKILL_PATH" ] || [ ! -f "${DOMI_SKILL_PATH}/scripts/check_pin.sh" ]; then
  echo "⚠ sync-from-domi skill not found locally; skipping DomI drift check"
  echo "  → install via: claude plugin marketplace add domattioli/DomI && claude plugin install sync-from-domi@DomI"
else
  set +e
  bash "${DOMI_SKILL_PATH}/scripts/check_pin.sh"
  DOMI_DRIFT_RC=$?
  set -e

  case $DOMI_DRIFT_RC in
    0)
      : # synced; continue
      ;;
    1)
      echo ""
      echo "============================================================"
      echo "🛑 HARD STOP: downstream is BEHIND DomI"
      echo "============================================================"
      echo "Invoke the sync-from-domi skill before any write work:"
      echo "  > sync from DomI"
      echo "Or run manually:"
      echo "  bash ${DOMI_SKILL_PATH}/scripts/update_pin.sh"
      echo "  (then commit .domi-pin and any updated skills)"
      echo "============================================================"
      if [ "${DOMI_BLOCK_ON_DRIFT:-1}" = "1" ]; then
        exit 1
      fi
      ;;
    2)
      echo "ⓘ First-time DomI pin needed; will create on next sync"
      ;;
    3)
      echo ""
      echo "============================================================"
      echo "🛑 HARD STOP: DomI pin FORKED (manifest hash mismatch)"
      echo "============================================================"
      echo "Local edits to vendored DomI artifacts suspected."
      echo "Operator must resolve manually before continuing."
      echo "============================================================"
      exit 1
      ;;
    4)
      echo "⚠ DomI drift check skipped (gh unavailable); continuing"
      ;;
  esac
fi
# --- end DomI drift check ---

# ============================================================================
# Audit checks
# ============================================================================
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo ".")}"

echo ""
echo "=== ADMESH-Domains On-Start Checks ==="

# CLAUDE.md presence
if [ ! -f "$REPO_ROOT/CLAUDE.md" ]; then
  echo "  ❌ CLAUDE.md missing — bootstrap with /maintain-claude-md init"
  exit 1
else
  echo "  ✓ CLAUDE.md present"
fi

# Git hygiene snapshot
BRANCH=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
DIRTY=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
echo "  ✓ Branch: $BRANCH ($DIRTY uncommitted file(s))"

echo "=== Done ==="
