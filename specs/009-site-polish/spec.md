# Feature Specification: Site Polish + New Tabs (Statistics, Create, Test Suites)

**Feature Branch**: `009-site-polish`
**Created**: 2026-04-26
**Status**: Clarified (2026-04-26) — awaiting `/plan`
**Input**: First-pass review of the live GitHub Pages site (deployed in spec 008) surfaced eight items: a layout bug on drag-drop pages, a redundant tab, a naming nit, three new content tabs, a missing mission statement, and a map-rendering correctness issue.

## Summary

Polish the static site published from spec 008 and add three new tabs without changing the registry data model or the publishing pipeline. Specifically:

1. Fix dropzone/heading overlap on Preview and Upload pages.
2. Drop the redundant **Browse** tab — Home already provides search + map + cards.
3. Rename **Contribute → Upload** (clearer to first-time visitors).
4. Add a **Statistics** tab — superlatives and aggregates derived client-side from `manifest.json`.
5. Add a 1–2 sentence **mission statement** to the Home page.
6. Stop plotting bounding boxes for non-geographic Domains on the world map.
7. Add a **Create** tab as an under-construction placeholder for future mesh-authoring tools (SAM-style waterbody selection, freehand draw → fort.14, NL → mesh).
8. Add a **Test Suites** tab listing the `TestCases` Domain meshes with direct download links and a bulk `curl`/`wget` snippet for use with `madmeshr` and local pytest fixtures.

The site remains static. No backend, no PyPI version bump (data/site changes don't bump the package per CLAUDE.md). A single commit to `main` triggers `pages.yml` and the site redeploys.

## Goals

- Address visible UX issues from the first review pass before broader announcement.
- Surface non-obvious value in the registry (Statistics, Test Suites) so visitors see *why* the registry is useful, not just *what's in it*.
- Reserve a slot (Create) for the upcoming authoring tools so visitors know they're coming.
- Keep all aggregation client-side — `manifest.json` is already in the bundle.

## Non-Goals

- Implementing the Create tools themselves (tracked in issues #1 NL→fort.14, #2 draw→fort.14).
- Adding a backend, database, or auth.
- Bumping the PyPI package version — purely site/data work.
- Reworking the build pipeline (`scripts/build_site.py` may grow new copies but not new logic).

## User Scenarios & Testing

### User Story 1 — Visitor can read headings on the upload form (Priority: P1)

A first-time contributor opens the Upload page; the heading and intro paragraph are not obscured by the drag-drop area or the map preview.

**Why this priority**: Blocks core contribution flow; first-impression bug.

**Acceptance Scenarios**:

1. **Given** the Upload page on a 1280×800 viewport, **When** the page loads, **Then** the `<h1>` and intro `<p>` are fully visible above the dropzone with no overlap.
2. **Given** the Preview page, **When** the visitor scrolls, **Then** no canvas/map element overlaps the page heading at any scroll position.

---

### User Story 2 — Modeler explores registry superlatives (Priority: P2)

A modeler lands on the new **Statistics** tab and sees, at a glance: largest meshes by node/element/file size, refinement-level histogram, license + application coverage, and total registry size.

**Why this priority**: Demonstrates registry breadth/depth in one screen — turns an opaque list into a story.

**Acceptance Scenarios**:

1. **Given** the Statistics page, **When** it loads, **Then** the user sees top-5 lists for largest mesh by node count, by element count, and by file size — populated from `manifest.json`.
2. **Given** the same page, **When** rendered, **Then** a refinement-level histogram, an application-tag distribution, and a license breakdown appear, each with counts.
3. **Given** the page, **When** rendered, **Then** the total node count, element count, file bytes, and contributor count are visible.

---

### User Story 3 — Researcher fetches the test mesh suite (Priority: P2)

A researcher building a mesh-tooling library (e.g. `madmeshr`) wants the canonical small/abstract test meshes to wire into pytest fixtures. They open **Test Suites**, copy the bulk `curl` block, and run it locally.

**Why this priority**: Concrete, reusable artifact for downstream library authors — a primary persona.

**Acceptance Scenarios**:

1. **Given** the Test Suites page, **When** it loads, **Then** every mesh in the `TestCases` Domain is listed with name, node count, file size, and a direct HF download URL.
2. **Given** the same page, **When** the visitor clicks "Copy bulk download", **Then** a `curl`/`wget` snippet covering all test meshes is copied to clipboard.
3. **Given** any link in the list, **When** clicked, **Then** the browser begins downloading the file from HuggingFace (HTTP 200).

---

### User Story 4 — Visitor previews future tooling on Create tab (Priority: P3)

A visitor clicks **Create**, sees a clear "Coming Soon" page describing the planned tools and pointing to the tracking issues, and is not confused into thinking the feature is broken.

**Acceptance Scenarios**:

1. **Given** the Create page, **When** loaded, **Then** the heading explicitly says "Coming Soon" or equivalent.
2. **Given** the page, **When** loaded, **Then** at least one link to GitHub issue #1 or #2 is present.

---

### User Story 5 — World map shows only real-world domains (Priority: P2)

A visitor on the Home page sees rectangles only for Domains with geographic coordinates; synthetic/abstract Domains (TestCases, BaranjaHill UTM) do not get phantom bboxes.

**Acceptance Scenarios**:

1. **Given** a Domain whose meshes are all non-geographic, **When** the Home page map renders, **Then** no rectangle is drawn for that Domain.
2. **Given** a Domain with mixed geographic/non-geographic meshes, **When** the map renders, **Then** the union bbox is computed only over the geographic subset.

---

### User Story 6 — Visitor learns the project's mission in one sentence (Priority: P3)

A first-time visitor lands on Home and reads a short mission statement above the totals.

**Acceptance Scenarios**:

1. **Given** the Home page, **When** loaded, **Then** a 1–2 sentence mission paragraph appears above the `.totals` block.

---

### User Story 7 — Navigation matches site content (Priority: P3)

The top nav reflects the new structure: no Browse duplicate, **Upload** instead of Contribute, plus Statistics, Create, Test Suites.

**Acceptance Scenarios**:

1. **Given** any page, **When** the header renders, **Then** the nav contains exactly: Home, Preview, Upload, Statistics, Create, Test Suites, Feedback.
2. **Given** a deep-link to `/contribute.html`, **When** loaded, **Then** the visitor sees content (either the renamed page or a redirect to `/upload.html`).

---

## Functional Requirements

- **FR-001**: The Preview and Upload pages MUST render the page heading and intro text without overlap from the dropzone, map, or canvas at common viewport sizes (≥768px wide).
- **FR-002**: The site nav MUST list: Home, Browse, Preview, Upload, Statistics, Create, Test Suites, Feedback. Browse is retained as the full search-and-list view; Home is trimmed (see FR-005a).
- **FR-003**: The Contribute page MUST be renamed to Upload — the file `contribute.html` becomes `upload.html`, the JS module `contribute.js` becomes `upload.js`, and all references update.
- **FR-004**: The Statistics page MUST display, computed client-side from `manifest.json`:
  - top-5 meshes by node count, by element count, and by file size,
  - distribution of `refinement_level` values,
  - distribution of `license` values,
  - distribution of `application` tags (across all Domains' meshes),
  - aggregate totals: domain count, mesh count, total bytes, total node count, contributor count.
- **FR-005**: The Home page MUST include a 1–2 sentence mission statement (sourced from the ADMESH wiki, pending exact wording) above the totals block.
- **FR-005a**: The Home page MUST be trimmed to a landing/marketing layout: mission statement, world map, totals, and a small high-level superlatives block (e.g. top 3 contributors, largest mesh, most refined). The full search input, domain card grid, and table view MUST move to the Browse page. Home MUST link to Browse for full discovery.
- **FR-005b**: The Browse page (`browse.html`) MUST replace its current meta-refresh redirect with a real explore view containing the search input, domain card grid, and (optionally) a sortable flat table of all meshes.
- **FR-006**: The Home page world map MUST NOT plot a bounding box for any Domain whose meshes are entirely non-geographic. Mixed Domains MUST plot only the union of their geographic meshes.
- **FR-007**: The Create page MUST exist with: (a) a functional file-upload field accepting `.14`/`.2dm`, (b) a mock-terminal output panel (styled `<pre>`, not a live shell) that displays placeholder/example commands and any client-side validation messages from the uploaded file, (c) clear "Coming Soon" messaging for the authoring tools, and (d) at least one link to tracking issue #1 or #2.
- **FR-008**: The Test Suites page MUST list every mesh whose `test_case` flag is `true` (across any Domain), with: filename, node count, file size, and a direct HuggingFace download URL.
- **FR-008a**: The `admesh_domains.schema.Mesh` dataclass MUST gain an additive `test_case: bool = False` field. Existing TestCases-domain meshes MUST be backfilled with `test_case = true` in `registry_data/manifest.toml` and `admesh_domains/data/manifest.toml`. `SCHEMA_VERSION` MUST NOT be bumped (additive change). The site build (`scripts/build_site.py`) MUST propagate the field into `manifest.json`.
- **FR-009**: The Test Suites page MUST provide a one-click "copy bulk download" action emitting a multi-line snippet that fetches every test-case mesh, with a UI toggle between `curl` (default) and `wget`.
- **FR-010**: The build (`scripts/build_site.py`) MUST copy all new HTML/JS assets into `site/dist/` without manual configuration.
- **FR-011**: A PyPI version bump IS required for this work because of FR-008a (schema change). Bump from 0.3.1 → 0.3.2 in both `pyproject.toml` and `admesh_domains/__init__.py`. *(Updated from initial draft after Q-5 clarification — adding a schema field is code, not pure data.)*
- **FR-012**: The repo `README.md` MUST link to the live site near the top of the file. The link MUST use the `https://domattioli.github.io/ADMESH-Domains/` URL — this is the durable form even if a custom domain is later added, because GitHub Pages preserves the `*.github.io` URL as a permanent 301 redirect when CNAME is configured.

## Success Criteria

- **SC-001**: A visitor inspecting the Upload or Preview page in any current browser at 1280×800 sees no element overlapping the page heading. *(FR-001)*
- **SC-002**: The Statistics page loads in under 500ms after `manifest.json` is cached and shows correct numbers verifiable against a 30-second manual check (e.g. "hagen" appears in the top-5 by file size). *(FR-004)*
- **SC-003**: The Test Suites page's bulk-download snippet, pasted into a clean shell, fetches every TestCases mesh with all HTTP statuses 200. *(FR-008, FR-009)*
- **SC-004**: The Home map shows zero rectangles attributable to TestCases or other purely non-geographic Domains. *(FR-006)*
- **SC-005**: All renamed/new tabs render with no console errors on first load. *(FR-002, FR-003, FR-007)*
- **SC-006**: A push to `main` triggers `pages.yml` and deploys all changes (no manual steps). *(FR-010)*

## Clarifications

### Session 2026-04-26

- **Q-1**: Browse tab → **kept** as the full list/explore view; Home is trimmed to mission + world map + high-level superlatives (totals, top contributors, headline stats). Search + cards + table live on Browse.
- **Q-2**: Statistics → **charts via tiny CDN library** (uPlot, ~40KB, no deps — preferred over Chart.js for size).
- **Q-3**: Statistics → **show contributor count + names** with mesh counts.
- **Q-4**: Create page → **functional file-upload field + mock-terminal output panel** (styled `<pre>` showing example/placeholder commands; not a real shell). Tracking issues #1/#2 still linked.
- **Q-5**: Test Suites → **add a mesh-level boolean `test_case` field** to `schema.Mesh`. Additive change, no `SCHEMA_VERSION` bump. Existing TestCases-domain meshes get `test_case = true`; site filters by this flag (not by domain name).
- **Q-6**: Test Suites bulk-download → **show curl by default with a toggle to wget**.
- **Q-7**: Mission statement → **pull verbatim from the ADMESH project wiki** (https://github.com/domattioli/ADMESH/wiki). The wiki was inaccessible at clarification time (404); user will paste exact wording before `/tasks`. Placeholder draft: "ADMESH-Domains is the open registry of ADCIRC-compatible mesh domains for the [ADMESH](https://github.com/domattioli/ADMESH) project — a curated catalog for coastal modeling, hydrodynamics research, and reproducible simulation."
- **Q-8**: Old `/contribute.html` → **meta-refresh redirect to `/upload.html`**.

## Open Questions

- **Q-7 follow-up**: User to paste the exact mission-statement wording from the ADMESH wiki (https://github.com/domattioli/ADMESH/wiki) before `/tasks`. Until then the FR-005 placeholder draft stands.

## Dependencies

- Site infrastructure from spec 008 (build script, `pages.yml`, `manifest.json` schema).
- HuggingFace dataset `domattioli/ADMESH-Domains` for Test Suites download URLs.
- No new Python packages, no new JS libraries.

## Constitution Check

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest is source of truth | PASS | Site displays manifest; adds `test_case` field (additive, no schema version bump) |
| II. Pure-Python, optional heavy deps | N/A | Static site; adds uPlot JS library (~40KB, no Python deps) |
| III. Schema changes are explicit | PASS | Adds `test_case: bool` field to Mesh; additive, no SCHEMA_VERSION bump |
| IV. Atomic releases — and separate code from data | N/A | Site-only; no PyPI bump, deployed via `pages.yml` on push to main |
| V. Test before tagging | PASS | Site builds on every push; no new dependencies to test |
| VI. Curation over auto-magic | PASS | Test Suites manually curated; Create page is placeholder |
| VII. External Upstream (DomI) | PASS | No DomI interaction changes |
