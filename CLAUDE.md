# CLAUDE.md

<!-- maintained-by: maintain-claude-md skill -->

Project-level guidance for Claude (and other coding agents) on this repo.

## DomI Sync Contract

This repo = downstream consumer of [`domattioli/DomI`](https://github.com/domattioli/DomI), which provides shared skills + policy via Claude Code plugins.

**On every session start**, `scripts/instructions_on_start.sh` invokes `sync-from-domi` skill's `check_pin.sh` to compare local `.domi-pin` against `domattioli/DomI@main`. If repo **behind** upstream (drift), hook **HARD STOPS** session + refuses write work until operator says `> sync from DomI` (or runs `update_pin.sh` manually). Forked pin (manifest hash mismatch) also hard-stops.

**Plugins installed at user scope**:
- `sync-from-domi@DomI` — drift check, pin refresh, sync issue closure
- `request-from-domi@DomI` — file/vote on `request-skill` issues upstream
- `introspect@DomI` — end-of-session retrospective + feedback to DomI

**Pin file**: `.domi-pin` (committed). Records upstream SHA + `MANIFEST.md` sha256. Regenerate with:
```bash
bash ~/.claude/plugins/cache/DomI/sync-from-domi/*/skills/sync-from-domi/scripts/update_pin.sh
```

DomI's side: `.github/workflows/notify-downstream.yml` opens `chore: sync DomI@<sha>` issue here on every push to `main` touching skills/manifest/policy. After syncing, comment new pin SHA on issue + close.

**Publish-gate rule**: if DomI drift detected at session start, sync from DomI **before** any data publish (`publish-data.yml`, mesh add/edit) or code/release publish (PyPI, HuggingFace, `release.yml`, `pypi-publish.sh`, `github-release.sh`). No exceptions.

## Routine Session Instructions

Standard routine bootstrap for cloud / scheduled sessions on this repo:

> Read https://raw.githubusercontent.com/domattioli/DomI/main/claude_routine_instructions.md then CLAUDE.md. Data-only changes (mesh add/edit) never trigger PyPI bump. Code/API/schema changes require tag → release.yml.

DomI governs cross-repo skills + policy. `.specify/memory/constitution.md` governs feature design within this repo. CLAUDE.md (this file) = local governance doc — no separate `constitution.md` at repo root.

## Stream Timeout Prevention

1. Each numbered task ONE AT A TIME. Complete fully, confirm, next.
2. Never write file >~150 lines in single tool call. Multi-pass append/edit if longer.
3. Fresh session if conversation long (20+ tool calls). Error worsens with session size.
4. Keep grep/search outputs short. Flags `--include`, `-l` (list files only) limit output size.
5. On timeout, retry shorter form. Don't repeat entire task from scratch.

## Release Skills

Claude Code **skill definitions** for `github-release` + `pypi-publish` = **DomI-managed** — ship from `domattioli/DomI` via `sync-from-domi` plugin. Don't edit local `SKILL.md` files; edit upstream + re-sync.

| Skill | Trigger phrases | Standalone script (always present) |
|---|---|---|
| `github-release` | "ship", "release", "ship vX.Y.Z", "create a release" | `scripts/github-release.sh` / `scripts/github_release.py` |
| `pypi-publish` | "publish to PyPI", "upload the wheel", "push to PyPI" | `scripts/pypi-publish.sh` / `scripts/pypi_publish.py` |

`scripts/github-release.sh` + `scripts/pypi-publish.sh` shell scripts remain in repo as **standalone, non-skill release tooling** — runnable directly from CI, terminal, or `gh workflow`. Not DomI-managed; don't depend on skill being installed.

If DomI skill definitions missing locally:
```bash
> sync from DomI                     # operator-invoked
# or:
claude plugin install sync-from-domi@DomI && bash ~/.claude/plugins/cache/DomI/sync-from-domi/*/skills/sync-from-domi/scripts/update_pin.sh
```

**Never publish (PyPI/HF/GitHub release) while DomI drift open** — see publish-gate rule in DomI Sync Contract above.

## What this repo is

Python package (`admesh-domains` on PyPI) + HuggingFace dataset (`domattioli/ADMESH-Domains`) together forming registry of ADCIRC mesh domains. Two-level data model:
- **Domain** — geographic region or logical group (e.g. `WNAT`, `LakeErie`, `TestCases`)
- **Mesh** — specific realization of Domain (one `.14` or `.2dm` file with own resolution, contributor, etc.)

Composite IDs look like `WNAT/hagen@v1`. Registry currently holds 13 Domains + 40 Meshes (~59 MB).

## Key conventions

- **Pure-Python only** for runtime deps. Heavy deps (`huggingface_hub`, `pyarrow`, `jinja2`) live behind optional extras `[hf]` + `[publish]`. Base install must stay small.
- **Dataclasses, not pydantic.** Validation hand-rolled in `*.validate()` methods. Don't pull pydantic.
- **`from __future__ import annotations`** in every module. Type hints = lazy strings.
- **TOML manifest = single source of truth.** Parquet sidecar (`manifest.parquet`) = *derived* at publish time. Don't write code depending on sidecar being authoritative.
- **Mesh files live on HF, not in wheel.** `MANIFEST.in` excludes `registry_data/meshes/` from sdist. `Mesh.load()` fetches via `huggingface_hub.hf_hub_download` (cached).
- **HF slug = mixed-case**: `domattioli/ADMESH-Domains` (capital A, D, M). Use literally — don't lowercase.

## Repo layout

```
admesh_domains/      Python package
admesh_domains/data/ Bundled manifest.toml (in wheel)
registry_data/       Source-of-truth manifest + mesh files (excluded from wheel)
specs/               Spec-driven design (one folder per feature)
.specify/            Spec-kit infrastructure (constitution, templates)
scripts/             One-shot data tooling
tests/               pytest suite
.github/workflows/   release.yml (tag → PyPI + HF), validate-pr.yml (CI)
```

## Common workflows

### Validate manifest
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
**Use for code, API, schema, or publisher changes — NOT for adding meshes.**
```bash
# 1. Bump version in pyproject.toml AND admesh_domains/__init__.py
# 2. Commit and create release:
scripts/github-release.sh                 # Creates GitHub release, extracts notes from CHANGELOG.md
scripts/pypi-publish.sh                   # Publishes to PyPI (builds if needed, retries on error)
# Or together for CI/CD:
git tag v0.X.Y && git push origin v0.X.Y
# Triggers release.yml: PyPI + HF tagged with same vX.Y.Z
```

### Release Skills (Manual Publishing)

**`github-release.sh`** — Non-interactive GitHub release creation
- Auto-detects: credentials (gh auth), version (pyproject.toml), repo (git remote), release notes (CHANGELOG.md)
- Creates git tag + GitHub release with release notes + dist packages
- Validates: gh CLI authenticated, dist files exist, version format valid
- Output: One-line success with release URL, exit code 0/1
- Suitable for: CI/CD workflows, manual releases, automated release gates

**`pypi-publish.sh`** — Non-interactive PyPI publishing
- Auto-detects: credentials (PYPI_TOKEN env var or ~/.pypirc), package name/version (pyproject.toml)
- Builds packages if missing (python -m build)
- Uploads to PyPI via twine with 3-attempt retry (exponential backoff 2s/4s/8s)
- Validates: PyPI credentials exist, package files match expected naming
- Verifies: Polls PyPI endpoint to confirm package appears (up to 5 attempts)
- Output: One-line success with PyPI URL, exit code 0/1
- Suitable for: CI/CD workflows, independent PyPI publishes (without GitHub release)

### Mesh schema fields (added in 0.3.2, all optional/additive)

- `kind: "mesh" | "boundary"` (default `"mesh"`) — `"boundary"` means outline polygon with no element connectivity. Site hides geometry-render button for boundaries.
- `test_case: bool` (default `false`) — surface this mesh on **Test Suites** site tab + (when issue #11 lands) via `from admesh_domains import test_meshes`.
- `uploaded_date: str` — ISO date added to registry.
- `modified_date: str` — ISO date underlying file last changed (file mtime fine source).
- `contributor: str` — full name; site formats as "F. M. Last (YYYYMMDD)".

`SCHEMA_VERSION` did **not** bump for these — additive.

### Adding a mesh (data-only update — NO PyPI bump)
**Mesh additions / removals / metadata edits = data, not code. Don't tag.**
```bash
# 1. Drop new mesh file into registry_data/meshes/, then run
#    auto-suggester to find right Domain (introduced in v0.3.0):
admesh-domains domain suggest registry_data/meshes/new.14
#    -> ranks existing Domains by IoU + either confirms match or
#       drops you into interactive prompt emitting paste-ready
#       TOML stub for new Domain.
# 2. Edit registry_data/manifest.toml (and admesh_domains/data/manifest.toml)
#    to add entry under chosen Domain.
# 3. Commit + push:
git add registry_data/ admesh_domains/data/manifest.toml
git commit -m "Add foo.14 to <Domain>"
git push origin main
# Triggers publish-data.yml automatically: HF gets new revision
# tagged 'data-YYYY-MM-DD-<sha7>'. PyPI untouched.
```

### Auditing existing Domain assignments
```bash
# Run suggester against every existing mesh; reports any whose current
# Domain disagrees with rank-1 suggestion (curation drift detector).
admesh-domains domain audit
admesh-domains domain audit --threshold 0.1   # tune sensitivity
admesh-domains domain audit --json            # machine-readable output
```

### Manual data publish
```bash
# Run data-only HF publish out-of-band (no commit needed):
gh workflow run publish-data.yml -R domattioli/ADMESH-Domains
# Or with custom tag:
gh workflow run publish-data.yml -R domattioli/ADMESH-Domains -f tag=data-special-rev
```

## Branch Discipline & Naming Policy

**Branch creation = ad-hoc** (no spec-kit workflow on this smaller project). When creating feature branch:

1. **Branch naming**: `feature/short-description` or `fix/issue-number` for clarity
   - Example: `feature/cache-busting`, `fix/schema-validation`
2. **All PRs must merge to main** (no long-lived feature branches)
   - Create PR on branch
   - Resolve conflicts against main
   - Squash-merge (keeps main history clean)
   - Delete branch after merge

**Policy enforcement**:
- Main branch requires PR review before merge
- No direct pushes to main
- CI runs on every PR (`validate-pr.yml` checks Python versions 3.9–3.12)
- Stale branches cleaned up; don't force stale code through

**Release workflow** (code/API changes):
- Tag `v0.X.Y` on main → triggers `release.yml` → PyPI + HuggingFace with semantic version
- Data-only changes (mesh additions/edits): No PyPI bump; push to main → triggers `publish-data.yml` → HF tagged `data-YYYY-MM-DD-<sha7>`

## Specs index

Active + shipped specs live under `specs/`. Use spec-kit-style format: `spec.md`, `plan.md`, `tasks.md`, plus optional `data-model.md`, `contracts/`, `quickstart.md`, `research.md`. Constitution at `.specify/memory/constitution.md` defines principles gating feature plans.

| Spec | Status |
|---|---|
| `005-adcirc-mesh-registry` | Superseded by standalone repo migration |
| `006-huggingface-publisher` | Shipped in v0.2.0 |

## Don'ts

- **Don't add backward-compat shims** for old field names. Schema at 0.x — anything goes.
- **Don't bundle mesh files in wheel.** Always go through HF.
- **Don't lowercase `ADMESH-Domains`** in HF slug.
- **Don't bump SCHEMA_VERSION for additive changes.** Only for breaking ones.
- **Don't write to PyPI/HF without user explicitly asking** — releases tag-triggered for reason.
- **Don't bump PyPI version when adding/removing/editing meshes.** Mesh changes = *data* updates, go through `publish-data.yml` to HF only. Bumping package version misleads users about what changed. PyPI versions reserved for code, API, schema, or publisher changes.
