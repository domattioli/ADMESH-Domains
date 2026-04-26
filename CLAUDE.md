# CLAUDE.md

Project-level guidance for Claude (and other coding agents) working on this repo.

## Stream Timeout Prevention

1. Do each numbered task ONE AT A TIME. Complete one task fully,
   confirm it worked, then move to the next.
2. Never write a file longer than ~150 lines in a single tool call.
   If a file will be longer, write it in multiple append/edit passes.
3. Start a fresh session if the conversation gets long (20+ tool calls).
   The error gets worse as the session grows.
4. Keep individual grep/search outputs short. Use flags like
   `--include` and `-l` (list files only) to limit output size.
5. If you do hit the timeout, retry the same step in a shorter form.
   Don't repeat the entire task from scratch.

## What this repo is

A Python package (`admesh-domains` on PyPI) plus a HuggingFace dataset (`domattioli/ADMESH-Domains`) that together form a registry of ADCIRC mesh domains. Two-level data model:
- **Domain** — a geographic region or logical group (e.g. `WNAT`, `LakeErie`, `TestCases`)
- **Mesh** — a specific realization of a Domain (one `.14` or `.2dm` file with its own resolution, contributor, etc.)

Composite IDs look like `WNAT/hagen@v1`. The registry currently holds 13 Domains and 40 Meshes (~59 MB).

## Key conventions

- **Pure-Python only** for runtime deps. Heavy deps (`huggingface_hub`, `pyarrow`, `jinja2`) live behind optional extras `[hf]` and `[publish]`. Base install must stay small.
- **Dataclasses, not pydantic.** Validation is hand-rolled in `*.validate()` methods. Don't pull pydantic.
- **`from __future__ import annotations`** in every module. Type hints are lazy strings.
- **TOML manifest is the single source of truth.** The Parquet sidecar (`manifest.parquet`) is *derived* at publish time. Don't write code that depends on the sidecar being authoritative.
- **Mesh files live on HF, not in the wheel.** `MANIFEST.in` excludes `registry_data/meshes/` from the sdist. `Mesh.load()` fetches via `huggingface_hub.hf_hub_download` (cached).
- **HF slug is mixed-case**: `domattioli/ADMESH-Domains` (capital A, D, M). Use it literally — don't lowercase.

## Repo layout

```
admesh_domains/      Python package
admesh_domains/data/ Bundled manifest.toml (in the wheel)
registry_data/       Source-of-truth manifest + mesh files (excluded from wheel)
specs/               Spec-driven design (one folder per feature)
.specify/            Spec-kit infrastructure (constitution, templates)
scripts/             One-shot data tooling
tests/               pytest suite
.github/workflows/   release.yml (tag → PyPI + HF), validate-pr.yml (CI)
```

## Common workflows

### Validate a manifest
```bash
admesh-domains validate                              # bundled
admesh-domains validate registry_data/manifest.toml  # dev (with mesh files)
```

### Run tests
```bash
pip install -e ".[publish]" pytest
pytest tests/
```

### Local publisher dry-run (no HF write)
```bash
admesh-domains publish --tag v0.0.0-dryrun \
  --manifest registry_data/manifest.toml --dry-run --verbose
```

### Releasing code (bumps PyPI + HF)
**Use this for code, API, schema, or publisher changes — NOT for adding meshes.**
```bash
# Bump version in pyproject.toml AND admesh_domains/__init__.py
git tag v0.X.Y && git push origin v0.X.Y
# Triggers release.yml: PyPI release + HF tagged with same vX.Y.Z
```

### Adding a mesh (data-only update — NO PyPI bump)
**Mesh additions / removals / metadata edits are data, not code. Don't tag.**
```bash
# Edit registry_data/manifest.toml (and admesh_domains/data/manifest.toml),
# add the file under registry_data/meshes/, commit, push to main:
git add registry_data/ admesh_domains/data/manifest.toml
git commit -m "Add foo.14 to <Domain>"
git push origin main
# Triggers publish-data.yml automatically: HF gets a new revision
# tagged 'data-YYYY-MM-DD-<sha7>'. PyPI is untouched.
```

### Manual data publish
```bash
# Run the data-only HF publish out-of-band (no commit needed):
gh workflow run publish-data.yml -R domattioli/ADMESH-Domains
# Or with a custom tag:
gh workflow run publish-data.yml -R domattioli/ADMESH-Domains -f tag=data-special-rev
```

## Specs index

Active and shipped specs live under `specs/`. Use the spec-kit-style format: `spec.md`, `plan.md`, `tasks.md`, plus optional `data-model.md`, `contracts/`, `quickstart.md`, `research.md`. The constitution at `.specify/memory/constitution.md` defines the principles that gate feature plans.

| Spec | Status |
|---|---|
| `005-adcirc-mesh-registry` | Superseded by the standalone repo migration |
| `006-huggingface-publisher` | Shipped in v0.2.0 |

## Don'ts

- **Don't add backward-compat shims** for old field names. Schema is at 0.x — anything goes.
- **Don't bundle mesh files in the wheel.** Always go through HF.
- **Don't lowercase `ADMESH-Domains`** in the HF slug.
- **Don't bump SCHEMA_VERSION for additive changes.** Only for breaking ones.
- **Don't write to PyPI/HF without the user explicitly asking** — releases are tag-triggered for a reason.
- **Don't bump the PyPI version when adding/removing/editing meshes.** Mesh changes are *data* updates and go through `publish-data.yml` to HF only. Bumping the package version misleads users about what changed. PyPI versions reserved for code, API, schema, or publisher changes.
