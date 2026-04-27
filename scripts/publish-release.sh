#!/bin/bash
# publish-release: Automated GitHub release creation + PyPI publishing
#
# Usage:
#   ./publish-release.sh [VERSION] [OPTIONS]
#
# OPTIONS:
#   --no-pypi         Skip PyPI upload (GitHub release only)
#   --draft           Create GitHub release as draft
#   --repo REPO       Override GitHub repo (owner/name)
#   --notes FILE      Override release notes source
#   --help            Show this message
#
# Examples:
#   ./publish-release.sh                    # Auto-detect version, full release
#   ./publish-release.sh 0.3.4              # Explicit version
#   ./publish-release.sh 0.3.4 --draft      # Draft release
#   ./publish-release.sh 0.3.4 --no-pypi    # GitHub only

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Defaults
VERSION=""
SKIP_PYPI=0
DRAFT=0
REPO="domattioli/admesh-domains"
NOTES_FILE=""
DRY_RUN=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-pypi) SKIP_PYPI=1; shift ;;
    --draft) DRAFT=1; shift ;;
    --repo) REPO="$2"; shift 2 ;;
    --notes) NOTES_FILE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --help) show_help; exit 0 ;;
    -*)
      echo -e "${RED}Error: Unknown option $1${NC}"
      exit 1
      ;;
    *)
      if [ -z "$VERSION" ]; then
        VERSION="$1"
      else
        echo -e "${RED}Error: Multiple versions specified${NC}"
        exit 1
      fi
      shift
      ;;
  esac
done

# Helper functions
log() { echo -e "${BLUE}→${NC} $*"; }
success() { echo -e "${GREEN}✓${NC} $*"; }
error() { echo -e "${RED}✗${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }

show_help() {
  head -20 "$0" | tail -18
}

# Auto-detect version from pyproject.toml
if [ -z "$VERSION" ]; then
  log "Auto-detecting version from pyproject.toml..."
  if [ ! -f "pyproject.toml" ]; then
    error "pyproject.toml not found in current directory"
    exit 1
  fi
  VERSION=$(grep "^version = " pyproject.toml | sed 's/version = "\(.*\)"/\1/')
  if [ -z "$VERSION" ]; then
    error "Could not parse version from pyproject.toml"
    exit 1
  fi
  success "Version: $VERSION"
fi

# Validate version format (semantic versioning)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  error "Invalid version format: $VERSION (expected X.Y.Z)"
  exit 1
fi

TAG="v$VERSION"
log "Release tag: $TAG"

# ============================================================================
# VALIDATION PHASE
# ============================================================================

log "Validating prerequisites..."

# Check gh CLI
if ! command -v gh &>/dev/null; then
  error "gh CLI not found. Install with: https://cli.github.com"
  exit 1
fi
success "gh CLI found"

# Check gh authentication
if ! gh auth status &>/dev/null; then
  error "gh CLI not authenticated"
  echo "Authenticate with: gh auth login"
  exit 1
fi
success "gh CLI authenticated"

# Check git state
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  error "Not in a git repository"
  exit 1
fi

if ! git diff-index --quiet HEAD --; then
  error "Working directory has uncommitted changes"
  echo "Commit or stash changes before releasing"
  exit 1
fi
success "Git working directory clean"

# Check if tag already exists
if git rev-parse "$TAG" &>/dev/null; then
  error "Tag $TAG already exists"
  exit 1
fi
success "Tag $TAG does not exist"

# Check for distribution packages
if [ $SKIP_PYPI -eq 0 ]; then
  if ! command -v twine &>/dev/null; then
    error "twine not found. Install with: pip install twine"
    exit 1
  fi
  success "twine found"

  if [ ! -d "dist" ] || [ -z "$(ls dist/*.{whl,tar.gz} 2>/dev/null)" ]; then
    error "No distribution packages found in dist/"
    echo "Build packages with: python -m build"
    exit 1
  fi
  success "Distribution packages found"
fi

# Extract release notes
log "Extracting release notes..."
if [ -n "$NOTES_FILE" ]; then
  if [ ! -f "$NOTES_FILE" ]; then
    error "Notes file not found: $NOTES_FILE"
    exit 1
  fi
  RELEASE_NOTES=$(cat "$NOTES_FILE")
  success "Notes from: $NOTES_FILE"
elif [ -f "CHANGELOG.md" ]; then
  # Extract notes for this version from CHANGELOG.md
  # Format: ## [X.Y.Z] - YYYY-MM-DD
  RELEASE_NOTES=$(sed -n "/^## \[$VERSION\]/,/^## \[/p" CHANGELOG.md | head -n -1)
  if [ -z "$RELEASE_NOTES" ]; then
    warn "No CHANGELOG entry for version $VERSION"
    RELEASE_NOTES="Release version $VERSION"
  else
    success "Notes from CHANGELOG.md"
  fi
else
  warn "CHANGELOG.md not found, using generic notes"
  RELEASE_NOTES="Release version $VERSION"
fi

# ============================================================================
# EXECUTION PHASE
# ============================================================================

log "Creating release..."

# Create git tag
if [ $DRY_RUN -eq 0 ]; then
  git tag "$TAG" -m "Release $VERSION"
  git push origin "$TAG"
  success "Git tag created and pushed: $TAG"
else
  success "[DRY RUN] Would create and push tag: $TAG"
fi

# Create GitHub release
GH_OPTS="--title Release $VERSION"
GH_OPTS="$GH_OPTS --notes $(echo "$RELEASE_NOTES" | sed 's/"/\\"/g' | tr '\n' ' ')"
if [ $DRAFT -eq 1 ]; then
  GH_OPTS="$GH_OPTS --draft"
fi

if [ $DRY_RUN -eq 0 ]; then
  RELEASE_URL=$(gh release create "$TAG" $GH_OPTS --repo "$REPO" 2>&1 | grep "created" | grep -oP 'https://[^\s]+' || echo "")

  if [ -z "$RELEASE_URL" ]; then
    RELEASE_URL="https://github.com/$REPO/releases/tag/$TAG"
  fi
  success "GitHub release created"
  success "Release URL: $RELEASE_URL"
else
  RELEASE_URL="https://github.com/$REPO/releases/tag/$TAG"
  success "[DRY RUN] Would create GitHub release"
  success "[DRY RUN] Release URL: $RELEASE_URL"
fi

# Upload to PyPI
if [ $SKIP_PYPI -eq 0 ]; then
  log "Uploading to PyPI..."
  if [ $DRY_RUN -eq 0 ]; then
    # Check for .pypirc or ask for credentials
    if twine upload dist/* --skip-existing 2>&1 | grep -q "ERROR"; then
      error "PyPI upload failed"
      exit 1
    fi
    PYPI_URL="https://pypi.org/project/admesh-domains/$VERSION/"
    success "PyPI upload complete"
    success "PyPI URL: $PYPI_URL"
  else
    success "[DRY RUN] Would upload to PyPI"
    PYPI_URL="https://pypi.org/project/admesh-domains/$VERSION/"
  fi
else
  PYPI_URL=""
  warn "Skipping PyPI upload (--no-pypi)"
fi

# ============================================================================
# SUMMARY
# ============================================================================

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Release $VERSION published successfully!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}GitHub Release:${NC}"
echo "  $RELEASE_URL"
echo ""
if [ -n "$PYPI_URL" ]; then
  echo -e "${BLUE}PyPI Package:${NC}"
  echo "  $PYPI_URL"
  echo ""
fi
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Verify GitHub release at: $RELEASE_URL"
if [ -n "$PYPI_URL" ]; then
  echo "  2. Verify PyPI at: $PYPI_URL"
  echo "  3. Test installation: pip install --upgrade admesh-domains==$VERSION"
fi
echo ""

exit 0
