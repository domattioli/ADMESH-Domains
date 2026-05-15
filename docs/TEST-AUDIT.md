# Test Surface Audit — ADMESH-Domains

**Snapshot:** 2026-05-15
**Branch:** `daily-issue-fixing` @ `bf5e247` (post-DomI@9dd6491 sync)
**Issues:** [`#52`](https://github.com/domattioli/ADMESH-Domains/issues/52) (holistic) + [`#53`](https://github.com/domattioli/ADMESH-Domains/issues/53) (DomI mirror, upstream → `domattioli/DomI#63`)

---

## 1. Surface inventory

### 1.1 Test files (`tests/`)

| File | Test count | LOC focus | Status |
|---|---|---|---|
| `test_cli_domain.py` | 9 | CLI `admesh-domains suggest`, JSON output, Tier-2 ranking | All pass |
| `test_compare_feature.py` | 61 | Mesh comparison site build + UI surface | All pass |
| `test_geometry.py` | 42 | Bounding box, suggest-domain, Tier-2 boundary extraction | **2 fail** (cluster A) |
| `test_publisher.py` | 19 | HuggingFace publisher dry-run, dedup, deletion detection | **3 fail** (cluster B) |
| `test_registry_query.py` | 36 | `get_mesh`, bounding-box lookups, region/application filters | **3 fail** (cluster A) |
| `test_registry_validator.py` | 24 | Manifest validation, schema primitives | **2 fail** (cluster C) |
| **Total** | **191 collected** | — | **181 pass / 10 fail** |

Test config: `pyproject.toml` declares `pytest>=7.0`, `pytest-cov>=4.0` as test deps. No `pytest.ini`, no `[tool.pytest.ini_options]` block — defaults rule.

### 1.2 Fixtures

- `tests/conftest.py:1-30` — two session-scoped fixtures: `dev_manifest_path`, `loaded_manifest`. Loads from real `registry_data/manifest.toml`; **tests depend on registry state**, not isolated fixture state. (Tradeoff: realistic, but couples test pass/fail to manifest content drift.)
- `tests/fixtures/registry/` — committed fixture directory. Used by tests that need a minimal manifest separate from the live one.

### 1.3 Public API surface vs test coverage

Exported from `admesh_domains/__init__.py:30-55` (16 symbols):

| Symbol | Tested? | Where |
|---|---|---|
| `__version__` | No (string constant; would only catch a typo) | — |
| `SCHEMA_VERSION` | No (constant) | — |
| `BoundingBox` | Partial | `test_geometry.py`, `test_registry_query.py` |
| `Domain` | Partial | `test_registry_validator.py`, indirect |
| `Mesh` | Partial | `test_publisher.py`, `test_registry_query.py` |
| `RegistryMetadata` | **No** | — |
| `SchemaError` | **No direct test** | (raised inside other paths) |
| `Manifest` | Yes | `test_registry_validator.py`, `test_registry_query.py` |
| `ManifestNotFoundError` | **No** | — |
| `ManifestValidationError` | Yes | `test_registry_validator.py:89,104` (currently *failing* — see cluster C) |
| `load_manifest` | Yes | indirect via conftest fixture |
| `find_domains` | Yes | `test_registry_query.py` |
| `find_meshes` | Yes | `test_registry_query.py` |
| `get_domain` | Yes | `test_registry_query.py` |
| `get_mesh` | **Broken** | `test_registry_query.py:113,157,163` + 2 callers in `test_geometry.py` (cluster A) |
| `list_applications` | Yes | `test_registry_query.py` |
| `list_domains` | Yes | `test_registry_query.py` |
| `list_regions` | Yes | `test_registry_query.py` |
| `test_meshes` | Yes | `test_registry_query.py` |

**Coverage gaps:** `RegistryMetadata`, `ManifestNotFoundError`, `SchemaError` have no direct asserts. Low severity individually; together they signal that error-path coverage is lighter than happy-path coverage.

### 1.4 CI workflows (`.github/workflows/`)

| Workflow | Trigger | What it gates | Tests run? |
|---|---|---|---|
| `validate-pr.yml` | every PR + push to `main` | `admesh-domains validate` + `pytest tests/ -v` matrix on Py 3.9/3.11/3.12 | **Yes** (the test gate) |
| `release.yml` | tag push `v[0-9]+.[0-9]+.[0-9]+` | PyPI upload → HF publish | **No** — tests are NOT re-run on tag |
| `publish-data.yml` | push to `main` touching `registry_data/manifest.toml` or `registry_data/meshes/**` | HF data tag `data-YYYY-MM-DD-<sha7>` | **No** |
| `pages.yml` | push to `main` touching `site/**`, manifest, or `scripts/build_site.py` | Build + deploy GitHub Pages | **No** |

**Gate analysis:**
- `validate-pr.yml` is the only test-gating workflow. It runs on every PR — protects `main`.
- `release.yml` does **NOT** re-run tests. It trusts that `validate-pr.yml` passed on `main` before the tag was cut. **Risk:** if tests are red on `main` (already true today via the 10 failures from `daily-issue-fixing` being merged-in pieces), `release.yml` will publish anyway.
- `publish-data.yml` does **NOT** run tests. Defensible for pure-data updates, but any manifest schema drift would slip through.
- 4 workflows / 6 test files / 191 tests: ratio is healthy for a project this size. No redundant runners.

### 1.5 Slowest tests (`pytest --durations=10`)

| Duration | Test |
|---|---|
| 5.01s | `tests/test_geometry.py::TestTier2SuggestDomain::test_tier2_same_mesh_ranks_first` |
| 4.72s | `tests/test_cli_domain.py::TestDomainSuggest::test_tier2_same_mesh_ranks_first` |
| 4.64s | `tests/test_cli_domain.py::TestDomainSuggest::test_tier2_json_includes_boundary_metrics` |
| 0.23s | `tests/test_geometry.py::TestTier2BoundaryExtraction::test_extract_boundary_from_fort14` |
| <0.10s | All remaining 187 tests |

Three Tier-2 tests dominate runtime (~14s of ~15s total). They run real shapely boundary extraction on a full fort.14. Acceptable for a 15s suite; would warrant `@pytest.mark.slow` markers if the suite grew past ~60s.

---

## 2. Findings (severity-tagged, with file:line refs)

### 2.1 Critical — broken tests gating a release that doesn't re-run them

**[C1] Cluster A — `Domain.get_mesh` method missing (5 failures).**
- `admesh_domains/query.py:164` calls `d.get_mesh(mesh_id)` where `d` is a `Domain` instance.
- `admesh_domains/schema.py:205-289` (the `Domain` dataclass) defines `validate`, `to_dict`, `from_dict`, and property `has_meshes` — **no `get_mesh` method**.
- Affected tests: `test_registry_query.py:113,157,163`, `test_geometry.py:138-145` (two `TestSuggestDomain` cases).
- Introduced by commit `d768e78 fix: restore schema.py from main (daily-issue-fixing was truncated)` — the restore reverted a method that `query.py` still expects. Cross-file refactor regression.
- Severity: **critical**. `get_mesh` is a top-level public export (`admesh_domains/__init__.py`); a `pip install`-er calling `admesh_domains.get_mesh(...)` hits an `AttributeError`.
- Filed: follow-up issue (see Step 9 of Run Summary).

**[C2] Cluster B — `mixed-hybrid@v1` mesh file missing on disk (3 failures).**
- `registry_data/manifest.toml` declares `Rectangles/mixed-hybrid@v1` with `filename = "rectangular_mixed_hybrid_mesh.14"`.
- `registry_data/meshes/` contains `rectangular_mesh_{quadrilateral,triangle}1.14` and `rectangular_skewed_mesh_*.14` — **but no `rectangular_mixed_hybrid_mesh.14`**.
- Affected tests: `test_publisher.py:140,155,164` (all `TestPublishDryRun` cases — fail before assertion via `PublishValidationError`).
- Introduced by commit `dfa4d59 Resolve issue #41: clarify/test mixed-element mesh registration` — manifest entry added without the actual mesh file.
- **Constitution Principle I violation:** manifest is source of truth, but referenced file must exist. Drift between two parts of the source of truth.
- Severity: **critical**. Publisher dry-run is the last gate before HF publish. With this broken, every `admesh-domains publish --dry-run` will refuse — masking real publish-time errors.
- Filed: follow-up issue.

**[C3] Cluster C — Validator regressions (2 failures).**
- `test_registry_validator.py:89` — `test_duplicate_mesh_ids_in_domain_fail` expects `pytest.raises(ManifestValidationError)`; live code does not raise.
- `test_registry_validator.py:104` — `test_domain_with_slash_in_name_fails` expects same; live code does not raise.
- Both validations are **schema invariants** (duplicate IDs make `get_mesh` ambiguous; slash-in-name breaks the `Domain/Mesh` composite-id grammar).
- Likely cause: `d768e78 fix: restore schema.py from main` restored a version of validation that predates these two rules.
- Severity: **critical**. Two schema invariants are now unenforced — bad manifests can be committed without `admesh-domains validate` rejecting them.
- Filed: follow-up issue.

### 2.2 High — release flow has no test re-gate

**[H1] `release.yml` does not re-run `pytest`.** It trusts `validate-pr.yml` on `main`. Today, `daily-issue-fixing` carries 10 red tests; if those merge to `main` without a CI run that catches them, the next tag push will ship a wheel against a red baseline. Suggested fix: add `pytest tests/ -q` as a release-job pre-step (or have `release.yml` `needs:` a fresh `test` job). Effort: low.

**[H2] No public-API exhaustive test.** No test iterates `admesh_domains.__all__` and asserts each symbol imports cleanly. Would catch the `get_mesh` regression at commit time. Effort: ~10 lines.

**[H3] `validate-pr.yml` matrix is Py 3.9 / 3.11 / 3.12.** Python 3.10 was just dropped from classifiers (#42), aligning the test matrix with the supported set — but 3.13 is generally available and not yet in the matrix. Defer until stability is verified upstream.

### 2.3 Medium — coverage and discoverability

**[M1] No `pytest-cov` invocation in CI.** `pytest-cov>=4.0` is declared in deps but never run by any workflow. Coverage data is unmeasured. Add `pytest --cov=admesh_domains --cov-report=term-missing` to `validate-pr.yml` after the regular test step. Effort: 2 lines.

**[M2] `RegistryMetadata`, `ManifestNotFoundError`, `SchemaError` exports have no direct assertion.** Either remove from `__all__` (signal: not part of the supported surface) or add a minimal smoke test per symbol. Effort: ~15 lines.

**[M3] Test-vs-manifest coupling.** `loaded_manifest` fixture loads the live `registry_data/manifest.toml`. Any future mesh removal/add will silently change test outcomes that depend on specific IDs (`WNAT/hagen@v1`, `ChesapeakeBay/default@v1` are hard-coded in 6+ tests). Two options: (a) commit a frozen `tests/fixtures/registry/manifest-fixed.toml` and use it for ID-specific tests; (b) parametrize tests over `manifest.all_meshes()` to remove the coupling. (a) is lower-effort and recommended.

**[M4] No `@pytest.mark.slow` markers.** The 3 Tier-2 tests at >4s each are not marked. Today the suite is fast enough not to matter; flag for re-evaluation if total runtime exceeds ~60s.

### 2.4 Low — hygiene

**[L1] `tests/__pycache__/` shows in `ls`.** Already gitignored — no commit risk. Listed for completeness only.

**[L2] No `TESTING.md` or `CONTRIBUTING.md` section explaining how to run tests locally.** A 5-line block (`pip install -e ".[dev,publish]"; pytest`) in `CONTRIBUTING.md` would cover the contributor onboarding gap.

**[L3] No version-bump checklist.** A pre-release `pytest` test that ensures `__version__` in `__init__.py` matches `pyproject.toml` version would catch a forgotten bump. Effort: ~5 lines. Defer until evidence of a missed bump.

**[L4] `test_meshes()` helper exported as part of public API.** Public API symbol starts with `test_` — pytest collects it. `pyproject.toml` doesn't disable that collection. Resolved historically by `a951210 fix: ... suppress test_meshes pytest collection`, but worth recording so a future refactor doesn't reintroduce the trap.

---

## 3. Prioritized backlog (top 10)

| Rank | Finding | Effort | Impact |
|---|---|---|---|
| 1 | [C1] Add `Domain.get_mesh(mesh_id)` method to `schema.py` | XS (~10 lines) | Unblocks 5 tests; fixes a broken public-API export |
| 2 | [C2] Commit `registry_data/meshes/rectangular_mixed_hybrid_mesh.14` OR remove the manifest entry | XS / S (depends on intent of #41) | Unblocks 3 tests; restores Principle I |
| 3 | [C3] Restore `ManifestValidationError` for duplicate mesh IDs + slash-in-domain-name | S (~20 lines in `manifest.py`) | Unblocks 2 tests; re-locks schema invariants |
| 4 | [H1] Add `pytest tests/ -q` pre-step in `release.yml` | XS (5 lines YAML) | Prevents red-tagged release |
| 5 | [H2] Add public-API exhaustive test | XS (~10 lines) | Catches cross-file refactor regressions like C1 |
| 6 | [M3] Frozen `tests/fixtures/registry/manifest-fixed.toml` for ID-specific tests | S (~30 lines fixture + 6 test updates) | Decouples tests from live registry drift |
| 7 | [M1] Add `--cov=admesh_domains` to CI | XS | Measurable coverage; baseline for future work |
| 8 | [M2] Smoke tests for `RegistryMetadata`, `ManifestNotFoundError`, `SchemaError` | XS | Closes silent gaps in `__all__` coverage |
| 9 | [L2] `CONTRIBUTING.md` test-run section | XS | Onboarding |
| 10 | [L4] Codify `test_meshes` non-collection in `conftest.py` (not just `pyproject.toml`) | XS | Defense in depth |

---

## 4. "Do nothing" list

| Smell | Why intentional |
|---|---|
| Three >4s Tier-2 tests | They exercise real shapely boundary extraction on a real fort.14. Marking them slow buys little when the suite is 15s total. |
| Tests depend on live `registry_data/manifest.toml` | Conscious tradeoff: realism over isolation. See M3 — only ID-specific tests need de-coupling, not the whole suite. |
| `release.yml` doesn't run `validate-pr.yml` | They have different triggers; reusing would require a callable workflow refactor. Adding a single pytest step in `release.yml` (H1) is simpler. |
| No `pytest.ini` | Pyproject `[project.optional-dependencies]` handles deps; no config keys needed yet. Add `[tool.pytest.ini_options]` only when a marker / addopt is justified. |

---

## 5. Upstream-relevant (filed on DomI#63)

Findings that need a DomI change rather than a local fix:

1. **`pytest-cov` not idiomatic across consumers.** ADMESH-Domains declares it but never invokes it. DomI's TEST-AUDIT.md probably has the same observation — a `gh-test-coverage` workflow snippet that every consumer can opt into would standardize. Upstream because it affects all 7 consumers identically.
2. **No DomI skill for "public API parity test".** Issue [H2] above is a class of bug every consumer has. A `validate-public-api` skill that reads `__init__.py::__all__` and asserts every symbol is importable would prevent the cross-file refactor regression that produced C1 here. Vote-worthy.
3. **Release workflow re-test gate.** DomI ships `release.yml` patterns elsewhere; standardize the "run tests before tagging" step so consumers don't have to remember.

The rest of the findings here are **local-only** (file follow-up bug issues on this repo, not on DomI).

---

## 6. References

- This audit: `domattioli/ADMESH-Domains#52`, `#53`
- Upstream inbox: `domattioli/DomI#63`
- Companion hooks audit: `docs/HOOKS-AUDIT.md`, `domattioli/ADMESH-Domains#54`
- Workflows: `.github/workflows/{pages,publish-data,release,validate-pr}.yml`
- Constitution: `.specify/memory/constitution.md`
