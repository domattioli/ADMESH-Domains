# PLAN: query.find_meshes() filters (Issue #7)

## Phase 1: Survey & Understand Current State
1. Read current `admesh_domains/query.py`: find_meshes() signature and logic
2. Check `admesh_domains/cli.py`: current meshes/list command structure
3. Review test manifest: count meshes with kind="boundary" and test_case=True
4. Understand how Domain/Mesh navigation works in the codebase

**Outcome:** Know the current filtering, loop structure, and CLI argument pattern.

## Phase 2: Implement query.find_meshes() filters
1. Add optional `kind: str | None = None` parameter (validate: "mesh" | "boundary")
2. Add optional `test_case: bool | None = None` parameter
3. Update docstring with examples
4. Update type hints
5. Implement filtering logic in the mesh loop
6. Verify backward compatibility (no params = old behavior)

**Outcome:** find_meshes() API complete and tested locally.

## Phase 3: Implement CLI flags
1. Identify the CLI command (likely `admesh-domains meshes` or `list`)
2. Add `--kind` argument with choices=[mesh, boundary]
3. Add `--test-case` flag (boolean)
4. Wire flags to find_meshes() calls in the handler
5. Test via CLI: `admesh-domains meshes --test-case`, etc.

**Outcome:** CLI flags working, commands return correct filtered results.

## Phase 4: Test & Validation
1. Write parametrized unit tests in `tests/test_registry_query.py`
   - Test each filter independently
   - Test combinations (kind + test_case)
   - Test with no filters (backward compat)
2. Run pytest: `pytest tests/test_registry_query.py -v`
3. Run CLI tests: invoke commands and verify output
4. Validate all 5 test_case meshes are discoverable

**Outcome:** All tests pass, coverage > 90%.

## Phase 5: Documentation
1. Update README.md Quick Start with filter examples
2. Update CLAUDE.md if query patterns changed significantly
3. Add docstring examples to function signature

**Outcome:** Users can discover and use filters via README.

## Phase 6: Commit & Release Track Decision
1. Commit with message: `Resolve issue #7: Add kind and test_case filters to find_meshes()`
2. Decide: bump patch version (v0.3.2 → v0.3.3) or release without version bump?
   - Since this is an API enhancement (new parameters), patch bump is warranted
3. Update pyproject.toml + admesh_domains/__init__.py versions
4. Commit version bump separately: `Bump version to 0.3.3`

**Outcome:** Code ready for PR review and merge to main.

## Dependencies
- Phase 1 → Phase 2 (must understand current state first)
- Phase 2 → Phase 3 (query layer must work before CLI)
- Phase 3, 4 → Phase 5 (parallel: implement + test, then document)
- All → Phase 6 (commit last)

## Estimated Timeline
- Phase 1: 15 min
- Phase 2: 30 min
- Phase 3: 20 min
- Phase 4: 30 min
- Phase 5: 15 min
- Phase 6: 10 min
**Total: ~2 hours**
