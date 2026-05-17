# Issue #54: Audit Claude Code Hooks — Report DomI-Relevant Findings to Upstream

## Problem
ADMESH-Domains has no documented inventory of its Claude Code hooks (repo-scope, user-scope, repo scripts referenced by upstream). DomI ships a prescribed hook surface (commit d11ca39, full spec on `domattioli/DomI#60`) and consumer repos need to (a) confirm coverage, (b) report gaps that should be solved centrally upstream, (c) record any repo-specific hook needs locally. Without this audit there is no shared evidence base for what to push to DomI vs keep in `.claude/settings.json`.

## Acceptance Criteria
- [ ] Hooks inventory committed as `docs/HOOKS-AUDIT.md` on `daily-issue-fixing`
- [ ] Upstream-relevant findings posted as a comment on `domattioli/DomI#64` using the prescribed report format
- [ ] Local-only assessment recorded; `.claude/settings.json` only updated if a hook is unambiguously local-scope
- [ ] No code or settings changes to upstream DomI from this work
- [ ] Override contract (`CLAUDE_BRANCH_OVERRIDE=1`, `CLAUDE_INTERACTIVE=1`) honored / documented

## Scope

**Inventoried surfaces (read-only):**
- `~/.claude/settings.json` (user-scope hooks + statusLine)
- `.claude/settings.json` (repo-scope permissions/hooks)
- `scripts/*.sh` (repo scripts invoked by upstream session hooks: `instructions_on_start.sh`, `cloud-startup.sh`, `instructions.sh`)
- `.githooks/` (none present — confirmed)
- `scripts/hooks/` (none present — confirmed)

**Reference (DomI's prescribed surface, commit d11ca39):**

| Event | Hook | Purpose |
|---|---|---|
| SessionStart | `session_start.sh` | runs `instructions_on_start.sh` |
| PreToolUse:Bash | `branch_guard.sh` | claude/*, --no-verify, force-push, colon-rename |
| PreToolUse:Bash | `commit_msg_guard.sh` | conventional commit format |
| PreToolUse:Write\|Edit | `secret_path_guard.sh` | secret paths |
| Stop | `stop_introspect.sh` | `/introspect` reminder |

## Implementation
- Write `docs/HOOKS-AUDIT.md` containing: inventory table, gap analysis vs DomI's prescribed surface, classification (upstream-relevant / local-only / N/A), override contract notes.
- Post a single comment on `domattioli/DomI#64` using the report format declared in the issue body.
- Leave `.claude/settings.json` untouched **unless** the audit surfaces a hook that is clearly repo-specific (e.g., a guard tied to `registry_data/` or PyPI-track behavior) — keep base install discipline.

## Risk
- Low. Read-only audit + one doc + one upstream comment. No schema, manifest, or release-track impact.
- Mild: hooks landscape may shift if DomI ships its prescribed surface during this run; doc references commit `d11ca39` to date the snapshot.

## Release Track
Code (docs + optional `.claude/settings.json` tweak). No PyPI bump. No Hub sync.

## Constitution Check

| Principle | Status | Justification |
|---|---|---|
| I. TOML manifest is source of truth | N/A | No `registry_data/manifest.toml` change |
| II. Pure-Python, optional heavy deps | N/A | No package deps touched |
| III. Schema changes are explicit | N/A | No schema |
| IV. Atomic releases — and separate code from data | PASS | Docs/config only; no PyPI tag, no `publish-data.yml` trigger |
| V. Test before tagging | N/A | No release |
| VI. Curation over auto-magic | PASS | Audit recommends central guard hooks (DomI) over per-repo drift |
| VII. External Upstream (DomI) | PASS | Findings split: upstream items filed on DomI#64; pin unchanged |
