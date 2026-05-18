# Spec 064: Content-Addressable Identifiers for Domains and Meshes

**Feature:** Optional content-derived unique identifiers for `Domain` and `Mesh`, computed from canonical content (geometry bytes, normalized boundary, or both).
**Status:** Draft (Design Phase — scoping review needed)
**MVP Scope:** `Mesh.content_uid` only (deterministic SHA-256 of `.14` file bytes). Domain content-UID deferred.
**Effort:** LARGE — splittable on axis below.
**Track:** Code (new optional schema field; no SCHEMA_VERSION bump if additive-only).

---

## Problem Statement (from #64)

Quoting the issue verbatim:
> not sure if these are needed, whether meshes need them too, what constitutes a "domain" (eg what if two compared domains are 99.99% similar but their lat/long is just slightly different? this feature request may go beyond uid into a much larger scoped problem

Two distinct concerns are entangled:

1. **Naming UIDs** (already solved): each `Mesh` is uniquely addressed by `Domain.name + "/" + Mesh.id` (e.g., `ChesapeakeBay/default@v1`). `Mesh.full_id()` computes this; `Domain.name` validation forbids `/` to keep the grammar unambiguous. This is the *curatorial* identifier — stable across renames inside the manifest, human-meaningful, and already enforced by `schema.py`.
2. **Content-derived equivalence** (open): if two domains share a near-identical boundary (lat/long differ by 1e-5), should they collapse to the same identity? If a mesh file is byte-renamed, should it still be recognized as the same artifact? This is *content addressing* — useful for dedup, provenance, and cross-revision pinning, but introduces a similarity threshold the curator must specify.

**Recommendation:** Do **both**, but ship them as separate features. (1) is already done. (2) splits cleanly along two axes.

---

## Current State Audit

| Surface | What exists today | Where |
|---|---|---|
| Mesh local ID | `id: str` (e.g., `"default@v1"`) | `schema.py:Mesh.id` |
| Mesh global ID | `full_id()` → `"<Domain>/<mesh_id>"` | `schema.py:Mesh.full_id` |
| Mesh registration validation | Composite-ID grammar enforced (`Domain.name` rejects `/`) | `schema.py:Domain.validate` |
| Mesh content identity | **none** — `size_mb` is the only content-derived field, and it is coarse | — |
| Domain identity | `name: str` (e.g., `"ChesapeakeBay"`) — slug, curator-assigned | `schema.py:Domain.name` |
| Domain geometric identity | **none** — `bounding_box` is approximate, no canonical hash | — |
| Duplicate detection | none — manual visual inspection during curation | — |

**Implication:** the existing system handles renaming, deletion, versioning at the registry-curator layer (you-the-human notice when two entries are dupes). It does **not** help when the same `.14` file is uploaded under two different `Mesh.id` slugs, or when two domains drift apart by 1e-5 degrees due to projection roundtrips.

---

## Proposed Design (Split into 3 sub-features)

### Sub-feature A — `Mesh.content_uid` (file-hash UID) — **MVP**

Add one optional field to `Mesh`:

```python
content_uid: Optional[str] = None  # "sha256:<hex>" of canonical .14 bytes
```

Computed by:
```python
def compute_content_uid(self) -> str:
    """SHA-256 of the raw .14 bytes. Stable across rename. None if file missing."""
    path = self.path()
    if path is None or not path.exists():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
```

CLI helper:
```
admesh-domains uid-audit registry_data/manifest.toml
```
walks every mesh, computes `content_uid`, reports duplicates (same hash, different `full_id()`).

**Properties:**
- Additive field; no `SCHEMA_VERSION` bump (Principle III).
- No new base-install deps; `hashlib` is stdlib.
- Curator-opt-in: field stays `None` until `uid-audit --write` populates the manifest.
- Detects exact duplicates (byte-identical files registered twice).
- Does **not** detect near-duplicates (different float precision, reordered nodes).

**Risk:** byte-canonical hashing is sensitive to whitespace and line-ending churn. Mitigation: lock canonical form via `_canonical_bytes(path: Path) -> bytes` that normalizes `\r\n` → `\n` and trailing whitespace; store the normalization version alongside the hash (`sha256-v1:<hex>`) so we can re-canonicalize without losing old UIDs.

### Sub-feature B — `Domain.content_uid` (boundary-hash UID)

Same shape as A, but computed from a canonical boundary representation:

```python
# Domain
content_uid: Optional[str] = None  # "boundary-v1:<hex>"
```

Computation: extract the convex hull (or alpha-shape) of each child mesh's boundary nodes, normalize to integer grid at fixed precision (e.g., 1e-4 degrees), serialize as canonical WKT, hash.

**Why separate from A:** requires `shapely` (new optional dep — `[geometry]` extra), needs precision-choice debate, and the canonical-form contract must be locked before any UID is stored or we can't compare across releases.

### Sub-feature C — Near-duplicate detection (similarity, not identity)

For "99.99% similar boundary" detection, identity hashing is the wrong tool. This needs:
- IoU on convex hulls (`Domain.iou(other) >= 0.999`)
- Hausdorff distance on boundary polygons
- Centroid + area delta within tolerance

This is a query feature, not an identity feature: `find_similar_domains(domain, threshold=0.999) -> list[Domain]`. It lives in `query.py`, not `schema.py`, and does **not** persist a hash. Suggest deferring until a real dedup task arrives — currently no Pacific or near-overlapping domains exist in the registry.

---

## Acceptance Criteria

Per sub-feature, gated on operator picking which subset ships:

### A (MVP)
- [ ] `Mesh.content_uid: Optional[str]` field added; `None` by default.
- [ ] `Mesh.compute_content_uid()` returns `"sha256-v1:<hex>"` or `None` (file missing).
- [ ] `admesh-domains uid-audit <manifest>` walks all meshes, reports duplicates by hash.
- [ ] `admesh-domains uid-audit --write` mutates `manifest.toml` to backfill the field (atomic; preserves order).
- [ ] `Manifest.find_by_uid(uid: str) -> Optional[Mesh]` lookup helper.
- [ ] Test: two renamed copies of the same `.14` hash identical → audit flags them.
- [ ] Test: roundtrip determinism — `manifest → write → reread` preserves UIDs.
- [ ] `SCHEMA_VERSION` unchanged (additive field).
- [ ] No new base-install dep (`hashlib` is stdlib).

### B (boundary hash, deferred)
- [ ] Canonical-form contract documented in `docs/CONTENT_UID.md` (precision, projection, WKT vs WKB).
- [ ] `shapely` added to `[geometry]` extra (or piggybacks on existing `[publish]`).
- [ ] `Domain.content_uid` populates lazily; `boundary-v1:<hex>` prefix.
- [ ] All current 13 domains hash to 13 distinct UIDs.

### C (similarity query, deferred)
- [ ] Separate spec; not blocking A or B.

---

## Files to Touch (per sub-feature)

### A (MVP)
- `admesh_domains/schema.py` — add `content_uid` field + `compute_content_uid()` to `Mesh`.
- `admesh_domains/manifest.py` — add `find_by_uid()` to `Manifest`.
- `admesh_domains/cli.py` — register `uid-audit` subcommand.
- `tests/test_schema.py` — add `TestContentUid`.
- `tests/test_manifest.py` — add `test_find_by_uid_roundtrip`.
- `docs/CONTENT_UID.md` — new short doc describing the contract, normalization rules, and prefix grammar.
- `registry_data/manifest.toml`, `admesh_domains/data/manifest.toml` — **only after** operator runs `uid-audit --write` and reviews diff.

### B
- `admesh_domains/geometry.py` — add canonical-boundary serializer.
- `admesh_domains/schema.py` — add `content_uid` to `Domain`.
- `pyproject.toml` — `[geometry]` extra (or extend `[publish]`).

### C
- `admesh_domains/query.py` — `find_similar_domains()`.

---

## Approach (sub-feature A)

1. Implement `Mesh.compute_content_uid()` reading via `Mesh.path()`; canonicalize bytes (`\r\n → \n`, strip trailing whitespace per line); SHA-256; prefix with `sha256-v1:`.
2. `uid-audit` walks `Manifest`, computes UIDs, groups by hash; reports duplicates as `WARN`, missing files as `INFO`.
3. `--write` flag rewrites `manifest.toml` preserving comments + order (use `tomlkit`, not `tomllib` — already a `[publish]` dep transitively? if not, this stays opt-in CLI feature only).
4. Track: Code. Triggers `release.yml` only on tag push; no PyPI bump until the *whole* of sub-feature A ships and CHANGELOG documents it.

---

## Constitution Check (sub-feature A — MVP)

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest source of truth | PASS | All UID storage flows through `manifest.toml`; `uid-audit --write` is the only mutation path. No runtime auto-edit. |
| II. Pure-Python, optional heavy deps | PASS | `hashlib` is stdlib; `tomlkit` (if needed for in-place rewrite) goes behind `[publish]` extra (already present). Base install untouched. |
| III. Schema explicit | PASS | `content_uid` is additive optional field; readers tolerate absence. No `SCHEMA_VERSION` bump per Principle III ("Adding optional fields = not breaking change"). |
| IV. Atomic releases — code/data split | PASS | Code track (new API + CLI subcommand). `release.yml` on `v0.X.Y` tag. Data backfill (running `uid-audit --write`) is a separate data-track commit that fires `publish-data.yml`. |
| V. Test before tagging | PASS | `tests/test_schema.py::TestContentUid` required before tag. |
| VI. Curation over auto-magic | PASS | UID is **opt-in** — populated only when curator runs `uid-audit --write`, never auto-computed at load time. Avoids the #57 orphan-entry failure mode (manifest writes are explicit and reviewed). |

---

## Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| Canonicalization drift across releases | HIGH | Version the prefix (`sha256-v1`, `sha256-v2`); on bump, recompute, store both, deprecate old in CHANGELOG. |
| Whitespace/line-ending churn invalidates UIDs | MEDIUM | Strict canonical-form spec in `docs/CONTENT_UID.md`; test that CRLF/LF variants of the same `.14` produce identical UID. |
| Backfill PR churn (all 41 meshes get new field at once) | MEDIUM | `uid-audit --write` is opt-in; backfill is a single reviewable data-track commit, separate from the code-track PR that adds the field. |
| Near-duplicate users confuse identity for similarity | LOW | `docs/CONTENT_UID.md` opens with "exact-match only; for similarity use `find_similar_domains()` (planned)". |
| `tomlkit` not yet a dep — adds install weight if needed | LOW | Restrict in-place rewrite to the `[publish]` extra (already heavy). For users without it, `uid-audit` is read-only. |

---

## Budget Assessment & Split Rationale

| Sub-feature | Budget | Split-on |
|---|---|---|
| A — `Mesh.content_uid` (file hash) | **Medium** | Standalone; 1 spec / 1 plan / 1 PR. |
| B — `Domain.content_uid` (boundary hash) | **Medium** | Standalone; depends on `[geometry]` extra decision. |
| C — `find_similar_domains` (similarity) | **Medium** | Standalone; lives in `query.py`. |
| **Total #64 scope** | **LARGE** | **Splittable on the 3-feature axis above.** |

Per routine ("Budget LARGE + splittable → stop. List sub-issues."), no implementation in this run. The three sub-issues below should be filed, each tractable in one session.

---

## Sub-Issues to Open (proposal — operator approves)

1. **`feat: Mesh.content_uid file-hash UID (MVP for #64)`** — sub-feature A. Adds optional `content_uid` field, `compute_content_uid()`, `uid-audit` CLI. Track: Code. Budget: medium. Closes part of #64.
2. **`feat: Domain.content_uid boundary-hash UID`** — sub-feature B. Adds `[geometry]` extra (or extends `[publish]`), `Domain.content_uid`, canonical boundary serializer. Track: Code. Budget: medium. Depends on #64 sub-feature A landing first (shared `docs/CONTENT_UID.md`).
3. **`feat: find_similar_domains() near-duplicate query`** — sub-feature C. Similarity (not identity). Lives in `query.py`. Track: Code. Budget: medium. No dependency on A or B. Defer until a real near-duplicate domain exists in registry.

Issue #64 stays open as the umbrella; each sub-issue links back via `Relates #64`.

---

## Open Clarifications (route to operator before implementation)

1. **Canonical form for `.14`** — accept exact bytes, or normalize EOL + trailing whitespace? (`docs/CONTENT_UID.md` MUST lock this before any UID is stored.)
2. **In-place rewrite tool** — `tomlkit` (preserves comments, costs install weight) vs simple line-based patcher (fragile but zero new deps)?
3. **UID prefix grammar** — `sha256-v1:<hex>` (proposed) vs CAS-style `urn:sha-256:<hex>`?
4. **Auto-compute on load** — strict opt-in (proposed; Principle VI) vs compute-and-cache transparently?
5. **Domain boundary precision** — 1e-4 degrees (≈11 m at equator) vs configurable? Affects sub-feature B.
6. **Sub-issue ordering** — ship A first standalone, or block on B (so doc lands once)?

---

## References

- Issue #64 (this spec)
- `admesh_domains/schema.py` — `Mesh.full_id()`, `Domain.name` validation
- `.specify/memory/constitution.md` — Principles I (manifest truth), III (schema-explicit), VI (curation)
- Issue #57 — orphan manifest entry (cautionary tale informing opt-in storage)
- Issue #59, spec 034 — `--register` opt-in precedent for atomic manifest writes
- Issue #25 — downstream consumer (mesh strategy comparison) that would benefit from dedup signal

---

**Author:** daily-issue-fixing routine
**Date:** 2026-05-18
**Scope:** Spec only. No code in this commit. Per routine: LARGE+splittable → STOP, list sub-issues.
