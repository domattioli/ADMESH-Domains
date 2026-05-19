# Mesh.content_uid — Content-Addressable Identifier

**Status:** Implemented (MVP — sub-feature A of [#64](https://github.com/domattioli/ADMESH-Domains/issues/64); see [#65](https://github.com/domattioli/ADMESH-Domains/issues/65)).
**Scope:** `Mesh.content_uid` only. `Domain.content_uid` (boundary hash) is sub-feature B (#66); near-duplicate similarity queries are sub-feature C (#67).

## What it is

An optional, deterministic content-derived identifier for a `Mesh`. It is a SHA-256 of the mesh file's canonical bytes, prefixed with `sha256-v1:`:

```
sha256-v1:<64 lowercase hex chars>
```

The UID is **opt-in**: the field defaults to `None` and is only persisted into `manifest.toml` when a curator runs `admesh-domains uid-audit --write`. The library never auto-mutates the manifest at runtime (Constitution Principle VI).

## What it solves

- Detects when the same mesh file is registered under two different `Mesh.id` slugs.
- Lets downstream consumers pin a mesh by content rather than by curator-assigned name.
- Stable across renames in `manifest.toml`.

## What it does *not* solve

- **Near-duplicate detection.** If two boundaries agree to within 1e-5 degrees, the file bytes differ and the UIDs differ. Use `find_similar_domains()` (sub-feature C, #67) for that.
- **Cross-format equivalence.** A `.14` (ADCIRC) and a `.2dm` (SMS) describing the same geometry hash differently.
- **Schema drift detection.** This hashes file bytes, not metadata.

## Canonical form (v1)

Mesh files vary in line-ending convention (LF on Linux, CRLF on Windows, occasional CR-only legacy artifacts) and may carry incidental trailing whitespace. The canonicalization function `admesh_domains.schema.canonical_mesh_bytes` normalizes both before hashing:

1. **Line endings:** `\r\n` and bare `\r` are both rewritten to `\n`.
2. **Per-line trailing whitespace:** `b" "` and `b"\t"` stripped from the end of each line. Leading whitespace is preserved (ADCIRC `.14` indentation can be significant).
3. **Trailing empty lines:** preserved (the final newline counts).

A round-trip of the same logical content through CRLF↔LF conversion does *not* change the UID.

## Prefix versioning

The `sha256-v1:` prefix locks the canonicalization rules above. If the canonical form ever needs to change (e.g., to also normalize internal whitespace, or to canonicalize node-ordering), the new variant must ship under a new prefix (`sha256-v2:` etc.) and the previous version stays valid until explicitly retired. Readers compare full prefixed strings — they do not strip the prefix.

## CLI

```bash
# Read-only: compute UIDs for every mesh, report duplicates.
admesh-domains uid-audit                                  # bundled manifest
admesh-domains uid-audit registry_data/manifest.toml      # dev checkout
admesh-domains uid-audit --json                           # machine-readable

# Curator action: persist computed UIDs back into the manifest.
admesh-domains uid-audit registry_data/manifest.toml --write
```

Exit codes:

| Code | Meaning |
|---|---|
| `0` | No duplicates. |
| `1` | At least one duplicate group found. |
| `3` | `--write` with no source path (in-memory manifest). |
| `4` | `--write` requested but `tomlkit` not installed (`pip install admesh-domains[publish]`). |

`--write` requires `tomlkit` (installed transitively with the `[publish]` extra). Read-only audits work on a bare install — `hashlib` is stdlib.

## Python API

```python
from admesh_domains import load_manifest

m = load_manifest("registry_data/manifest.toml")

# Compute on demand (file must exist on disk).
mesh = next(m.all_meshes())
uid = mesh.compute_content_uid()  # "sha256-v1:..." or None if file missing

# Lookup by UID (after content_uid has been populated).
found = m.find_by_uid("sha256-v1:abc...")
```

## Schema impact

`content_uid` is an additive optional field on `Mesh`. **`SCHEMA_VERSION` is unchanged** (Constitution Principle III: "Adding optional fields = not breaking change"). Readers on older versions of the library ignore the field; readers on this version tolerate its absence.

## Backfill policy

Populating UIDs across the registry is a **data-track operation**: it edits `registry_data/manifest.toml` only. Per Constitution Principle IV, that commit should land separately from the code-track commit that introduces the field, so reviewers see two distinct diffs:

1. Code commit (this feature): adds the field, the `compute_content_uid()` method, the `Manifest.find_by_uid()` lookup, the `uid-audit` CLI, and tests.
2. Data commit (separate, optional): the curator runs `admesh-domains uid-audit registry_data/manifest.toml --write`, reviews the diff, and pushes. `publish-data.yml` then mirrors the change to HuggingFace.

## Related

- Spec: [`specs/064-content-uids/spec.md`](../specs/064-content-uids/spec.md) §A.
- Umbrella issue: [#64](https://github.com/domattioli/ADMESH-Domains/issues/64).
- MVP issue: [#65](https://github.com/domattioli/ADMESH-Domains/issues/65).
- Sibling: [#66](https://github.com/domattioli/ADMESH-Domains/issues/66) (Domain boundary hash), [#67](https://github.com/domattioli/ADMESH-Domains/issues/67) (similarity query).
- Cautionary tale (atomic manifest writes): [#57](https://github.com/domattioli/ADMESH-Domains/issues/57).
