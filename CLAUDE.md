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

## Release Skills

These two skills must be present in your global `~/.claude/skills/` inventory every session:

| Skill | Trigger phrases | Script |
|---|---|---|
| `github-release` | "ship", "release", "ship vX.Y.Z", "create a release" | `python scripts/github_release.py` |
| `pypi-publish` | "publish to PyPI", "upload the wheel", "push to PyPI" | `python scripts/pypi_publish.py` |

Skills are installed at `~/.claude/skills/github-release/SKILL.md` and `~/.claude/skills/pypi-publish/SKILL.md`. If missing, reinstall: clone `https://github.com/anthropics/claude-plugins-official.git`, copy the skill-creator plugin, then recreate the two skill files above.

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
- Creates git tag and GitHub release with release notes and dist packages
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

- `kind: "mesh" | "boundary"` (default `"mesh"`) — `"boundary"` means an outline polygon with no element connectivity. The site hides the geometry-render button for boundaries.
- `test_case: bool` (default `false`) — surface this mesh on the **Test Suites** site tab and (when issue #11 lands) via `from admesh_domains import test_meshes`.
- `uploaded_date: str` — ISO date added to the registry.
- `modified_date: str` — ISO date the underlying file last changed (file mtime is a fine source).
- `contributor: str` — full name; the site formats it as "F. M. Last (YYYYMMDD)".

`SCHEMA_VERSION` did **not** bump for these — they're additive.

### Adding a mesh (data-only update — NO PyPI bump)
**Mesh additions / removals / metadata edits are data, not code. Don't tag.**
```bash
# 1. Drop the new mesh file into registry_data/meshes/, then run the
#    auto-suggester to find the right Domain (introduced in v0.3.0):
admesh-domains domain suggest registry_data/meshes/new.14
#    -> ranks existing Domains by IoU and either confirms a match or
#       drops you into an interactive prompt that emits a paste-ready
#       TOML stub for a new Domain.
# 2. Edit registry_data/manifest.toml (and admesh_domains/data/manifest.toml)
#    to add the entry under the chosen Domain.
# 3. Commit and push:
git add registry_data/ admesh_domains/data/manifest.toml
git commit -m "Add foo.14 to <Domain>"
git push origin main
# Triggers publish-data.yml automatically: HF gets a new revision
# tagged 'data-YYYY-MM-DD-<sha7>'. PyPI is untouched.
```

### Auditing existing Domain assignments
```bash
# Run the suggester against every existing mesh; reports any whose current
# Domain disagrees with the rank-1 suggestion (curation drift detector).
admesh-domains domain audit
admesh-domains domain audit --threshold 0.1   # tune sensitivity
admesh-domains domain audit --json            # machine-readable output
```

### Manual data publish
```bash
# Run the data-only HF publish out-of-band (no commit needed):
gh workflow run publish-data.yml -R domattioli/ADMESH-Domains
# Or with a custom tag:
gh workflow run publish-data.yml -R domattioli/ADMESH-Domains -f tag=data-special-rev
```

## Branch Discipline & Naming Policy

**Branch creation is ad-hoc** (no spec-kit workflow on this smaller project). When creating a feature branch:

1. **Branch naming**: `feature/short-description` or `fix/issue-number` for clarity
   - Example: `feature/cache-busting`, `fix/schema-validation`
2. **All PRs must be merged to main** (no long-lived feature branches)
   - Create PR on the branch
   - Resolve conflicts against main
   - Squash-merge (keeps main history clean)
   - Delete the branch after merge

**Policy enforcement**:
- Main branch requires PR review before merge
- No direct pushes to main
- CI runs on every PR (`validate-pr.yml` checks Python versions 3.9–3.12)
- Stale branches are cleaned up; don't force stale code through

**Release workflow** (code/API changes):
- Tag `v0.X.Y` on main → triggers `release.yml` → PyPI + HuggingFace with semantic version
- Data-only changes (mesh additions/edits): No PyPI bump; push to main → triggers `publish-data.yml` → HF tagged `data-YYYY-MM-DD-<sha7>`

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
