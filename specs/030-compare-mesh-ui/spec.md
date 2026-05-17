# Spec 030: Compare Mesh UI (Phase 2 of Spec 029)

**Parent**: Spec 029 / Issue #25 — Side-by-Side Mesh Strategy Comparison
**GitHub Issue**: #30

## Summary

Implement the 3-panel mesh comparison webpage that lets users select a domain and view up to three mesh variants (triangle, quad-dominant, mixed) side-by-side with key metrics and a recommendation banner. All data comes from the already-built `manifest.json` on the client side — no backend changes required.

## Context

Phase 1 (data model + API contract) is complete: specs/029-mesh-strategy-comparison/contracts/comparison-api.md defines client-side variant grouping by `element_type`. This spec covers the visible frontend work users will interact with.

Users currently have no way to compare mesh strategies for the same domain. They can browse and download individual meshes but cannot see how a triangular mesh differs from a quad mesh on the same domain with quantitative metrics.

## User Scenarios & Testing

### Primary Flow: Compare Mesh Variants

1. User clicks "Compare" in the site navigation
2. Compare page loads with a domain dropdown populated from the registry
3. User selects a domain (e.g., "Rectangles")
4. User clicks "Compare" button
5. Page shows 1–3 panels (one per available variant type: triangle, quad, mixed)
6. Each panel displays: strategy label, element type, bounding box SVG, element count, node count, file size, and contributor
7. A recommendation banner identifies the best variant (fewest elements = most efficient)
8. User can toggle mesh line overlay on/off per panel (optional control)
9. User returns to Browse page via nav

### Edge Cases

- Domain has only 1 variant → single panel + note "Other variants not in registry"
- Domain has no mesh data → "No meshes available for this domain"
- Slow initial load → spinner shown while manifest fetches
- Mobile screen → panels stack vertically (usable at ≥375px)
- Domain with >3 meshes of same type → use first found per strategy type

## Functional Requirements

1. **Navigation** — "Compare" link added to the site header alongside Browse and Upload

2. **Domain Selector** — Dropdown lists all domains from manifest.json; defaults to first domain on page load

3. **Variant Grouping** — Meshes are grouped by strategy:
   - `triangle` → `element_type === "triangle"` or filename contains "tri"
   - `quad-dominant` → `element_type === "quadrilateral"` or filename contains "quad"
   - `mixed` → `element_type === "mixed"` or filename contains "mixed"

4. **Panel Rendering** — Each detected strategy gets one panel with:
   - Strategy label (Triangle / Quad-Dominant / Mixed)
   - Bounding box SVG (reuse existing bboxSvgFallback pattern)
   - Element count (from manifest; display "—" if absent)
   - Node count (from manifest; display "—" if absent)
   - File size in MB (from manifest)
   - Contributor name

5. **Recommendation Banner** — Below panels, identify variant with lowest element count as "best for efficiency"; if counts equal or unknown, skip banner

6. **Responsive Layout** — 3-column grid on desktop (≥768px), single column on mobile (≤375px)

7. **Graceful Degradation** — Missing variants noted; no console errors for absent data

## Success Criteria

- Users can view mesh strategy comparisons for any domain with multiple mesh types within 2 seconds
- At least one domain (Rectangles) shows 2+ panels with accurate metric data
- Navigation to the Compare page works from every page via the header link
- Page is usable on a 375px-wide mobile viewport without horizontal scrolling
- Recommendation banner appears for any domain where element counts differ between variants
- Site builds cleanly with `python scripts/build_site.py` after changes
- No JavaScript console errors on page load or after clicking Compare

## Key Entities

- **Domain**: selected from manifest.json dropdown
- **Mesh Variant**: grouped representation of 1+ meshes sharing a strategy (triangle/quad/mixed)
- **Panel**: UI card displaying one variant's metrics and bounding box
- **Recommendation Banner**: summary callout identifying the most efficient variant

## Assumptions

- Variant detection is heuristic (element_type field or filename keyword); no new manifest fields needed
- `element_count` and `node_count` may be absent for many meshes; display "—" gracefully
- Bounding box visualization reuses the existing `bboxSvgFallback` pattern from browse.js
- No zoom/pan sync between panels in Phase 2 (deferred to v0.5)
- No export/save in Phase 2
- Quality metrics (aspect ratio, element quality score) are deferred to Phase 3+

## Dependencies

- Spec 029 Phase 1 complete (data contract: specs/029-mesh-strategy-comparison/contracts/)
- Existing `manifest-loader.js` and `nav.js` patterns
- Existing `styles.css` design tokens (--accent, --card-bg, --border, etc.)

## Scope Boundaries

**In**: compare.html, compare.js, nav.js update, styles.css additions
**Out**: backend API, on-demand mesh generation, quality metric parsing, export, 3D view, zoom sync

## Constitution Check

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest is source of truth | PASS | Reads manifest.json; no mutations |
| II. Pure-Python, optional heavy deps | N/A | Static site; JavaScript only |
| III. Schema changes are explicit | N/A | No schema changes |
| IV. Atomic releases — and separate code from data | N/A | Site-only; no PyPI bump, no data release |
| V. Test before tagging | PASS | Spec 031 adds comprehensive pytest suite for comparison feature |
| VI. Curation over auto-magic | PASS | Recommendation algorithm is simple (fewest elements); human selects strategies |
| VII. External Upstream (DomI) | PASS | No DomI interaction changes |

## Release Track

Code Track — site changes only. No manifest.toml edits, no PyPI version bump required for Phase 2 alone.
