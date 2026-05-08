# TASKS: query.find_meshes() filters (Issue #7)

## Phase 1: Survey & Understand
- **T1.1** Read current admesh_domains/query.py: find_meshes() signature, loop structure
- **T1.2** Check admesh_domains/cli.py: current meshes or list command, argument pattern
- **T1.3** Count existing test_case and kind values in registry_data/manifest.toml
- **T1.4** Document current query flow and CLI structure in notes

## Phase 2: Implement find_meshes() filters
- **T2.1** Edit admesh_domains/query.py: add kind and test_case parameters to find_meshes()
- **T2.2** Implement filtering logic in the mesh loop
- **T2.3** Update type hints (add Optional[str] and Optional[bool])
- **T2.4** Add docstring with examples
- **T2.5** Test manually: `python -c "from admesh_domains import find_meshes; print(find_meshes(test_case=True))"`

## Phase 3: Implement CLI flags
- **T3.1** Identify CLI command for meshes (grep admesh_domains/cli.py for 'meshes' or 'list')
- **T3.2** Add --kind argument (choices: mesh, boundary)
- **T3.3** Add --test-case boolean flag
- **T3.4** Wire flags to find_meshes() in the command handler
- **T3.5** Test CLI: `admesh-domains meshes --test-case` and `admesh-domains meshes --kind boundary`

## Phase 4: Unit Tests
- **T4.1** Read tests/test_registry_query.py: understand existing test structure
- **T4.2** Add test_find_meshes_kind_filter() — test kind="mesh" and kind="boundary"
- **T4.3** Add test_find_meshes_test_case_filter() — test test_case=True and test_case=False
- **T4.4** Add test_find_meshes_combined_filters() — test kind + test_case together
- **T4.5** Add test_find_meshes_no_filters() — backward compatibility check
- **T4.6** Run pytest: `pytest tests/test_registry_query.py::test_find_meshes* -v`
- **T4.7** Verify all 5 test_case=True meshes returned

## Phase 5: Documentation
- **T5.1** Update README.md: add filter examples to Quick Start
- **T5.2** Update docstring in find_meshes() with concrete examples
- **T5.3** (Optional) Update CLAUDE.md if query patterns changed

## Phase 6: Commit & Release
- **T6.1** `git add admesh_domains/query.py admesh_domains/cli.py tests/test_registry_query.py README.md`
- **T6.2** `git commit -m "Resolve issue #7: Add kind and test_case filters to find_meshes()"`
- **T6.3** Bump version in pyproject.toml: v0.3.2 → v0.3.3
- **T6.4** Bump version in admesh_domains/__init__.py
- **T6.5** `git add pyproject.toml admesh_domains/__init__.py`
- **T6.6** `git commit -m "Bump version to 0.3.3"`
- **T6.7** Run final tests: `pytest tests/ -q`
- **T6.8** Run CLI validation: `admesh-domains meshes --help` (verify flags present)

## Execution Order
1. T1.1 → T1.2 → T1.3 → T1.4 (sequential: understand state)
2. T2.1 → T2.2 → T2.3 → T2.4 → T2.5 (sequential: implement and test)
3. T3.1 → T3.2 → T3.3 → T3.4 → T3.5 (sequential: CLI implementation)
4. T4.1 → T4.2 → T4.3 → T4.4 → T4.5 → T4.6 → T4.7 (sequential: test)
5. T5.1 → T5.2 → (T5.3) (sequential: docs)
6. T6.1 → T6.2 → T6.3 → T6.4 → T6.5 → T6.6 → T6.7 → T6.8 (sequential: commit & verify)

## Success Metrics
- ✓ find_meshes() accepts kind and test_case parameters
- ✓ Filters work correctly (return expected mesh instances)
- ✓ CLI flags --kind and --test-case present and functional
- ✓ All 5 test_case meshes discoverable
- ✓ Backward compatible (no filters = old behavior)
- ✓ Tests pass: pytest 113 tests
- ✓ README updated with examples
- ✓ Version bumped to 0.3.3
