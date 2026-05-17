# Spec 031: Test and Validate Mesh Comparison Feature

**Parent Issue**: #25 (Side-by-Side Mesh Strategy Comparison)
**Issue**: #31 (Phase 3/029)
**Release Track**: Site/Docs -- no PyPI bump, no manifest mutation

## Problem

Phase 2 (issue #30) built the 3-panel comparison UI but no automated tests exist to validate
the feature's correctness, edge cases, or structural integrity. This phase adds a pytest-based
test suite that covers what is verifiable without a running browser.

## Approach

Write `tests/test_compare_feature.py` with four test classes:

1. **TestSiteBuild** -- verify site builds cleanly and compare artifacts exist in `site/dist/`
2. **TestCompareHtmlStructure** -- parse compare.html for required IDs, aria attributes, script tag, nav inclusion
3. **TestCompareCSS** -- verify responsive grid, panel, banner classes in styles.css
4. **TestCompareLogic** -- Python equivalents of `inferStrategy()`, `groupVariants()`, `recommend()` tested with mock data and real manifest domains

## Constraints

- No PyPI version bump (site-only change)
- No manifest mutations (Principle VI)
- Pre-existing Tier 2 shapely failures are out of scope
- Browser-level concerns (console errors, toggle interaction) documented as manual

## Manual Testing Required (browser only)

- No console errors (F12 dev tools)
- Toggle controls (mesh lines, element display) work without page reload
- Progressive load indicator on slow network
- Actual visual rendering of SVG thumbnails

## Constitution Check

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest is source of truth | N/A | No manifest touched; site/docs only |
| II. Pure-Python, optional heavy deps | PASS | Tests in Python; no new heavy dependencies |
| III. Schema changes are explicit | N/A | No schema changes |
| IV. Atomic releases — and separate code from data | N/A | Site/docs feature; no separate release track |
| V. Test before tagging | PASS | Adding comprehensive test suite for comparison feature |
| VI. Curation over auto-magic | N/A | Tests do not mutate manifest or auto-suggest |
| VII. External Upstream (DomI) | PASS | No DomI interaction changes |
