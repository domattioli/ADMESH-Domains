# Tasks: Compare Mesh UI (Issue #30)

**Feature**: 3-panel mesh strategy comparison page
**Spec**: specs/030-compare-mesh-ui/spec.md
**Plan**: specs/030-compare-mesh-ui/PLAN.md
**Total tasks**: 8 | **Parallel opportunities**: T002, T003, T004

---

## Phase 1: Setup (no blocking dependencies)

- [x] T001 Verify build passes before changes: `python scripts/build_site.py`

---

## Phase 2: Foundational — Nav + Styles (parallel, different files)

- [x] T002 [P] Add `["compare.html", "Compare"]` to PAGES array in site/src/js/nav.js between Browse and Upload entries
- [x] T003 [P] Append `.compare-grid`, `.compare-panel`, `.compare-banner`, and responsive media query styles to site/src/styles.css

---

## Phase 3: User Story — Compare Page [US1]

*US1: User selects a domain and sees up to 3 mesh variant panels with metrics and a recommendation banner.*

- [x] T004 [P] [US1] Create site/src/compare.html — domain selector `<select>`, Compare `<button>`, `<div id="compare-panels">` container, `<div id="compare-banner">` banner, header/footer divs using renderNav/renderFooter pattern
- [x] T005 [US1] Create site/src/js/compare.js — implement `inferStrategy(mesh)`, `groupVariants(domain)`, `bboxSvgFallback(mesh)` (inline copy from browse.js pattern), `renderPanels(domain)`, `recommend(variants)`, wire up domain dropdown from manifest and Compare button click handler

---

## Phase 4: Polish & Validation

- [x] T006 Build site and verify success: `python scripts/build_site.py` — confirmed output includes compare.html and hashed compare.js
- [x] T007 Validate manifest unchanged: `admesh-domains validate registry_data/manifest.toml`
- [x] T008 Commit all changes referencing issue #30

---

## Dependencies

```
T001 → T002, T003, T004 (parallel)
T002, T003, T004 → T005
T005 → T006
T006 → T007
T007 → T008
```

## Independent Test Criteria (US1)

- `site/dist/compare.html` exists after build
- `site/dist/js/compare.*.js` exists (hashed) after build
- nav.js PAGES array contains `["compare.html", "Compare"]`
- Rectangles domain shows 2 panels (triangle + quad) on the compare page
- Recommendation banner appears when variants have different element counts / sizes
