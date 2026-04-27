#!/bin/bash
set -euo pipefail

REPO_URL="${1:-https://github.com/domattioli/ADMESH-Domains.git}"
REPO_DIR="${2:-/workspace/$(basename "$REPO_URL" .git)}"
BASE_BRANCH="main"

echo "===> Routine setup starting"
echo "===> Repository: $REPO_URL"
echo "===> Target directory: $REPO_DIR"

# --------------------------------------------------------------------
# 1. Prerequisites
# --------------------------------------------------------------------
if ! command -v node >/dev/null 2>&1; then
  echo "===> Installing Node.js 20.x"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

# --------------------------------------------------------------------
# 2. Fresh clone at main
#    Note: ADMESH-Domains has a rich CLAUDE.md committed to the repo;
#    do NOT overwrite it. We append the stream-timeout block only if
#    it's missing.
# --------------------------------------------------------------------
echo "===> Cloning repository at $BASE_BRANCH"
rm -rf "$REPO_DIR"
mkdir -p "$(dirname "$REPO_DIR")"
git clone --branch "$BASE_BRANCH" "$REPO_URL" "$REPO_DIR"
cd "$REPO_DIR"

if ! grep -q "Stream Timeout Prevention" CLAUDE.md 2>/dev/null; then
  echo "===> Appending stream-timeout block to CLAUDE.md"
  cat >> CLAUDE.md <<'CLAUDEMD'

## Stream Timeout Prevention

1. Do each numbered task ONE AT A TIME. Complete one task fully,
   confirm it worked, then move to the next.
2. Never write a file longer than ~150 lines in a single tool call.
   If a file will be longer, write it in multiple append/edit passes.
3. Start a fresh session if the conversation gets long (20+ tool calls).
   The error gets worse as the session grows.
4. Keep individual grep/search outputs short. Use flags like
   --include and -l (list files only) to limit output size.
5. If you do hit the timeout, retry the same step in a shorter form.
   Don't repeat the entire task from scratch.
CLAUDEMD
fi

# --------------------------------------------------------------------
# 3. Smart branch logic — match spec-kit NNN-<short-name> convention.
#    Look for an existing NNN-* feature branch before creating a new one.
# --------------------------------------------------------------------
echo "===> Scanning for existing spec-kit feature branches..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "$CURRENT_BRANCH" = "$BASE_BRANCH" ]; then
  CANDIDATES=$(git branch -a --format='%(refname:short)' | \
    grep -E '^(origin/)?[0-9]{3}-' | \
    sed 's|^origin/||' | sort -u | head -5) || true

  if [ -n "$CANDIDATES" ]; then
    echo "===> Found candidate branches:"
    echo "$CANDIDATES"
    TARGET_BRANCH=$(echo "$CANDIDATES" | head -1)
    echo "===> Checking out: $TARGET_BRANCH"
    git checkout "$TARGET_BRANCH" 2>/dev/null || true
  else
    # Determine next free spec number from specs/ directory.
    # Use 10# prefix to force base-10 (avoid octal interpretation of leading zeros)
    NEXT_NUM=$(ls -d specs/[0-9][0-9][0-9]-* 2>/dev/null | \
      sed -E 's|specs/([0-9]{3}).*|\1|' | sort -n | tail -1)
    NEXT_NUM=$(printf "%03d" $(( 10#${NEXT_NUM:-0} + 1 )))
    NEW_BRANCH="${NEXT_NUM}-routine-$(date +%s)"
    echo "===> No existing spec-kit branches. Creating: $NEW_BRANCH"
    git checkout -b "$NEW_BRANCH"
  fi
fi

# --------------------------------------------------------------------
# 4. Python deps — resilient install.
#    Base [dev] for tests; [publish] for publisher dry-runs and the
#    site build (pyarrow, jinja2, matplotlib).
# --------------------------------------------------------------------
PIP_ARGS="--retries 5 --timeout 120 --prefer-binary"
pip_install() {
  local attempt=1
  local max_attempts=3
  while [ $attempt -le $max_attempts ]; do
    if python3 -m pip install $PIP_ARGS "$@"; then
      return 0
    fi
    echo "===> pip install attempt $attempt failed; sleeping $((attempt * 10))s"
    sleep $((attempt * 10))
    attempt=$((attempt + 1))
  done
  echo "===> pip install gave up after $max_attempts attempts: $*" >&2
  return 1
}

{
  pip_install --upgrade pip || true
  if [ -f pyproject.toml ]; then
    echo "===> Installing admesh-domains[dev,publish]"
    pip_install -e ".[dev,publish]" \
      || pip_install -e ".[dev]" \
      || pip_install -e . \
      || echo "===> WARN: pyproject install failed; continuing"
  fi
} || echo "===> WARN: python deps step had failures; session can install lazily"

# --------------------------------------------------------------------
# 5. GSD (retry-wrapped)
# --------------------------------------------------------------------
gsd_install() {
  local attempt=1
  while [ $attempt -le 3 ]; do
    if npx --yes get-shit-done-cc@latest --claude --global; then
      return 0
    fi
    echo "===> GSD install attempt $attempt failed; sleeping $((attempt * 10))s"
    sleep $((attempt * 10))
    attempt=$((attempt + 1))
  done
  echo "===> GSD install failed after 3 attempts" >&2
  return 1
}
gsd_install || echo "===> WARN: GSD not installed; /gsd-* commands will be missing"

# --------------------------------------------------------------------
# 6. Superpowers plugin pre-seed
# --------------------------------------------------------------------
mkdir -p "$HOME/.claude"
if command -v claude >/dev/null 2>&1 && claude plugin --help >/dev/null 2>&1; then
  echo "===> Installing superpowers plugin"
  claude plugin marketplace add obra/superpowers-marketplace || true
  claude plugin install superpowers@obra/superpowers-marketplace || true
else
  echo "===> Pre-seeding plugins.json"
  cat > "$HOME/.claude/plugins.json" <<'JSON'
{
  "marketplaces": {
    "obra/superpowers-marketplace": {
      "source": "github:obra/superpowers-marketplace"
    }
  },
  "plugins": {
    "superpowers": {
      "marketplace": "obra/superpowers-marketplace",
      "enabled": true
    }
  }
}
JSON
fi

# --------------------------------------------------------------------
# 7. Sanity output — always runs.
#    Validates the bundled manifest as a smoke check.
# --------------------------------------------------------------------
cd "$REPO_DIR"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
COMMIT=$(git rev-parse --short HEAD)
GSD_COUNT=$(ls ~/.claude/skills/ 2>/dev/null | grep -c '^gsd-' || echo 0)

echo ""
echo "===> Setup complete!"
echo "===> Repository: $(basename "$REPO_URL" .git)"
echo "===> Branch: $BRANCH @ $COMMIT"
echo "===> Directory: $REPO_DIR"
echo "===> GSD skills available: $GSD_COUNT"

if command -v admesh-domains >/dev/null 2>&1; then
  echo "===> Validating bundled manifest..."
  admesh-domains validate || echo "===> WARN: bundled manifest validation failed"
else
  echo "===> WARN: admesh-domains CLI not on PATH; in-session install needed"
fi

echo "===> Active spec folder: $(ls -d specs/[0-9][0-9][0-9]-* 2>/dev/null | tail -1 || echo 'none')"
echo "===> Guidelines: $REPO_DIR/CLAUDE.md and $REPO_DIR/.specify/memory/constitution.md"
