# Tasks: HuggingFace Dataset Publisher

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Numbered, dependency-ordered work items for implementing spec 006. Each task has a clear "done when" criterion. Tasks marked `[P]` can run in parallel with siblings; serial tasks gate downstream work.

---

## Phase 0 — Research (verify before building)

- **T-001** [P] **Verify `create_commit` accepts batch operations.** Run a throwaway script (locally, against a private test dataset) that uploads 5 small files in one `create_commit` call. **Done when**: confirmed batch works, recorded any per-commit op-count limit observed.
- **T-002** [P] **Confirm `hf_hub_download` cache layout cross-platform.** Read `huggingface_hub.constants.HF_HUB_CACHE` on macOS/Linux. **Done when**: noted in `data-model.md`.
- **T-003** [P] **Decide sdist content policy.** Re-run `python -m build` with a draft `MANIFEST.in` that excludes `registry_data/meshes/`. **Done when**: sdist size is < 100 KB and `pip install` from sdist still works.
- **T-004** [P] **Smoke-test the release secrets.** Trigger `.github/workflows/smoke-test-secrets.yml` via workflow_dispatch. **Done when**: green run; both tokens authenticate.
- **T-005** **Manually create the HF dataset repo.** On https://huggingface.co/new-dataset, create `domattioli/admesh-domains` (Public, MIT or no-license-yet). **Done when**: empty dataset exists at that slug.

## Phase 1 — Design Artifacts

- **T-010** **Author `data-model.md`.** Parquet column types per spec, sha256 derivation, sidecar lifecycle, schema-version embedding in Parquet metadata.
- **T-011** **Author `contracts/publisher-api.md`.** Function signatures, exception classes, `PublishResult` dataclass.
- **T-012** **Author `quickstart.md`.** Maintainer recipe: secrets → tag → verify → manual publish.

Phase 1 documents inform Phase 2 implementation; do not start T-020+ until Phase 1 review is signed off.

## Phase 2 — Build (publisher core)

- **T-020** **Implement `compute_sha256(path) -> str`** in `admesh_domains/publisher.py`. Plus unit test with a fixture file. **Done when**: test passes, function is the single source of hash truth.
- **T-021** **Implement `fetch_prior_hashes(hf_repo, token) -> dict[str, str]`.** Downloads prior `manifest.parquet` if it exists; returns `{}` on first publish. Unit test with mocked `huggingface_hub.hf_hub_download` (404 → empty dict). **Done when**: dedup data path works.
- **T-022** **Implement `build_parquet_sidecar(manifest, hashes) -> bytes`.** Uses `pyarrow`, writes to in-memory buffer, embeds `schema_version` in Parquet metadata. Unit test compares against snapshot. **Done when**: roundtrip read-back matches input.
- **T-023** **Author `templates/dataset_card.md.j2`** + `render_dataset_card(manifest, tag) -> str`. Snapshot-test the rendered output for a fixture manifest. **Done when**: rendered card includes domain/mesh counts, total size, quickstart code, source link.
- **T-024** **Implement `publish(manifest, tag, *, hf_repo, token, dry_run=False) -> PublishResult`.** Composes the above: validate → hash → diff → render → batched `create_commit` → `create_tag` → update `main` branch. Unit test with mocked `huggingface_hub` (asserts ops list shape). **Done when**: dry-run path emits a sane plan; live path commits exactly one revision.

## Phase 3 — Runtime API & CLI

- **T-030** **Add `Mesh.load()` to `schema.py`.** Calls `huggingface_hub.hf_hub_download` for `meshes/<domain>/<filename>` from the configured slug. Returns local `Path`. Imports `huggingface_hub` lazily and raises a clear `ImportError` if the `[hf]` extra isn't installed. Unit test with mocked download. **Done when**: `pip install admesh-domains[hf]` then `Mesh.load()` works against a real published mesh.
- **T-031** **Wire `publish` subcommand into `cli.py`.** Args: `--tag` (required), `--dry-run`, `--repo` (default from constant). Reads `HF_TOKEN` from env. **Done when**: `admesh-domains publish --tag v0.2.0 --dry-run` prints plan; `admesh-domains publish --help` documents all flags.
- **T-032** **Update `pyproject.toml` with `[publish]` and `[hf]` extras.** Verify `pip install -e ".[publish]"` and `pip install -e ".[hf]"` both resolve cleanly on Python 3.9–3.12. **Done when**: editable installs work; base install size unchanged.
- **T-033** **Author `MANIFEST.in`** to exclude `registry_data/meshes/` from the sdist. **Done when**: `python -m build` produces sdist < 100 KB and the wheel is unchanged.

## Phase 4 — CI/CD

- **T-040** **Author `.github/workflows/release.yml`.** Triggers on tag matching `v[0-9]+.[0-9]+.[0-9]+` (and `workflow_dispatch`). Steps:
  1. Checkout (`fetch-depth: 0` so the tag is visible).
  2. Set up Python 3.11.
  3. `pip install build twine` and `pip install -e ".[publish]"`.
  4. `python -m build` (sdist + wheel).
  5. `twine check dist/*`.
  6. `twine upload dist/*` using `PYPI_API_TOKEN`.
  7. Only on PyPI success: `admesh-domains publish --tag $GITHUB_REF_NAME` using `HF_TOKEN`.
  8. Forked-repo guard: `if: github.repository == 'domattioli/ADMESH-Domains'`.
  **Done when**: dry-run via workflow_dispatch with a fake tag prints expected plan and exits 0 without uploading anything; followed by a real tag pushing 0.2.0 end-to-end.
- **T-041** **Delete `.github/workflows/smoke-test-secrets.yml`.** It's served its purpose by Phase 0; release.yml exercises both tokens.

## Phase 5 — Validation

- **T-050** **First production publish.** Bump version to 0.2.0 in `pyproject.toml` and `__init__.py`, push tag `v0.2.0`. Verify all 5 success criteria from `spec.md`:
  - SC-001: published in ≤ 5 min.
  - SC-002: 100% of meshes appear at `meshes/<domain>/<filename>`.
  - SC-003: Re-trigger workflow_dispatch for same tag → zero file uploads.
  - SC-004: Dataset card renders correctly with totals + quickstart.
  - SC-005: From clean machine, `pip install admesh-domains[hf]`, then `Mesh.load()` round-trips a real mesh file.
- **T-051** **Update repo README** with HF dataset link and the `pip install admesh-domains[hf]` install line.
- **T-052** **Close out the spec** by adding a "Status: Complete" header to `spec.md` once SC-001..005 verified.

---

## Sequencing Summary

```
Phase 0 (T-001..005, mostly parallel)
    ↓
Phase 1 (T-010..012 serial — design first)
    ↓
Phase 2 (T-020..024 serial — publisher core)
    ↓
Phase 3 (T-030 [P], T-031 after T-030, T-032..033 [P])
    ↓
Phase 4 (T-040 → T-041 after green release)
    ↓
Phase 5 (T-050 → T-051..052)
```

## Out-of-band side tasks

- Track in GitHub issues, not here:
  - **#3** — Domain auto-suggester (filed)
  - License field on `Mesh` (deferred from spec 005; needed before accepting outside contributions)
  - `bounding_box` field on `Mesh` (foundation for issue #3 and the dataset-card map)

## Estimated total

~13 implementation tasks (T-020..T-052) + 5 research tasks. Solo dev, ~1–2 weekends end-to-end.
