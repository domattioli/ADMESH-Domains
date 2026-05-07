# Research: Compare Mesh UI (Issue #30)

## Decision: Client-side variant grouping strategy

**Decision**: Group by `element_type` field when present; fall back to filename keywords ("tri", "quad", "mixed").

**Rationale**: Only the `Rectangles` domain has `element_type` set in manifest.toml. All other domains lack this field. The filename-based fallback handles future mesh uploads that include "quad" or "triangle" in the filename. This means the Compare page will show meaningful results for `Rectangles` now and benefit more domains as they add `element_type` metadata.

**Alternatives considered**: Requiring `element_type` on all meshes — rejected because it would require a data migration and is a Principle VI violation (no runtime manifest editing).

---

## Decision: Metrics to display per panel

**Decision**: Show element_type label, size_mb, contributor, and bounding box SVG. Show element_count and node_count as "—" if absent (most current domains don't have these fields).

**Rationale**: The manifest only provides `element_count` and `node_count` for the Rectangles domain (both are currently absent — they show as 0/missing). Graceful degradation with "—" is the right call.

**Impact on recommendation**: Recommendation banner only fires if at least one variant has a non-zero element_count. Otherwise, it shows the panel with the lowest `size_mb` as best.

---

## Decision: Page build integration

**Decision**: `compare.html` is a static file under `site/src/` — no changes to `build_site.py` needed. The existing build copies all `.html` files from `site/src/` to `site/dist/`.

**Rationale**: Examined `build_site.py` — it uses `shutil.copytree` with content-hash renaming for JS/CSS. Adding `compare.html` just works.

---

## Decision: Nav placement

**Decision**: Add `["compare.html", "Compare"]` to the PAGES array in `nav.js` between Browse and Upload.

**Rationale**: Compare is a discovery feature, logically between Browse (see all) and Upload (contribute).
