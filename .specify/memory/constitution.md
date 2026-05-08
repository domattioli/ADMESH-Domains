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

`ADMESH-Domains` is a downstream consumer of [`domattioli/DomI`](https://github.com/domattioli/DomI), which governs shared skills, MANIFEST, and cross-repo policy.

1. `.domi-pin` (committed) records the upstream SHA + MANIFEST.md sha256. Never hand-edit; regenerate via `update_pin.sh`.
2. `scripts/instructions_on_start.sh` hard-stops on drift (exit 1 or 3). Run `/sync-from-domi` before any write work when blocked.
3. DomI skills take precedence over inline reimplementation. Submit changes upstream via `request-from-domi`; this repo is pull-only.
4. **Publish gate**: sync from DomI before any data publish (`publish-data.yml`), PyPI release, or HuggingFace update if drift is detected at session start.
5. ADMESH is the primary consumer of this registry. Coordinate domain additions affecting ADMESH pipelines with the ADMESH maintainers.

## Constitution version

1.1 — 2026-05-08: Added § VII External Upstream (DomI).
