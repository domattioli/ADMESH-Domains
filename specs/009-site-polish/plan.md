# Implementation Plan: Site Polish + New Tabs

**Branch**: `009-site-polish` | **Date**: 2026-04-26 | **Spec**: [spec.md](spec.md)

## Summary

Iterative polish on the static site shipped in spec 008, plus three new tabs (Statistics, Create, Test Suites) and one additive schema change (`Mesh.test_case: bool`). All site code stays plain HTML + ES modules + a single Python build script. One new CDN dep: **uPlot** (~40KB, no transitive deps) for charts on Statistics. PyPI bump 0.3.1 → 0.3.2 because the schema gains a field.

Constitution alignment: TOML stays the source of truth (Principle I) — `manifest.toml` gains `test_case = true` on test meshes, and the build still derives `manifest.json`. No new runtime Python deps (Principle II) — uPlot is browser-only, loaded via CDN. PRs remain the only mutation path (Principle VI).

## Technical Context

- **Languages**: HTML, CSS, ES2022 modules, Python 3.11+ for the build script. No new toolchain.
- **Site root**: existing `site/`. New files only; one rename (`contribute.* → upload.*`); one redirect kept (`contribute.html` meta-refresh).
- **Build**: extend `scripts/build_site.py` to emit `test_case` into `manifest.json`. No structural changes.
- **Charts**: uPlot 1.6.x via unpkg with SRI hash. Loaded only on `statistics.html`.
- **Schema change**: `admesh_domains.schema.Mesh` gains `test_case: bool = False`. Additive — `SCHEMA_VERSION` stays at current value. Validation accepts missing field as `False`.
- **Manifest backfill**: existing TestCases-domain meshes (6 in `TestCases`) get `test_case = true` in both `registry_data/manifest.toml` and `admesh_domains/data/manifest.toml`.
- **CSS fix (item 1)**: identify the actual overlapping element on Preview/Upload by viewing in browser; likely a missing `margin-top` on the dropzone wrapper or an `#map`/`#geometry-canvas` height issue.
- **Home trim (FR-005a)**: move `#search`, `#domain-cards`, table view from `index.html` into `browse.html`. Home keeps mission, totals, world map, and a new small superlatives block.
- **Browse page (FR-005b)**: replace meta-refresh with real content. Same JS modules as old Home (manifest-loader, search, map).
- **Statistics page**: client-side aggregation in `js/statistics.js` from `manifest.json`. uPlot for histograms (refinement, license, application). Top-5 lists as plain tables.
- **Create page**: file-upload field reuses `mesh-parser.js` from spec 008. A `<pre id="terminal">` panel shows mock-styled placeholder output and any parser errors. No real shell.
- **Test Suites page**: filter `manifest.json` meshes by `test_case === true`. Render table + bulk-download snippet with curl/wget toggle.
- **PyPI release**: standard `git tag v0.3.2 && git push origin v0.3.2` triggers `release.yml`.

## Project Structure

```text
site/src/
├── index.html              # MODIFIED — trimmed: mission + map + superlatives
├── browse.html             # REPLACED — real explore view (was meta-refresh)
├── upload.html             # RENAMED from contribute.html
├── contribute.html         # REPLACED — meta-refresh redirect → /upload.html
├── statistics.html         # NEW
├── create.html             # NEW
├── tests.html              # NEW (Test Suites)
├── styles.css              # MODIFIED — fix overlap; styles for terminal, charts
└── js/
    ├── nav.js              # MODIFIED — new PAGES list
    ├── map.js              # MODIFIED — guard against domains with zero geographic meshes
    ├── upload.js           # RENAMED from contribute.js
    ├── browse.js           # NEW (extracted from old index.js logic)
    ├── statistics.js       # NEW
    ├── create.js           # NEW
    └── tests.js            # NEW

scripts/
└── build_site.py           # MODIFIED — propagate test_case into manifest.json

admesh_domains/
├── schema.py               # MODIFIED — Mesh.test_case: bool = False
└── data/manifest.toml      # MODIFIED — backfill test_case = true (6 meshes)

registry_data/
└── manifest.toml           # MODIFIED — backfill test_case = true (6 meshes)

tests/
└── test_schema.py          # MODIFIED — assert new field defaults False, accepts True

pyproject.toml              # MODIFIED — 0.3.1 → 0.3.2
admesh_domains/__init__.py  # MODIFIED — 0.3.1 → 0.3.2
README.md                   # already updated (site link added)
```

## Phasing

### Phase 0 — Spikes (skip; all known patterns)
The CSS overlap fix needs a quick browser inspect, but no upfront research. uPlot API is well-documented; one-time read.

### Phase 1 — Schema + manifest backfill (Python)
- T-001: Add `Mesh.test_case: bool = False` in `admesh_domains/schema.py`.
- T-002: Update `Mesh.from_toml` (or equivalent) to read the new field with default.
- T-003: Backfill `test_case = true` on 6 TestCases meshes in both `manifest.toml` files.
- T-004: Extend `tests/test_schema.py` with default-False and True cases.
- T-005: Run `pytest tests/` — must stay green.

### Phase 2 — Build script (Python)
- T-006: Update `scripts/build_site.py` to emit `test_case` per mesh in `manifest.json`.
- T-007: Run `python scripts/build_site.py` — verify `site/dist/manifest.json` contains `test_case: true` on TestCases meshes.

### Phase 3 — Nav + rename (low-risk shuffle)
- T-008: Rename `site/src/contribute.html` → `upload.html`; update internal `<script>` ref + `<title>`.
- T-009: Rename `site/src/js/contribute.js` → `upload.js`; no logic changes.
- T-010: Replace `site/src/contribute.html` with a meta-refresh redirect to `/upload.html`.
- T-011: Update `PAGES` in `site/src/js/nav.js`: `Home, Browse, Preview, Upload, Statistics, Create, Test Suites, Feedback`.
- T-012: Update `site/README.md` page list.

### Phase 4 — Home trim + Browse build-out
- T-013: Move search input + domain card grid markup from `index.html` to `browse.html`. Add a sortable flat-table view to `browse.html`.
- T-014: Add `js/browse.js` (extracted/copied logic from current `index.js`).
- T-015: Trim `index.html`: keep `<h1>`, mission `<p>`, `.totals`, `#map`, new `#superlatives` block. Remove search and card grid.
- T-016: Add `#superlatives` rendering in `js/index.js` (or split into `js/home.js`): top-3 contributors with mesh counts, largest mesh, most refined mesh.
- T-017: Insert mission statement (placeholder until user pastes wiki text).

### Phase 5 — Map correctness
- T-018: In `js/map.js::addDomainBboxes`, skip any domain whose filtered (geographic) mesh list is empty. Verify on Home with TestCases and BaranjaHill.

### Phase 6 — Statistics page
- T-019: Create `statistics.html` with uPlot CDN + SRI, header/footer slots, container divs for top-5 tables and chart canvases.
- T-020: Create `js/statistics.js` — load manifest, compute aggregates: top-5 by node/element/size, refinement histogram, license/application distributions, contributor list with counts, totals.
- T-021: Render top-5 tables (plain HTML), uPlot bar charts for distributions.
- T-022: Add `.stat-section`, `.uplot` styles to `styles.css`.

### Phase 7 — Create page
- T-023: Create `create.html` with `<h1>Create — Coming Soon</h1>`, intro copy, file-upload `<input type="file">`, `<pre id="terminal">` panel, links to issues #1/#2.
- T-024: Create `js/create.js` — on file upload, run `bboxFromFile` + `parseFort14Full` from existing modules; pipe results and errors into the terminal `<pre>` with mock-shell styling.
- T-025: Add `.terminal` styles to `styles.css` (dark bg, monospace, scrollable).

### Phase 8 — Test Suites page
- T-026: Create `tests.html` with table container, curl/wget toggle UI, copy button.
- T-027: Create `js/tests.js` — load manifest, filter by `m.test_case === true`, render table.
- T-028: Implement bulk-download snippet generator: produce `curl -L -O <url>` per mesh (and `wget <url>` variant); copy-to-clipboard.

### Phase 9 — CSS overlap fix
- T-029: Build site, serve locally, inspect Preview + Upload pages, identify the overlapping element, add the fix in `styles.css`.

### Phase 10 — Verification + release
- T-030: Local smoke check: `python scripts/build_site.py && python -m http.server -d site/dist 8000` — load every tab, confirm no console errors.
- T-031: Manual sanity: Statistics numbers (e.g. hagen in top-5 by size); Test Suites bulk snippet pasted into shell returns 200s.
- T-032: Bump version 0.3.1 → 0.3.2 in `pyproject.toml` + `__init__.py`.
- T-033: Commit with conventional message; push to `main`; watch `pages.yml` + `validate-pr.yml`.
- T-034: `git tag v0.3.2 && git push origin v0.3.2`; watch `release.yml` (PyPI + HF tag).

## Risks

- **Schema additive but downstream parsers**: any external consumer reading `manifest.toml` strictly will ignore unknown keys (TOML semantics are forgiving). Risk low.
- **uPlot CSS conflicts**: uPlot ships its own minimal CSS. Scope its load to `statistics.html` only.
- **Home trim regression**: search-on-home is a current entry point. Mitigation: Home prominently links to Browse, and `browse.html` URL is the same one that was already in nav.
- **CSS fix is unscoped until inspected**: if the actual cause is more complex (e.g. flex shrink issue on small viewports), allow up to one extra revision pass.

## Out of scope

- Custom domain (Q-7 from spec 008 still deferred).
- Real Pyodide REPL on Create (decided: mock terminal only).
- JS unit tests (still deferred from spec 008).
- Lighthouse / a11y CI (still deferred).
