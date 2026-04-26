# Feature Specification: HuggingFace Dataset Publisher

**Feature Branch**: `006-huggingface-publisher`
**Created**: 2026-04-25
**Status**: Draft
**Input**: Adaptation of the original `005-adcirc-mesh-registry/contracts/hf-publisher.md` to the current Domain → Meshes schema (v0.1.1)

## Summary

Auto-publish each tagged release of the `admesh-domains` registry to a public HuggingFace Dataset. The Dataset becomes the canonical mirror for mesh files (which are too large to bundle in the PyPI wheel) and provides a queryable Parquet sidecar that downstream tools can read without depending on the Python loader.

The publisher runs as a GitHub Action on every `v*` tag push, and is also exposed as a CLI command (`admesh-domains publish`) for ops use.

## Clarifications

### Session 2026-04-25 (initial)

- **Q (C-1)**: HuggingFace target slug? → **A**: `domattioli/admesh-domains` (personal account; no HF org setup needed). May migrate to an org slug later if collaborators join.
- **Q (C-2)**: Which tags trigger a publish? → **A**: Strict semver only — workflow filter `v[0-9]+.[0-9]+.[0-9]+`. Pre-releases / RC tags do not publish.
- **Q (C-3)**: License handling for v1? → **A**: Publish all 40 meshes. They were imported from public GitHub repos so are de facto already-public. Per-mesh `license` field deferred to a later spec; revisit before accepting outside contributions.

### Session 2026-04-25 (clarify)

- **Q (C-4)**: Content-hash dedup mechanism? → **A**: Compute sha256 at publish time, write the column into the Parquet sidecar, and on subsequent runs read the *previous* sidecar from HF to decide skip/re-upload. No `Mesh` schema change, no PR-author burden. First run uploads everything (no prior sidecar to compare against).
- **Q (C-5)**: HF dataset file-path layout? → **A**: Group by domain — `meshes/<domain_name>/<original_filename>`, e.g. `meshes/WNAT/WNAT_Hagen.14`. Original filenames preserved (no information loss); collision-proof if two domains ever ship a `WNAT.14`.
- **Q (C-6)**: Required vs optional `huggingface_hub` / `pyarrow` deps? → **A**: Optional extra — `pip install admesh-domains[publish]` for the publisher; `pip install admesh-domains[hf]` for runtime `Mesh.load()` from HF. Base install stays light.
- **Q (C-7)**: Should `Mesh.load()` fetch from HF? → **A**: Yes — `Mesh.load()` calls `huggingface_hub.hf_hub_download(...)` for the configured dataset. Files cache to `HF_HUB_CACHE` (cross-platform), with built-in progress bars and resumable downloads — appropriate even for the largest meshes today (~15 MB) and for future multi-GB additions. Requires the `[hf]` extra.
- **Q (C-8)**: HF "latest" tracking branch? → **A**: Yes — keep `main` always pointing at the latest semver tag, in addition to per-tag revisions. Casual users get latest-by-default with `snapshot_download`; pin-conscious users use `revision="v0.2.0"`.
- **Q (C-9)**: Couple PyPI publish to the same workflow? → **A**: Yes — single GitHub Action on a semver tag does both `twine upload` (PyPI) and HF publish. Requires `PYPI_API_TOKEN` and `HF_TOKEN` repo secrets. PyPI step runs first; HF step runs only if PyPI succeeds.

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

- **FR-001**: A GitHub Actions workflow at `.github/workflows/release.yml` triggers on push of any tag matching the strict semver pattern `v[0-9]+.[0-9]+.[0-9]+`.
- **FR-002**: The workflow also supports `workflow_dispatch` for manual re-runs.
- **FR-003**: The publisher reads `admesh_domains/data/manifest.toml`, validates it, and refuses to proceed on any error.
- **FR-004**: The publisher uploads each mesh file under `registry_data/meshes/<filename>` to HF as `meshes/<domain_name>/<filename>` (e.g. `meshes/WNAT/WNAT_Hagen.14`) via a single batched `huggingface_hub.create_commit` call.
- **FR-005**: For dedup, the publisher downloads the previous `manifest.parquet` from HF (if present), reads the prior `content_sha256` per file, and skips re-uploading files whose hash hasn't changed. First run (no prior sidecar) uploads everything.
- **FR-006**: A Parquet sidecar (`manifest.parquet`) is written at the dataset root, containing one row per mesh with flattened columns (see Data Model section), including the freshly-computed `content_sha256`.
- **FR-007**: A dataset card (`README.md`) is rendered from a Jinja template and written to the HF dataset repo.
- **FR-008**: All HF writes for a given run land in a single atomic commit (`huggingface_hub.create_commit` with batched operations), tagged on HF with the release tag (e.g. `v0.2.0`) via `huggingface_hub.create_tag`.
- **FR-009**: After a successful tagged commit, the workflow updates the HF `main` branch to point at the same revision, so `snapshot_download(...)` defaults to the latest published tag.
- **FR-010**: The release workflow first runs `twine upload dist/*` to PyPI using `PYPI_API_TOKEN`; the HF publish step runs only on PyPI success. A failure during HF publish does NOT roll back PyPI (PyPI versions are immutable anyway).
- **FR-011**: The CLI exposes the HF operation as `admesh-domains publish [--dry-run] [--tag STR]`. Token is read from `HF_TOKEN` env var.
- **FR-012**: `--dry-run` mode prints planned uploads, deletes, and dataset-card diff without touching HF.
- **FR-013**: `Mesh.load()` is added to the runtime API. When called, it downloads the file from the configured HF dataset via `huggingface_hub.hf_hub_download` (cached under `HF_HUB_CACHE`) and returns the local `Path`. Requires the `[hf]` extra.

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

All publisher-side deps are gated behind the `[publish]` extra; runtime HF download is gated behind `[hf]`. Base install stays at the current `tomli ; python_version < '3.11'` only.

- `[publish]` extra:
  - `huggingface_hub >= 0.20` — auth, batched create_commit, create_tag
  - `pyarrow >= 14.0` — Parquet sidecar read/write
  - `jinja2 >= 3.0` — dataset card templating
  - `twine >= 4.0` — PyPI upload (already in dev workflow, surfaced explicitly here)
- `[hf]` extra:
  - `huggingface_hub >= 0.20` — runtime `Mesh.load()` downloads
- Existing: `admesh_domains.manifest.load_manifest`, `Manifest.all_meshes()`, `Mesh.path` (already in v0.1.1)
- New repo secrets required: `HF_TOKEN` (write to `domattioli/admesh-domains`), `PYPI_API_TOKEN` (already used manually).

## Open Questions for Plan Phase

- Should the dataset card include a small folium / static-image map of mesh bounding boxes? Leaning **no** for v1 — no `bounding_box` data on Meshes yet, so there's nothing to plot. Revisit when bbox is populated.
- Should there be a `[publish]` test that exercises the publisher end-to-end against a *test* HF dataset (e.g. `domattioli/admesh-domains-ci`) on every PR? Adds CI cost but catches breakage early.
