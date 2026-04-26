# Implementation Plan: HuggingFace Dataset Publisher

**Branch**: `006-huggingface-publisher` | **Date**: 2026-04-25 | **Spec**: [spec.md](spec.md)

## Summary

Ship two coupled deliverables in a single release workflow:

1. **`publisher.py`** — pure-Python module that takes a validated `Manifest`, computes per-mesh sha256 hashes, dedups against the prior `manifest.parquet` on HF, builds a fresh Parquet sidecar + Jinja-rendered dataset card, and atomically commits everything to `huggingface.co/datasets/domattioli/admesh-domains` via `huggingface_hub.create_commit`.
2. **`.github/workflows/release.yml`** — semver-tag-triggered pipeline that runs `twine upload` to PyPI, then runs the publisher against the freshly-tagged manifest, then updates the HF `main` branch to the new revision.

Plus a runtime addition: `Mesh.load()` that fetches from the HF mirror via `hf_hub_download` (gated behind the `[hf]` extra so casual users don't pull `huggingface_hub`).

## Technical Context

- **Language/Version**: Python 3.9+ (matches base package; `huggingface_hub` and `pyarrow` both ship pure-Python or manylinux wheels for 3.9–3.13).
- **New deps (gated as extras)**:
  - `[publish]`: `huggingface_hub >= 0.20`, `pyarrow >= 14.0`, `jinja2 >= 3.0`, `twine >= 4.0`
  - `[hf]`: `huggingface_hub >= 0.20`
- **Target platforms**: Linux (CI), macOS (local dev). Windows is *aspirational* — `huggingface_hub` works there, untested.
- **Performance**: NFR-001 caps the full publish at 5 minutes for 40 meshes / 59 MB. The sha256 dedup (post-first-publish) should make subsequent publishes finish in well under 1 minute when no files changed.
- **Storage on HF**: ~60 MB initial, growing as meshes are added. Well under HF's per-dataset free-tier limits.
- **Auth**: `HF_TOKEN` env var (read by `huggingface_hub` natively); `PYPI_API_TOKEN` consumed by `twine`.

## Project Structure

### Documentation (this feature)

```text
specs/006-huggingface-publisher/
├── spec.md          # done
├── plan.md          # this file
├── data-model.md    # Phase 1 — Parquet column schema, content_sha256 derivation
├── contracts/
│   └── publisher-api.md   # Phase 1 — public function signatures, exceptions
├── quickstart.md    # Phase 1 — "release in 5 minutes" maintainer guide
└── tasks.md         # Phase 2 — output of /tasks
```

### Source Code

```text
admesh_domains/
├── publisher.py                  # NEW — main publisher module (currently empty)
├── templates/
│   └── dataset_card.md.j2        # NEW — HF README template
├── schema.py                     # MODIFY — add Mesh.load()
└── cli.py                        # MODIFY — add `publish` subcommand

.github/workflows/
├── release.yml                   # NEW — semver-tag triggered pipeline
└── publish-hf.yml                # DELETE — replaced by release.yml (the empty stub from earlier)

tests/
└── test_publisher.py             # NEW — unit tests w/ mocked huggingface_hub

pyproject.toml                    # MODIFY — add [publish] and [hf] extras
```

## Phase 0 — Research

Items to verify before writing code (each ≤ 30 min):

- **R-1**: `huggingface_hub.create_commit` operation limits — does it accept arbitrary numbers of file ops in one commit, or is there a batch ceiling? (Need 40+ ops for first publish.)
- **R-2**: Can `create_commit` upload binary mesh files alongside text README and Parquet in a single commit? (Confirm Operation types: `CommitOperationAdd` for files, `CommitOperationDelete` for tombstones — both should accept arbitrary content.)
- **R-3**: How does `hf_hub_download` resolve `revision="main"` vs `revision="v0.2.0"` and where does it cache? (Confirm `HF_HUB_CACHE` honors XDG on Linux, `~/Library/Caches/huggingface` on macOS.)
- **R-4**: PyPI behavior on tag re-push — twine will fail loudly on duplicate version, which is the correct behavior. Verify the workflow surfaces this as a clear error rather than silently masking it.
- **R-5**: Confirm sdist size after the v0.1.1 surprise (18.8 MB included `registry_data/meshes/`). Decide: keep meshes out of the sdist (smaller upload, but breaks `pip install --no-binary`), or accept the size. **Tentative**: exclude via `MANIFEST.in` since meshes belong on HF.

## Phase 1 — Design Artifacts

To author next (separate documents):

### `data-model.md`

- Parquet schema (all 16 columns from spec.md), with pyarrow type for each.
- `content_sha256` derivation: `hashlib.sha256(file_bytes).hexdigest()` — single-pass, no streaming needed (max file is ~15 MB).
- Sidecar lifecycle: read prior → diff hashes → write new with new hashes.
- Schema versioning: embed `schema_version` (matches `admesh_domains.SCHEMA_VERSION`) as Parquet file metadata.

### `contracts/publisher-api.md`

- Function signatures for `publisher.py`:
  - `publish(manifest, tag, *, hf_repo, token, dry_run=False) -> PublishResult`
  - `compute_sha256(path: Path) -> str`
  - `build_parquet_sidecar(manifest, hashes: dict[str, str]) -> bytes`
  - `render_dataset_card(manifest, tag) -> str`
  - `fetch_prior_hashes(hf_repo, token) -> dict[str, str]`
- Custom exceptions: `PublisherError`, `PublishTokenError`, `PublishValidationError`.
- `PublishResult` dataclass: `tag`, `commit_sha`, `uploaded`, `skipped`, `deleted`, `dry_run`.

### `quickstart.md`

Maintainer-facing recipe:
1. One-time HF setup (create dataset, generate token, add `HF_TOKEN` + `PYPI_API_TOKEN` repo secrets).
2. Cutting a release: `git tag v0.2.0 && git push origin v0.2.0`.
3. What to verify on HF afterwards (revision, file count, dataset card render).
4. Manual publish for ops use: `pip install admesh-domains[publish] && admesh-domains publish --tag v0.2.0`.

## Phase 2 — Tasks (deferred to /tasks)

Highlights of expected task structure (full breakdown in `tasks.md` after `/tasks`):

- **T-001..T-005**: Phase 0 research items (above).
- **T-010..T-015**: Implement `publisher.py` (one task per public function), each with mocked-`huggingface_hub` unit test.
- **T-020**: Author `templates/dataset_card.md.j2` + render-snapshot test.
- **T-025**: Add `Mesh.load()` to `schema.py` + test (mock `hf_hub_download`).
- **T-030**: Wire CLI `publish` subcommand into `cli.py`.
- **T-035**: Update `pyproject.toml` with `[publish]` and `[hf]` extras; verify `pip install admesh-domains[publish]` resolves.
- **T-040**: Author `.github/workflows/release.yml`. Test by pushing a throwaway tag against a *test* HF slug (`domattioli/admesh-domains-test`).
- **T-045**: Author `MANIFEST.in` to exclude `registry_data/meshes/` from sdist.
- **T-050**: First production publish — `git tag v0.2.0`, observe end-to-end, verify HF dataset state matches spec acceptance criteria.

## Constitution Check

This repo has no formal `.specify/memory/constitution.md`, but the implicit principles from spec 005 still apply:

| Principle | Status | Notes |
|---|---|---|
| Pure-Python | **PASS** | `huggingface_hub`, `pyarrow`, `jinja2` all ship pure-Python or manylinux wheels for the supported Python range. |
| Reference-test discipline | **PASS (adapted)** | No upstream reference; use snapshot tests for the dataset card and Parquet schema, plus mocked-`huggingface_hub` tests for the publisher. |
| Stage-by-stage bottom-up | **PASS** | Phase ordering: research → publisher core (with mocks) → CLI → workflow → first real publish. Each layer has tests before the next is wired in. |

## Risk & Complexity Tracking

- **R-1 (high)**: First real publish exposes any `huggingface_hub` API assumption that didn't hold under mocks. Mitigation: T-040's throwaway-tag test against the *test* HF slug catches this before a real release tag.
- **R-2 (medium)**: `pyarrow` is a non-trivial dep (~50 MB install). Putting it under `[publish]` extra contains the impact — base install stays at ~50 KB.
- **R-3 (low)**: HF outage during publish leaves the dataset in its prior good state (atomic commit). PyPI side already shipped; the next tag will retry HF cleanly.
- **R-4 (low)**: Re-publishing the same tag is idempotent (sha256 dedup + atomic commit), so accidental double-runs are harmless.

## Done When

- A fresh tag `git push origin v0.2.0` results in: PyPI 0.2.0 published, HF `domattioli/admesh-domains` updated with all 40 meshes under `meshes/<domain>/<filename>`, `manifest.parquet` regenerated, `README.md` rendered, HF `main` branch fast-forwarded — all within 5 minutes.
- Acceptance scenarios in `spec.md` (User Stories 1, 2, 3) all pass when validated manually.
- `pip install admesh-domains[hf]` followed by `Mesh.load()` for a known mesh downloads from HF and returns a local `Path`.
