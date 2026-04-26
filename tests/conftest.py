"""Pytest fixtures shared across the test suite."""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_MANIFEST = REPO_ROOT / "registry_data" / "manifest.toml"


@pytest.fixture(scope="session")
def dev_manifest_path() -> Path:
    """Path to the dev-checkout manifest (with mesh files alongside)."""
    assert DEV_MANIFEST.exists(), f"missing dev manifest at {DEV_MANIFEST}"
    return DEV_MANIFEST


@pytest.fixture(scope="session")
def loaded_manifest(dev_manifest_path: Path):
    """Parsed Manifest from the dev checkout."""
    from admesh_domains import load_manifest
    return load_manifest(dev_manifest_path)
