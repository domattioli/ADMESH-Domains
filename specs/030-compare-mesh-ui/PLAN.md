# Plan 030: Compare Mesh UI (Issue #30)

## Constitution Verification

**Principle I — Source of Truth**: ✓ No changes to manifest.toml. Read-only client-side.
**Principle II — Pure Python**: ✓ No new Python deps. Pure JS site changes.
**Principle III — Schema Version**: ✓ No schema changes.
**Principle IV — Release Track**: Code Track. Site changes only. No PyPI bump in Phase 2.
**Principle VI — Curation**: ✓ No runtime manifest editing.

## Files to Create

- `site/src/compare.html` — page with domain selector, panel container, recommendation banner
- `site/src/js/compare.js` — manifest fetch, variant grouping, panel render, recommendation

## Files to Modify

- `site/src/js/nav.js` — add `["compare.html", "Compare"]` to PAGES between Browse and Upload
- `site/src/styles.css` — add `.compare-grid` 3-column layout + responsive stacking

## Tasks (ordered)

1. **nav.js** — insert Compare into PAGES array
2. **styles.css** — append .compare-grid and .compare-panel styles
3. **compare.html** — create page with header/footer hooks, domain select, panels container, banner placeholder
4. **compare.js** — implement: manifest load → domain dropdown → inferStrategy() → groupVariants() → renderPanels() → recommend()
5. **Build validation** — `python scripts/build_site.py` passes
6. **Validate** — `admesh-domains validate registry_data/manifest.toml` passes
7. **Commit** — atomic commit referencing issue #30

## Risks

| Risk | Mitigation |
|------|----------|
| No domains have multiple strategy variants | Rectangles has tri+quad → sufficient for demo |
| element_count/node_count absent on all meshes | Display "—"; recommendation falls back to size_mb |
| CSS grid breaks on narrow screens | Test at 375px; use media query to stack |
