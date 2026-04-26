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

## IV. Atomic releases

Releases are tag-triggered (`v[0-9]+.[0-9]+.[0-9]+`) and atomic across PyPI + HF:

- PyPI uploads first; if it fails, the workflow stops
- HF publish runs only on PyPI success
- HF writes go through one `create_commit` (no partial state visible)
- HF tag and `main` branch update happen in the same workflow run

Hot-fixes follow the same path — bump the patch version, push the tag. Never edit a published artifact in place.

## V. Test before tagging

Every PR runs `validate-pr.yml`: manifest validation + pytest matrix (3.9/3.11/3.12) + publisher dry-run. Releases skip none of these — `release.yml` re-validates and re-tests before any upload.

When adding a feature:
- Public functions need at least one unit test (mock external services).
- Schema changes need a roundtrip test (write → read → equality).
- Publisher changes need a dry-run snapshot test.

## VI. Curation over auto-magic

When the registry needs human judgment (which Domain a new mesh belongs to, what its `applications` are, whether a mesh is `real-world` vs `synthetic`), prefer **suggest-then-approve** tools over fully automatic resolution. Auto-suggesters are fine; auto-mergers are not.

The PR review is the curation gate.

## Constitution version

1.0 — established 2026-04-26. Amend by editing this file in a PR with rationale; bump the version on substantial changes.
