# ADMESH-Domains Constitution

The non-negotiable principles that gate every feature plan in `specs/`. Plans must explicitly address each principle (PASS / N/A justified / FAIL → don't proceed).

## I. The TOML manifest is the source of truth

The Domain → Meshes hierarchy in `registry_data/manifest.toml` is the only authoritative state. All other artifacts are *derived*:

- `admesh_domains/data/manifest.toml` — bundled copy in the wheel
- `manifest.parquet` on HF — flat sidecar for queryability
- `README.md` on HF — auto-rendered dataset card
- Anything in PyPI metadata

If a feature wants to change registry state, it edits the TOML. Schema-changing features must update both manifest copies AND the parser AND the Parquet builder in one PR. Any drift between these is a bug.

## II. Pure-Python, optional heavy deps

Base install (`pip install admesh-domains`) must stay under ~100 KB and pull only:

- `tomli ; python_version < '3.11'`

Anything heavier (`huggingface_hub`, `pyarrow`, `jinja2`, `pandas`, `shapely`, `matplotlib`, `folium`, ...) must live behind an optional extra (`[hf]`, `[publish]`, future `[viz]`, etc.). Extras are imported lazily inside the function that needs them, with a clear `ImportError` pointing at the install command.

Justification for any new base-install dep must appear in the spec.

## III. Schema changes are explicit

Schema version (`admesh_domains.SCHEMA_VERSION`) is bumped only for breaking changes:

- Removing a field
- Changing a field's type
- Renaming a field
- Changing a constraint that rejects previously-valid data

Adding optional fields is **not** a breaking change and stays at the same SCHEMA_VERSION. The Parquet sidecar gains columns silently — readers must tolerate unknown columns.

Schema version is **independent** of the package version (PyPI) and the manifest data version (`metadata.version`). Don't conflate them.

## IV. Atomic releases — and separate code from data

There are **two release tracks** with strictly separate concerns:

**Code track** (PyPI + HF together):

- Triggered by a strict-semver git tag (`v[0-9]+.[0-9]+.[0-9]+`)
- `release.yml` runs PyPI upload first; HF publish runs only on PyPI success
- HF writes go through one `create_commit` (no partial state)
- HF tag and `main` branch update happen in the same workflow run
- Use this for: code, API, schema, publisher, dataset-card-template changes
- Hot-fixes follow the same path — bump the patch version, push the tag

**Data track** (HF only):

- Triggered by push to `main` touching `registry_data/**` or `admesh_domains/data/manifest.toml` (or manual `workflow_dispatch`)
- `publish-data.yml` publishes to HF with a `data-YYYY-MM-DD-<sha7>` tag
- **PyPI is not touched.** Bumping the package version for a data change misleads users about what's in the wheel.
- Use this for: adding/removing/editing meshes or Domain metadata
- Every data change still gets a reproducible HF revision; readers can pin to `data-2026-04-26-abcdef0` exactly like a code release

Never edit a published artifact in place. PyPI is immutable; HF revisions are git-style commits.

## V. Test before tagging

Every PR runs `validate-pr.yml`: manifest validation + pytest matrix (3.9/3.11/3.12) + publisher dry-run. Releases skip none of these — `release.yml` re-validates and re-tests before any upload.

When adding a feature:
- Public functions need at least one unit test (mock external services).
- Schema changes need a roundtrip test (write → read → equality).
- Publisher changes need a dry-run snapshot test.

## VI. Curation over auto-magic

When the registry needs human judgment (which Domain a new mesh belongs to, what its `applications` are, whether a mesh is `real-world` vs `synthetic`), prefer **suggest-then-approve** tools over fully automatic resolution. Auto-suggesters are fine; auto-mergers are not.

The PR review is the curation gate.

## VII. External Upstream (DomI)

Foundational skills and policy governed by [domattioli/DomI](https://github.com/domattioli/DomI).

1. `.domi-pin` ledger MUST be committed and current.
2. Session start auto-checks drift via `scripts/instructions_on_start.sh`. Hard stop on drift; `/sync-from-domi` unblocks.
3. Skills from DomI take precedence over inline implementations. Local repo-specific skills (those NOT shipped by DomI) are exempt.
4. Repo-specific principles in this constitution override DomI universal defaults where they conflict.
5. This section does NOT affect existing repo-specific algorithmic principles.

## Constitution version

1.1 — established 2026-04-26. Amended 2026-05-08: added principle VII (External Upstream: DomI). Amend by editing this file in a PR with rationale; bump the version on substantial changes.
