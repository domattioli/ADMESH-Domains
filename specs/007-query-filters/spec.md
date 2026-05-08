# SPEC: query.find_meshes() filters for kind and test_case (Issue #7)

## Goal
Expose `Mesh.kind` and `Mesh.test_case` schema fields (added in v0.3.2) through filtering parameters in the query API and CLI.

## Why
Users need a programmatic way to:
- Filter for boundary polygons only (`kind="boundary"`) vs. full meshes
- Discover test case meshes for benchmarking or pytest fixtures
- Query these fields via CLI for scripts and automation

## Acceptance Criteria
- [ ] `find_meshes(kind=None, test_case=None)` accepts optional filtering parameters
- [ ] `find_meshes(kind="mesh")` returns only meshes with kind="mesh"
- [ ] `find_meshes(kind="boundary")` returns only boundary polygons
- [ ] `find_meshes(test_case=True)` returns only meshes flagged for test suite (all 5 test_case entries)
- [ ] CLI command gains `--kind {mesh,boundary}` flag
- [ ] CLI command gains `--test-case` boolean flag
- [ ] All filters are chainable (e.g., `--kind boundary --test-case`)
- [ ] Type hints and docstrings updated
- [ ] Tests added in `tests/test_registry_query.py`
- [ ] README.md Quick Start updated with filter examples

## Deliverables

### Code Changes
1. **admesh_domains/query.py**: Update `find_meshes()` signature and implementation
2. **admesh_domains/cli.py**: Add `--kind` and `--test-case` flags to the meshes/list command
3. **tests/test_registry_query.py**: Add filter test cases
4. **README.md**: Add filter examples to Quick Start

### No Changes Needed
- Schema (fields already exist)
- SCHEMA_VERSION (additive feature, not breaking)
- pyproject.toml (no new deps)
- manifest.toml (data-level, not code-level)

## Constraints
- Pure Python only — no new dependencies
- Must work with base install (no [publish] or [hf] extras)
- Backward compatible: parameters are optional, default behavior unchanged
- Release track: **Code** (API enhancement) — may bump patch version in pyproject.toml

## Testing Strategy
- Unit tests: parametrized tests for each filter combination
- CLI tests: invocation with flags via subprocess or runner
- Roundtrip: verify filters return expected mesh instances with correct attributes

## Risks
- None identified — additive feature, backward compatible, no schema changes

## Estimate
**Small:** ~3-4 hours. Straightforward parameter addition, well-scoped.
