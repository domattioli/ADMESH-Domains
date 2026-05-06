# Plan: Tier 2 Auto-Suggester Implementation

**Phase:** 005  
**Issue:** #5  
**Release Track:** Code  
**Status:** In Execution  
**Owner:** auto-suggester team  

## Approach

Extend `admesh_domains/suggest.py` with boundary-polygon similarity matching. Add shapely to optional `[suggest]` extra. Route CLI `--tier 2` flag to new `Tier2Matcher` class. Tests validate boundary extraction on all 40 meshes + edge cases.

## Tasks (Atomic, Ordered by Dependency)

### Phase 1: Setup & Boundary Extraction (Foundational)

**Task 1.1: Create Tier2Matcher class stub**
- File: `admesh_domains/suggest.py`
- Add class `Tier2Matcher` with `__init__` and stubbed `match()` method
- Lazy-import shapely with clear `ImportError` message
- Tests: Verify lazy import error when shapely not installed
- ✓ Commit: "Add Tier2Matcher class stub (issue #5)"

**Task 1.2: Implement boundary extraction from fort.14**
- File: `admesh_domains/suggest.py`
- Method: `Tier2Matcher._extract_boundary(mesh_path)` → returns shapely Polygon
- Algorithm: Find all edges that appear in only 1 element; order them into a closed ring
- Handle edge cases: Holes (interior rings), multiple disconnected boundaries, degenerate cases
- Tests: Extract boundary from each of 40 existing meshes; validate closure + non-self-intersection
- ✓ Commit: "Implement boundary extraction (issue #5)"

### Phase 2: Similarity Metrics (Core Logic)

**Task 2.1: Implement Hausdorff distance**
- File: `admesh_domains/suggest.py`
- Method: `Tier2Matcher._hausdorff_distance(poly1, poly2)` → float
- Use shapely.hausdorff_distance() (no custom implementation needed)
- Tests: Known synthetic polygon pairs with verified distances
- ✓ Commit: "Implement Hausdorff distance metric (issue #5)"

**Task 2.2: Implement polygon IoU (Intersection over Union)**
- File: `admesh_domains/suggest.py`
- Method: `Tier2Matcher._polygon_iou(poly1, poly2)` → float ∈ [0, 1]
- Use shapely: `intersection().area / union().area`
- Handle zero-area cases (degenerate polygons)
- Tests: Known polygon pairs with verified IoU values
- ✓ Commit: "Implement polygon IoU metric (issue #5)"

**Task 2.3: Implement composite score**
- File: `admesh_domains/suggest.py`
- Method: `Tier2Matcher._composite_score(bbox_iou, boundary_iou)` → float
- Default: `(bbox_iou + boundary_iou) / 2` (equal weight)
- Config: Make tunable via constructor kwarg (future)
- Tests: Score calculation for known metrics
- ✓ Commit: "Implement composite score (issue #5)"

### Phase 3: Core Matching Logic

**Task 3.1: Implement match() main routine**
- File: `admesh_domains/suggest.py`
- Method: `Tier2Matcher.match(query_mesh, manifest)` → list[SuggestionResult]
- For each domain in manifest:
  - For each mesh in domain:
    - Extract boundaries (query vs. target)
    - Compute Hausdorff + polygon IoU
    - Compute composite score
  - Rank by composite score
- Return top N suggestions
- Tests: Query against all 40 meshes; verify ranking
- ✓ Commit: "Implement Tier2Matcher.match() (issue #5)"

### Phase 4: CLI Integration

**Task 4.1: Add --tier flag to CLI**
- File: `admesh_domains/cli.py`
- Command: `domain suggest --tier 1|2 <mesh_path>`
- Default: tier 1 (backward compat)
- Route to appropriate matcher class
- Error handling: Tier 2 without [suggest] extra → clear message
- Tests: CLI invocations for both tiers
- ✓ Commit: "Add --tier CLI flag (issue #5)"

### Phase 5: Optional Extra & Dependencies

**Task 5.1: Add [suggest] extra to pyproject.toml**
- File: `pyproject.toml`
- Add extra: `suggest = ["shapely>=2.0,<3.0"]`
- Keep base install pure-Python (no shapely)
- ✓ Commit: "Add [suggest] extra with shapely (issue #5)"

### Phase 6: Tests & Validation

**Task 6.1: Comprehensive unit tests**
- File: `tests/test_suggest_tier2.py` (new)
- Test coverage:
  - Boundary extraction: 40 real meshes + synthetic edge cases
  - Hausdorff distance: Known polygon pairs
  - Polygon IoU: Overlapping, non-overlapping, concentric
  - Composite score: Various bbox/boundary combinations
  - CLI integration: `--tier 2 <mesh>` (with and without extra)
  - Error handling: Missing shapely, degenerate inputs
- Target: >90% code coverage for new classes
- ✓ Commit: "Add comprehensive tests for Tier2Matcher (issue #5)"

**Task 6.2: Integration test**
- File: `tests/test_suggest_tier2.py`
- Test: Query each of 10 representative meshes against full manifest
- Verify: Tier 1 and Tier 2 produce different (sensible) rankings
- Edge case: Antimeridian meshes (Pacific domain)
- ✓ Commit: "Add integration tests (issue #5)"

### Phase 7: Validation & Cleanup

**Task 7.1: Run full test suite**
- Command: `pytest tests/ -q`
- Verify: All tests pass, no regressions in existing code
- Coverage: `pytest --cov=admesh_domains tests/`
- Fail if coverage < 90% for new code
- ✓ Commit: (none, validation only)

**Task 7.2: Validate manifest & schema**
- Command: `admesh-domains validate registry_data/manifest.toml`
- Verify: No manifest drift, schema version unchanged
- Verify: SCHEMA_VERSION not bumped (additive feature)
- ✓ Commit: (none, validation only)

### Phase 8: Version Bump & Release Prep

**Task 8.1: Bump version to next patch**
- Files: `pyproject.toml` + `admesh_domains/__init__.py`
- Old: 0.4.1 → New: 0.4.2 (patch bump)
- Reason: Code change (new API), same schema
- ✓ Commit: "Bump version to 0.4.2"

**Task 8.2: Commit version bump**
- ✓ Commit: "Bump version to 0.4.2 for Tier 2 feature"

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| Boundary extraction fails on non-convex coastlines | Medium | Test against real Pacific meshes; handle self-intersecting polygons |
| Shapely version incompatibility (2.x API churn) | Low | Pin to shapely>=2.0,<3.0; lazy import with version check |
| Composite score weights cause ranking inversions | Medium | Default to equal weights; make tunable for future tuning |
| Performance on large manifests | Low | Boundary extraction is O(mesh_size); matching is O(meshes²)—acceptable for 40 meshes |
| Manifest re-curation drift | Medium | Clearly document that Tier 2 scores may suggest manifest edits (post-code phase) |

## Verification

**Before commit:**
1. All tests pass: `pytest tests/ -q`
2. Manifest validation: `admesh-domains validate`
3. CLI works: `admesh-domains domain suggest --tier 2 <test_mesh>`
4. No schema changes: SCHEMA_VERSION unchanged
5. Coverage: New code >90%

**After commit (pre-release):**
1. Branch review (human)
2. Tag v0.4.2, push to main
3. release.yml triggers → PyPI + HF

## Deliverables

- ✓ `admesh_domains/suggest.py` — Tier2Matcher class (boundary extraction, Hausdorff, IoU, composite score, match routine)
- ✓ `admesh_domains/cli.py` — `--tier` flag for `domain suggest`
- ✓ `pyproject.toml` — `[suggest]` extra with shapely
- ✓ `tests/test_suggest_tier2.py` — Unit + integration tests
- ✓ Version bumps: pyproject.toml + __init__.py → 0.4.2
- ✓ PLAN.md (this file)
- ✓ No manifest.toml edits (data work, post-code)
- ✓ No SCHEMA_VERSION bump (additive feature)
