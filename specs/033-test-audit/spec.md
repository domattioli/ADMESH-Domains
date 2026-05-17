# Issues #52 + #53: Audit Test Surface — Produce TEST-AUDIT.md, Report Upstream

## Problem
ADMESH-Domains is a published PyPI package (`v0.4.1`). Releases ship to anyone who `pip install`s. The test suite (6 files, 191 collected tests, 4 CI workflows) has no audit on record. Two coordinated issues — repo-local #52 (holistic suite audit) and downstream-coordination #53 (mirror DomI's TEST-AUDIT methodology + upstream report on DomI#63) — both demand the same artifact: `TEST-AUDIT.md` on `daily-issue-fixing`. They are resolved together by one document plus one DomI#63 comment.

## Acceptance Criteria
- [ ] `docs/TEST-AUDIT.md` committed on `daily-issue-fixing` covering both issues' dimensions
- [ ] Each finding has a file:line reference or `[global]` tag
- [ ] Prioritized backlog with items linking back to findings
- [ ] "Do nothing" list for intentional smells
- [ ] Upstream-relevant findings filed on `domattioli/DomI#63` in the prescribed format
- [ ] Local-only follow-up bug issues filed (one per failure cluster) — Step 9 of the routine
- [ ] No code changes in the audit commit (bug fixes, if any, in separate commits)

## Scope

**Surfaces audited (read-only):**
- `tests/` — all 6 files, 191 tests
- `tests/conftest.py` — fixture surface
- `tests/fixtures/registry/` — committed fixtures
- `pyproject.toml` — pytest config + test deps
- `.github/workflows/*.yml` — 4 workflows (`pages.yml`, `publish-data.yml`, `release.yml`, `validate-pr.yml`)
- `admesh_domains/__init__.py` — public API surface mapped 1:1 to tests
- Live `pytest` run: 10 failures, 181 passes; durations table

**Out of scope for this artifact:**
- Writing new tests (each backlog item becomes its own follow-up issue)
- Fixing the 10 pre-existing failures (separate bug issues filed in Step 9)
- Refactoring CI workflows

## Implementation
- Author `docs/TEST-AUDIT.md` per the merged dimension list from #52 (10 dimensions) and #53 (DomI mirror methodology, split local vs upstream).
- File three bug follow-up issues in this repo for the failure clusters surfaced by the audit.
- Comment on DomI#63 with upstream-relevant findings using the format prescribed in that issue body.

## Risk
- Low. Read-only audit + one doc + one upstream comment + three follow-up issues. No schema, manifest, or release-track impact.
- Mild scope risk: the audit may surface bugs the user expects fixed. Fixes are deliberately deferred to follow-up bug issues so the audit commit stays pure (the issues' own scope discipline mandates this).

## Release Track
Code (docs only). No PyPI bump. No Hub sync. No SCHEMA_VERSION change.

## Constitution Check

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest is source of truth | N/A | No manifest mutation. (Audit surfaces a violation — `mixed-hybrid@v1` file missing — but does not fix it.) |
| II. Pure-Python, optional heavy deps | N/A | No package dep change |
| III. Schema changes are explicit | N/A | No schema |
| IV. Atomic releases — code/data separation | PASS | Docs only; no tag, no `publish-data.yml` trigger |
| V. Test before tagging | PASS | Audit reinforces this principle — surfaces broken gate |
| VI. Curation over auto-magic | PASS | Audit documents what's broken; fixes go through review |
| VII. External Upstream (DomI) | PASS | Upstream findings filed on DomI#63; pin already at `9dd6491` |
