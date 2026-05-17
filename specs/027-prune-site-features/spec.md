# Spec 027 — Prune Site to Two Core Features

**Issue**: [#27 — Feature Request: Prune the website features for now](https://github.com/domattioli/ADMESH-Domains/issues/27)
**Release track**: Code (site/ + 404.html + nav.js footer)
**Status**: In progress

## Problem

Issue #27 reaffirms that the public site should expose **only two features**:
1. Upload & Mesh & Compare → `upload.html`, `compare.html`, `mesh.html` (detail), `domain.html` (detail)
2. Download & Browse → `browse.html`, `domain.html`, `mesh.html`

Spec 010 already pulled `Statistics`, `Create`, `Test Suites`, and `Feedback` out of the primary nav and copied them as `.bak` files to `site/archived/`. **However**, the live source files in `site/src/` were not deleted, so `scripts/build_site.py` still ships them to GitHub Pages on every publish. They are non-navigable orphans.

`preview.html` is similarly orphaned — only referenced from `404.html`.

## Acceptance Criteria

- `site/src/` contains only pages that serve the two features above plus `index.html`, `404.html`, `domain.html`, `mesh.html`, `contribute.html`, and `styles.css`.
- The five orphan HTML pages (`create.html`, `feedback.html`, `preview.html`, `statistics.html`, `tests.html`) and their JS counterparts are removed from `site/src/`.
- The `Feedback` link in the footer is replaced with a direct link to GitHub issues (no more `feedback.html`).
- `404.html` no longer references `preview.html`; falls back to home only.
- The `.bak` archives in `site/archived/` are retained — they remain the documented restoration path.
- `python scripts/build_site.py` succeeds.
- `pytest tests/` succeeds.
- No changes to `admesh_domains/`, `pyproject.toml`, or `manifest.toml`. No PyPI version bump (site-only change).

## Files to Create / Modify

**Delete** (site/src/):
- `create.html`, `js/create.js`
- `feedback.html`, `js/feedback.js`
- `preview.html`, `js/preview.js`
- `statistics.html`, `js/statistics.js`
- `tests.html`, `js/tests.js`

**Modify**:
- `site/src/404.html` — remove `preview.html` reference
- `site/src/js/nav.js` — replace `feedback.html` footer link with GitHub issues URL; drop archived-page comment block (no longer needed since archive doc lives in `site/archived/README.md`)

**Create**:
- `specs/027-prune-site-features/spec.md` (this file)
- `specs/027-prune-site-features/PLAN.md`
- `specs/027-prune-site-features/tasks.md`

## Approach

A pure deletion + small footer fix. No new code. The current nav already lists only `Home / Browse / Compare / Upload`, matching #27's intent — this spec just finalizes the cleanup spec 010 deferred.

## Risks

- **Low**: GitHub Pages cached URLs to deleted pages will 404. Mitigated by `404.html` already pointing to home.
- **Low**: Any external bookmark to `feedback.html` will break. Mitigated by replacing footer link with GitHub issues URL on first push.
- **None**: No schema, no manifest, no API change. Constitution principles I, II, III, IV, VI all PASS (N/A — no data or schema touched).

## Token Budget

**Small**. Five file deletions, two small edits, three spec files.

## Constitution Check

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest is source of truth | N/A | No manifest touched |
| II. Pure-Python, optional heavy deps | N/A | No Python deps touched |
| III. Schema changes are explicit | N/A | No schema touched |
| IV. Atomic releases — and separate code from data | PASS | Site-only; no PyPI bump, no `publish-data.yml` trigger |
| V. Test before tagging | PASS | Existing pytest tests still pass; no new code features |
| VI. Curation over auto-magic | N/A | No runtime manifest mutation |
| VII. External Upstream (DomI) | PASS | No changes to DomI interaction; pinned DomI version maintained |
