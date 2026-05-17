# Feature Specification: Tier 2 Auto-Suggester (Boundary Polygon Matching)

**Feature Branch**: `daily-issue-fixing`  
**Created**: 2026-05-06  
**Status**: 🚧 In Development  
**Issue**: [#5](https://github.com/domattioli/ADMESH-Domains/issues/5)  
**Parent Spec**: [007-domain-auto-suggester](../007-domain-auto-suggester/spec.md)  

## Summary

Extend the **Tier 1** auto-suggester (bbox IoU only) with **Tier 2** boundary-polygon matching. Tier 1 succeeds for geographically isolated domains but fails when two mesh bboxes overlap but their actual coastlines diverge (e.g., two inset meshes of the same gulf with different resolution zones). Tier 2 extracts the outer boundary polygon from each fort.14 file and compares via **Hausdorff distance** and/or **polygon IoU** to resolve ambiguity.

## Problem Statement

**Tier 1 limitation**: Consider two meshes covering the Gulf of Mexico with identical bboxes:
- `GOMfine.14` — high-resolution coastal zone, bbox = `(-97.5, 25.0, -82.5, 30.0)`
- `GOMcoarse.14` — low-resolution deepwater zone, same bbox

Both meshes match existing Domain `WNAT` equally well under bbox IoU. Without boundary matching, the suggester can't distinguish which is a closer analog. Tier 2 uses the actual coastline/element boundary to break the tie.

## Approach

1. **Boundary extraction**: For each fort.14 file, trace the outer boundary (unique edges with only one adjacent element) and order them into a closed polygon.
2. **Polygon comparison**: Compute two metrics between boundaries:
   - **Hausdorff distance**: maximum distance from any point on polygon A to the closest point on polygon B. Smaller = more similar.
   - **Polygon IoU**: intersection area / union area of the two polygons. Higher = more similar.
3. **Composite scoring**: Combine `bbox_iou` + `boundary_hausdorff` + `boundary_iou` into a single score, or surface all three separately.
4. **Opt-in flag**: `admesh-domains domain suggest --tier 2 path.14` activates boundary matching. Default stays Tier 1.
5. **New extra**: Add `[suggest]` optional extra (pull in `shapely` for polygon ops) — Constitution Principle II (heavy deps are optional).

## User Scenarios

### Scenario 1 — Distinguish overlapping-bbox meshes

**Given** two meshes with identical bboxes but different coastline boundaries  
**When** contributor runs `domain suggest --tier 2 new.14`  
**Then** the output lists candidates ranked by composite score (bbox + boundary), and Tier 2 breaks the tie correctly.

### Scenario 2 — Fallback to Tier 1 when shapely unavailable

**Given** user runs `--tier 2` but has not installed `[suggest]` extra  
**When** the CLI detects missing shapely  
**Then** it falls back to Tier 1 (bbox only) and logs a warning: "boundary matching requires shapely; install with `pip install admesh-domains[suggest]`".

### Scenario 3 — Audit with Tier 2

**Given** `admesh-domains domain audit --tier 2`  
**When** run against the registry  
**Then** any meshes where Tier 2 score changes the rank-1 candidate are reported.

## Requirements

### Functional

- **FR-001**: New function `extract_boundary_polygon(mesh_path) -> Polygon | None` in `admesh_domains.geometry`. Returns ordered exterior ring of the fort.14 domain boundary (unique edges with one adjacent element).
- **FR-002**: New function `polygon_iou(poly_a, poly_b) -> float` — intersection / union area of two `shapely.Polygon` objects. Handles interior rings (holes), invalid geometries, and edge cases gracefully.
- **FR-003**: New function `hausdorff_distance(poly_a, poly_b) -> float` — maximum distance from any vertex of poly_a to the nearest point on poly_b. Wrapper around `shapely.Polygon.hausdorff_distance()`.
- **FR-004**: Refactor `suggest_domain()` to accept optional `tier: int = 1` parameter. When `tier=2`, add boundary metrics to candidate scoring.
- **FR-005**: New CLI flag `--tier 2` on `admesh-domains domain suggest <PATH>`. Defaults to `tier=1`.
- **FR-006**: New `[suggest]` optional extra in `pyproject.toml`: `suggest = ["shapely>=2.0"]`.
- **FR-007**: When `--tier 2` is requested but shapely is not installed, print a user-friendly warning and fall back to Tier 1. Exit code remains as if Tier 1 ran.
- **FR-008**: Output format (text and JSON) updated to show boundary metrics when Tier 2 is active:
  ```
  Suggestions for new.14 (bbox: -97.5, 25.0, -82.5, 30.0) [TIER 2]:
    1. WNAT
       per-mesh IoU=0.72, union IoU=0.51
       boundary: hausdorff=12.5 km, polygon IoU=0.68  (confident)
  ```
- **FR-009**: JSON output includes `tier`, `boundary_metrics` sub-object (if applicable):
  ```json
  {
    "path": "new.14",
    "tier": 2,
    "bbox": [-97.5, 25.0, -82.5, 30.0],
    "candidates": [
      {
        "domain": "WNAT",
        "per_mesh_iou": 0.72,
        "union_iou": 0.51,
        "boundary_hausdorff_km": 12.5,
        "boundary_polygon_iou": 0.68,
        "confidence": "confident"
      }
    ],
    "exit_code": 0
  }
  ```
- **FR-010**: `admesh-domains domain audit --tier 2` compares rank-1 candidates at Tier 1 vs Tier 2 and reports any "promotion" (Tier 2 ranks a different candidate first).

### Non-Functional

- **NFR-001**: Boundary extraction for a 50K-node mesh completes in < 2 seconds (mesh parse + polygon ops).
- **NFR-002**: Constitution Principle II: shapely is **optional**. Base install unchanged. Graceful degradation when shapely is missing.
- **NFR-003**: Hausdorff distance is computed in degrees; output is converted to kilometers using mean Earth radius (6371 km) times latitude correction.
- **NFR-004**: Polygon IoU threshold for "confident match" is `>= 0.6` (higher bar than bbox IoU 0.5, since boundary is more specific).

## Data Model

No schema changes. Tier 2 computes derived metrics in-memory.

```python
@dataclass
class IoUScore:
    # ... existing Tier 1 fields ...
    boundary_hausdorff_km: float | None = None  # TIER 2
    boundary_polygon_iou: float | None = None   # TIER 2
```

## Success Criteria

- **SC-001**: For every existing mesh, running `domain suggest --tier 2` either returns Tier 1 result (if shapely unavailable) or Tier 2 with boundary metrics.
- **SC-002**: A test case with two overlapping-bbox meshes shows Tier 2 breaking ties that Tier 1 leaves ambiguous.
- **SC-003**: `audit --tier 2` runs in < 5 seconds on the 40-mesh registry.
- **SC-004**: Graceful fallback when shapely is missing: no error, just a warning + Tier 1 result.
- **SC-005**: JSON output includes `tier` and boundary metrics (or `null` if Tier 1).

## Edge Cases

- **Mesh file with no elements** → no boundary polygon. Return `None`; Tier 2 skips this mesh.
- **Degenerate boundary** (e.g., single isolated node) → invalid geometry. shapely handles gracefully; Tier 2 skips.
- **Polygon with interior rings (holes)** → compute IoU on exterior only, or include holes? Tentative: exterior only. Holes are sub-mesh details and don't affect domain assignment.
- **Very large Hausdorff distance** (> 1000 km, e.g., meshes on different continents) → still reportable but low confidence.

## Dependencies

- **New**: `shapely>=2.0` (optional, `[suggest]` extra)
- **Existing**: `admesh_domains.geometry` (Tier 1 helpers), `admesh_domains.schema` (BoundingBox, Polygon types)

## Out of Scope

- **Polygon smoothing / simplification** — use geometries as-is.
- **Coordinate-system reprojection** — only compare if both meshes are in the same coord system (heuristic lat/lon check).
- **Tier 3 (ML embeddings)** — defer to future spec.

## Constitution Check

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest is source of truth | PASS | Suggester reads only; never writes |
| II. Pure-Python, optional heavy deps | PASS | shapely gated behind `[suggest]` extra; base install unchanged |
| III. Schema changes are explicit | N/A | No schema changes; only derives metrics in-memory |
| IV. Atomic releases — and separate code from data | PASS | Code track; feature bump to v0.4.X release |
| V. Test before tagging | PASS | Unit tests for boundary extraction, polygon IoU, fallback behavior |
| VI. Curation over auto-magic | PASS | Suggester proposes; human reviews and decides; Tier 2 is advisory |
| VII. External Upstream (DomI) | PASS | No DomI interaction changes |

## Open Questions

- Should Tier 2 output include a "confidence upgrade" notation? E.g., "Tier 1: IoU=0.32 (uncertain) → Tier 2: boundary IoU=0.68 (confident)"? Tentative **yes**.
- When computing Hausdorff distance between multi-part geometries (meshes with disconnected boundary regions), should we take the minimum over all pairs or the maximum? Tentative: minimum (most forgiving; if any part is close, it's a match).
- Polygon validation: should we silently drop invalid/self-intersecting geometries or raise an error? Tentative: silently skip and log a warning.

## Done When

- `admesh-domains domain suggest --tier 2 registry_data/meshes/SampleMesh.14` returns Tier 2 metrics + correct ranking.
- `admesh-domains domain suggest path.14` without `--tier 2` still works (Tier 1 unchanged).
- If shapely is missing, `--tier 2` falls back to Tier 1 with a warning.
- `audit --tier 2` shows no promotions (Tier 1 and Tier 2 agree on rank-1 for existing meshes, or report the discrepancies).
- JSON output is valid and includes `tier` + `boundary_metrics` fields.
- Tests pass on Python 3.9+ with and without `[suggest]`.
- v0.4.1 ships with Tier 2 included.
