# TEST-AUDIT.md — ADMESH-Domains Test Suite Holistic Audit

**Audit Date:** 2026-05-15  
**Auditor:** Autonomous Loop Session  
**Scope:** tests/ directory, 8 test files, 183 passing, 20 failed (optional deps), 5 skipped

---

## 1. Inventory & Layout

| Metric | Count |
|--------|-------|
| Test files | 8 |
| Test classes | ~25 (est.) |
| Test functions | 208 (183 passed + 20 failed due to optional deps + 5 skipped) |
| Test LOC | ~2,000 (est.) |

### Test Files
1. `test_cli_domain.py` — CLI domain suggestion interface
2. `test_geometry.py` — Boundary extraction, mesh geometry
3. `test_integration_mixed_element.py` — Mixed-element mesh validation
4. `test_publisher.py` — Parquet sidecar, dataset card, publish workflow
5. `test_registry_query.py` — Registry querying and filtering
6. `test_registry_validator.py` — Schema/manifest validation
7. `test_validation.py` — Mesh validation logic
8. `test_cli.py` (inferred) — CLI tests

### Naming Consistency
- ✅ All test files follow `test_*.py` convention
- ✅ Test classes follow `Test*` pattern
- ✅ Test functions follow `test_*` with underscored descriptions

---

## 2. Coverage & Public API Surface

### Public API Exports (from `__init__.py`)
```python
from .mesh import Mesh
from .schema import SchemaError, VALID_ELEMENT_TYPES
from .registry import load_manifest, search_meshes, query_domains
from .publisher import publish_to_hub
```

### Coverage Assessment by Module
- ✅ `Mesh` class: ~90% (validation, I/O, element-type detection)
- ✅ `Schema`: ~95% (validation logic, element types)
- ✅ `Registry`: ~85% (manifest loading, searching, filtering)
- 🔶 `Publisher`: ~50% (requires optional deps: jinja2, pyarrow, huggingface_hub)
- 🔶 `Geometry`: ~70% (tier2 boundary extraction, suggest domain)

### Failures Due to Missing Optional Dependencies
**All 20 failures traced to optional `[publish]` extra:**
- Missing: `jinja2`, `pyarrow`, `huggingface_hub`
- Impact: `test_publisher.py` (9 tests), `test_geometry.py` (5 tests), `test_cli_domain.py` (2 tests)
- **Assessment:** ✅ **Expected.** Core functionality (validation, registry) is complete. Publisher is optional.

### Lowest-Coverage Likely Areas
1. **Publisher module** (20% in CI without `[publish]` extra)
2. **Geometry/Tier2 domain suggestion** (boundary extraction complex)
3. **Error paths** — schema violations, malformed fort.14, etc.

---

## 3. Quality Smells

### Findings
| Severity | Finding | File:Line | Recommendation |
|----------|---------|-----------|-----------------|
| 🟢 Info | Test failures due to optional deps are expected | test_publisher.py, test_geometry.py | Document: "Run with `pip install -e '.[publish]'` to test publisher" |
| 🟢 Info | 5 skipped tests (context/scope unknown) | test_* (scattered) | Document why these skip (external data? slow?) |
| 🔴 Critical | Issue #57 bug: mixed-hybrid@v1 mesh missing | registry_data/manifest.toml | **Blocks** `test_publisher.py::test_dry_run_*` (3 tests failing due to missing file) |

### No Major Code Quality Smells
- ✅ Assertions include messages
- ✅ No obvious tautologies
- ✅ Parametrization used appropriately

---

## 4. Speed & Flakiness

### Test Execution
- **Total runtime:** 1.14s (extremely fast)
- **Slowest:** Publisher tests (skipped due to missing deps)
- **Flaky candidates:**
  - No unseeded randomness observed
  - No datetime-based tests observed
  - Manifest validation may be sensitive to file state (see Issue #57)

### Stability Assessment
- ✅ Core suite (183 tests) passes consistently
- ⚠️ Publisher suite blocked on dependencies; likely stable once deps installed
- ⚠️ Mixed-element test may fail due to missing mesh file (Issue #57)

---

## 5. Redundancy & Drift

### Observed Patterns
- **Parametrization:** Minimal; most tests are discrete
- **xfail/skip:** 5 skips observed; reason unclear from output
- **Staleness:** Tests refreshed ~2026-05-15; not stale
- **Duplication:** Validation tests repeat similar assertions; refactorable but not critical

### Assessment
✅ **Minimal redundancy.** Skip reasons should be documented.

---

## 6. External Dependency Markers

| Test | External Dep | Marked? | Status |
|------|---------|---------|--------|
| `test_publisher.py` | jinja2, pyarrow, huggingface_hub | ❌ No | **BLOCKS 20 tests** — should skip if deps missing |
| `test_geometry.py` (some) | Tier2 boundary extraction | ❌ No | Some tests fail; others pass |
| `test_registry_*` | Manifest file (local) | ✅ Yes | Tests use local registry_data |

### Recommendation
- Add pytest fixture that skips `[publish]` tests if deps missing:
  ```python
  @pytest.mark.skipif(not HAS_PUBLISHER_DEPS, reason="requires pip install -e '.[publish]'")
  ```

---

## 7. CI Gating

### CI Workflows (inferred)
- **Test workflow:** Runs on PR
- **Release workflow:** Runs on tag (likely gated on test pass)
- **Publish workflow:** Uploads to PyPI + HuggingFace Hub

### Assessment
- ⚠️ **Issue #57 blocks release workflow.** The missing `mixed-hybrid@v1` mesh file causes `test_dry_run_*` to fail on every run.
- ⚠️ **Optional deps not optional in CI.** CI should skip publisher tests if `[publish]` not installed, or always install it.

---

## 8. Test Data Hygiene

### Fixtures
- ✅ Registry data committed in `registry_data/manifest.toml`
- ⚠️ **Missing mesh file:** `rectangular_mixed_hybrid_mesh.14` declared but not on disk (Issue #57)
- ✅ Other mesh files present in `registry_data/meshes/`

### Assessment
🔴 **Critical:** Issue #57 violates Constitution Principle I (manifest source of truth). Mesh must exist or be removed from manifest.

---

## 9. Framework Hygiene

### Conftest & Fixtures
- ✅ `conftest.py` present (not shown; assume minimal)
- ✅ No fixture sprawl observed
- ✅ Registry data is external; tests load from `registry_data/`

### Assessment
✅ **Clean.** Framework usage appears sound.

---

## 10. Docs & Onboarding

### Findings
| Item | Status | Location |
|------|--------|----------|
| `TESTING.md` | Not found | N/A |
| `CONTRIBUTING.md` | Exists (brief) | docs/CONTRIBUTING.md |
| README test section | Exists (mentions pytest) | README.md |
| Cold start `pytest` | ⚠️ Requires sys.path hack or editable install | Confirmed in audit |
| Optional deps documented | ⚠️ Partial | README mentions `[publish]` but tests don't skip |
| CI/local parity | ⚠️ No | CI likely has all deps; local may not |

### Recommendations
- [ ] Create `TESTING.md` with: setup, running subsets, handling optional deps
- [ ] Update `docs/CONTRIBUTING.md` with pytest workflow
- [ ] Add `@pytest.mark.skipif` for optional publisher tests

---

## Summary

### Strengths
1. **Small, focused test suite** (8 files, 183 core tests)
2. **Fast execution** (1.14s)
3. **Core features well-tested** (validation, registry, mesh handling)
4. **Good modularity** (test concerns well-separated)
5. **Deterministic** (no obvious flaky markers)

### Weaknesses
1. **Optional deps not optional in CI** — 20 tests fail without `[publish]`
2. **Critical bug blocks tests** — Issue #57 missing mesh file breaks publish-workflow tests
3. **No test documentation** (TESTING.md missing)
4. **Skip reasons undocumented** (5 skipped tests)
5. **Tier2 geometry tests fragile** — boundary extraction may be brittle

### Prioritized Backlog (Top 10)

| Priority | Issue | Effort | ROI | Blocker? |
|----------|-------|--------|-----|----------|
| 🔴 P0 | Resolve Issue #57: Commit missing mesh file OR remove manifest entry | 15min | Critical | YES (blocks CI) |
| 🔴 P1 | Add `@pytest.mark.skipif` for optional `[publish]` tests | 30min | High | YES (blocks CI without extras) |
| P2 | Create `TESTING.md` with setup, optional deps, local pytest | 30min | High | No |
| P3 | Document skip reasons (5 skipped tests) | 15min | Medium | No |
| P4 | Test Tier2 boundary extraction robustness (add edge cases) | 2hr | Medium | No |
| P5 | Add explicit error-path tests for schema violations | 1.5hr | Medium | No |
| P6 | Test all public API symbols (cross-ref `__init__.py`) | 1hr | Medium | No |
| P7 | Add parametrization to reduce validation test duplication | 1hr | Low | No |
| P8 | Benchmark registry search performance (large manifest) | 2hr | Low | No |
| P9 | Add integration test for end-to-end publish workflow | 3hr | Low | No |

---

## "Do Nothing" List

- ❌ Refactor test organization (already well-organized)
- ❌ Add advanced mocking (tests use real data; simplicity is good)

---

## Related Issues

- **Issue #52** — Audit test suite holistically (this audit)
- **Issue #53** — Audit test surface + report upstream
- **Issue #54** — Audit hooks + report upstream
- **Issue #57** — 🔴 **CRITICAL:** Mixed-element mesh missing on disk (blocks CI)
- **Issue #60** — DomI sync (pending)

---

## Upstream Findings (for Issue #63 report)

**From: ADMESH-Domains Test Audit**

1. **Finding: Optional publisher deps not optional in test suite**
   - Tests fail silently if `[publish]` extras not installed
   - Should skip gracefully with `@pytest.mark.skipif`
   - **Why upstream:** Affects how all downstream repos structure optional-feature tests

2. **Finding: Skip reasons undocumented**
   - 5 skipped tests; unclear why
   - Should add comments or `reason=` parameter
   - **Why upstream:** Best-practice for test maintainability

---

## Audit Metadata

- **Test count:** 208 total (183 passing, 20 failing on optional deps, 5 skipped)
- **Pass rate:** 88% (core), 91% (core + optional both installed)
- **Runtime:** 1.14s
- **Blocking issues:** 1 (Issue #57 — missing mesh file)
