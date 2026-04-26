# Contract: Publisher Python API

The public surface of `admesh_domains.publisher`. Stable for the duration of schema 0.2; breaking changes bump the schema MAJOR.

## Module

```python
from admesh_domains.publisher import (
    publish,
    compute_sha256,
    fetch_prior_hashes,
    build_parquet_sidecar,
    render_dataset_card,
    PublishResult,
    PublisherError,
    PublishTokenError,
    PublishValidationError,
    DEFAULT_HF_REPO,
)
```

## Constants

```python
DEFAULT_HF_REPO: str = "domattioli/ADMESH-Domains"
```

The canonical HF dataset slug. CI passes this implicitly; CLI users can override with `--repo`.

## `publish(...)` — main entrypoint

```python
def publish(
    manifest: Manifest,
    tag: str,
    *,
    hf_repo: str = DEFAULT_HF_REPO,
    token: str | None = None,
    dry_run: bool = False,
) -> PublishResult: ...
```

**Args**:

- `manifest` — already-loaded, already-validated `Manifest` object.
- `tag` — release tag string, e.g. `"v0.2.0"`. Used for the HF tag and Parquet metadata.
- `hf_repo` — target dataset slug; defaults to `DEFAULT_HF_REPO`.
- `token` — HF write token. If `None`, read from `HF_TOKEN` env var. Raises `PublishTokenError` if missing.
- `dry_run` — if `True`, computes the plan (uploads/skips/deletes) and renders artifacts, but performs no HF writes.

**Behavior** (in order):

1. Validate every `Mesh.path` exists locally; fail fast if not.
2. Compute sha256 for every mesh.
3. Fetch prior hashes from HF (empty dict on first publish).
4. Build the upload list (changed/new files only) and the deletion list (files in prior sidecar but not in current manifest).
5. Build the Parquet sidecar bytes and render the dataset card.
6. If `dry_run`: return `PublishResult` with planned operations; no HF API calls.
7. Otherwise: single `create_commit` with `[upload_file ops] + [delete_file ops] + [add manifest.parquet] + [add README.md]`. Then `create_tag(tag)` and update `main` branch via a follow-up empty commit (or `update_branch` if available).
8. Return the populated `PublishResult`.

**Errors**:

- `PublishTokenError` — token missing/invalid (caught early before any network calls).
- `PublishValidationError` — manifest fails local validation, or a referenced mesh file is missing on disk.
- `PublisherError` — any other runtime failure (HF API error, hash mismatch, etc.). Wraps the underlying exception.

## `PublishResult`

```python
@dataclass
class PublishResult:
    tag: str
    hf_repo: str
    dry_run: bool
    commit_sha: str | None     # None on dry-run
    uploaded: list[str]        # hf_paths uploaded
    skipped: list[str]         # hf_paths skipped (hash match)
    deleted: list[str]         # hf_paths deleted
    total_meshes: int
    total_size_mb: float
```

`commit_sha` is the SHA-1 of the HF revision created. `None` on dry-run.

## Helper functions (also public)

### `compute_sha256(path: Path) -> str`

Returns lowercase hex sha256 of the file at `path`. Raises `FileNotFoundError` if missing.

### `fetch_prior_hashes(hf_repo: str, token: str) -> dict[str, str]`

Downloads `manifest.parquet` from `revision="main"` of `hf_repo`, returns `{hf_path: content_sha256}`. Returns `{}` if the file or repo does not exist (first publish).

### `build_parquet_sidecar(manifest: Manifest, hashes: dict[str, str], tag: str) -> bytes`

Returns Parquet-encoded bytes per the schema in [data-model.md](../data-model.md). `hashes` keys are `full_id`; the function looks up each hash by `full_id`.

### `render_dataset_card(manifest: Manifest, tag: str) -> str`

Returns the rendered Markdown of the dataset card README, using the bundled Jinja template.

## Exceptions

```python
class PublisherError(Exception): ...
class PublishTokenError(PublisherError): ...
class PublishValidationError(PublisherError): ...
```

All inherit from `Exception` via `PublisherError` so callers can `except PublisherError` to catch any publisher-originated failure.

## CLI surface

```
admesh-domains publish --tag v0.2.0 [--repo SLUG] [--dry-run]
```

Reads `HF_TOKEN` from env. Exit codes: `0` on success, `1` on validation/token error, `2` on HF API error.
