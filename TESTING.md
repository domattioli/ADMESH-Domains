# Testing ADMESH-Domains

Guide for running and writing tests.

## Quick Start

```bash
# Install with optional dependencies
pip install -e ".[dev,publish]"

# Run tests
pytest -v

# Run core tests only (skip optional-dep failures)
pytest -m "not network" -v

# Run specific test
pytest tests/test_validation.py::test_mesh_validation -v
```

## Test Suite Overview

**8 test files | 183 passing | 20 failing (optional deps) | 5 skipped | Runtime: 1.14s**

### Test Files

| File | Purpose | Status |
|------|---------|--------|
| `test_validation.py` | Mesh schema validation | ✅ Pass |
| `test_registry_query.py` | Domain/mesh searching | ✅ Pass |
| `test_registry_validator.py` | Manifest integrity | ✅ Pass |
| `test_integration_mixed_element.py` | Mixed-element handling | ✅ Pass |
| `test_cli.py` | CLI interface | ✅ Pass (inferred) |
| `test_cli_domain.py` | Domain suggestion CLI | ⚠️ Requires `[publish]` |
| `test_geometry.py` | Boundary extraction, Tier2 | ⚠️ Requires `[publish]` |
| `test_publisher.py` | Parquet/dataset card/HF | ⚠️ Requires `[publish]` |

### Optional Dependencies

**20 failing tests require `[publish]` extra:**
```bash
pip install -e ".[publish]"  # Installs jinja2, pyarrow, huggingface_hub
pytest -v  # Now all tests pass
```

Tests gracefully skip if deps missing:
```bash
pytest -m "not network" -v  # Deselect network-requiring tests
```

## Running Tests

### All tests (with optional deps)
```bash
pip install -e ".[publish]"
pytest -v
```

### Core tests only (no optional deps)
```bash
pytest -m "not network" -v
```

### Specific test
```bash
pytest tests/test_validation.py::test_element_type_validation -v
```

### With coverage
```bash
pip install pytest-cov
pytest --cov=admesh_domains --cov-report=html tests/
```

## Writing Tests

### Test Template

```python
import pytest
from admesh_domains import Mesh, Domain, SchemaError

def test_mesh_validation():
    """Describe what is tested."""
    domain_data = {
        "name": "TestDomain",
        "meshes": [
            {
                "id": "test@v1",
                "filename": "test.14",
                "element_type": "triangle",
            }
        ]
    }
    domain = Domain(**domain_data)
    assert domain.validate() is None  # Returns None if valid
```

### Assertions

- **Always include failure messages:**
  ```python
  assert len(meshes) > 0, "No meshes found in registry"
  ```

- **Test public API:**
  ```python
  # Test exported symbols
  from admesh_domains import Mesh, load_manifest, search_meshes
  ```

- **Optional dep handling:**
  ```python
  @pytest.mark.skipif(not HAS_PUBLISH_DEPS, reason="requires pip install -e '.[publish]'")
  def test_publisher_output():
      # Test requiring jinja2, pyarrow, huggingface_hub
      pass
  ```

## Debugging Tests

### Print debug info
```bash
pytest -v -s tests/test_validation.py  # -s = show stdout
```

### Drop into debugger
```bash
pip install pytest-pdb
pytest --pdb tests/test_validation.py
```

## Known Issues

### 20 tests fail without `[publish]` extra

**Root cause:** Optional dependencies (jinja2, pyarrow, huggingface_hub) not installed.

**Fix:**
```bash
pip install -e ".[publish]"
pytest -v
```

**Or skip these tests:**
```bash
pytest -m "not network" -v
```

### 5 tests skipped

Skip reasons undocumented; see backlog item in TEST-AUDIT.md.

### Mixed-element validation sparse

Issue #41 added element_type schema. Only one mixed-element test fixture exists. Backlog: generate synthetic mixed-element meshes for deeper coverage.

## CI & Release Gates

- **Test gate:** Core tests must pass on all Python versions (3.9–3.12)
- **Publisher gate:** Full suite passes with `[publish]` before release
- **Data gate:** Manifest validates before mesh publish (publish-data.yml)

## Local Testing Workflows

### Validate manifest before publish
```bash
admesh-domains validate registry_data/manifest.toml
```

### Dry-run publisher (no HF upload)
```bash
admesh-domains publish --tag v0.0.0-dryrun --manifest registry_data/manifest.toml --dry-run --verbose
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'admesh_domains'"
```bash
pip install -e .
```

### Tests fail with "ModuleNotFoundError: jinja2" / "pyarrow" / "huggingface_hub"
```bash
pip install -e ".[publish]"
```

### "pytest: command not found"
```bash
pip install pytest
# Or with dev deps:
pip install -e ".[dev]"
```

### Test failures in publisher tests
- Ensure manifest is valid: `admesh-domains validate registry_data/manifest.toml`
- Check HF credentials if network tests fail: `huggingface-cli login`
- Mixed-element test file missing: See Issue #57 (resolved in main)

## Related

- Issue #52: Test suite holistic audit (TEST-AUDIT.md)
- Issue #53: Test surface audit + upstream report
- Issue #54: Hooks audit + upstream report
- TEST-AUDIT.md: Detailed audit findings + prioritized backlog
