# Feature Specification: GitHub Pages Site for Browsing, Previewing, and Contributing Domain Files

**Feature Branch**: `008-github-pages-site`
**Created**: 2026-04-26
**Status**: Clarified (2026-04-26) — awaiting `/plan`
**Input**: A GitHub Pages website where users can upload, download, and preview ADMESH domain/mesh files — making the registry discoverable to people who don't live in a terminal.

## Summary

Stand up a static site published from this repo via GitHub Pages that lets a visitor:

1. **Browse** the registry — a searchable, filterable list/map of all Domains and their Meshes, sourced from the canonical `manifest.toml` (or its derived `manifest.parquet` on HuggingFace).
2. **Preview** a mesh — render its bounding box on a world map, show metadata (node count, element type, license, contributor), and (stretch) draw the actual mesh geometry in-browser.
3. **Download** a mesh file — a one-click link that pulls the underlying file from the HuggingFace dataset (`domattioli/ADMESH-Domains`), since the wheel deliberately doesn't bundle mesh files.
4. **Contribute** a new mesh — a guided form that walks a contributor through the metadata fields, runs the auto-suggester (spec 007) client-side or via a hosted API, and either (a) opens a pre-filled GitHub PR against `registry_data/manifest.toml` or (b) emits a paste-ready TOML stub the contributor commits themselves.

The site is **static** (no backend server we have to operate) and rebuilds automatically whenever the manifest changes.

## Goals

- Make the registry usable for non-CLI users (coastal modelers, students, reviewers).
- Keep the registry's source of truth unchanged — the site is a *view*, not a parallel store.
- Avoid operational burden — no servers, no databases, no API keys held by the site.
- Reuse existing artifacts: `manifest.parquet`, `bbox_map.png`, the HF dataset card, and the auto-suggester logic.

## Non-Goals

- Hosting raw mesh files ourselves (HuggingFace already does this; we link out).
- User accounts, authentication, or per-user state.
- Editing or deleting existing meshes via the UI (PRs against the manifest remain the only mutation path).
- Running ADCIRC simulations in the browser.
- Real-time collaboration / multi-user editing.

## User Scenarios & Testing

### User Story 1 — Modeler discovers a regional mesh (Priority: P1)

A coastal modeler searches "Chesapeake" and lands on the site. They see the `ChesapeakeBay` Domain card, click it, see the list of meshes with node counts and bbox preview, and download `Chesapeake_Bay.14` directly.

**Why this priority**: Core value prop. If discovery + download doesn't work, the rest is decoration.

**Independent Test**: From a clean browser, navigate to the site, search for an existing Domain, click through, and download a real mesh file from HF.

**Acceptance Scenarios**:

1. **Given** the published site, **When** a visitor searches "WNAT", **Then** the WNAT Domain card and its 4 meshes appear within 1 second.
2. **Given** a Domain page, **When** the visitor clicks "Download" on a mesh, **Then** the browser fetches the file from `https://huggingface.co/datasets/domattioli/ADMESH-Domains/resolve/main/meshes/<Domain>/<filename>`.
3. **Given** a mesh card, **When** the visitor hovers/clicks the bbox preview, **Then** an interactive map shows the bbox highlighted on a world basemap.

---

### User Story 2 — Reviewer previews a PR's new mesh (Priority: P2)

A reviewer wants to see where a proposed new mesh sits geographically before approving the PR. They paste the mesh's bbox (or upload the file) into a "Preview" page and see it overlaid on existing Domains.

**Why this priority**: Speeds up review without requiring local CLI install.

**Acceptance Scenarios**:

1. **Given** the preview page, **When** the reviewer uploads a `.14` file, **Then** the bbox is parsed in-browser and rendered on the same map as existing Domains, with the suggester's rank-1 candidate highlighted.
2. **Given** the same upload, **When** parsing fails (bad header, projected coords), **Then** a clear error tells the reviewer what went wrong and links to the file-format docs.

---

### User Story 3 — Contributor submits a new mesh (Priority: P3)

A new contributor has a `.14` file but doesn't know how to fill out the manifest. They open the "Contribute" page, drop the file, fill a guided form (name, license, contributor, applications), see the suggested Domain, and click "Open PR" which pre-fills a GitHub PR against `registry_data/manifest.toml`.

**Why this priority**: Lowers contribution friction but is fully covered today by the CLI workflow. Worth doing — not the first milestone.

**Acceptance Scenarios**:

1. **Given** the contribute page, **When** the contributor completes the form and clicks "Open PR", **Then** a new browser tab opens GitHub's PR-creation page with a pre-filled diff adding the mesh entry to `manifest.toml`.
2. **Given** an incomplete form, **When** the contributor clicks "Open PR", **Then** missing required fields are flagged inline and the button is disabled.
3. **Given** a "no match" suggester result, **When** the contributor proceeds, **Then** the form expands to also collect new-Domain fields (full_name, category, region, applications).

---

### User Story 4 — Anyone bookmarks the dataset (Priority: P3)

A researcher cites the registry in a paper and wants a stable URL with a human-readable summary, totals, and a citation block.

**Acceptance Scenarios**:

1. **Given** the home page, **When** a visitor scrolls to the bottom, **Then** a BibTeX block matching the HF dataset card appears with a copy button.
2. **Given** any Domain or Mesh page, **When** the URL is shared, **Then** the page loads as a deep link without requiring search/navigation.

## Edge Cases

- **Manifest grows large.** Today: 13 Domains / 41 meshes / 62 MB. The site must stay snappy at 10× this size — search / filter must remain client-side without lag, OR fall back to paginated views.
- **Mesh file not yet on HF.** A new mesh in a PR isn't on HF until merge + data-publish workflow runs. The site should clearly distinguish "manifest entry exists, file pending publish" from "fully available."
- **Antimeridian-wrapping bbox** (deferred per spec 007 / issue #4). The map preview should not draw a degenerate world-spanning rectangle; show a warning + link to the issue.
- **Synthetic / projected-coord meshes.** No lat/lon → no map preview; the page should show metadata only with an explanatory note.
- **HF rate-limiting / outage.** If the file CDN is slow, the download button should still work (HF retries handle it) but the site itself must not fail to load if HF is down.
- **Browser without JS.** Acceptable to require JS, but the home page should at minimum show static text + a link to the GitHub repo.

## Functional Requirements

- **FR-001** Site is published from this repo via GitHub Pages (custom domain optional).
- **FR-002** Site rebuilds automatically when `registry_data/manifest.toml` (or `admesh_domains/data/manifest.toml`) changes on `main`. Stale-by-at-most-one-commit is acceptable.
- **FR-003** Home page shows: total Domains, total Meshes, total size, a world map of bboxes, and a search box.
- **FR-004** Domain pages list every Mesh with: id, filename, type, node_count, element_type, refinement_level, license, mirror_eligible, contributor, download link.
- **FR-005** Mesh download links point to the HuggingFace dataset's `resolve/main/meshes/<Domain>/<filename>` URL.
- **FR-006** A "Preview" page accepts a local `.14` / `.2dm` / `.grd` file via drag-and-drop, parses the bbox in-browser, and renders it on the registry map alongside existing Domains.
- **FR-007** A "Contribute" page collects mesh metadata, runs the suggester (client-side port of spec 007's IoU logic), and produces either (a) a pre-filled GitHub PR URL or (b) a copy-paste TOML stub.
- **FR-008** All registry data is read from a single derived artifact (e.g. `manifest.json` or the HF `manifest.parquet` via Parquet-WASM); the TOML is *not* parsed in the browser.
- **FR-009** Site is purely static (HTML/CSS/JS bundle). No backend, no API keys baked into client code.
- **FR-010** Site links prominently to the GitHub repo, the HuggingFace dataset, and the PyPI package.
- **FR-011** A "Feedback" page/nav-link opens a pre-filled GitHub issue (`/issues/new?...&labels=feedback`) with the current page URL auto-included in the body and a category selector (bug / suggestion / question / other).

## Success Criteria *(mandatory)*

- **SC-001** A first-time visitor can find and download an existing mesh in under 30 seconds.
- **SC-002** Every Domain and Mesh in `manifest.toml` appears on the site within one commit-to-publish cycle (CI build + Pages deploy ≤ 5 minutes).
- **SC-003** Uploading a known-registry mesh to the Preview page yields rank-1 = its actual Domain (parity with CLI suggester).
- **SC-004** Lighthouse performance score ≥ 90 on the home page (mobile + desktop).
- **SC-005** Site loads and renders the home page (totals, map) even if HuggingFace is unreachable — only file downloads should fail in that case.
- **SC-006** Zero secrets / API tokens are present in the deployed bundle (verified by build-time scan).

## Clarifications

### Session 2026-04-26

- **Q-1 Framework** → **a) Plain HTML + tiny JS, no framework.** Lowest magic, easiest to maintain, GitHub Pages serves it directly. Astro was the runner-up; revisit if the site grows past a handful of pages.
- **Q-2 Map library** → **a) Leaflet + OpenStreetMap tiles.** Mature, tiny, free, no API key.
- **Q-3 Manifest consumption** → **a) Build step bakes a `manifest.json` from `manifest.toml` into the bundle.** Fast, offline-capable, zero runtime dep on HF for the browse experience.
- **Q-4 Mesh parsing for Preview** → **a) Pure JS port of `bbox_from_fort14` / `bbox_from_2dm`.** ~100 lines, zero deps, fast. Pyodide rejected as overkill.
- **Q-5 Contribute flow** → **a) Pre-filled GitHub PR URL** as the single path. Form collects metadata, builds the diff against `manifest.toml`, opens GitHub's "create new file" / "edit file" URL with the body pre-populated.
- **Q-6 Full-geometry rendering** → **a) Yes in v1.** Parse nodes + elements client-side, render via Canvas/WebGL. Scope acknowledged; if implementation slips, fall back to bbox-only with a follow-up spec.
- **Q-7 Domain** → **TBD** — placeholder is `domattioli.github.io/ADMESH-Domains`. Custom domain to be chosen before launch (candidates: `admesh.dev`, `admesh.io`, `admeshdomains.org`).
- **Q-8 Analytics** → **b) Privacy-respecting** — start with [GoatCounter](https://www.goatcounter.com/) (free tier, no cookies, no PII). Plausible is the upgrade path if needed.
- **Q-9 Theming** → **c) Fresh minimal theme.** Restrained typography, generous whitespace, light + dark mode via `prefers-color-scheme`. No framework CSS.
- **Q-10 Accessibility** → **a) WCAG 2.1 AA from day one.** Semantic HTML, keyboard navigation, color-contrast checks in CI.
- **Q-11 Feedback tab (new)** → A "Feedback" link in the site nav opens a pre-filled GitHub issue (`/issues/new?title=...&body=...&labels=feedback`) — same no-backend pattern as the contribute flow. Form captures: page URL (auto), category (bug / suggestion / question / other), free-text body. Optional contact field.

## Open Questions (deferred)

- **Q-7 (custom domain)** — pick before launch.

## Out of Scope (for this spec)

- In-browser ADCIRC simulation or visualization of model output.
- Editing existing manifest entries via the UI.
- Per-user accounts, favorites, or comments.
- A mobile app (the site should be responsive; native is out of scope).
- Server-side mesh validation beyond what `validate-pr.yml` already does.

## Dependencies

- Spec 006 (HuggingFace publisher) — provides `manifest.parquet` and `bbox_map.png`.
- Spec 007 (Domain auto-suggester) — its IoU logic must be ported to JS for the Preview/Contribute pages.
- A new GitHub Actions workflow (`pages.yml`) that builds the site and deploys to Pages.

## Constitution Check

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest is source of truth | PASS | Site is read-only view of manifest; contribution flow writes to manifest via PR |
| II. Pure-Python, optional heavy deps | N/A | Site is static HTML/CSS/JS; no Python runtime |
| III. Schema changes are explicit | N/A | No schema changes |
| IV. Atomic releases — and separate code from data | N/A | Site-only; no PyPI bump, no separate release track |
| V. Test before tagging | PASS | Site builds on every push; GitHub Pages deployment is automated |
| VI. Curation over auto-magic | PASS | Contribution flow suggests Domain (spec 007); human reviews PR |
| VII. External Upstream (DomI) | PASS | No DomI interaction changes |

## Carry-Overs / Follow-Ups

- Full-geometry rendering of meshes (node/element triangulation) — likely its own spec.
- Antimeridian-safe map preview — blocked on issue #4.
- Automatic OG-image generation per Domain page (social-share previews).
- "Compare two meshes" view (overlay bboxes / geometries side-by-side).
