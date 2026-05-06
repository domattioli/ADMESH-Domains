# Spec: Tier 2 Auto-Suggester — Boundary-Polygon Similarity

**Issue:** #5  
**Release Track:** Code (PyPI + HF)  
**Owner:** auto-suggester team  
**Status:** Spec written  
**Acceptance Date:** —  

## What We're Building

Extend the domain auto-suggester (Tier 1: bbox IoU only) with boundary-polygon similarity matching. This unlocks suggestions for mesh pairs with overlapping bboxes but different actual coastlines (e.g., nested insets in the same gulf).

## Requirements

### Functional
- Extract the outer boundary polygon from a fort.14 mesh (the unique edges that bound element 1 only, in order)
- Compute Hausdorff distance between two boundary polygons (worst-case deviation)
- Compute polygon IoU (Intersection over Union) via shapely
- Combine bbox IoU + boundary IoU into a composite score (weighted, tunable)
- New CLI flag: `admesh-domains domain suggest --tier 2 <mesh_file>` (default: tier 1)
- Return suggestions ranked by composite score
- Edge cases:
  - Non-convex boundaries (typical coastlines)
  - Self-intersecting polygons (rare but possible in hand-drawn meshes)
  - Antimeridian-wrapping domains (Pacific meshes)
  - Degenerate boundaries (single island, null island)

### Non-Functional
- Base install remains pure-Python, <100 KB
- Heavy deps (shapely) go behind optional `[suggest]` extra
- Lazy import with clear `ImportError` if user calls `--tier 2` without `[suggest]`
- No schema version bump (additive feature)
- Tests: boundary extraction, IoU calculation, composite scoring, edge cases
- Validation: `admesh-domains validate` still passes; no manifest drift

## Success Criteria

1. **Boundary extraction works** for all 40 existing meshes (including Pacific antimeridian cases)
2. **Composite score** correctly interpolates bbox IoU + boundary IoU
3. **CLI flag** `--tier 2` works; default `--tier 1` unchanged
4. **Optional extra** `[suggest]` installs shapely; base install does not
5. **Tests pass** (>90% coverage for new code)
6. **No manifest.toml edits** (data curation is post-code phase)

## Boundaries

- **Out of scope:** Tier 3+ (Voronoi cells, mesh element distribution, etc.)
- **Out of scope:** Manifest re-curation (data-only work, handled separately)
- **Out of scope:** Site/UI integration (display composite scores on web UI)
- **Out of scope:** Performance optimization (vectorized boundary matching)

## Unknowns / Decisions Required

1. **Weighting formula:** How to combine bbox IoU + boundary IoU?
   - Equal weights: `(bbox_iou + boundary_iou) / 2`
   - Boundary-heavy: `0.3 * bbox_iou + 0.7 * boundary_iou`
   - Decision: Default to equal; make tunable via config later
2. **Hausdorff threshold:** When are two boundaries "too different"? (affects ranking)
3. **Boundary extraction algorithm:** Shell induction via unique edges; handle degenerate cases?

## Implementation Notes

- Reference spec 007 (`admesh_domains/suggest.py` Tier1Matcher) for existing code structure
- Use shapely >= 2.0 with lazy import pattern from admesh_domains/registry.py
- Test data: All 40 existing meshes + synthetic edge-case meshes

## Related Artifacts

- [Spec 007: Domain Auto-Suggester](../007-domain-auto-suggester/spec.md) — Tier 1 (shipped)
- [Issue #5](https://github.com/domattioli/ADMESH-Domains/issues/5) — GitHub issue
- [Constitution Principle II](../../.specify/memory/constitution.md#ii-pure-python-optional-heavy-deps) — Optional extras policy
