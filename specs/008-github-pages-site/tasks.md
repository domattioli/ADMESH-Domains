# Tasks: GitHub Pages Site

**Branch**: `008-github-pages-site` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Tasks are ordered. `[P]` = can run in parallel with the prior task. Each task is independently testable.

## Phase 0 — Research spikes

- **T-001** Spike: bare `site/dist/index.html` with one Leaflet marker, deployed via Pages action, confirm subpath (`/ADMESH-Domains/`) works. Document outcome in plan.md "Decisions" section. (R-1, R-3)
- **T-002** [P] Spike: hand-build a GitHub PR-prefill URL for the smallest plausible Mesh-add diff and the largest plausible new-Domain diff. Measure URL length; document the cutoff at which we fall back to copy-paste. (R-2)
- **T-003** [P] Spike: render WNAT_Hagen mesh on a 1200×800 canvas; record FPS + first-paint time. Decide whether canvas suffices for v1 or geometry rendering must drop scope. (R-5)
- **T-004** [P] Decide test runner (`node:test` vs Vitest) and whether the repo gets a `package.json` at the root. Document. (R-4)
- **T-005** Lighthouse baseline on the T-001 spike. Confirm ≥ 90 perf is reachable; if not, identify blockers. (R-6)

## Phase 1 — Build script + CI

- **T-006** Write `scripts/build_site.py`: reads `registry_data/manifest.toml`, writes `site/dist/manifest.json` with the shape defined in `data-model.md`. Stdlib only. Includes `schema_version`, `generated_at`, totals, full domain/mesh tree.
- **T-007** [P] Write `scripts/build_site.py` asset-copy logic: copy `site/src/**` → `site/dist/**`, preserve structure, hash-bust `styles.css` and JS modules.
- **T-008** Add unit test `tests/test_build_site.py` — feeds a minimal manifest fixture, asserts the resulting JSON validates against the documented shape and counts match.
- **T-009** Write `.github/workflows/pages.yml`: triggers on push to `main` when `registry_data/manifest.toml`, `admesh_domains/data/manifest.toml`, or `site/**` changes. Runs `python scripts/build_site.py`, then `actions/upload-pages-artifact@v3` + `actions/deploy-pages@v4`.
- **T-010** Add the workflow's required Pages permissions block (`pages: write`, `id-token: write`) and concurrency guard (one deploy at a time).

## Phase 2 — Static scaffolding + theming

- **T-011** Create `site/src/styles.css`: minimal theme, CSS custom properties for colors, `prefers-color-scheme: dark` override, system font stack.
- **T-012** [P] Create `site/src/_partials/nav.html` (or inline-include script) with Home / Browse / Preview / Contribute / Feedback links. Add to all pages.
- **T-013** Create `site/src/index.html`: totals (domains, meshes, size), search box, world map placeholder, footer with repo/HF/PyPI links + BibTeX.
- **T-014** [P] Create stub pages: `domain.html`, `mesh.html`, `preview.html`, `contribute.html`, `feedback.html` — header, nav, empty `<main>`, footer.

## Phase 3 — Browse: manifest loader, search, detail pages

- **T-015** Write `site/src/js/manifest-loader.js`: `loadManifest()` fetches `manifest.json` once and caches in `sessionStorage` keyed by `schema_version + generated_at`.
- **T-016** Write `site/src/js/search.js`: client-side filter over domains + meshes by name, full_name, region, application, license. Debounced 100ms.
- **T-017** Wire search into `index.html`: type to filter the visible Domain cards. Empty state + result count.
- **T-018** Implement `domain.html`: read `?d=<name>` from URL, hydrate page with metadata + Mesh table. Each row has a "Download" link to `https://huggingface.co/datasets/domattioli/ADMESH-Domains/resolve/main/meshes/<Domain>/<filename>`.
- **T-019** [P] Implement `mesh.html`: read `?d=<name>&m=<id>` from URL, hydrate full mesh metadata + bbox preview map + download.
- **T-020** Add 404 fallback (`site/src/404.html`) — searches by URL slug, redirects if a fuzzy match exists.

## Phase 4 — Map module

- **T-021** Write `site/src/js/map.js`: thin wrapper around Leaflet. `createMap(elementId, opts)`, `addBboxLayer(bboxes, opts)` (rectangle per real-world Domain), `highlight(domainName)`.
- **T-022** Wire the home-page map: render every real-world Domain's bbox; click a rectangle → navigate to that Domain page. Mirrors `bbox_map.png` but interactive.
- **T-023** Wire mesh.html bbox preview using `addBboxLayer` with a single rectangle.

## Phase 5 — Mesh parser + suggester (JS port)

- **T-024** Write `site/src/js/mesh-parser.js`: port `bbox_from_fort14`, `bbox_from_2dm`, `bbox_from_mesh_file` (extension dispatch). Same return shape as Python (`{minLon, minLat, maxLon, maxLat}` or `null`).
- **T-025** Add `iter_elements()` generator to `mesh-parser.js` — yields `[n1, n2, n3]` triangle indices. Returns lazily so the renderer can stream.
- **T-026** Write `site/tests/mesh-parser.test.js`: cases mirroring `tests/test_geometry.py::TestMeshFileParsing`. Use known fixtures (small synthetic + a snippet of WNAT_Hagen).
- **T-027** Write `site/src/js/suggester.js`: port `area`, `intersection`, `union`, `compute_iou`, `domain_union_bbox`, `per_mesh_iou`, `suggest_domain` from `geometry.py`. Same thresholds (`CONFIDENT_THRESHOLD = 0.5`, `UNCERTAIN_THRESHOLD = 0.05`).
- **T-028** Write `site/tests/suggester.test.js`: parity check against `test_geometry.py::TestSuggestDomain` using the same WNAT/ChesapeakeBay/Pacific fixtures. Rank-1 must match the Python version.

## Phase 6 — Geometry renderer

- **T-029** Write `site/src/js/geometry-render.js`: `renderMesh(canvas, nodes, elements, bbox)` — projects lon/lat to canvas, draws element edges, fits to bbox, caps at 200k elements with a "(showing first N elements)" banner if exceeded.
- **T-030** Add zoom + pan via pointer events. No external deps.
- **T-031** Document a fallback path in `geometry-render.js` — if T-003 spike showed canvas too slow at our scale, this module renders bbox-only and emits a console note.

## Phase 7 — Preview page

- **T-032** Wire `preview.html`: drag-and-drop or `<input type=file>`, parse via `mesh-parser.js`, render bbox on map alongside existing Domains, run `suggester.js`, list rank-1..3 candidates with IoU scores, render geometry on canvas (per T-029). Show clear error UI on parse failure.

## Phase 8 — Contribute flow

- **T-033** Write `site/src/js/pr-builder.js`: takes form fields → emits a TOML fragment matching the manifest schema → composes a `github.com/.../edit/main/registry_data/manifest.toml?value=...` URL. If new-Domain mode, generates the full `[[domains]]` block.
- **T-034** Add a length-check helper in `pr-builder.js`: if URL > 7000 bytes, emit a "copy-paste mode" instead with a copy button + step-by-step instructions.
- **T-035** Wire `contribute.html`: file drop → parse bbox → run suggester → form pre-fills with rank-1 Domain. User edits, clicks "Open PR" → opens PR URL in a new tab.
- **T-036** Write `site/tests/pr-builder.test.js`: known input → exact expected URL (snapshot). Plus a length-overflow test that triggers the copy-paste fallback.

## Phase 9 — Feedback

- **T-037** Wire `feedback.html`: form (category radio: bug/suggestion/question/other; body textarea; optional contact). Submit composes `github.com/<owner>/<repo>/issues/new?title=...&body=...&labels=feedback,site` URL with the current page URL auto-prefixed in the body. Open in new tab.

## Phase 10 — A11y, perf, analytics

- **T-038** Run `axe-core` against every page in CI; fail on serious/critical violations. Add to `pages.yml` as a pre-deploy step.
- **T-039** [P] Run Lighthouse against the deployed Pages URL in CI; assert mobile + desktop perf ≥ 90. Save reports as workflow artifacts.
- **T-040** Add GoatCounter `<script>` tag (single line, no cookies) to all pages once a tracking ID is provisioned. Stub the ID via a build-time env var so it's empty on PR previews.

## Phase 11 — Docs + launch

- **T-041** Update `CLAUDE.md` with a "Site" section: how to build locally (`python scripts/build_site.py && python -m http.server -d site/dist`), where pages.yml lives, how to bump if the manifest schema changes.
- **T-042** Update top-level `README.md` to link to the Pages URL once live.
- **T-043** [P] Add a "Browse online" badge + link to the HF dataset card.
- **T-044** Resolve Q-7 (custom domain). If chosen, configure DNS + add `site/src/CNAME`. Otherwise document the default URL and close out.

## Acceptance evidence map

Each spec success criterion → tasks producing the evidence:

- **SC-001** (find + download in 30s) → T-013, T-015, T-018
- **SC-002** (commit-to-publish ≤ 5 min) → T-006, T-009, T-010
- **SC-003** (preview rank-1 = actual Domain, parity with CLI) → T-027, T-028, T-032
- **SC-004** (Lighthouse ≥ 90) → T-005, T-039
- **SC-005** (home renders if HF down) → T-006 (manifest baked into bundle), T-022 (map uses local data)
- **SC-006** (no secrets in bundle) → CI scan in T-009 (add `gitleaks` or `trufflehog` step)
