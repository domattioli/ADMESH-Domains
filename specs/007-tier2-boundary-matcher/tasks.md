# Tasks: Tier 2 Auto-Suggester (Boundary Polygon Matching)

**Date**: 2026-05-06 | **Branch**: `daily-issue-fixing` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Task List (Ordered by Dependency)

### Phase 0: Research & Sanity Checks

- [ ] **T-001**: Spike: Verify `shapely.Polygon.hausdorff_distance()` API and performance with 50K-node boundary. Document result.
- [ ] **T-002**: Spike: Test shapely's handling of invalid/self-intersecting geometries. Confirm graceful degradation.
- [ ] **T-003**: Spike: Examine existing fort.14 parser in `geometry.py`. Identify code to extract element-edge connectivity.
- [ ] **T-004**: Spike: Prototype graceful ImportError handling for shapely. Verify message clarity.

### Phase 1: Boundary Extraction & Polygon Ops

- [ ] **T-010**: Implement `geometry.extract_boundary_polygon(mesh_path) -> Polygon | None`
  - Acceptance: parses fort.14, traces unique edges, returns closed `shapely.Polygon` or `None` if invalid
  - Files: `admesh_domains/geometry.py`
  - Depends on: T-003
  
- [ ] **T-011**: Implement `geometry.polygon_iou(poly_a, poly_b) -> float`
  - Acceptance: handles `None` inputs, computes intersection/union, returns [0, 1] range
  - Files: `admesh_domains/geometry.py`
  - Tests: `tests/test_geometry.py` — identical → 1.0, disjoint → 0.0, partial → in (0, 1)
  - Depends on: none
  
- [ ] **T-012**: Implement `geometry.hausdorff_distance(poly_a, poly_b) -> float | None`
  - Acceptance: wraps `shapely.hausdorff_distance()`, converts degrees→km, returns `None` for invalid
  - Files: `admesh_domains/geometry.py`
  - Tests: `tests/test_geometry.py` — identical → ~0, separated → positive
  - Depends on: none

### Phase 2: Scoring & Suggest Logic Refactor

- [ ] **T-020**: Extend `IoUScore` dataclass with optional Tier 2 fields
  - Add: `boundary_hausdorff_km: float | None = None`
  - Add: `boundary_polygon_iou: float | None = None`
  - Files: `admesh_domains/geometry.py`
  - Depends on: none

- [ ] **T-021**: Refactor `geometry.suggest_domain(new_bbox, manifest, tier=1) -> list[IoUScore]`
  - Add `tier` parameter (int, default 1)
  - Tier 1: existing logic (bbox only)
  - Tier 2: extract boundary, compute polygon metrics, populate new fields in `IoUScore`
  - Graceful fallback if shapely missing (log warning, downgrade to Tier 1)
  - Composite scoring: if Tier 2 data available, rank by polygon IoU; else by bbox IoU
  - Files: `admesh_domains/geometry.py`
  - Tests: `tests/test_geometry.py` — Tier 1 unchanged, Tier 2 adds metrics, fallback works
  - Depends on: T-010, T-011, T-012, T-020

### Phase 3: CLI Flag & Output

- [ ] **T-030**: Add `--tier` flag to `admesh-domains domain suggest` command
  - Accept `--tier 1` or `--tier 2` (default `1`)
  - Pass to `suggest_domain(..., tier=tier)`
  - Update help text
  - Files: `admesh_domains/cli.py`
  - Depends on: T-021

- [ ] **T-031**: Update `domain suggest` text output formatter for Tier 2
  - When `tier=2` and boundary metrics present, show on separate line:
    ```
    boundary: hausdorff=12.5 km, polygon IoU=0.68
    ```
  - If shapely missing, show note: "(boundary matching unavailable; install with `pip install admesh-domains[suggest]`)"
  - Files: `admesh_domains/cli.py`
  - Depends on: T-030

- [ ] **T-032**: Update JSON output schema for Tier 2
  - Add `"tier"` field at root level
  - Add `"boundary_hausdorff_km"` and `"boundary_polygon_iou"` to each candidate object (nullable)
  - Files: `admesh_domains/cli.py`
  - Depends on: T-030

### Phase 4: Optional Extra & Dependencies

- [ ] **T-040**: Add `[suggest]` extra to `pyproject.toml`
  - Define: `suggest = ["shapely>=2.0"]`
  - Files: `pyproject.toml`
  - Depends on: none

### Phase 5: Tests

- [ ] **T-050**: Write unit tests for boundary extraction
  - Test: rectangular mesh (4 elements) → boundary is closed quad
  - Test: mesh with interior elements → boundary is unique edges only
  - Test: degenerate mesh (no elements) → returns `None`
  - Files: `tests/test_geometry.py`
  - Depends on: T-010
  
- [ ] **T-051**: Write unit tests for polygon IoU
  - Test: identical polygons → 1.0
  - Test: disjoint polygons → 0.0
  - Test: overlapping → value in (0, 1)
  - Test: one wholly contains other → IoU = smaller_area / larger_area
  - Files: `tests/test_geometry.py`
  - Depends on: T-011

- [ ] **T-052**: Write unit tests for Hausdorff distance
  - Test: identical → ~0
  - Test: translated → positive distance
  - Test: invalid geometry → returns `None`
  - Files: `tests/test_geometry.py`
  - Depends on: T-012

- [ ] **T-053**: Write integration tests for `suggest_domain(..., tier=2)`
  - Test: Tier 1 unchanged when `tier=1`
  - Test: Tier 2 includes boundary metrics when `tier=2` + shapely available
  - Test: Tier 2 falls back + warns when shapely missing
  - Files: `tests/test_geometry.py`
  - Depends on: T-021

- [ ] **T-054**: Write CLI tests for `--tier` flag
  - Test: `--tier 1` (default behavior)
  - Test: `--tier 2` with shapely available
  - Test: `--tier 2` without shapely → fallback + warning
  - Test: JSON output shape with `tier` + boundary fields
  - Files: `tests/test_cli_domain.py`
  - Depends on: T-030, T-031, T-032

### Phase 6: Validation & Release

- [ ] **T-060**: Run existing registry through Tier 2
  - For each existing mesh: `domain suggest --tier 2 mesh_path`
  - Verify rank-1 candidate = actual Domain
  - Note any Tier 1 vs Tier 2 ranking changes
  - Files: manual (no new code)
  - Depends on: T-054 (tests must pass)

- [ ] **T-061**: Run full test suite and validation
  - `pytest tests/ -v` (all tests green on Python 3.9+)
  - `admesh-domains validate registry_data/manifest.toml` (no regressions)
  - Files: no new code
  - Depends on: T-050..T-054

- [ ] **T-062**: Update version and commit
  - Bump version in `pyproject.toml` and `admesh_domains/__init__.py` to v0.4.1
  - Commit message: "Resolve issue #5: Add Tier 2 boundary-polygon auto-suggester"
  - Files: `pyproject.toml`, `admesh_domains/__init__.py`
  - Depends on: T-061

- [ ] **T-063**: Push to `daily-issue-fixing` and create PR
  - `git push origin daily-issue-fixing`
  - Create pull request against main (draft)
  - Depends on: T-062

## Dependency Graph

```
T-001..T-004  (research, parallel)
     ↓
T-003 → T-010 (boundary extraction)
        T-010 → T-050 (boundary tests)
T-001 → T-012 (Hausdorff)
        T-012 → T-052 (Hausdorff tests)
T-002 → T-011 (polygon IoU)
        T-011 → T-051 (polygon IoU tests)
T-010 + T-011 + T-012 → T-020 (IoUScore extension)
T-020 → T-021 (suggest_domain refactor)
        T-021 → T-053 (integration tests)
T-021 → T-030 (CLI flag)
T-030 → T-031 (text output)
T-030 → T-032 (JSON output)
T-031 + T-032 → T-054 (CLI tests)
T-054 → T-060 (registry validation)
T-060 → T-061 (full test suite)
T-061 → T-062 (version bump + commit)
T-062 → T-063 (push + PR)
```

## Acceptance Criteria (Done When)

- [ ] All tasks T-001..T-062 completed and checkmarked
- [ ] All tests pass: `pytest tests/ -q` green on Python 3.9, 3.11, 3.12
- [ ] Registry validation green: `admesh-domains validate registry_data/manifest.toml`
- [ ] Manual validation: `domain suggest --tier 2` works on sample meshes
- [ ] CLI fallback: `--tier 2` without shapely shows warning + Tier 1 result
- [ ] JSON output valid: `domain suggest --tier 2 --json | jq '.tier'` returns `2`
- [ ] Committed to `daily-issue-fixing` branch
- [ ] PR created (draft) against main with Tier 2 spec + plan in description
- [ ] Issue #5 linked in PR description

## Token Budget

**Estimate**: Small-to-Medium (3-4 hours of work)
- Boundary extraction: 30 min
- Polygon ops: 20 min
- Refactor suggest_domain: 40 min
- CLI flag + output: 30 min
- Tests: 60 min
- Validation + release: 30 min
- **Total**: ~190 min (~3.2 hours)

**Rationale**: Mostly data-structure changes and algorithm wrapping (shapely does the heavy lifting). No breaking schema changes, no manifest mutations, no complex new dependencies beyond shapely (already a common FOSS geospatial library).
