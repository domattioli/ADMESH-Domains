#!/bin/bash
# pypi-publish: Publish package to PyPI
#
# Non-interactive PyPI publishing. Auto-detects credentials,
# package name, and version from pyproject.toml.
#
# Usage:
#   ./pypi-publish.sh                   # Auto-detect version
#   ./pypi-publish.sh --version 0.3.4   # Explicit version
#   ./pypi-publish.sh --repo /path/to   # Override project root

set -e

VERSION=""
PROJECT_ROOT="."

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --version) VERSION="$2"; shift 2 ;;
    --repo) PROJECT_ROOT="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ============================================================================
# DETECT PACKAGE NAME AND VERSION
# ============================================================================

if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
  echo "✗ pyproject.toml not found in $PROJECT_ROOT"
  exit 1
fi

# Extract package name
PACKAGE_NAME=$(sed -n '/^\[project\]/,/^\[/p' "$PROJECT_ROOT/pyproject.toml" | \
  grep "^name = " | sed 's/name = "\(.*\)"/\1/')

if [ -z "$PACKAGE_NAME" ]; then
  echo "✗ Could not detect package name from pyproject.toml"
  exit 1
fi

# Extract or use provided version
if [ -z "$VERSION" ]; then
  VERSION=$(grep "^version = " "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/')
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

# ============================================================================
# CREDENTIALS DETECTION
# ============================================================================

HAS_CREDS=0

# Check PYPI_TOKEN env var
if [ -n "$PYPI_TOKEN" ]; then
  HAS_CREDS=1
fi

# Check ~/.pypirc
if [ -f "$HOME/.pypirc" ] && grep -q "password" "$HOME/.pypirc"; then
  HAS_CREDS=1
fi

if [ $HAS_CREDS -eq 0 ]; then
  echo "✗ No PyPI credentials found. Create ~/.pypirc or set PYPI_TOKEN"
  exit 1
fi

# Validate credentials work
if ! twine check "$PROJECT_ROOT/dist"/* 2>/dev/null | grep -q "passed"; then
  echo "⚠ twine check failed, will attempt upload anyway"
fi

# ============================================================================
# BUILD IF NEEDED
# ============================================================================

DIST_DIR="$PROJECT_ROOT/dist"
EXPECTED_WHL="$DIST_DIR/${PACKAGE_NAME//-/_}-$VERSION-py3-none-any.whl"
EXPECTED_TAR="$DIST_DIR/${PACKAGE_NAME}-$VERSION.tar.gz"

# Check if we need to build (look for version-specific packages)
if [ ! -f "$EXPECTED_WHL" ] || [ ! -f "$EXPECTED_TAR" ]; then
  if [ ! -d "$DIST_DIR" ]; then
    mkdir -p "$DIST_DIR"
  fi

  # Attempt to build
  cd "$PROJECT_ROOT"
  python -m build 2>/dev/null || {
    echo "✗ Failed to build packages"
    exit 1
  }
  cd - > /dev/null
fi

# ============================================================================
# VALIDATE DISTRIBUTION FILES
# ============================================================================

if [ ! -d "$DIST_DIR" ] || [ -z "$(ls "$DIST_DIR"/${PACKAGE_NAME}* 2>/dev/null)" ]; then
  echo "✗ No distribution packages found for $PACKAGE_NAME in $DIST_DIR"
  exit 1
fi

# ============================================================================
# UPLOAD WITH RETRY
# ============================================================================

MAX_RETRIES=3
RETRY=0
UPLOAD_SUCCESS=0

while [ $RETRY -lt $MAX_RETRIES ]; do
  if twine upload "$DIST_DIR/${PACKAGE_NAME}-${VERSION}"* --skip-existing 2>/dev/null; then
    UPLOAD_SUCCESS=1
    break
  fi

  RETRY=$((RETRY + 1))
  if [ $RETRY -lt $MAX_RETRIES ]; then
    SLEEP_TIME=$((2 ** RETRY))
    sleep "$SLEEP_TIME"
  fi
done

if [ $UPLOAD_SUCCESS -eq 0 ]; then
  echo "✗ PyPI upload failed after $MAX_RETRIES attempts"
  exit 1
fi

# ============================================================================
# VERIFY ON PYPI
# ============================================================================

PYPI_URL="https://pypi.org/project/$PACKAGE_NAME/$VERSION/"

# Check if package appears on PyPI
MAX_VERIFY_RETRIES=5
VERIFY_RETRY=0
FOUND=0

while [ $VERIFY_RETRY -lt $MAX_VERIFY_RETRIES ]; do
  if curl -s "$PYPI_URL" | grep -q "Release history"; then
    FOUND=1
    break
  fi
  VERIFY_RETRY=$((VERIFY_RETRY + 1))
  if [ $VERIFY_RETRY -lt $MAX_VERIFY_RETRIES ]; then
    sleep 2
  fi
done

if [ $FOUND -eq 0 ]; then
  echo "⚠ Package upload succeeded but not yet visible on PyPI (may take a few seconds)"
fi

# ============================================================================
# SUCCESS
# ============================================================================

echo "✅ PyPI Published: $PYPI_URL"
exit 0
