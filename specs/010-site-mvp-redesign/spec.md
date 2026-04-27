# Spec 010: Site MVP Redesign — Feature Retirement & Streamlining

## Summary

Temporarily retire advanced website features to focus on core functionality: browse + download meshes, and upload + compare domains. Archive removed pages but keep code for future restoration. Implement bare-bones comparison logic for uploaded domains against the registry.

## Context

- Current site has 7 primary pages: Home, Browse, Upload, Statistics, Create, Test Suites, Feedback
- Goal: streamline to 2 functional tabs + Home
- Keep old code documented for future re-enablement (spec-kit principle: archived work is searchable)

## Scope

### Keep (active)
- **Home** (index.html) — landing page, registry stats
- **Browse** (browse.html) — view/filter/download meshes
- **Upload** (upload.html) — upload domain, compare against registry

### Archive (hide from nav, keep code)
- Statistics (site/src/statistics.html) → site/archived/statistics.html.bak
- Create (site/src/create.html) → site/archived/create.html.bak
- Test Suites (site/src/tests.html) → site/archived/tests.html.bak
- Feedback (site/src/feedback.html) → site/archived/feedback.html.bak

### New/Modified
- **Upload comparison logic** — bare-bones mesh comparison (geometry bounds IoU, node count)
- **nav.js** — remove Statistics, Create, Test Suites, Feedback links

## Acceptance Criteria

- [ ] nav.js updated: only Browse + Upload in PAGES array
- [ ] Archived pages moved to site/archived/ with .bak extension and README documenting retirement
- [ ] Upload tab displays basic mesh comparison (bbox IoU, node count delta)
- [ ] Comparison persists in upload form so user can toggle between meshes
- [ ] No 404s or broken links from remaining pages
- [ ] specs/010-site-mvp-redesign/RETIRED.md documents what was removed and why

## Definition of Done

- [ ] Site builds cleanly with new nav
- [ ] Browse tab works as before
- [ ] Upload tab shows mesh comparison results
- [ ] Old pages archived with clear restoration notes
- [ ] Tested in browser: all links work, no console errors
