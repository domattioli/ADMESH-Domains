# ADMESH Domains

Source repository for the **ADCIRC mesh domain registry**: a curated catalog of coastal-simulation meshes with a Python loader, HuggingFace dataset mirror, and PR-based contribution workflow.

| Where to go | What you'll find |
|---|---|
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

The user-facing API (`find_domains`, `find_meshes`, `get_mesh`, `Mesh.load`) is documented on the HF dataset card.

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

## Contributing

Open an issue first if you're proposing a new domain, schema change, or behavior change. PRs welcome — the validator will run on every push.

Currently filed:
- [#1 Natural-language → fort.14 generation](https://github.com/domattioli/ADMESH-Domains/issues/1)
- [#2 Interactive draw → fort.14 export](https://github.com/domattioli/ADMESH-Domains/issues/2)
- [#3 Domain auto-suggester for new mesh PRs](https://github.com/domattioli/ADMESH-Domains/issues/3)

## Specs

Active and shipped specs live under [`specs/`](specs/). Each folder contains `spec.md`, `plan.md`, `tasks.md`, and supporting docs.

| Spec | Status |
|---|---|
| [005 — ADCIRC mesh registry](https://github.com/domattioli/ADMESH-Domains/tree/main/specs) (legacy from monorepo, see migration note) | Superseded |
| [006 — HuggingFace dataset publisher](specs/006-huggingface-publisher/spec.md) | ✅ Shipped in v0.2.0 |

## License

MIT — see [LICENSE](LICENSE).
