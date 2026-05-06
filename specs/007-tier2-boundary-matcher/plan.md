# Implementation Plan: Tier 2 Auto-Suggester (Boundary Polygon Matching)

**Branch**: `daily-issue-fixing` | **Date**: 2026-05-06 | **Spec**: [spec.md](spec.md)

## Summary

Extend Tier 1 bbox-only suggesting with Tier 2 boundary-polygon metrics (Hausdorff distance + polygon IoU) to resolve ties when mesh bboxes overlap but coastlines differ. New `--tier 2` CLI flag, optional `[suggest]` extra with shapely, graceful fallback when shapely is missing.

**Keeps base install unchanged** (Constitution Principle II). Shapely is pulled in only when `pip install admesh-domains[suggest]` is explicitly requested.

## Technical Context

- **Language**: Python 3.9+ (base package).
- **New heavy dep**: `shapely>=2.0` (optional, `[suggest]` extra).
- **CLI shape**: Add `--tier 2` flag to existing `domain suggest` subcommand (no new subcommands).
- **Performance**: Boundary extraction + polygon ops for a 50K-node mesh: < 2 seconds per mesh (shapely is highly optimized).
- **Refactor opportunity**: Move boundary-extraction logic out of inline code into reusable helper.

## Project Structure

### Source code (new + edits)

```text
admesh_domains/
├── geometry.py
│   ├── (EDIT) add extract_boundary_polygon()
│   ├── (EDIT) add polygon_iou()
│   ├── (EDIT) add hausdorff_distance()
│   └── (EDIT) refactor suggest_domain() to accept tier param
└── cli.py
    └── (EDIT) add --tier flag to domain suggest command

pyproject.toml
└── (EDIT) add [suggest] extra with shapely>=2.0

tests/
├── test_geometry.py
│   └── (EDIT) add tier 2 tests (boundary extraction, polygon ops)
└── test_cli_domain.py
    └── (EDIT) add --tier 2 flag tests, fallback behavior
```

### Documentation

```text
specs/007-tier2-boundary-matcher/
├── spec.md          # done
├── plan.md          # this file
└── tasks.md         # Phase 2 — output of /tasks
```

## Phase 0 — Research (Quick Sanity Checks)

Each item ≤ 10 min:

- **R-1**: Verify `shapely.Polygon.hausdorff_distance()` exists and takes two Polygons. → Yes, standard shapely API.
- **R-2**: Confirm shapely can compute polygon intersection/union areas. → Yes, `shapely.ops.unary_union()` + `.intersection()` + `.area`.
- **R-3**: Check if current fort.14 parser (in `geometry.py`) exposes element connectivity needed to extract boundary. → Verify in code.
- **R-4**: Test graceful ImportError pattern: can we catch missing shapely at function entry and provide helpful message? → Yes, standard try/except pattern.

## Phase 1 — Implementation Tasks

### Task Group 1: Boundary Extraction & Polygon Ops (T-010 .. T-012)

**T-010**: Implement `extract_boundary_polygon(mesh_path: str) -> Polygon | None`
- Parse fort.14 file (reuse existing `BoundingBox` / mesh-reading logic)
- Build element-edge adjacency map
- Trace unique edges (degree = 1) in order
- Convert to `shapely.Polygon`
- Return `None` if degenerate

**T-011**: Implement `polygon_iou(poly_a, poly_b) -> float`
- Handle `None` inputs (return 0)
- Compute intersection + union areas
- Return `intersection_area / union_area`
- Test edge case: one polygon wholly contains the other

**T-012**: Implement `hausdorff_distance(poly_a, poly_b) -> float | None`
- Wrapper around `shapely.Polygon.hausdorff_distance()`
- Convert result from degrees to kilometers
- Handle invalid geometries gracefully (return `None`)

### Task Group 2: Scoring & Suggest Logic (T-020 .. T-021)

**T-020**: Refactor `suggest_domain(new_bbox, manifest, tier=1) -> list[IoUScore]`
- Add `tier` parameter (1 or 2)
- When `tier=1`: use existing Tier 1 logic (bbox only)
- When `tier=2`: 
  - Try to extract boundary from new mesh
  - For each Domain candidate, also extract boundary (once, cached)
  - Compute `boundary_hausdorff_km` + `boundary_polygon_iou`
  - Update `IoUScore` dataclass to include new fields
  - Composite scoring: weight bbox (0.4) + boundary polygon IoU (0.5) + proximity (0.1)?
    - Or surface all three and let human decide?
    - Tentative: surface all; ranking driven by polygon IoU when available

**T-021**: Graceful fallback when shapely is missing
- Wrap boundary extraction in try/except `ImportError`
- Log warning: "boundary matching requires shapely; install with `pip install admesh-domains[suggest]`"
- Downgrade to Tier 1 automatically

### Task Group 3: CLI & Output (T-030 .. T-031)

**T-030**: Add `--tier` flag to `domain suggest` subcommand
- Accept `--tier 1` or `--tier 2` (default `1`)
- Pass `tier` param to `suggest_domain()`
- Update help text

**T-031**: Update text and JSON output for Tier 2 metrics
- When `tier=2`, show `boundary_hausdorff_km` and `boundary_polygon_iou` in text output
- JSON includes `tier` field + optional `boundary_metrics` object

### Task Group 4: Validation & Tests (T-040 .. T-042)

**T-040**: Unit tests for boundary extraction
- Test fort.14 with simple rectangular mesh (4 elements) → verify boundary is closed quad
- Test mesh with interior elements → verify only unique edges included
- Test degenerate mesh (no elements) → verify returns `None`

**T-041**: Unit tests for polygon ops
- Test polygon IoU: identical → 1.0, disjoint → 0.0, partial overlap → in (0, 1)
- Test Hausdorff: identical → 0, separated → positive

**T-042**: Smoke test: `domain suggest --tier 2 SampleMesh.14`
- Verify it runs without error
- If shapely missing: verify fallback + warning message
- JSON output valid

### Task Group 5: Validation Against Registry (T-050)

**T-050**: Run Tier 2 against existing meshes
- For each mesh: `domain suggest --tier 2 mesh.14` → verify rank-1 is correct Domain
- Compare Tier 1 vs Tier 2 rankings: any promotions?
- Report discrepancies

### Task Group 6: Release & Documentation (T-060)

**T-060**: Update pyproject.toml
- Add `[suggest]` extra with `shapely>=2.0`
- Update README.md if needed

**T-061**: Commit all changes to `daily-issue-fixing` branch
- Atomic: boundary extraction + polygon ops + scoring + CLI + tests

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. TOML as source of truth | **PASS** | Suggester reads only. No manifest mutations. |
| II. Pure-Python, optional heavy deps | **PASS** | shapely → `[suggest]` extra. Base unchanged. ImportError → fallback. |
| III. Schema versioning | **N/A** | No schema change. Existing `IoUScore` extended with optional fields. |
| IV. Atomic releases | **PASS** | Code track: v0.4.1 bump. release.yml ships PyPI + HF. |
| V. Test before tagging | **PASS** | T-040..T-042 + T-050 provide unit + integration coverage. |
| VI. Curation over auto-magic | **PASS** | Tier 2 *proposes* better ranking; human *decides*. |

## Risk Tracking

- **R-1 (medium)**: Boundary extraction from fort.14 is O(elements + edges). For very large meshes (1M elements), this could be slow. Mitigation: cache extracted boundaries in memory during `domain audit` to avoid re-parsing.
- **R-2 (low)**: shapely polygon validity. Some meshes might produce invalid/self-intersecting boundary polygons. Mitigation: T-041 includes invalid-geometry tests; we skip and log warning.
- **R-3 (low)**: Coordinate system assumptions. Current code assumes all meshes are in lat/lon. If mixed, polygon comparison is meaningless. Mitigation: add heuristic check (skip if one is clearly projected).

## Done When

- `admesh-domains domain suggest --tier 2 SampleMesh.14` returns Tier 2 metrics.
- Without `--tier 2`, Tier 1 logic unchanged.
- If shapely missing, `--tier 2` falls back to Tier 1 + warning.
- `audit --tier 2` reports any Tier 1 vs Tier 2 ranking discrepancies.
- JSON output includes `tier` + `boundary_metrics` fields.
- All tests green.
- v0.4.1 tagged and ships through release.yml.
