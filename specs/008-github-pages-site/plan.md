# Implementation Plan: GitHub Pages Site

**Branch**: `008-github-pages-site` | **Date**: 2026-04-26 | **Spec**: [spec.md](spec.md)

## Summary

A static site published from this repo via GitHub Pages. Three pillars:

1. **Browse** — searchable list/map of Domains and Meshes, deep-linkable URLs, download buttons that point at the HF dataset.
2. **Preview** — drag-drop a `.14` / `.2dm` / `.grd`, parse the bbox (and full mesh geometry in v1) entirely in-browser, overlay it on existing Domains.
3. **Contribute & Feedback** — guided form composes a pre-filled GitHub PR URL (contribute) or pre-filled issue URL (feedback). No backend, no API keys.

Implemented as **plain HTML + ES modules + a small JS bundle** (no framework). All registry data is baked at build time into a single `manifest.json`. Map is Leaflet + OSM. Mesh parsing is a pure-JS port of `bbox_from_fort14` / `bbox_from_2dm` plus a node/element parser for the geometry view.

Constitution alignment: TOML stays the source of truth (Principle I) — the build derives `manifest.json`, just like the publisher derives `manifest.parquet`. No new runtime deps in the Python package (Principle II) — the site lives under `site/` with its own toolchain. PRs remain the only mutation path (Principle VI — curation over auto-magic).

## Technical Context

- **Languages**: HTML, CSS, modern JS (ES2022 modules, no transpiler). Python 3.11+ for the build script.
- **Site root**: new top-level `site/` directory. No changes to the `admesh_domains` package itself.
- **Build**: a single Python script `scripts/build_site.py` (uses stdlib `tomllib` + `json`) reads `registry_data/manifest.toml` and writes `site/dist/manifest.json` plus copies static assets. No npm, no bundler, no Node toolchain. Total build time should be well under 10 seconds.
- **Map**: Leaflet 1.9 served from a pinned CDN URL with SRI hash (or vendored locally — decide in Phase 0).
- **Mesh parsing**: new `site/src/mesh-parser.js` (~150 lines) — direct port of `admesh_domains/geometry.py::bbox_from_fort14` and `bbox_from_2dm`, plus an `iter_elements()` generator for the geometry renderer.
- **Geometry rendering**: HTML `<canvas>` + plain 2D context for v1 (≤ ~200k elements). WebGL upgrade is a follow-up if perf demands it.
- **Suggester (client-side)**: port the IoU math from `geometry.py` (`area`, `intersection`, `union`, `compute_iou`, `per_mesh_iou`, `suggest_domain`) into `site/src/suggester.js`. All ~80 lines, pure functions.
- **Hosting**: GitHub Pages from `gh-pages` branch (deploy-from-action) or directly from `/site/dist` on `main` via the official Pages action. Pick in Phase 0.
- **Domain**: TBD (Q-7 deferred). Default `domattioli.github.io/ADMESH-Domains` works out of the box.
- **Analytics**: GoatCounter pixel (one `<script>` tag, no cookies). Deferred until launch.
- **Accessibility target**: WCAG 2.1 AA. Audited via `axe-core` CLI in CI.

## Project Structure

```text
site/
├── src/
│   ├── index.html            # home — totals, search, world map
│   ├── domain.html            # ?d=WNAT — domain detail
│   ├── mesh.html              # ?d=WNAT&m=hagen@v1 — mesh detail
│   ├── preview.html           # drag-drop preview
│   ├── contribute.html        # guided form -> GitHub PR URL
│   ├── feedback.html          # form -> GitHub issue URL
│   ├── styles.css
│   └── js/
│       ├── manifest-loader.js # fetch + cache manifest.json
│       ├── search.js          # client-side fuzzy search
│       ├── map.js             # Leaflet wrapper
│       ├── mesh-parser.js     # fort.14 / 2dm parser (port of geometry.py)
│       ├── suggester.js       # IoU + ranking (port of geometry.py)
│       ├── geometry-render.js # canvas mesh render
│       ├── pr-builder.js      # composes GitHub /new + /edit URLs
│       └── feedback.js        # composes GitHub /issues/new URL
├── tests/                     # Vitest or plain node:test — pick in Phase 0
│   ├── mesh-parser.test.js
│   ├── suggester.test.js
│   └── pr-builder.test.js
└── README.md                  # how to build + deploy locally

scripts/
└── build_site.py             # NEW — manifest.toml -> manifest.json + asset copy

.github/workflows/
└── pages.yml                 # NEW — build + deploy on push to main

specs/008-github-pages-site/
├── spec.md          # done
├── plan.md          # this file
├── data-model.md    # Phase 1 — manifest.json shape, URL schema, PR-builder contract
├── contracts/
│   └── pr-url-format.md  # Phase 1 — exact PR + issue URL schemes
├── quickstart.md    # Phase 1 — visitor + contributor walkthroughs
└── tasks.md         # Phase 2 — output of /tasks
```

## Phase 0 — Research

Quick verifications before scaffolding (each ≤ 30 min):

- **R-1** Confirm Leaflet renders correctly on GitHub Pages with `<base>` tag handling for project-page subpath (`/ADMESH-Domains/`). Spike: bare `index.html` with one marker.
- **R-2** Validate the GitHub PR pre-fill URL pattern. The `github.com/<owner>/<repo>/edit/main/<path>?value=...&message=...` and `github.com/<owner>/<repo>/new/main?filename=...&value=...` URLs accept query-string overrides — confirm length limits (browsers cap ~8 KB; a manifest entry diff is small enough). Document max-length fallback (copy-paste TOML).
- **R-3** Decide `gh-pages` branch vs. official `actions/deploy-pages@v4` from `main`. Latter is now the recommended path; pick it unless there's a blocker.
- **R-4** Pick test runner — Vitest (one npm dep) vs. node's built-in `node:test` (zero deps). Lean toward `node:test` to keep "no npm in repo root" — but Vitest gives nicer DX. Decide based on whether we want a `package.json` at all.
- **R-5** Confirm canvas geometry rendering at our largest current mesh (WNAT_Hagen, ~250k elements?). If too slow, fall back to bbox-only with a "geometry rendering coming soon" note + carry-over.
- **R-6** Lighthouse baseline run on the spike to confirm ≥ 90 perf score is reachable without a framework.

Output of Phase 0 → fold decisions back into this plan as a "Decisions" section before starting Phase 1.

## Phase 1 — Design Artifacts

- **`data-model.md`** — defines:
  - `manifest.json` shape: top-level totals, domains array (each with meshes array + flattened bbox cols), schema_version, generated_at. Mirrors the Parquet sidecar but JSON-shaped.
  - URL schema: `/`, `/domain.html?d=<name>`, `/mesh.html?d=<name>&m=<id>`, `/preview.html`, `/contribute.html`, `/feedback.html`. Deep-linkable via query strings (no hash routing).
  - PR-builder contract: input (form fields) → output (URL string). Template covers both "edit existing manifest" (add a Mesh under existing Domain) and "create new manifest fragment" (new Domain).
  - Feedback URL contract: input (category, body, page URL) → `/issues/new?...&labels=feedback,site` URL.

- **`contracts/pr-url-format.md`** — exact GitHub URL schemes used, length limits, how the TOML diff is rendered as the URL `value` parameter, what falls back to copy-paste mode.

- **`quickstart.md`** — three walkthroughs:
  1. Visitor: "I want to download the WNAT mesh" — 4 clicks.
  2. Reviewer: "I want to preview a mesh in this PR" — drag, drop, see overlay.
  3. Contributor: "I have a new mesh" — fill form → click → land on prefilled GitHub PR.

## Phase 2 — Tasks

Generated by `/tasks` from this plan. Expect ~25–35 tasks across:

- Build script + CI workflow (T-001..T-005)
- Static page scaffolding + nav + theming (T-006..T-012)
- Manifest loader + search + home page (T-013..T-016)
- Domain & Mesh detail pages (T-017..T-020)
- Map module (T-021..T-023)
- Mesh parser + tests (T-024..T-026)
- Suggester port + tests (T-027..T-028)
- Geometry renderer (T-029..T-031)
- Preview page wiring (T-032)
- Contribute form + PR builder + tests (T-033..T-036)
- Feedback form (T-037)
- A11y audit + Lighthouse + analytics (T-038..T-040)

## Risks & Mitigations

- **Geometry rendering blows the time budget.** If R-5 shows canvas can't keep up at 250k elements, drop FR-006's geometry stretch goal to bbox-only, file a follow-up spec, and ship the rest.
- **PR-prefill URL exceeds browser limits.** R-2 confirms; if a large new-Domain submission overflows, fall back to copy-paste TOML mode automatically.
- **GitHub Pages SPA-style deep links break on hard refresh.** Use real `.html` files per page (not hash routing) — sidesteps the problem entirely. Already in the plan.
- **Manifest grows 10×.** Search stays client-side up to ~500 meshes; beyond that, paginate or move to a prebuilt search index (Lunr.js). Cross that bridge when we hit it.
- **Spam via the prefill issue/PR URLs.** GitHub already auth-gates submission — nothing posted without the user clicking "Submit." Bots can't bypass that.

## Out of Scope (this plan)

- Custom domain DNS setup (Q-7 — pick before launch).
- Backend services of any kind.
- Editing existing manifest entries via UI.
- Server-side mesh validation beyond what `validate-pr.yml` already does.
- Mobile-app wrappers.

## Acceptance

Plan is "done" when:
- All Phase 0 research items resolved with documented decisions.
- `data-model.md`, `contracts/pr-url-format.md`, `quickstart.md` exist.
- `tasks.md` generated by `/tasks` with executable, ordered task list.
- Spec's SC-001..SC-006 each have at least one task that produces the evidence to verify them.
