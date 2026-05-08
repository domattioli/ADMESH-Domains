# Issue #28: Audit Bloat RE Python Scripts

## Problem
Repository may contain deprecated .py scripts from earlier migrations or one-shot utilities that are no longer necessary.

## Acceptance Criteria
- [x] Audit all Python scripts in `scripts/` and root
- [x] Identify which scripts are one-shot utilities vs. actively used
- [x] Document findings
- [x] Remove deprecated scripts

## Scope
**Scripts to analyze:**
- `scripts/build_site.py` — KEEP (active: builds website)
- `scripts/extract_bboxes.py` — KEEP (utility: thin wrapper around geometry.py)
- `scripts/github_release.py` — KEEP (active: release skill)
- `scripts/pypi_publish.py` — KEEP (active: release skill)
- `scripts/import_meshes.py` — **REMOVE** (one-shot: v0.1.0 import, not referenced)
- `scripts/regroup_manifest.py` — **REMOVE** (one-shot: v0.1.1 migration, not referenced)

## Implementation
- Remove `scripts/import_meshes.py` (145 lines, created 2026-04-25, one-shot mesh consolidation from 3 external repos)
- Remove `scripts/regroup_manifest.py` (100+ lines, created 2026-04-25, migration from flat to nested structure)
- Verify tests still pass
- Commit cleanup

## Risk
None—these are one-shot utilities with no remaining dependencies.

## Release Track
Code (cleanup, no schema/data changes)
