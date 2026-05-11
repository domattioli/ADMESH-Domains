# Spec 029: Side-by-Side Mesh Strategy Comparison

## Summary

Add a lightweight "Compare Mesh Strategies" view that lets users visually compare different mesh approaches on the same domain. Users can generate (or select) multiple mesh variants for a single domain (Triangle, Quad-Dominant, Mixed) and view results side-by-side with metrics, helping them understand mesh tradeoffs and choose the best strategy for their use case.

## Context

Users today have no intuitive way to understand why one mesh is better than another, when to use more optimal strategies, or how those choices affect simulation behavior or cost. This feature positions meshes as benchmarkable, comparable artifacts rather than trial-and-error configurations.

Comparison helps build intuition: "Mixed mesh is best balance for Gibraltar; Quad-dominant is better for regular geometries; Triangle dominates irregular coastlines."

## User Scenarios & Testing

### Primary Flow: Compare Strategies for a Domain

1. User navigates to Compare page
2. Selects a domain from dropdown (e.g., "Gibraltar Strait")
3. Clicks "Compare" button
4. System generates/loads 3 mesh variants: Triangle, Quad-Dominant, Mixed
5. 3-panel layout appears side-by-side:
   - Left: Triangle mesh with overlay, element count, quality metrics
   - Center: Quad-Dominant mesh with overlay, element count, quality metrics
   - Right: Mixed mesh with overlay, element count, quality metrics
6. Below panels: recommendation banner ("⭐ Mixed = best balance for this domain")
7. User can toggle:
   - Mesh lines on/off
   - Element display on/off
   - Metric details (expand/collapse)
8. User can save/export comparison for documentation

### Edge Cases

- Domain has no pre-generated variants → show load spinner, generate on-demand
- Only 1 or 2 variants available → display available variants, note missing ones
- User on slow connection → progressive load; show mesh outline first, detail later
- Mobile/small screen → stack panels vertically instead of 3-wide

## Functional Requirements

1. **Domain Selector** - Dropdown list of all domains, quick search/filter, pre-populate with first domain

2. **Mesh Variant Management** - Backend support for Triangle, Quad-Dominant, Mixed variants; fallback if variants unavailable; caching

3. **Three-Panel Comparison View** - Side-by-side panels (responsive stacking on mobile) with domain overlay, mesh render, element count, quality metrics, strategy label

4. **Interactive Controls** - Mesh wireframe toggle, element display toggle, metric detail expand/collapse, optional sync zoom/pan across panels

5. **Metrics Display** - Element count, min/max/avg quality (0–1), average element size, boundary alignment, optional performance metrics

6. **Recommendation Logic** - Heuristic-based banner identifying best strategy (e.g., "⭐ Mixed = best balance")

7. **Responsive Layout** - 3-column desktop, 2+1 tablet, stacked mobile (≥usable at 375px)

## Success Criteria

- Users can select any domain and view 3 mesh variants side-by-side
- Comparison loads within 2 seconds
- Three panels render correctly without visual glitches
- Element counts and metrics match registry data
- Recommendation correctly identifies best strategy for ≥80% of test domains
- Toggles work without page reload
- Mobile layout usable on ≤375px screens
- Users can interpret which mesh is "best"
- Feature integrates without breaking existing Browse/Download workflow

## Key Entities

- **Domain**: geographic area (boundary, metadata)
- **Mesh Variant**: Triangle | Quad-Dominant | Mixed
- **Mesh Data**: geometry, quality metrics, element count
- **Comparison View**: presentation layer combining 3 meshes + controls

## Assumptions

- Variants are pre-computed or generatable on-demand
- Quality metrics are standardized across mesh types
- "Best balance" can be a simple heuristic (fewest elements + acceptable quality)
- Registry API provides queryable mesh metadata
- Domain list is stable during session

## Known Clarifications Needed

1. **Variant Generation**: Are Triangle/Quad/Mixed variants pre-computed in the registry, or generated on-demand?
2. **Panel Sync**: Do the three panels sync zoom/pan to show the same geographic region?
3. **Load Performance**: Is 2-second load acceptable, or prioritize instant-load with pre-fetch?

## Dependencies

- Existing site infrastructure (Home, Browse, Upload pages)
- Registry API for mesh variant metadata
- Map library (Folium/Leaflet/Mapbox)
- Mesh quality functions (reuse admesh_domains if available)

## Scope Boundaries

**In**: 3-panel layout, mesh visualization, metrics, recommendation banner, responsive design, toggles
**Out**: Advanced analytics, custom generation, export, history, multi-domain comparison, 3D visualization

## Constitution Check

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest is source of truth | PASS | Displays manifest data; no writes or mutations |
| II. Pure-Python, optional heavy deps | N/A | Site-only specification; no Python runtime |
| III. Schema changes are explicit | N/A | No schema changes |
| IV. Atomic releases — and separate code from data | PASS | Code track; site changes only, no manifest mutations |
| V. Test before tagging | PASS | UI tested via browser rendering; coordinated with spec 031 testing |
| VI. Curation over auto-magic | PASS | Recommendation based on element count; manual selection of strategies |
| VII. External Upstream (DomI) | PASS | No DomI interaction changes |

## Release Track

Code Track (site changes + UI logic)

## Version & Milestones

Target: v0.4.0 (extends Spec 010 MVP redesign)
