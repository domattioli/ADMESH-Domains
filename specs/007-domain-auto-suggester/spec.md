# Feature Specification: Domain Auto-Suggester

**Feature Branch**: `007-domain-auto-suggester`
**Created**: 2026-04-26
**Status**: Draft
**Issue**: [#3](https://github.com/domattioli/ADMESH-Domains/issues/3)
**Input**: When a contributor adds a new mesh via PR, the registry should suggest which existing Domain it likely belongs to (or recommend creating a new one) based on geometry. Human-in-the-loop: the tool proposes, the reviewer decides.

## Summary

Add a CLI command `admesh-domains suggest-domain <new-mesh.14>` that:

1. Parses the new mesh's bounding box from its fort.14 / .2dm header.
2. Compares it against every existing Domain's bounding box(es) in the manifest.
3. Prints a ranked list of candidate Domains (with overlap scores) plus an explicit "none of the above — propose a new Domain" option.
4. Exits with a status code that distinguishes "confident match", "uncertain match", and "no match" so CI / pre-commit can branch on it.

This is the **Tier 1** implementation from the carry-over discussion: bbox-overlap scoring only. Tier 2 (boundary-polygon Hausdorff/IoU) and Tier 3 (geometry embeddings) are out of scope and tracked separately.

## Clarifications

### Session 2026-04-26

- **Q (C-1)**: Where does the suggester run? → **A**: As a CLI command, runnable both locally (pre-commit) and in CI (a `suggest-domain` GitHub Action that comments on PRs that add a mesh file). PR comment integration is a follow-up; the CLI is the contract.
- **Q (C-2)**: What overlap metric? → **A**: **IoU** (intersection over union) of bounding boxes, plus a simple "centroid distance" tiebreaker. IoU is between 0 and 1, easy to threshold, and treats a small mesh inside a big domain bbox as a strong match.
- **Q (C-3)**: Confidence thresholds? → **A**: `IoU >= 0.5` = confident match (one candidate). `0.05 <= IoU < 0.5` = uncertain (multiple candidates ranked). `IoU < 0.05` for all = no match (suggest new Domain).
- **Q (C-4)**: How does the suggester handle non-geographic bboxes (synthetic test cases, projected coords)? → **A**: It only compares same-coordinate-system bboxes. Any mesh whose bbox sits outside lat/lon range is auto-suggested as a synthetic-category Domain (no IoU computed against geographic Domains).
- **Q (C-5)**: Is this a hard CI gate or an advisory check? → **A**: Advisory only — the suggester never blocks a merge. Reviewer decides.

## User Scenarios & Testing

### User Story 1 — Contributor adds a regional mesh and gets the right Domain suggested (Priority: P1)

A contributor downloads a new ADCIRC mesh of the Gulf of Mexico from NOAA and wants to add it to the registry. They run the suggester and get back the right Domain to add it under, or a clear "none" with a recommendation to propose a new Domain.

**Why this priority**: This is the core scenario. Without this, contributors guess, and we end up with `WNAT_3` and `WNAT_v3` and `WNAT_test_v3` as separate flat entries again.

**Independent Test**: Take an existing real-world mesh in our registry, run the suggester against it, confirm the suggester ranks its actual parent Domain first.

**Acceptance Scenarios**:

1. **Given** a new mesh whose bbox is `(-95, 25, -80, 31)` (Gulf of Mexico — overlaps WNAT), **When** the contributor runs `admesh-domains suggest-domain new.14`, **Then** the output lists `WNAT` first with `IoU >= 0.5` and exit code `0` (confident).
2. **Given** a new mesh whose bbox is `(-110, 30, -100, 40)` (US Southwest, no current Domain), **When** the contributor runs the command, **Then** the output says "no confident match" and prints the highest-IoU candidate plus an explicit "propose a new Domain" hint, with exit code `1`.
3. **Given** a new mesh whose bbox is `(-180, -90, 180, 90)` (whole world — overlaps everything), **When** the suggester runs, **Then** all real-world Domains appear in the ranked list with their IoU scores, and the user gets exit code `2` (ambiguous).

---

### User Story 2 — Maintainer wants to bulk-audit existing Domain assignments (Priority: P2)

A maintainer suspects some current Mesh-to-Domain assignments are wrong (e.g. someone put a Lake Erie mesh under `GreatLakes`). They want to run the suggester against every existing mesh and see disagreements.

**Why this priority**: Useful but not urgent. Curation drift is a slow problem. Lower priority because most current assignments are correct (we did the import manually and carefully).

**Acceptance Scenarios**:

1. **Given** the existing manifest, **When** the maintainer runs `admesh-domains audit-domains`, **Then** the output lists meshes whose suggester result differs from their current assignment, with both the current and suggested Domain.

---

### User Story 3 — PR comment from CI (Priority: P3)

When a PR adds a `.14` file to `registry_data/meshes/`, a GitHub Action runs the suggester and posts a comment with the recommendations.

**Why this priority**: Nice-to-have UX. Lower priority because the local CLI already covers the workflow, and PR comments require additional GitHub Action plumbing.

**Acceptance Scenarios**:

1. **Given** a PR adds `meshes/new.14`, **When** CI runs, **Then** a comment appears within 2 minutes containing the ranked suggestions and a link to the suggester docs.

## Edge Cases

- **Mesh file unparseable** → suggester errors with exit code 3 and a clear message; reviewer falls back to manual.
- **Manifest empty / first mesh ever** → output is "no current Domains exist; propose a new one" with exit code 1.
- **Mesh bbox is degenerate (zero area)** → IoU is undefined; suggester treats as "no match" (exit 1).
- **Multiple Domains tied within 0.01 IoU** → all listed in the uncertain bucket; user picks.
- **Coordinate-system mismatch** (e.g. new mesh in UTM, existing all lat/lon) → no comparisons made; suggester reports "no compatible Domains found" and recommends new Domain with `category=real-world` if the user confirms it's projected, else `synthetic`.

## Requirements

### Functional

- **FR-001**: New CLI subcommand `admesh-domains suggest-domain PATH`.
- **FR-002**: The command parses the bbox from the mesh file (reusing `scripts/extract_bboxes.py` logic — refactor into `admesh_domains.geometry`).
- **FR-003**: For each existing Domain with at least one geographic-bbox mesh, compute the IoU of the new bbox vs. the Domain's union bbox.
- **FR-004**: Print a ranked list:
  ```
  Suggestions for new.14 (bbox: -95.00, 25.00, -80.00, 31.00):
    1. WNAT          IoU=0.62  (confident)
    2. ChesapeakeBay IoU=0.04  (low)
    Propose new Domain: 'NewDomain'
  ```
- **FR-005**: Exit codes: `0` confident match, `1` no match, `2` ambiguous (≥2 candidates above 0.5 IoU), `3` parse error.
- **FR-006**: Optional `--json` flag emits machine-readable output for CI consumption.
- **FR-007**: New CLI subcommand `admesh-domains audit-domains` that runs the suggester against every existing mesh and reports disagreements (User Story 2).
- **FR-008**: A new module `admesh_domains/geometry.py` houses bbox / IoU helpers, importable by external tooling.

### Non-Functional

- **NFR-001**: Suggester for a single 50K-node mesh completes in under 1 second on a modern laptop (mesh parse + IoU calcs over 13 Domains).
- **NFR-002**: No new heavy dependencies. IoU is arithmetic; uses stdlib only. Stays in the base install (no `[publish]` extra needed).
- **NFR-003**: Constitution Principle VI ("curation over auto-magic") is honored — the suggester proposes, the human decides; exit codes are advisory, never blocking.

## Data Model

No schema changes. The suggester reads existing `Mesh.bounding_box` values (added in v0.2.1) and computes derived per-Domain "union bboxes" in memory.

```python
# admesh_domains/geometry.py
@dataclass
class IoUScore:
    domain_name: str
    iou: float
    centroid_distance_deg: float | None
    confidence: str  # "confident" | "uncertain" | "low"


def compute_iou(a: BoundingBox, b: BoundingBox) -> float:
    """Intersection over union of two bboxes. Returns 0 for disjoint."""

def domain_union_bbox(domain: Domain) -> BoundingBox | None:
    """Smallest bbox covering all of a Domain's meshes' bboxes (geographic only)."""

def suggest_domain(
    new_bbox: BoundingBox, manifest: Manifest
) -> list[IoUScore]:
    """Ranked candidate Domains, highest IoU first."""
```

## Success Criteria

- **SC-001**: For every current real-world mesh in the registry, running the suggester returns its actual parent Domain as the rank-1 candidate.
- **SC-002**: A synthetic Gulf-of-Mexico bbox (no current Domain) gets exit code 1 + a "propose new Domain" message.
- **SC-003**: The full audit (`audit-domains`) on the current 40-mesh registry runs in under 2 seconds.
- **SC-004**: `--json` output is valid JSON parseable by `jq`.
- **SC-005**: Adding the suggester does NOT add any base-install dependencies (verified by `pip install admesh-domains` install-size diff).

## Assumptions

- All Meshes that should be auto-suggestable have a populated `bounding_box` (true as of v0.2.1).
- IoU is "good enough" for Tier 1. Higher accuracy via boundary polygon comparison is a follow-up spec.
- Coordinate-system inference is heuristic only (lat/lon if values are in `[-180, 180] × [-90, 90]`, otherwise "projected/unknown"). A future spec may add explicit `Mesh.coordinate_system` if the heuristic breaks.

## Out of Scope

- **Boundary polygon comparison** (Hausdorff distance, IoU on boundary polygon, not just bbox). Defer to spec 008+.
- **Geometry embedding / ML clustering**. Defer to spec 009+.
- **Reprojection between coordinate systems**. Out of scope until we have a use case.
- **PR comment automation** beyond exit-code-based CI gating. Defer until the CLI itself is in use.
- **A "merge two Domains" CLI** — different problem (curation cleanup), separate spec.

## Dependencies

- New module: `admesh_domains/geometry.py` (stdlib only)
- New CLI subcommands: `suggest-domain`, `audit-domains` in `admesh_domains.cli`
- Refactor opportunity: move bbox-extraction logic from `scripts/extract_bboxes.py` into `admesh_domains.geometry` so the same code parses both new submissions and existing meshes
- Existing: `Mesh.bounding_box`, `Domain.meshes`, `BoundingBox` (all in `schema.py`)

## Open Questions for Plan Phase

- Should the suggester also propose a `category` (real-world vs synthetic) based on the bbox coordinate-system heuristic? Probably yes — the contributor would have to set it anyway.
- What format for "propose new Domain" — a TOML stub the contributor pastes into `manifest.toml`, or just a textual hint?
- Should `audit-domains` output be sortable by IoU disagreement magnitude so the worst offenders surface first?
