# ADMESH-Domains Constitution

Non-negotiable principles gating every feature plan in `specs/`. Plans must explicitly address each principle (PASS / N/A justified / FAIL → don't proceed).

## I. The TOML manifest is the source of truth

Domain → Meshes hierarchy in `registry_data/manifest.toml` = only authoritative state. All other artifacts *derived*:

- `admesh_domains/data/manifest.toml` — bundled copy in wheel
- `manifest.parquet` on HF — flat sidecar for queryability
- `README.md` on HF — auto-rendered dataset card
- Anything in PyPI metadata

If feature wants to change registry state, edits TOML. Schema-changing features must update both manifest copies AND parser AND Parquet builder in one PR. Any drift between these = bug.

## II. Pure-Python, optional heavy deps

Base install (`pip install admesh-domains`) must stay under ~100 KB + pull only:

- `tomli ; python_version < '3.11'`

Anything heavier (`huggingface_hub`, `pyarrow`, `jinja2`, `pandas`, `shapely`, `matplotlib`, `folium`, ...) must live behind optional extra (`[hf]`, `[publish]`, future `[viz]`, etc.). Extras imported lazily inside function needing them, with clear `ImportError` pointing at install command.

Justification for any new base-install dep must appear in spec.

## III. Schema changes are explicit

Schema version (`admesh_domains.SCHEMA_VERSION`) bumped only for breaking changes:

- Removing field
- Changing field's type
- Renaming field
- Changing constraint that rejects previously-valid data

Adding optional fields = **not** breaking change, stays at same SCHEMA_VERSION. Parquet sidecar gains columns silently — readers must tolerate unknown columns.

Schema version = **independent** of package version (PyPI) + manifest data version (`metadata.version`). Don't conflate.

## IV. Atomic releases — and separate code from data

**Two release tracks** with strictly separate concerns:

**Code track** (PyPI + HF together):

- Triggered by strict-semver git tag (`v[0-9]+.[0-9]+.[0-9]+`)
- `release.yml` runs PyPI upload first; HF publish runs only on PyPI success
- HF writes go through one `create_commit` (no partial state)
- HF tag + `main` branch update happen in same workflow run
- Use for: code, API, schema, publisher, dataset-card-template changes
- Hot-fixes follow same path — bump patch version, push tag

**Data track** (HF only):

- Triggered by push to `main` touching `registry_data/**` or `admesh_domains/data/manifest.toml` (or manual `workflow_dispatch`)
- `publish-data.yml` publishes to HF with `data-YYYY-MM-DD-<sha7>` tag
- **PyPI not touched.** Bumping package version for data change misleads users about what's in wheel.
- Use for: adding/removing/editing meshes or Domain metadata
- Every data change still gets reproducible HF revision; readers can pin to `data-2026-04-26-abcdef0` exactly like code release

Never edit published artifact in place. PyPI immutable; HF revisions = git-style commits.

## V. Test before tagging

Every PR runs `validate-pr.yml`: manifest validation + pytest matrix (3.9/3.11/3.12) + publisher dry-run. Releases skip none — `release.yml` re-validates + re-tests before any upload.

When adding feature:
- Public functions need at least one unit test (mock external services).
- Schema changes need roundtrip test (write → read → equality).
- Publisher changes need dry-run snapshot test.

## VI. Curation over auto-magic

When registry needs human judgment (which Domain new mesh belongs to, what its `applications` are, whether mesh = `real-world` vs `synthetic`), prefer **suggest-then-approve** tools over fully automatic resolution. Auto-suggesters fine; auto-mergers not.

PR review = curation gate.

## VII. External Upstream (DomI)

Foundational skills and policy governed by [domattioli/DomI](https://github.com/domattioli/DomI).

1. `.domi-pin` ledger MUST be committed and current.
2. Session start auto-checks drift via `scripts/instructions_on_start.sh`. Hard stop on drift; `/sync-from-domi` unblocks.
3. Skills from DomI take precedence over inline implementations. Local repo-specific skills (those NOT shipped by DomI) are exempt.
4. Repo-specific principles in this constitution override DomI universal defaults where they conflict.
5. This section does NOT affect existing repo-specific algorithmic principles.

## Constitution version

1.0 — established 2026-04-26. Amend by editing this file in PR with rationale; bump version on substantial changes.
