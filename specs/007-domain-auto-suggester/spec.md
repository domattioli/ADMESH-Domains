# Feature Specification: Domain Auto-Suggester

**Feature Branch**: `007-domain-auto-suggester`
**Created**: 2026-04-26
**Status**: ✅ Complete (shipped in v0.3.0 — 2026-04-26)
**Issue**: [#3](https://github.com/domattioli/ADMESH-Domains/issues/3)
**Input**: When a contributor adds a new mesh via PR, the registry should suggest which existing Domain it likely belongs to (or recommend creating a new one) based on geometry. Human-in-the-loop: the tool proposes, the reviewer decides.
**Verified**: SC-001..005 all pass — `admesh-domains domain audit` returns 0 disagreements across the full 41-mesh registry, `domain suggest` returns rank-1 = current Domain for every existing real-world mesh, `--json` output is jq-parseable, base install size unchanged (no new deps).

## Summary

Add a CLI command `admesh-domains suggest-domain <new-mesh.14>` that:

1. Parses the new mesh's bounding box from its fort.14 / .2dm header.
2. Compares it against every existing Domain's bounding box(es) in the manifest.
3. Prints a ranked list of candidate Domains (with overlap scores) plus an explicit "none of the above — propose a new Domain" option.
4. Exits with a status code that distinguishes "confident match", "uncertain match", and "no match" so CI / pre-commit can branch on it.

This is the **Tier 1** implementation from the carry-over discussion: bbox-overlap scoring only. Tier 2 (boundary-polygon Hausdorff/IoU) and Tier 3 (geometry embeddings) are out of scope and tracked separately.

## Clarifications

### Session 2026-04-26 (initial)

- **Q (C-1)**: Where does the suggester run? → **A**: As a CLI command, runnable both locally (pre-commit) and in CI (a GitHub Action that comments on PRs that add a mesh file). PR comment integration is a follow-up; the CLI is the contract.
- **Q (C-2)**: What overlap metric? → **A**: **IoU** (intersection over union) of bounding boxes, plus a simple "centroid distance" tiebreaker.
- **Q (C-3)**: Confidence thresholds? → **A**: `IoU >= 0.5` = confident match. `0.05 <= IoU < 0.5` = uncertain (multiple candidates ranked). `IoU < 0.05` for all = no match (suggest new Domain).
- **Q (C-4)**: How does the suggester handle non-geographic bboxes? → **A**: It only compares same-coordinate-system bboxes. Any mesh whose bbox sits outside lat/lon range is auto-suggested as a synthetic-category Domain.
- **Q (C-5)**: Is this a hard CI gate or an advisory check? → **A**: Advisory only — the suggester never blocks a merge.

### Session 2026-04-26 (clarify)

- **Q (C-6)**: Per-mesh vs Domain-union IoU? → **A**: **Both**. Compute the *best per-mesh IoU* within each Domain AND the *Domain-union bbox IoU*. Show both numbers in output. Rank primarily by per-mesh IoU (more accurate); union is a secondary signal that surfaces "this matches a wide-coverage Domain."
- **Q (C-7)**: Antimeridian / dateline crossing? → **A**: Skip wrapping bboxes for v1; log a warning. We have zero Pacific meshes today. Antimeridian-safe IoU is deferred to a future spec.
- **Q (C-8)**: "Propose new Domain" output when no match? → **A**: **Interactive prompt** by default — asks for `name`, `full_name`, `category` (real-world / synthetic, default real-world), `region` (if real-world), `applications` (comma-separated, optional). Then prints a paste-ready TOML stub with the answers + parsed bbox. A `--non-interactive` flag (auto-set when stdin isn't a tty, e.g. CI) skips the prompt and prints the TOML stub with `<TBD>` placeholders.
- **Q (C-9)**: CLI verb pattern? → **A**: **Grouped verb-noun**: `admesh-domains domain suggest <PATH>` and `admesh-domains domain audit`. New `domain` group also gets a `domain list` alias for the existing `domains` command (kept for backward compat). Future grouping for meshes (`mesh load`, `mesh show`, etc.) will follow the same pattern.
- **Q (C-10)**: Default output format? → **A**: Pretty text by default (ranked list, color when stdout is a tty), `--json` flag for machine-readable output. No tty auto-detect for the format choice — explicit flag only, simpler to reason about.

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

- **FR-001**: New CLI command group `admesh-domains domain` with subcommands `suggest <PATH>`, `audit`, and `list` (alias for the existing `admesh-domains domains`).
- **FR-002**: `domain suggest <PATH>` parses the bbox from the mesh file (reusing `scripts/extract_bboxes.py` logic — refactor into `admesh_domains.geometry`).
- **FR-003**: For each existing Domain with at least one geographic-bbox mesh, compute **two** scores:
  - **per-mesh IoU**: max IoU of the new bbox against any single mesh in that Domain
  - **union IoU**: IoU of the new bbox against the Domain's union bbox (smallest bbox covering all of the Domain's meshes)
  Rank Domains by per-mesh IoU (descending); show both numbers in output.
- **FR-004**: Default (pretty) output:
  ```
  Suggestions for new.14 (bbox: -95.00, 25.00, -80.00, 31.00):
    1. WNAT          per-mesh IoU=0.62  union IoU=0.41  (confident)
    2. ChesapeakeBay per-mesh IoU=0.04  union IoU=0.04  (low)
    Propose new Domain: launch interactive prompt? [y/N]
  ```
  Color is used when stdout is a tty (green for confident, yellow for uncertain, gray for low). Plain text when piped.
- **FR-005**: Exit codes: `0` confident match (single Domain ≥ 0.5 IoU), `1` no match (all < 0.05 IoU), `2` ambiguous (≥2 candidates ≥ 0.5 IoU), `3` parse/IO error.
- **FR-006**: `--json` flag emits a machine-readable JSON object: `{"path": ..., "bbox": [...], "candidates": [{"domain": "...", "per_mesh_iou": ..., "union_iou": ..., "confidence": "..."}], "exit_code": ...}`.
- **FR-007**: When no confident match is found, by default the CLI launches an interactive prompt that asks for `name`, `full_name`, `category` (default "real-world"), `region` (if real-world), `applications` (comma-separated, optional), then prints a paste-ready TOML stub with the answers + parsed bbox + filename.
- **FR-008**: `--non-interactive` flag (auto-set when stdin is not a tty) skips the prompt and prints the TOML stub with `<TBD>` placeholders for the user to fill in.
- **FR-009**: New CLI subcommand `admesh-domains domain audit` runs the suggester against every existing mesh and reports disagreements between current Domain assignment and the rank-1 suggestion.
- **FR-010**: New module `admesh_domains/geometry.py` houses bbox / IoU helpers (`compute_iou`, `domain_union_bbox`, `per_mesh_iou`, `suggest_domain`), importable by external tooling.
- **FR-011**: Bboxes that wrap the antimeridian (`min_lon > max_lon`) are skipped with a warning logged to stderr; they are excluded from both the new mesh and existing Domain candidates. Antimeridian-safe IoU is out of scope for this spec.

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
- **Antimeridian-safe IoU**. We have zero Pacific meshes today. Wrapping bboxes are skipped with a warning per FR-011. Defer until a real Pacific mesh is contributed.
- **PR comment automation** beyond exit-code-based CI gating. Defer until the CLI itself is in use.
- **A "merge two Domains" CLI** — different problem (curation cleanup), separate spec.

## Dependencies

- New module: `admesh_domains/geometry.py` (stdlib only)
- New CLI subcommands: `suggest-domain`, `audit-domains` in `admesh_domains.cli`
- Refactor opportunity: move bbox-extraction logic from `scripts/extract_bboxes.py` into `admesh_domains.geometry` so the same code parses both new submissions and existing meshes
- Existing: `Mesh.bounding_box`, `Domain.meshes`, `BoundingBox` (all in `schema.py`)

## Constitution Check

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest is source of truth | PASS | Suggester reads manifest; never writes or mutates |
| II. Pure-Python, optional heavy deps | PASS | Uses stdlib only; no new dependencies required |
| III. Schema changes are explicit | N/A | No schema changes; derives metrics in-memory |
| IV. Atomic releases — and separate code from data | PASS | Code track; feature addition to v0.3.0 release |
| V. Test before tagging | PASS | Unit tests for IoU calculation, audit logic, exit codes |
| VI. Curation over auto-magic | PASS | Suggester proposes; human reviews and decides; advisory only |
| VII. External Upstream (DomI) | PASS | No DomI interaction changes |

## Open Questions for Plan Phase

- Should the suggester also propose a `category` (real-world vs synthetic) by inspecting the bbox coordinate system (lat/lon → real-world, otherwise → synthetic)? Leaning **yes** — the prompt's `category` default would be set from the heuristic rather than hardcoded.
- Should `domain audit` output be sortable by IoU disagreement magnitude (worst offenders first) and have a `--threshold` flag? Probably yes.
- The interactive prompt — pure stdlib `input()` (lightweight, no deps) or use `prompt_toolkit`/`rich.prompt` (better UX, new dep)? Leaning **stdlib** to honor Constitution Principle II.
