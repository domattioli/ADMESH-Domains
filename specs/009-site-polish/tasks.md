# Tasks: Site Polish + New Tabs

**Branch**: `009-site-polish` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Tasks are ordered. `[P]` = can run in parallel with the prior task. Each task is independently testable.

## Phase 1 — Schema + manifest backfill (Python)

- **T-001** Add `test_case: bool = False` to `admesh_domains.schema.Mesh` (the dataclass + any `__slots__` / field tuple). Additive; no `SCHEMA_VERSION` bump.
- **T-002** Update `Mesh.from_toml` (or wherever raw TOML dicts → `Mesh` instances) to read `data.get("test_case", False)`. Tolerate missing key.
- **T-003** Backfill `test_case = true` on the 6 TestCases meshes in `registry_data/manifest.toml`.
- **T-004** [P] Mirror the same backfill into `admesh_domains/data/manifest.toml`.
- **T-005** Extend `tests/test_schema.py`: assert default is `False` when key absent; assert round-trip preserves `True`.
- **T-006** Run `pytest tests/` — full suite green before moving on.

## Phase 2 — Build script propagation

- **T-007** In `scripts/build_site.py`, include `test_case` in each mesh dict written to `manifest.json`.
- **T-008** Run `python scripts/build_site.py`; grep `site/dist/manifest.json` for `"test_case": true` — must show 6 hits.

## Phase 3 — Nav + Contribute → Upload rename

- **T-009** Rename `site/src/contribute.html` → `upload.html`. Update `<title>`, `<h1>`, and any `<script src="js/contribute.js">` reference.
- **T-010** [P] Rename `site/src/js/contribute.js` → `upload.js`. No logic changes.
- **T-011** Create new `site/src/contribute.html` containing only a meta-refresh `<meta http-equiv="refresh" content="0; url=./upload.html">` plus a fallback `<a>`.
- **T-012** Update `PAGES` in `site/src/js/nav.js` to: `[Home, Browse, Preview, Upload, Statistics, Create, Test Suites, Feedback]`.
- **T-013** [P] Update `site/README.md` page list and any other docs pointing at `contribute.html`.

## Phase 4 — Home trim + Browse build-out

- **T-014** Build out `site/src/browse.html`: replace meta-refresh with the search input + `#domain-cards` grid + (optional) sortable `<table>` of all meshes. Header/footer slots like other pages.
- **T-015** Create `site/src/js/browse.js` (extracted from current `index.js` logic): manifest-loader, search filter, card render, table render. Reuse existing helpers; do not duplicate `findDomain`/`findMesh`.
- **T-016** Trim `site/src/index.html`: remove search input, `#domain-cards`, BibTeX (move BibTeX to Browse or About). Keep mission slot, `.totals`, `#map`, add `#superlatives` div.
- **T-017** Update `site/src/js/index.js` (or split into `js/home.js`): render mission, totals, map, superlatives. Compute superlatives from manifest: top-3 contributors by mesh count, largest mesh by node count, most-refined mesh by `refinement_level`.
- **T-018** Insert mission statement into `index.html` (use FR-005 placeholder draft until user pastes wiki text).

## Phase 5 — Map correctness

- **T-019** In `site/src/js/map.js::addDomainBboxes`, after computing the geographic-only mesh subset for a domain, `continue` if the subset is empty. Add a brief inline comment.
- **T-020** Visually verify on Home: TestCases and BaranjaHill produce no rectangle. Mixed domains (if any) produce a tighter union.

## Phase 6 — Statistics page

- **T-021** Create `site/src/statistics.html`: header/footer slots; uPlot CSS+JS via unpkg with SRI; container divs for `#totals`, `#top-nodes`, `#top-elements`, `#top-size`, `#refinement-chart`, `#license-chart`, `#application-chart`, `#contributors`.
- **T-022** Create `site/src/js/statistics.js`:
  - `loadManifest()`
  - aggregate: top-5 by node_count, element_count, size_mb
  - histogram: refinement_level, license, application (flatten across all meshes)
  - contributors: unique names with counts, sorted desc
  - totals: domain count, mesh count, total bytes, total node count, contributor count
- **T-023** Render top-5 lists as plain `<table>`. Render histograms as uPlot bar charts.
- **T-024** [P] Add styles to `styles.css`: `.stat-section`, `.uplot` overrides for theming (dark-mode aware).
- **T-025** Add Statistics page to PAGES (already done in T-012; verify here).

## Phase 7 — Create page

- **T-026** Create `site/src/create.html`: `<h1>Create — Coming Soon</h1>`, intro paragraph, file-upload `<input type="file" accept=".14,.2dm">`, `<pre id="terminal"></pre>` panel, links to GitHub issues #1 and #2.
- **T-027** Create `site/src/js/create.js`:
  - on file select, write a fake prompt line to the terminal (e.g. `$ admesh-create analyze <filename>`)
  - call `bboxFromFile` from the existing parser; print bbox or error
  - call `parseFort14Full` (if `.14`); print node/element counts
  - print "TODO: SAM-style waterbody selection — see issue #1" as the next "command"
- **T-028** [P] Add `.terminal` styles to `styles.css`: dark background, monospace font, scrollable, max-height ~400px, distinct from `pre` default.

## Phase 8 — Test Suites page

- **T-029** Create `site/src/tests.html`: header/footer slots, intro paragraph (use case: madmeshr / pytest fixtures), `<table id="tests-table">`, toggle UI (radio: curl / wget), `<pre id="bulk-snippet">`, copy button.
- **T-030** Create `site/src/js/tests.js`:
  - `loadManifest()`
  - flat-filter all meshes where `m.test_case === true`
  - render table: filename, domain, node_count, size_mb, direct download link
  - generate bulk snippet (curl default): `curl -L -O <url>` per mesh
  - toggle handler swaps to `wget <url>` per mesh
  - copy-to-clipboard button
- **T-031** [P] Verify via local server: every link returns 200; pasted snippet downloads all 6 files.

## Phase 9 — CSS overlap fix

- **T-032** Build site, serve with `python -m http.server -d site/dist 8000`. In browser DevTools, identify the element overlapping the heading on `/upload.html` and `/preview.html`. Likely candidates: `.dropzone` parent flex/grid, `#map`/`#geometry-canvas` height, missing `margin-top` on the form.
- **T-033** Apply the fix in `site/src/styles.css`. Re-build, verify visually at 1280×800 and at 768px width. Confirm `<h1>` and intro `<p>` are fully visible above the dropzone.

## Phase 10 — Verification + release

- **T-034** Local smoke check: load every tab — Home, Browse, Preview, Upload, Statistics, Create, Test Suites, Feedback. Open browser console; zero errors required.
- **T-035** Sanity-check Statistics: hagen (or known largest mesh) appears in top-5 by file size; refinement histogram is non-empty; contributor count > 0.
- **T-036** Sanity-check Test Suites: paste curl block in a temp dir; all 6 files download with HTTP 200.
- **T-037** Bump version `0.3.1` → `0.3.2` in `pyproject.toml` and `admesh_domains/__init__.py`.
- **T-038** Commit with conventional message (`feat: site polish + statistics/create/tests tabs + Mesh.test_case`). Push to `main`. Watch `pages.yml` and `validate-pr.yml` go green.
- **T-039** `git tag v0.3.2 && git push origin v0.3.2`. Watch `release.yml` complete (PyPI + HF tag).
- **T-040** Open the live site; click through every tab once.

## Acceptance Evidence Map

| Success Criterion | Producing Tasks |
|---|---|
| **SC-001** No overlap on Upload/Preview | T-032, T-033 |
| **SC-002** Statistics correct under 500ms | T-021, T-022, T-023, T-035 |
| **SC-003** Bulk download all 200s | T-029, T-030, T-036 |
| **SC-004** No phantom bboxes | T-019, T-020 |
| **SC-005** All tabs no console errors | T-009..T-013, T-026, T-027, T-029, T-030, T-034 |
| **SC-006** Push triggers deploy | T-007, T-038 |

## Out of scope (deferred from spec)

- Mission-statement final wording (awaiting wiki paste; T-018 uses placeholder).
- JS unit tests for new modules.
- Lighthouse / a11y CI.
- Custom domain.
