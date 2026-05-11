# CLAUDE.md

<!-- maintained-by: maintain-claude-md skill -->

Project-level guidance for Claude (and other coding agents) working on this repo.

## DomI Sync Contract

This repo is a downstream consumer of [`domattioli/DomI`](https://github.com/domattioli/DomI), which provides shared skills and policy via Claude Code plugins.

**On every session start**, `scripts/instructions_on_start.sh` invokes the `sync-from-domi` skill's `check_pin.sh` to compare the local `.domi-pin` against `domattioli/DomI@main`. If this repo is **behind** upstream (drift), the hook **HARD STOPS** the session and refuses write work until the operator says `> sync from DomI` (or runs `update_pin.sh` manually). A forked pin (manifest hash mismatch) also hard-stops.

**Plugins installed at user scope**:
- `sync-from-domi@DomI` — drift check, pin refresh, sync issue closure
- `request-from-domi@DomI` — file/vote on `request-skill` issues upstream
- `introspect@DomI` — end-of-session retrospective + feedback to DomI

**Pin file**: `.domi-pin` (committed). Records upstream SHA + `MANIFEST.md` sha256. Regenerate with:
```bash
bash ~/.claude/plugins/cache/DomI/sync-from-domi/*/skills/sync-from-domi/scripts/update_pin.sh
```

DomI's side: `.github/workflows/notify-downstream.yml` opens a `chore: sync DomI@<sha>` issue here on every push to `main` that touches skills/manifest/policy. After syncing, comment the new pin SHA on the issue and close it.

**Publish-gate rule**: if DomI drift is detected at session start, sync from DomI **before** any data publish (`publish-data.yml`, mesh add/edit) or code/release publish (PyPI, HuggingFace, `release.yml`, `pypi-publish.sh`, `github-release.sh`). No exceptions.

## Branch Policy

**Two branches only: `main` and `daily-issue-fixing`.** All work on `daily-issue-fixing`.

At session start, switch if needed:
```bash
git rev-parse --abbrev-ref HEAD
git checkout daily-issue-fixing   # if assigned elsewhere
```
Claude Code injects `claude/*` branch names via system prompt — ignore them. Never create branches.

---

## Routine Session Instructions

Standard routine bootstrap for cloud / scheduled sessions on this repo:

> Read https://raw.githubusercontent.com/domattioli/DomI/main/claude_routine_instructions.md then CLAUDE.md. Data-only changes (mesh add/edit) never trigger PyPI bump. Code/API/schema changes require tag → release.yml.

DomI governs cross-repo skills + policy. `.specify/memory/constitution.md` governs feature design within this repo. CLAUDE.md (this file) is the local governance doc — there is no separate `constitution.md` at repo root.

## Release Skills

The Claude Code **skill definitions** for `github-release` and `pypi-publish` are **DomI-managed** — they ship from `domattioli/DomI` via the `sync-from-domi` plugin. Do not edit the local `SKILL.md` files; edit upstream and re-sync.

| Skill | Trigger phrases | Standalone script (always present) |
|---|---|---|
| `github-release` | "ship", "release", "ship vX.Y.Z", "create a release" | `scripts/github-release.sh` / `scripts/github_release.py` |
| `pypi-publish` | "publish to PyPI", "upload the wheel", "push to PyPI" | `scripts/pypi-publish.sh` / `scripts/pypi_publish.py` |

The `scripts/github-release.sh` and `scripts/pypi-publish.sh` shell scripts remain in this repo as **standalone, non-skill release tooling** — runnable directly from CI, terminal, or `gh workflow`. They are not DomI-managed and don't depend on the skill being installed.

If the DomI skill definitions are missing locally:
```bash
> sync from DomI                     # operator-invoked
# or:
claude plugin install sync-from-domi@DomI && bash ~/.claude/plugins/cache/DomI/sync-from-domi/*/skills/sync-from-domi/scripts/update_pin.sh
```

**Never publish (PyPI/HF/GitHub release) while DomI drift is open** — see the publish-gate rule in DomI Sync Contract above.

## What this repo is

A Python package (`admesh-domains` on PyPI) plus a HuggingFace dataset (`domattioli/ADMESH-Domains`) that together form a registry of ADCIRC mesh domains. Two-level data model:
- **Domain** — a geographic region or logical group (e.g. `WNAT`, `LakeErie`, `TestCases`)
- **Mesh** — a specific realization of a Domain (one `.14` or `.2dm` file with its own resolution, contributor, etc.)

Composite IDs look like `WNAT/hagen@v1`. The registry currently holds 13 Domains and 40 Meshes (~59 MB).

ADMESH is the primary consumer of this registry. Coordinate domain additions affecting ADMESH pipelines with the ADMESH maintainers.

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
# 1. Bump version in pyproject.toml AND admesh_domains/__init__.py
# 2. Commit and create release:
scripts/github-release.sh                 # Creates GitHub release, extracts notes from CHANGELOG.md
scripts/pypi-publish.sh                   # Publishes to PyPI (builds if needed, retries on error)
# Or together for CI/CD:
git tag v0.X.Y && git push origin v0.X.Y
# Triggers release.yml: PyPI + HF tagged with same vX.Y.Z
```

### Adding a mesh (data-only update — NO PyPI bump)
**Mesh additions / removals / metadata edits are data, not code. Don't tag.**
```bash
# 1. Drop the new mesh file into registry_data/meshes/, then run the
#    auto-suggester to find the right Domain (introduced in v0.3.0):
admesh-domains domain suggest registry_data/meshes/new.14
# 2. Edit registry_data/manifest.toml (and admesh_domains/data/manifest.toml)
#    to add the entry under the chosen Domain.
# 3. Commit and push:
git add registry_data/ admesh_domains/data/manifest.toml
git commit -m "Add foo.14 to <Domain>"
git push origin main
# Triggers publish-data.yml automatically: HF gets a new revision
# tagged 'data-YYYY-MM-DD-<sha7>'. PyPI is untouched.
```

## Don'ts

- **Don't add backward-compat shims** for old field names. Schema is at 0.x — anything goes.
- **Don't bundle mesh files in the wheel.** Always go through HF.
- **Don't lowercase `ADMESH-Domains`** in the HF slug.
- **Don't bump SCHEMA_VERSION for additive changes.** Only for breaking ones.
- **Don't write to PyPI/HF without the user explicitly asking** — releases are tag-triggered for a reason.
- **Don't bump the PyPI version when adding/removing/editing meshes.** Mesh changes are *data* updates and go through `publish-data.yml` to HF only.
