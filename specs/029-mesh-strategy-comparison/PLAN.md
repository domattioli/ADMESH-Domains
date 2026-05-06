# Plan 029: Side-by-Side Mesh Strategy Comparison

## Constitution Verification

**Principle I — Source of Truth (manifest.toml)**
- ✓ No changes to registry_data/manifest.toml required
- New meshes registered via existing upload mechanism (not auto-mutation)

**Principle II — Pure Python, Optional Heavy Deps**
- ✓ Base admesh-domains library unchanged
- Site rendering (Folium/Mapbox) already behind [hf] extra
- No new base deps

**Principle III — Schema Version**
- ✓ No schema changes (comparing existing mesh types, not adding fields)

**Principle IV — Release Track (Code)**
- ✓ Site/UI changes only → Code track (no data mutation)
- Version: v0.4.0
- release.yml responsible for PyPI + HF sync

**Principle VI — Curation Over Auto-Magic**
- ✓ No runtime manifest editing
- Comparison is read-only display logic

## Scope

**In-Scope**:
- New site page: `site/src/compare.html`
- JavaScript logic: `site/src/js/compare.js`
- Mesh visualization layer (reuse Folium/existing map library)
- Metrics display and recommendation logic

**Out-of-Scope** (v0.5+):
- Advanced variant generation backend
- Custom mesh generation on-demand
- Comparison export/save feature
- 3D visualization

## Clarifications Resolved

**Q1: Variant Generation** → Assume pre-computed variants exist in registry (uploaded via Browse upload flow or populated by maintainers). On-demand generation deferred to v0.5.

**Q2: Panel Sync** → Independent panels for MVP. Sync (zoom/pan) deferred to v0.5.

**Q3: Load Performance** → Target 2 seconds for displaying 3 pre-loaded meshes. Progressive render: wireframe first, then detailed elements.

## Tasks

### Phase 1: Data Model & API (0.5 days)

1. **Data Contract** — Define comparison API endpoint:
   ```
   GET /api/domains/{domain_id}/mesh-variants
   Returns: { triangle: {...}, quad: {...}, mixed: {...} }
   ```

2. **Quality Metrics Computation** — Reuse admesh_domains.compute_quality() for:
   - Element count, min/max/avg quality, boundary quality
   - Cache results in registry_data/manifest.toml metadata (optional per-domain)

3. **Recommendation Heuristic** — Define scoring logic:
   - Best = (lowest element count + quality > threshold)
   - Fallback: fewest elements

### Phase 2: Frontend (1 day)

1. **HTML Template** (`site/src/compare.html`):
   - Domain selector dropdown
   - Compare button
   - 3-panel container (div layout, responsive CSS)
   - Control toggles (mesh lines, element display)
   - Recommendation banner

2. **JavaScript** (`site/src/js/compare.js`):
   - Fetch domain list, populate dropdown
   - On Compare click: fetch mesh variants via API
   - Render 3 meshes using Folium (or existing map library)
   - Compute and display metrics
   - Handle edge cases (missing variants, slow load)

3. **Styling** — Update `site/src/css/style.css`:
   - 3-column grid layout (desktop)
   - Responsive stacking (tablet/mobile)
   - Metric cards styling
   - Toggle button styles

### Phase 3: Integration & Testing (0.5 days)

1. **Build Site** — Verify `python scripts/build_site.py` succeeds

2. **Browser Testing**:
   - Domain selection works
   - Comparison renders without visual glitches
   - Metrics match registry data
   - Toggles work without page reload
   - Responsive: test on mobile/tablet/desktop

3. **Validation**:
   - No 404s from Compare page
   - No console errors (F12 dev tools)
   - Recommendation banner correctly identifies best strategy

## Timeline

- Total: ~2 days
- Dependencies: existing site build infrastructure, mesh API endpoint availability
- Blocker: If mesh variants not pre-computed, Phase 1 expands to include backend generation (deferred to v0.5 if needed)

## Files to Create/Modify

### Create
- `specs/029-mesh-strategy-comparison/spec.md` ✓
- `specs/029-mesh-strategy-comparison/PLAN.md` ✓
- `site/src/compare.html` (Phase 2)
- `site/src/js/compare.js` (Phase 2)

### Modify
- `site/src/js/nav.js` — add Compare link to PAGES array
- `site/src/css/style.css` — add 3-column grid + responsive styles
- `site/src/index.html` — optional: link to Compare from landing page
- `pyproject.toml` — version bump to v0.4.0

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Mesh variants not available in API | Defer to v0.5; display "Variants not available" placeholder |
| Performance: 3 meshes slow to render | Progressive load; wireframe first, detail later |
| Mobile layout breaks on small screens | Test on 375px viewport; use CSS flexbox for responsiveness |
| Recommendation logic wrong | Validate against 5+ known domains; adjust heuristic if needed |

## Release Checklist

- [ ] Spec 029 complete (SPEC.md, PLAN.md)
- [ ] Code changes committed to daily-issue-fixing
- [ ] Site builds cleanly: `python scripts/build_site.py`
- [ ] Browser testing complete (desktop, tablet, mobile)
- [ ] No console errors or 404s
- [ ] All toggles and controls work
- [ ] Metrics display matches registry data
- [ ] Recommendation logic validated on ≥3 test domains
- [ ] Version bumped to v0.4.0 (if shipping)
- [ ] PR created for human review
