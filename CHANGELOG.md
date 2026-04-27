# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.2] - 2026-04-26

### Added

- **Mesh schema fields** for richer mesh metadata:
  - `Mesh.kind` — Distinguish between complete meshes (`"mesh"`) and boundary-only outlines (`"boundary"`)
  - `Mesh.test_case` — Mark meshes for use in downstream test suites (boolean; filters via `find_meshes(test_case=True)`)
  - `Mesh.uploaded_date` — ISO 8601 date when mesh was added to the registry
  - `Mesh.modified_date` — ISO 8601 date when the underlying mesh file last changed
- **Site improvements**:
  - New **Statistics** tab — registry-wide metrics (domains, meshes, total size)
  - New **Test Suites** tab — curated test cases for downstream integration testing
  - New **Create** tab — interactive mesh upload and domain suggestion
  - Mesh geometry preview canvas with interactive zoom and pan

### Changed

- Mesh filtering now supports `kind` and `test_case` query parameters (see `find_meshes()`)
- Parquet sidecar on HF gained new columns for the schema fields above; readers must tolerate unknown columns

### Technical Notes

- Schema version remains `"0.2"` (additive fields, no breaking changes)
- The four new Mesh fields are all optional with sensible defaults
- See [Issue #7](https://github.com/domattioli/ADMESH-Domains/issues/7), [Issue #11](https://github.com/domattioli/ADMESH-Domains/issues/11), and [Issue #13](https://github.com/domattioli/ADMESH-Domains/issues/13)

## [0.3.1] - 2026-04-26

### Added

- **GitHub Pages site** ([domattioli.github.io/ADMESH-Domains](https://domattioli.github.io/ADMESH-Domains/)):
  - Interactive map view of all domains
  - Mesh search and filtering UI
  - Per-mesh detail pages with bounding box visualization
  - Download links to HuggingFace mirror
  - Contributor attribution and metadata display

### Changed

- README updated with links to the new interactive site

### Technical Notes

- Site built via `scripts/build_site.py` and hosted on GitHub Pages via `gh-pages` branch
- No Python package changes in this release (site-only)

## [0.3.0] - 2026-04-26

### Added

- **Domain auto-suggester** (`admesh-domains domain suggest <mesh-file>`):
  - Ranks existing domains by IoU with uploaded mesh
  - Interactive prompt for new domain creation
  - Parses mesh file geometry and computes bounding box
- **`test_meshes()` helper** — Fetch all registry meshes marked for testing (see `find_meshes(test_case=True)`)
- **`find_meshes()` filters** for `kind` and `test_case` (Issue #7, #11)

### Changed

- CLI now supports domain suggestion workflow
- Manifest validator detects new optional Mesh fields

### Technical Notes

- Uses `shapely` (optional `[hf]` extra) for geometry operations
- Domain suggestion stored in `registry_data/manifest.toml` only; auto-suggester is a curation aid, not authoritative
- See [Issue #3](https://github.com/domattioli/ADMESH-Domains/issues/3) for full design

## [0.2.5] - 2026-04-25

### Fixed

- License field validation now accepts all SPDX identifiers in `REDISTRIBUTABLE_LICENSES`

## [0.2.4] - 2026-04-25

### Added

- Import `nc_inundation_v6c.grd` into WNAT domain (41st mesh)

## [0.2.3] - 2026-04-25

### Added

- `Mesh.license` field (defaults all existing meshes to `"MIT"`)

## [0.2.2] - 2026-04-25

### Fixed

- Manifest parser handles edge cases in bounding box extraction

## [0.2.1] - 2026-04-25

### Fixed

- PyPI package metadata corrected

## [0.2.0] - 2026-04-25

### Added

- Initial HuggingFace dataset publication
- Parquet sidecar for queryable mesh metadata
- Auto-generated dataset card from registry manifest

## [0.1.0] - 2026-04-24

### Added

- Initial standalone registry migration from ADMESH
- 13 domains, 40 meshes bundled in manifest.toml
- Python loader API (`find_domains`, `find_meshes`, `get_domain`, `get_mesh`)
- CLI (`admesh-domains validate`, `admesh-domains domains`, etc.)
- Pure-Python base install (tomli only)
- pytest test suite (40+ tests)

---

## Release Notes

- **Code/API/schema releases** → Bump version in `pyproject.toml` and `admesh_domains/__init__.py`, push a git tag `v0.X.Y` → triggers `release.yml` to publish PyPI + HF
- **Data-only releases** (mesh additions/removals/metadata) → No PyPI bump; push to `main` → triggers `publish-data.yml` to HF with tag `data-YYYY-MM-DD-<sha7>`
