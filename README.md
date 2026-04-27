# ADMESH Domains

[![PyPI version](https://img.shields.io/pypi/v/admesh-domains.svg)](https://pypi.org/project/admesh-domains/)
[![Python versions](https://img.shields.io/pypi/pyversions/admesh-domains.svg)](https://pypi.org/project/admesh-domains/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests](https://github.com/domattioli/ADMESH-Domains/actions/workflows/validate-pr.yml/badge.svg)](https://github.com/domattioli/ADMESH-Domains/actions)
[![HuggingFace Dataset](https://img.shields.io/badge/%F0%9F%A4%97-Dataset-yellow)](https://huggingface.co/datasets/domattioli/ADMESH-Domains)

Source repository for the **ADCIRC mesh domain registry**: a curated catalog of coastal-simulation meshes with a Python loader, HuggingFace dataset mirror, and PR-based contribution workflow.

**🌐 Browse the registry: [domattioli.github.io/ADMESH-Domains](https://domattioli.github.io/ADMESH-Domains/)** — interactive map, search, preview, download, and contribute.

| Where to go | What you'll find |
|---|---|
| 🌐 [domattioli.github.io/ADMESH-Domains](https://domattioli.github.io/ADMESH-Domains/) | The website (browse / preview / download / contribute) |
| 📦 [pypi.org/project/admesh-domains](https://pypi.org/project/admesh-domains/) | The Python package |
| 🤗 [huggingface.co/datasets/domattioli/ADMESH-Domains](https://huggingface.co/datasets/domattioli/ADMESH-Domains) | The mesh files + Parquet sidecar + auto-generated dataset card (start here if you just want data) |
| 🧪 [domattioli/ADMESH](https://github.com/domattioli/ADMESH) | The parent ADMESH library this registry complements |

This repo is for **contributors and maintainers** of the registry — the data, schema, publisher pipeline, and CI live here. End users normally don't need to clone it; `pip install admesh-domains[hf]` is enough.

## Quick install

```bash
# Read the bundled manifest only (no mesh downloads, ~50 KB install)
pip install admesh-domains

# Add Mesh.load() — fetches mesh files from the HF mirror on demand
pip install admesh-domains[hf]
```

The user-facing API (`find_domains`, `find_meshes`, `get_mesh`, `test_meshes`, `Mesh.load`) is documented on the HF dataset card. For pytest fixtures, use `from admesh_domains import test_meshes` — it returns all registry meshes marked for testing.

## Repo layout

```
admesh_domains/          Python package (schema, manifest loader, query API,
                         CLI, HF publisher, dataset-card template)
admesh_domains/data/     Bundled manifest.toml shipped in the wheel
registry_data/           Source-of-truth manifest + mesh files (.14, .2dm)
                         excluded from the wheel/sdist; mirrored to HF
specs/                   Spec-driven design docs (one folder per feature)
scripts/                 One-shot data tooling (mesh import, bbox extractor)
tests/                   pytest suite (mocked huggingface_hub)
.github/workflows/       release.yml (tag → PyPI + HF) + validate-pr.yml (CI)
```

## Development

```bash
pip install -e ".[publish]" pytest
admesh-domains validate                 # check the bundled manifest parses
admesh-domains validate registry_data/manifest.toml   # ...and the dev one
pytest tests/                           # full suite
admesh-domains publish --tag v0.0.0-dryrun \
    --manifest registry_data/manifest.toml --dry-run --verbose
```

Every push and PR is validated by `.github/workflows/validate-pr.yml` (matrix across Python 3.9 / 3.11 / 3.12).

## Releasing — code vs. data

Two separate tracks; **don't conflate them**:

| Type of change | What to do | Workflow | Effect |
|---|---|---|---|
| Code, API, schema, publisher, template | Bump `pyproject.toml` + `__init__.py`, tag `vX.Y.Z`, push | `release.yml` | PyPI release + HF tagged `vX.Y.Z` |
| Add / remove / edit a mesh (data only) | Edit `registry_data/`, commit, push to `main` | `publish-data.yml` | HF tagged `data-YYYY-MM-DD-<sha7>`; **PyPI untouched** |

PyPI versions reflect *code/API* changes only. Data updates flow through HF without forcing a wheel bump (which would mislead users about what changed). Both tracks produce reproducible, pinned HF revisions.

See [specs/006-huggingface-publisher/quickstart.md](specs/006-huggingface-publisher/quickstart.md) for the full maintainer recipe.

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
- Schema and API changes per release
- Mesh metadata additions in v0.3.2
- Data-only updates tagged on HuggingFace

## Contributing

Open an issue first if you're proposing a new domain, schema change, or behavior change. PRs welcome — the validator will run on every push.

Currently filed:
- [#1 Natural-language → fort.14 generation](https://github.com/domattioli/ADMESH-Domains/issues/1)
- [#2 Interactive draw → fort.14 export](https://github.com/domattioli/ADMESH-Domains/issues/2)
- [#3 Domain auto-suggester for new mesh PRs](https://github.com/domattioli/ADMESH-Domains/issues/3)

## Data quality & mesh lineage

Every mesh in the registry includes optional `provenance` and `lineage` fields to distinguish original upstream sources from downstream re-meshes:

- **`provenance`**: One of `"upstream"` (original published source, complete topology) or `"derivative-admesh"` (regenerated via the ADmesh GUI, may be structurally simplified).
- **`lineage`**: A one-sentence note on the mesh's origin and any processing that affected it (e.g., boundary simplification).

### Western North Atlantic (WNAT) — lineage caveat

The WNAT domain contains three meshes with different provenance:

| Mesh | Nodes | BC Segments | Provenance | Use case |
|------|-------|-------------|-----------|----------|
| `WNAT_Hagen.14` | 52,774 | 113 (incl. Bermuda) | upstream | Default choice; publication-faithful; complete island topology |
| `WNAT_Test.14` | 9,934 | 0 | derivative-admesh | Pedagogical; ADmesh-regenerated for tutorials; Bermuda + island rings **stripped** |
| `WNAT_Onur.14` | 127,572 | 1 | derivative-admesh | Fine grid; ADmesh-regenerated; land boundary segments **stripped** |

**⚠️ Important:** `WNAT_Test.14` and `WNAT_Onur.14` are not faithful mesh densifications of `WNAT_Hagen.14`. When regenerated by the ADmesh GUI, their declared boundary sections (BC) were discarded. Downstream tools (e.g., ADMESH's `Domain.from_mesh()`) that pull a Test or Onur variant expecting the complete Hagen topology will lose Bermuda and 112 other island rings. If you need the original upstream-faithful mesh, use `WNAT_Hagen.14` explicitly.

See [issue #13](https://github.com/domattioli/ADMESH-Domains/issues/13) for the technical audit and reproduction script.

## Specs

Active and shipped specs live under [`specs/`](specs/). Each folder contains `spec.md`, `plan.md`, `tasks.md`, and supporting docs.

| Spec | Status |
|---|---|
| [005 — ADCIRC mesh registry](https://github.com/domattioli/ADMESH-Domains/tree/main/specs) (legacy from monorepo, see migration note) | Superseded |
| [006 — HuggingFace dataset publisher](specs/006-huggingface-publisher/spec.md) | ✅ Shipped in v0.2.0 |

## License

MIT — see [LICENSE](LICENSE).
