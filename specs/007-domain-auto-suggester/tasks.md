# Tasks: Domain Auto-Suggester

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Numbered, dependency-ordered work items for spec 007. `[P]` = can run in parallel with siblings; serial tasks gate downstream work. Each has a "done when" criterion.

---

## Phase 0 — Research (quick verifications)

- **T-001** [P] **Argparse nested-subparsers spike.** 5-line standalone script: top-level parser → subparsers `domain` → subparsers `suggest` / `audit` / `list`. Confirm `set_defaults(func=...)` is needed on every leaf, that `--help` traverses correctly, and that `domain` (no leaf) prints a useful error rather than crashing. **Done when**: notes captured inline; pattern locked for T-024.
- **T-002** [P] **Sanity-check `.grd` bbox parsing.** Already worked for `nc_inundation_v6c.grd` in v0.2.4 — quick reconfirm by running `bbox_from_fort14` against it and asserting the bbox matches the manifest. **Done when**: green assertion; no changes needed to the parser.
- **T-003** [P] **`sys.stdout.isatty()` cross-platform check.** Verify it returns False under `python -c 'import sys; print(sys.stdout.isatty())' | cat`. Confirm `NO_COLOR` env-var convention is honored if we add color. **Done when**: docstring in `geometry.py` references both signals.
- **T-004** **Decide: should `domain audit` re-validate manifests?** Plan tentatively says no. Confirm by running `validate` separately and noting whether users naturally pair the commands. **Done when**: decision committed to docstring.

## Phase 1 — Design Artifacts

- **T-010** **Author `data-model.md`.** `IoUScore` dataclass shape, `compute_iou` formula with worked examples (disjoint=0, identical=1, contained=ratio), antimeridian behavior (return 0 + stderr warning), JSON output schema for `--json`.
- **T-011** **Author `contracts/cli-api.md`.** Full argparse tree, exit codes (0/1/2/3), the interactive prompt's exact question order, `--non-interactive` TOML stub format with `<TBD>` placeholders.
- **T-012** **Author `quickstart.md`.** Contributor recipe: download mesh → `admesh-domains domain suggest path` → review → either commit under existing Domain (no PyPI) or paste TOML stub for new Domain → push to main → publish-data.yml ships to HF.

Phase 1 informs Phase 2; do not start T-020+ until T-010..012 are committed and reviewed.

## Phase 2 — Build (geometry core + CLI surface)

### geometry.py — math + parsing

- **T-020** **Implement bbox arithmetic helpers** in `admesh_domains/geometry.py`: `area(bb)`, `intersection(a, b) -> BoundingBox | None`, `union(a, b) -> BoundingBox`, `centroid(bb) -> tuple[float, float]`, `is_antimeridian_wrapping(bb) -> bool`. Unit test each. **Done when**: all six functions covered.
- **T-021** **Implement `compute_iou(a, b) -> float`.** Returns 0 for disjoint, zero-area, or antimeridian-wrapping bboxes (with warning to stderr for the last). **Done when**: test file covers identical (=1), disjoint (=0), contained, antimeridian skip.
- **T-022** **Implement `domain_union_bbox(domain) -> BoundingBox | None` and `per_mesh_iou(new_bbox, domain) -> float`.** Latter returns max IoU across the Domain's geographic-bbox meshes. **Done when**: tests against a known Domain produce expected values.
- **T-023** **Implement `IoUScore` dataclass + `suggest_domain(new_bbox, manifest) -> list[IoUScore]`.** Sorts by `per_mesh_iou` descending; populates `confidence` from thresholds (≥0.5 confident, ≥0.05 uncertain, else low). **Done when**: returns sensible ranked output for a known input.
- **T-024** **Refactor `bbox_from_fort14` and `bbox_from_2dm` from `scripts/extract_bboxes.py` into `admesh_domains/geometry.py`.** Make the script a thin wrapper that imports from the module. Existing manifest-population behavior unchanged. **Done when**: `python scripts/extract_bboxes.py` still produces an identical diff (zero) when run against the populated manifest.

### cli.py — command surface

- **T-025** **Add `domain` parser group to `cli.py` with three leaf subcommands** (`suggest`, `audit`, `list`). `domain list` delegates to existing `cmd_domains`. `set_defaults(func=...)` on each leaf. **Done when**: `admesh-domains domain --help` lists all three; `admesh-domains domain` (no subcommand) prints help.
- **T-026** **Implement `domain suggest <PATH>` text output.** Pretty ranked list with `per_mesh_iou` + `union_iou` columns; ANSI color (green/yellow/gray) when `sys.stdout.isatty()` and `NO_COLOR` is unset. **Done when**: against a copy of `WNAT_Hagen.14` it prints WNAT first with confidence "confident".
- **T-027** **Implement `--json` output for `domain suggest`.** Single-object JSON per the schema in data-model.md. **Done when**: `admesh-domains domain suggest path --json | jq '.candidates[0].domain'` returns "WNAT".
- **T-028** **Implement interactive new-Domain prompt.** Triggers when no candidate has `per_mesh_iou >= 0.5` and stdin is a tty. Asks: name, full_name, category (default real-world), region (if real-world), applications (CSV, optional). Prints paste-ready `[[domains]]` TOML block. **Done when**: a no-match input drops the user into the prompt, and the printed TOML parses successfully when added to a fixture manifest.
- **T-029** **Implement `--non-interactive` flag** (auto-set when stdin not a tty) **for `domain suggest`.** Skips prompt, prints TOML stub with `<TBD>` placeholders for everything except bbox + filename. **Done when**: `< /dev/null admesh-domains domain suggest path` doesn't hang; emits stub.
- **T-030** **Implement `domain audit`.** Iterates every mesh, runs `suggest_domain` on its bbox, reports each mesh whose current Domain ≠ rank-1 suggestion. `--threshold` flag (default 0.05) suppresses tiny IoU disagreements. `--json` for machine output. **Done when**: against the current registry prints "0 disagreements" and exits 0.

### tests

- **T-035** **Author `tests/test_geometry.py`** covering T-020..T-023. Include antimeridian fixture, identical-bbox fixture, contained-bbox fixture, disjoint fixture. **Done when**: 15+ tests, all green.
- **T-036** **Author `tests/test_cli_domain.py`** smoke-testing each subcommand. Use `argparse`'s in-process `main(argv=...)` invocation rather than subprocess, captures stdout/stderr with `capsys`. **Done when**: ~10 tests green, including a `--json` shape test and a `--non-interactive` stub-rendering test.

## Phase 3 — Documentation

- **T-040** **Update `CLAUDE.md`** with new "Suggesting a Domain for a new mesh" workflow section. Reference `domain suggest` in the data-track recipe.
- **T-041** **Update repo `README.md`** if it describes the CLI surface (it currently doesn't enumerate commands; check first — if not needed, skip).

## Phase 4 — Validation

- **T-050** **Run `domain suggest` against every existing geographic mesh.** Verify rank-1 = its actual parent Domain (SC-001). Script: loop over `find_meshes(category='real-world')`, call `suggest_domain(mesh.bounding_box, manifest)`, assert `result[0].domain_name == mesh._domain_name`. **Done when**: green for every real-world mesh.
- **T-051** **Run `domain audit` on the full registry.** Expect 0 disagreements (SC-002 sanity). **Done when**: green; if any disagreement appears, investigate (might be a real curation bug worth fixing).
- **T-052** **Verify `--json` shape with jq.** `admesh-domains domain suggest WNAT_Hagen.14 --json | jq '.candidates[0]'` returns valid JSON with the documented keys. **Done when**: green via `jq -e`.
- **T-053** **Verify install-size invariant** (Constitution II + spec NFR-002). Diff `pip install admesh-domains` size before/after — should be unchanged. **Done when**: confirmed, screenshot or `du -sh` numbers in PR.

## Phase 5 — Release

- **T-060** **Bump version to 0.3.0** in `pyproject.toml` and `admesh_domains/__init__.py`. Minor bump because new public CLI surface; no schema change so MAJOR stays at 0. **Done when**: both files updated.
- **T-061** **Tag and push `v0.3.0`.** `release.yml` runs PyPI upload then HF publish. **Done when**: PyPI 0.3.0 live, HF tag `v0.3.0` exists, `main` branch updated.
- **T-062** **Mark spec 007 Complete.** Add "Status: Complete (shipped in v0.3.0 — YYYY-MM-DD)" header. Reference the verifying release run. **Done when**: spec.md updated and committed.

---

## Sequencing Summary

```
Phase 0 (T-001..004 mostly parallel)
    ↓
Phase 1 (T-010..012 serial — design first)
    ↓
Phase 2 geometry (T-020 → T-021 → T-022 → T-023 → T-024 — strict chain)
       cli   (T-025 → T-026 / T-027 [P] → T-028 / T-029 [P] → T-030)
       tests (T-035 [P with T-020..023], T-036 [P with T-025..030])
    ↓
Phase 3 docs (T-040, T-041 [P])
    ↓
Phase 4 validation (T-050, T-051, T-052, T-053 mostly [P])
    ↓
Phase 5 release (T-060 → T-061 → T-062)
```

## Estimated total

~22 implementation tasks. Solo dev focused work: ~3–4 hours for the full pipeline (geometry core is the bulk; CLI is glue; tests + validation are quick).

## Out-of-band side tasks

Track in GitHub issues, not here:
- **#3** Domain auto-suggester (this spec — closes when v0.3.0 ships)
- New: file an issue for **antimeridian-safe IoU** once the first Pacific mesh appears (referenced by spec 007 FR-011 + Out of Scope)
- New: file an issue for **boundary-polygon comparison** as the Tier-2 follow-up (referenced by Out of Scope)
