# Feature Specification: HuggingFace Dataset Publisher

**Feature Branch**: `006-huggingface-publisher`
**Created**: 2026-04-25
**Status**: Draft
**Input**: Adaptation of the original `005-adcirc-mesh-registry/contracts/hf-publisher.md` to the current Domain → Meshes schema (v0.1.1)

## Summary

Auto-publish each tagged release of the `admesh-domains` registry to a public HuggingFace Dataset. The Dataset becomes the canonical mirror for mesh files (which are too large to bundle in the PyPI wheel) and provides a queryable Parquet sidecar that downstream tools can read without depending on the Python loader.

The publisher runs as a GitHub Action on every `v*` tag push, and is also exposed as a CLI command (`admesh-domains publish`) for ops use.

## Clarifications

### Session 2026-04-25

- **Q (C-1)**: HuggingFace target slug? → **A**: `domattioli/admesh-domains` (personal account; no HF org setup needed). May migrate to an org slug later if collaborators join.
- **Q (C-2)**: Which tags trigger a publish? → **A**: Strict semver only — workflow filter `v[0-9]+.[0-9]+.[0-9]+`. Pre-releases / RC tags do not publish.
- **Q (C-3)**: License handling for v1? → **A**: Publish all 40 meshes. They were imported from public GitHub repos so are de facto already-public. Per-mesh `license` field deferred to a later spec; revisit before accepting outside contributions.

## User Scenarios & Testing

### User Story 1 — Maintainer cuts a registry release (Priority: P1)

The registry maintainer pushes a release tag (`git tag v0.2.0 && git push --tags`). Within minutes, the HuggingFace dataset reflects the new state — added meshes uploaded, removed meshes (if any) deleted, manifest sidecar regenerated.

**Why this priority**: Without automated publishing, every release requires manual `huggingface_hub` scripting, which won't happen consistently. Automation is the entire point of this feature.

**Independent Test**: push a tag in CI, observe the HF dataset commit appears with the expected files.

**Acceptance Scenarios**:

1. **Given** the registry contains 40 meshes and 13 domains at tag `v0.2.0`, **When** the tag is pushed, **Then** the HF dataset commit at revision `v0.2.0` contains all 40 mesh files under `meshes/<filename>` and a Parquet sidecar with 40 rows.
2. **Given** a mesh file already exists in the HF dataset with the same content hash, **When** the publisher runs again for a new tag, **Then** that file is skipped (no re-upload), but the Parquet and dataset card are still regenerated.
3. **Given** the manifest validation fails on the tagged commit, **When** the workflow runs, **Then** the publisher hard-fails before touching the HF dataset, and the failure is reported in the GitHub Actions log.

---

### User Story 2 — Downstream user installs registry meshes from HF (Priority: P1)

A coastal modeler doesn't want to git-clone a 60+ MB repo. They install `admesh-domains` from PyPI, then either (a) call the loader to download a single mesh on demand, or (b) `huggingface_hub.snapshot_download(...)` the entire dataset to a local cache.

**Why this priority**: This is the user-visible benefit of the HF publisher. Bundling meshes in the wheel is wasteful; the GitHub repo isn't a CDN. HF gives both.

**Independent Test**: From a clean machine, install the wheel, call `Mesh.load()` on a known entry, verify the file lands locally.

**Acceptance Scenarios**:

1. **Given** a fresh `pip install admesh-domains` (no repo checkout), **When** the user calls `mesh.load()` for `WNAT/hagen@v1`, **Then** the publisher's HF mirror is hit, the file is downloaded into the XDG cache, and a local `Path` is returned.
2. **Given** the same file was loaded previously, **When** `mesh.load()` is called again, **Then** the cached copy is returned without a network round-trip.
3. **Given** the user calls `huggingface_hub.snapshot_download("admesh-domains/registry")`, **Then** they get the full mesh corpus + manifest in one call.

---

### User Story 3 — Dataset reader browses on the HuggingFace UI (Priority: P2)

A researcher who doesn't use the Python loader can browse the dataset on huggingface.co — see the list of domains/meshes, click into mesh files, read the dataset card, query the Parquet sidecar via the HF Dataset Viewer.

**Why this priority**: Discoverability beyond the PyPI/GitHub audience. Lower priority because the loader covers the primary use case.

**Acceptance Scenarios**:

1. **Given** a published dataset, **When** a user visits `huggingface.co/datasets/admesh-domains/registry`, **Then** the rendered dataset card shows total domain/mesh counts, a categorized table, and quickstart code.
2. **Given** the Parquet sidecar exists, **When** the user opens the HF Dataset Viewer, **Then** they see one row per mesh with columns for domain, mesh id, filename, size, region, applications, etc.

## Edge Cases

- **Missing HF_TOKEN secret** → workflow fails fast in pre-flight with a clear error; nothing uploaded.
- **HF token lacks write access** → first upload attempt fails; no partial state because all writes go through a single atomic commit.
- **Mesh file in manifest but missing on disk** → manifest validator (already in `cli.py`) catches this; publisher refuses to run.
- **Same tag pushed twice** → second run is idempotent (file uploads skip on hash match; commit is a no-op or "regenerated dataset card" only).
- **Tag pushed for a non-release branch state** → publisher trusts the tagged commit; ops responsibility to tag the right SHA.
- **Network failure mid-upload** → publisher retries (huggingface_hub default retry); if it ultimately fails, the HF commit doesn't go through, leaving the dataset in its prior good state.
- **Forked repo pushes a tag** → workflow only runs on the canonical repo (guarded via `if: github.repository == 'domattioli/ADMESH-Domains'`).

## Requirements

### Functional

- **FR-001**: A GitHub Actions workflow at `.github/workflows/publish-hf.yml` triggers on push of any tag matching `v*`.
- **FR-002**: The workflow also supports `workflow_dispatch` for manual re-runs.
- **FR-003**: The publisher reads `admesh_domains/data/manifest.toml`, validates it, and refuses to proceed on any error.
- **FR-004**: The publisher uploads each mesh file under `registry_data/meshes/<filename>` to HF as `meshes/<filename>` using `huggingface_hub.upload_file`.
- **FR-005**: Uploads are skipped for files already present in HF with the same content hash (sha256).
- **FR-006**: A Parquet sidecar (`manifest.parquet`) is written, containing one row per mesh with flattened columns (see Data Model section).
- **FR-007**: A dataset card (`README.md`) is rendered from a Jinja template and written to the HF dataset repo.
- **FR-008**: All HF writes for a given run land in a single commit, tagged with the release tag (e.g. `v0.2.0`).
- **FR-009**: The CLI exposes the same operation as `admesh-domains publish [--dry-run] [--token ENV] [--tag STR]`.
- **FR-010**: A `--dry-run` mode prints what would be uploaded/changed without touching HF.

### Non-Functional

- **NFR-001**: A full publish of the current 40-mesh / 59 MB registry completes in ≤ 5 minutes on `ubuntu-latest`.
- **NFR-002**: The publisher must be a pure-Python operation (no system-level dependencies beyond `huggingface_hub`, `pyarrow`, `jinja2`).
- **NFR-003**: HF token must never be logged or echoed; pass it via env var only.

## Data Model (Parquet sidecar)

One row per mesh, flat schema:

| Column | Type | Source |
|---|---|---|
| `domain` | string | parent `Domain.name` |
| `mesh_id` | string | `Mesh.id` |
| `full_id` | string | `<domain>/<mesh_id>` |
| `filename` | string | `Mesh.filename` |
| `description` | string \| null | `Mesh.description` |
| `size_mb` | float | `Mesh.size_mb` |
| `type` | string | `Mesh.type` |
| `element_type` | string \| null | `Mesh.element_type` |
| `refinement_level` | string \| null | `Mesh.refinement_level` |
| `node_count` | int \| null | `Mesh.node_count` |
| `aliases` | list\<string\> | `Mesh.aliases` |
| `category` | string | parent `Domain.category` |
| `region` | string \| null | parent `Domain.region` |
| `applications` | list\<string\> | parent `Domain.applications` |
| `content_sha256` | string | computed at publish time |
| `hf_path` | string | `meshes/<filename>` |

## Success Criteria

- **SC-001**: A `git push origin v0.2.0` results in a published HF dataset commit within 5 minutes (NFR-001).
- **SC-002**: 100% of meshes listed in the tagged manifest appear under `meshes/` in the published dataset.
- **SC-003**: A repeated publish of the same tag uploads zero mesh files (idempotent on content hash).
- **SC-004**: The dataset card lists total domains, total meshes, total size, and includes a working quickstart code block.
- **SC-005**: A user with no checkout of the repo can run `huggingface_hub.snapshot_download("admesh-domains/registry")` and receive the full corpus.

## Assumptions

- The HF org/dataset (`admesh-domains/registry`) is created manually in a one-time setup step before the first publish.
- An `HF_TOKEN` repository secret is configured in GitHub with write access to the target dataset.
- All meshes currently in the registry are redistributable. License-aware filtering is **out of scope** for this spec and tracked separately (depends on adding a `license` field to the `Mesh` schema).
- Schema version `0.2` is stable; the Parquet sidecar schema is implicitly versioned with it.
- `pyarrow` is acceptable as a dependency for sidecar generation (pure-Python wheel is fine on Linux/macOS/Windows).

## Out of Scope

- License-aware mirror eligibility (defer until `license` field added to `Mesh`).
- Tombstone / deprecation handling (defer until `review_state` field added).
- Sharded manifests (only meaningful at >5K meshes; we have 40).
- Geometry-derived bounding-box columns in Parquet (defer until `bounding_box` is populated on Meshes).
- A separate "registry-quality" CI gate beyond the existing manifest validator.

## Dependencies

- `huggingface_hub >= 0.20` — auth, file ops, atomic commits
- `pyarrow >= 14.0` — Parquet sidecar writes
- `jinja2 >= 3.0` — dataset card templating
- Existing `admesh_domains.manifest.load_manifest` and `Manifest.all_meshes()` (already shipped in v0.1.1)

## Open Questions for Plan Phase

- Should the dataset card include a small folium / static-image map of mesh bounding boxes, or stay text-only for v1? (Leans text-only — no `bounding_box` data on Meshes yet.)
- Do we want a `main` branch on HF that always tracks the latest tag, in addition to per-tag revisions?
