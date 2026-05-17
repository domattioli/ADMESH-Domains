# ADMESH Domains

<p align="center">
  <a href="https://pypi.org/project/admesh-domains/">
    <img src="https://img.shields.io/pypi/v/admesh-domains?style=flat-square&logo=python&logoColor=white" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/admesh-domains/">
    <img src="https://img.shields.io/pypi/pyversions/admesh-domains?style=flat-square&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://github.com/domattioli/ADMESH-Domains/actions/workflows/validate-pr.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/domattioli/ADMESH-Domains/validate-pr.yml?branch=main&style=flat-square&logo=github" alt="CI Status">
  </a>
  <a href="https://huggingface.co/datasets/domattioli/ADMESH-Domains">
    <img src="https://img.shields.io/badge/HuggingFace-dataset-yellow.svg?style=flat-square&logo=huggingface" alt="HuggingFace Dataset">
  </a>
</p>

Source repository for **ADCIRC mesh domain registry**: curated catalog of coastal-simulation meshes with Python loader, HuggingFace dataset mirror, PR-based contribution workflow.

**🌐 Browse registry: [domattioli.github.io/ADMESH-Domains](https://domattioli.github.io/ADMESH-Domains/)** — interactive map, search, preview, download, contribute.

| Where to go | What you'll find |
|---|---|
| 🌐 [domattioli.github.io/ADMESH-Domains](https://domattioli.github.io/ADMESH-Domains/) | Website (browse / preview / download / contribute) |
| 📦 [pypi.org/project/admesh-domains](https://pypi.org/project/admesh-domains/) | Python package |
| 🤗 [huggingface.co/datasets/domattioli/ADMESH-Domains](https://huggingface.co/datasets/domattioli/ADMESH-Domains) | Mesh files + Parquet sidecar + auto-generated dataset card (start here if you just want data) |
| 🧪 [domattioli/ADMESH](https://github.com/domattioli/ADMESH) | Parent ADMESH library this registry complements |

This repo for **contributors + maintainers** of registry — data, schema, publisher pipeline, CI live here. End users normally don't need to clone; `pip install admesh-domains[hf]` enough.

## Table of contents

- [Quick install](#quick-install)
- [Repo layout](#repo-layout)
- [Development](#development)
- [Releasing — code vs. data](#releasing--code-vs-data)
- [Releases](#releases)
- [Contributing](#contributing)
- [Data quality & mesh lineage](#data-quality--mesh-lineage)
  - [Western North Atlantic (WNAT) — lineage caveat](#western-north-atlantic-wnat--lineage-caveat)
- [Specs](#specs)
- [License](#license)

## Quick install

```bash
# Read bundled manifest only (no mesh downloads, ~50 KB install)
pip install admesh-domains

# Add Mesh.load() — fetches mesh files from HF mirror on demand
pip install admesh-domains[hf]
```

User-facing API (`find_domains`, `find_meshes`, `get_mesh`, `test_meshes`, `Mesh.load`) documented on HF dataset card. For pytest fixtures, use `from admesh_domains import test_meshes` — returns all registry meshes marked for testing.

## Repo layout

```
admesh_domains/          Python package (schema, manifest loader, query API,
                         CLI, HF publisher, dataset-card template)
admesh_domains/data/     Bundled manifest.toml shipped in wheel
registry_data/           Source-of-truth manifest + mesh files (.14, .2dm)
                         excluded from wheel/sdist; mirrored to HF
specs/                   Spec-driven design docs (one folder per feature)
scripts/                 One-shot data tooling (mesh import, bbox extractor)
tests/                   pytest suite (mocked huggingface_hub)
.github/workflows/       release.yml (tag → PyPI + HF) + validate-pr.yml (CI)
```

## Element Type Support

`element_type` field on each mesh entry encodes element geometry:

| Value | Description |
|---|---|
| `"triangle"` | All 3-node triangular elements |
| `"quadrilateral"` | All 4-node quadrilateral elements |
| `"Mixed-Element"` | Mix of triangles and quadrilaterals |
| omitted | Unspecified — always accepted (backward compatible) |

Field is optional; existing entries without `element_type` remain valid. `Mesh.validate()` enforces the enum for any non-null value. See [`docs/CATALOG_SCHEMA.md`](docs/CATALOG_SCHEMA.md) for full field reference and registration examples.

## Development

```bash
pip install -e ".[publish]" pytest
admesh-domains validate                 # check bundled manifest parses
admesh-domains validate registry_data/manifest.toml   # ...and dev one
pytest tests/                           # full suite
admesh-domains publish --tag v0.0.0-dryrun \
    --manifest registry_data/manifest.toml --dry-run --verbose
```

Every push + PR validated by `.github/workflows/validate-pr.yml` (matrix across Python 3.9 / 3.11 / 3.12).

## Releasing — code vs. data

Two separate tracks; **don't conflate**:

| Type of change | What to do | Workflow | Effect |
|---|---|---|---|
| Code, API, schema, publisher, template | Bump `pyproject.toml` + `__init__.py`, tag `vX.Y.Z`, push | `release.yml` | PyPI release + HF tagged `vX.Y.Z` |
| Add / remove / edit mesh (data only) | Edit `registry_data/`, commit, push to `main` | `publish-data.yml` | HF tagged `data-YYYY-MM-DD-<sha7>`; **PyPI untouched** |

PyPI versions reflect *code/API* changes only. Data updates flow through HF without forcing wheel bump (would mislead users about what changed). Both tracks produce reproducible, pinned HF revisions.

See [specs/006-huggingface-publisher/quickstart.md](specs/006-huggingface-publisher/quickstart.md) for full maintainer recipe.

```bash
# Code release (bumps PyPI):
# bump pyproject.toml + admesh_domains/__init__.py to e.g. 0.2.5
git tag v0.2.5 && git push origin v0.2.5

# Data update (HF only, no PyPI):
git add registry_data/ admesh_domains/data/manifest.toml
git commit -m "Add foo.14 to <Domain>"
git push origin main
```

## Releases

See [CHANGELOG.md](CHANGELOG.md) for:
- Full release history (v0.1.0 – current)
- Schema + API changes per release
- Mesh metadata additions in v0.3.2
- Data-only updates tagged on HuggingFace

## Contributing

Open issue first if proposing new domain, schema change, or behavior change. PRs welcome — validator runs on every push.

Currently filed:
- [#1 Natural-language → fort.14 generation](https://github.com/domattioli/ADMESH-Domains/issues/1)
- [#2 Interactive draw → fort.14 export](https://github.com/domattioli/ADMESH-Domains/issues/2)
- [#3 Domain auto-suggester for new mesh PRs](https://github.com/domattioli/ADMESH-Domains/issues/3)

## Data quality & mesh lineage

Every mesh in registry includes optional `provenance` + `lineage` fields to distinguish original upstream sources from downstream re-meshes:

- **`provenance`**: One of `"upstream"` (original published source, complete topology) or `"derivative-admesh"` (regenerated via ADmesh GUI, may be structurally simplified).
- **`lineage`**: One-sentence note on mesh's origin + any processing affecting it (e.g. boundary simplification).

### Western North Atlantic (WNAT) — lineage caveat

WNAT domain contains three meshes with different provenance:

| Mesh | Nodes | BC Segments | Provenance | Use case |
|------|-------|-------------|-----------|----------|
| `WNAT_Hagen.14` | 52,774 | 113 (incl. Bermuda) | upstream | Default choice; publication-faithful; complete island topology |
| `WNAT_Test.14` | 9,934 | 0 | derivative-admesh | Pedagogical; ADmesh-regenerated for tutorials; Bermuda + island rings **stripped** |
| `WNAT_Onur.14` | 127,572 | 1 | derivative-admesh | Fine grid; ADmesh-regenerated; land boundary segments **stripped** |

**⚠️ Important:** `WNAT_Test.14` + `WNAT_Onur.14` aren't faithful mesh densifications of `WNAT_Hagen.14`. When regenerated by ADmesh GUI, declared boundary sections (BC) discarded. Downstream tools (e.g. ADMESH's `Domain.from_mesh()`) pulling Test or Onur variant expecting complete Hagen topology will lose Bermuda + 112 other island rings. If you need original upstream-faithful mesh, use `WNAT_Hagen.14` explicitly.

See [issue #13](https://github.com/domattioli/ADMESH-Domains/issues/13) for technical audit + reproduction script.

## Specs

Active + shipped specs live under [`specs/`](specs/). Each folder contains `spec.md`, `plan.md`, `tasks.md`, supporting docs.

| Spec | Status |
|---|---|
| [005 — ADCIRC mesh registry](https://github.com/domattioli/ADMESH-Domains/tree/main/specs) (legacy from monorepo, see migration note) | Superseded |
| [006 — HuggingFace dataset publisher](specs/006-huggingface-publisher/spec.md) | ✅ Shipped in v0.2.0 |

## License

MIT — see [LICENSE](LICENSE).
