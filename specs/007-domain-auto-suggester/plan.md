# Implementation Plan: Domain Auto-Suggester

**Branch**: `007-domain-auto-suggester` | **Date**: 2026-04-26 | **Spec**: [spec.md](spec.md)

## Summary

Add an `admesh-domains domain` CLI command group with three subcommands — `suggest`, `audit`, `list` — backed by a new `admesh_domains/geometry.py` module that computes bbox IoU between a candidate mesh file and existing Domains. The `suggest` command parses a fort.14 / .grd / .2dm header to extract a bbox, ranks every Domain by per-mesh IoU plus union IoU, and either prints the ranked candidates or (on no-match) drops the user into an interactive prompt that emits a paste-ready TOML stub for a new Domain.

**Stays in the base install.** No new heavy deps — all math is stdlib arithmetic, output is plain `print()`, prompt is stdlib `input()`. Honors Constitution Principle II (pure-Python first) and Principle VI (curation over auto-magic — the tool proposes, the human decides via PR review).

## Technical Context

- **Language**: Python 3.9+ (matches base package).
- **New deps**: none. Existing access to `BoundingBox`, `Domain`, `Mesh`, `Manifest` already in `admesh_domains.schema` / `admesh_domains.manifest`.
- **CLI shape change**: today the CLI is flat (`admesh-domains validate / list / domains / meshes / show-domain / show-mesh / publish`). Spec 007 introduces a *grouped* `domain` namespace (`domain suggest`, `domain audit`, `domain list`). The existing `domains`, `show-domain` flat commands stay for back-compat in this minor; can be deprecated later.
- **Performance**: 41 meshes × 13 Domains × constant-time IoU = sub-millisecond on a laptop. NFR-001's 1-second budget is enormously slack.
- **Output**: pretty by default with optional ANSI color when stdout is a tty (use `sys.stdout.isatty()`); `--json` switch flips to a single JSON object on stdout. No tty auto-detect for format choice (per C-10).
- **Refactor**: move bbox-extraction logic from `scripts/extract_bboxes.py` into `admesh_domains.geometry` so the same code parses both new submissions (suggester) and existing meshes (the import script). Keep the script as a thin wrapper.

## Project Structure

### Source code (new + edits)

```text
admesh_domains/
├── geometry.py              # NEW — bbox math, IoU, mesh file parsing
└── cli.py                   # MODIFY — add 'domain' group with 3 subcommands

scripts/
└── extract_bboxes.py        # MODIFY — thin wrapper that imports from geometry

tests/
├── test_geometry.py         # NEW — IoU math, bbox parse, suggest_domain
└── test_cli_domain.py       # NEW — smoke tests for the 3 subcommands
```

### Documentation (this feature)

```text
specs/007-domain-auto-suggester/
├── spec.md          # done
├── plan.md          # this file
├── data-model.md    # Phase 1 — IoUScore + JSON schema, output formats
├── contracts/
│   └── cli-api.md   # Phase 1 — argparse surface, exit codes, prompts
├── quickstart.md    # Phase 1 — contributor "I downloaded a mesh, now what" recipe
└── tasks.md         # Phase 2 — output of /tasks
```

## Phase 0 — Research

Quick verifications before code (each ≤ 15 min):

- **R-1**: Confirm argparse supports nested subparsers (`domain` group → `suggest`/`audit`/`list` subcommands). Should — it's just `subparsers.add_parser("domain").add_subparsers(...)`. Verify with a 5-line spike.
- **R-2**: Verify the existing `bbox_from_fort14` parser handles `.grd` correctly (it's just suffix dispatch — already does, per nc_inundation_v6c import). No-op research item, just sanity check.
- **R-3**: Confirm `sys.stdout.isatty()` reliably distinguishes piped vs interactive on Linux/macOS. Standard, cross-platform, well-trodden.
- **R-4**: Decide whether `domain audit` should also re-validate manifests as a side effect. **Tentative: no** — keep audit single-purpose; users can run `validate` separately.

## Phase 1 — Design Artifacts

### `data-model.md`

- `IoUScore` dataclass — domain_name, per_mesh_iou (max over Domain's meshes), union_iou, centroid_distance_deg, confidence ∈ {confident, uncertain, low}.
- `compute_iou(a, b)` formula: `inter_area / (a.area + b.area - inter_area)`. Return 0 for disjoint or zero-area inputs.
- Antimeridian handling: detect via `min_lon > max_lon` on either input → return `0.0` and log a stderr warning. Per C-7 / FR-011.
- JSON output schema for `--json`:
  ```json
  {
    "path": "new.14",
    "bbox": [-95.0, 25.0, -80.0, 31.0],
    "candidates": [
      {"domain": "WNAT", "per_mesh_iou": 0.62, "union_iou": 0.41, "confidence": "confident"}
    ],
    "exit_code": 0
  }
  ```

### `contracts/cli-api.md`

- Full argparse tree for the `domain` group, exit codes (0/1/2/3 per FR-005), `--json` / `--non-interactive` flag semantics, the interactive prompt's exact question order.
- The new-Domain TOML stub format for `--non-interactive` mode (with `<TBD>` placeholders).

### `quickstart.md`

Contributor-facing recipe: download a mesh → run `admesh-domains domain suggest path.14` → review the output → either commit under existing Domain or paste the printed TOML stub into manifest.toml → push to main → `publish-data.yml` ships it to HF.

## Phase 2 — Tasks (deferred to /tasks)

Highlights of expected task structure:

- **T-001..004**: Phase 0 research items.
- **T-010..012**: Phase 1 design artifacts.
- **T-020**: `geometry.py` — `BoundingBox` arithmetic helpers (intersection, union, area, centroid).
- **T-021**: `geometry.py` — `compute_iou`, `domain_union_bbox`, `per_mesh_iou`, `IoUScore` dataclass.
- **T-022**: `geometry.py` — refactor mesh-file bbox parsing in from `scripts/extract_bboxes.py`. Make the script a thin importer.
- **T-023**: `geometry.py` — `suggest_domain(new_bbox, manifest) -> list[IoUScore]` main entry.
- **T-024**: `cli.py` — add `domain` group + `domain suggest <PATH>` subcommand with text/JSON output.
- **T-025**: `cli.py` — `domain audit` subcommand.
- **T-026**: `cli.py` — `domain list` alias (delegates to existing `cmd_domains`).
- **T-027**: `cli.py` — interactive new-Domain prompt + `--non-interactive` TOML-stub fallback.
- **T-028**: `tests/test_geometry.py` — IoU math (known cases, disjoint, identical, contained), antimeridian skip, parse_mesh_bbox roundtrip.
- **T-029**: `tests/test_cli_domain.py` — smoke each subcommand, verify exit codes and JSON shape.
- **T-030**: Update `CLAUDE.md` + `quickstart.md` with the new `domain` commands.
- **T-040**: Validation — run suggester against every existing mesh and confirm rank-1 = current Domain (SC-001).
- **T-041**: Run `audit` on the current registry; expect zero disagreements.
- **T-050**: Tag `v0.3.0` (new feature → minor bump in 0.x; no schema change so MAJOR stays at 0).

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. TOML manifest is source of truth | **PASS** | Suggester reads only; never writes the manifest. Output is paste-ready TOML for the human to commit. |
| II. Pure-Python, optional heavy deps | **PASS** | Stdlib only. No new entries in `dependencies` or `[publish]` / `[hf]` extras. |
| III. Schema changes are explicit | **N/A** | No schema change. Reads existing `Mesh.bounding_box` (added in v0.2.1). |
| IV. Atomic releases | **PASS** | Ships as a code release: v0.3.0 tag → release.yml → PyPI + HF together. |
| V. Test before tagging | **PASS** | T-028, T-029, T-040, T-041 cover unit and integration paths. validate-pr.yml gates merges. |
| VI. Curation over auto-magic | **PASS** | The suggester *proposes*; the reviewer *decides*. Exit codes are advisory (FR-005), interactive prompt yields a stub the human pastes — no auto-merge of registry state. |

## Risk & Complexity Tracking

- **R-1 (low)**: argparse nested subparsers can produce confusing help output if you skip `set_defaults(func=...)` on the top-level group parser. Mitigation: prototype the parser tree in T-024 before wiring callbacks.
- **R-2 (low)**: Antimeridian-skip surface area: any future Pacific contribution will silently produce IoU=0 against existing Domains. Mitigation: T-028 includes an antimeridian test that asserts the warning is emitted to stderr; future spec can implement safe-IoU.
- **R-3 (low)**: Output coloring may not work in older Windows terminals. Mitigation: skip color when `os.environ.get("NO_COLOR")` is set or when stdout isn't a tty (industry convention).

## Done When

- `admesh-domains domain suggest registry_data/meshes/WNAT_Hagen.14` returns rank-1 = `WNAT` with `per_mesh_iou >= 0.99` and exit code 0.
- `admesh-domains domain audit` on the current registry prints "0 disagreements" and exits 0.
- A synthetic `(-110, 30, -100, 40)` bbox via `--non-interactive` prints a paste-ready TOML stub with `<TBD>` placeholders + the parsed bbox.
- `--json` output is parseable by `jq '.candidates[0].domain'`.
- v0.3.0 ships through `release.yml` (PyPI + HF) without code-track issues.
- All tests green on Python 3.9 / 3.11 / 3.12 (validate-pr.yml).
