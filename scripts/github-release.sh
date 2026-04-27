#!/bin/bash
# github-release: Create GitHub release with release notes
#
# Non-interactive GitHub release creation. Auto-detects credentials,
# version, repo, and extracts release notes from CHANGELOG.md.
#
# Usage:
#   ./github-release.sh                    # Auto-detect version
#   ./github-release.sh --version 0.3.4    # Explicit version
#   ./github-release.sh --repo owner/name  # Override repo

set -e

VERSION=""
REPO=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --version) VERSION="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ============================================================================
# CREDENTIALS DETECTION
# ============================================================================

# Check gh CLI auth
if ! gh auth status &>/dev/null; then
  echo "✗ GitHub not authenticated. Run: gh auth login"
  exit 1
fi

# Validate token works
if ! gh api user &>/dev/null; then
  echo "✗ GitHub token invalid or expired"
  exit 1
fi

# ============================================================================
# AUTO-DETECT VERSION
# ============================================================================

if [ -z "$VERSION" ]; then
  if [ ! -f "pyproject.toml" ]; then
    echo "✗ pyproject.toml not found"
    exit 1
  fi
  VERSION=$(grep "^version = " pyproject.toml | sed 's/version = "\(.*\)"/\1/')
  if [ -z "$VERSION" ]; then
    echo "✗ Could not detect version from pyproject.toml"
    exit 1
  fi
fi

# Validate version format
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "✗ Invalid version format: $VERSION (expected X.Y.Z)"
  exit 1
fi

TAG="v$VERSION"

# ============================================================================
# AUTO-DETECT REPO
# ============================================================================

if [ -z "$REPO" ]; then
  REPO=$(git remote get-url origin | sed 's|.*/\([^/]*\)/\([^/]*\)\.git$|\1/\2|')
  if [ -z "$REPO" ]; then
    echo "✗ Could not detect repo from git remote"
    exit 1
  fi
fi

# ============================================================================
# EXTRACT RELEASE NOTES
# ============================================================================

RELEASE_NOTES="Release $VERSION"
if [ -f "CHANGELOG.md" ]; then
  NOTES=$(sed -n "/^## \[$VERSION\]/,/^## \[/p" CHANGELOG.md | head -n -1)
  if [ -n "$NOTES" ]; then
    RELEASE_NOTES="$NOTES"
  fi
fi

# ============================================================================
# VALIDATE DISTRIBUTION FILES
# ============================================================================

if [ ! -d "dist" ] || [ -z "$(ls dist/*.{whl,tar.gz} 2>/dev/null)" ]; then
  echo "✗ No distribution packages found in dist/"
  exit 1
fi

# ============================================================================
# CREATE GITHUB RELEASE
# ============================================================================

# Escape quotes and convert newlines to spaces for gh CLI
NOTES_ESCAPED=$(echo "$RELEASE_NOTES" | sed 's/"/\\"/g' | tr '\n' ' ')

if ! gh release create "$TAG" \
  --title "Release $VERSION" \
  --notes "$NOTES_ESCAPED" \
  --repo "$REPO" \
  dist/* 2>/dev/null; then
  echo "✗ Failed to create GitHub release"
  exit 1
fi

# ============================================================================
# SUCCESS
# ============================================================================

RELEASE_URL="https://github.com/$REPO/releases/tag/$TAG"
echo "✅ GitHub Release: $RELEASE_URL"
exit 0
