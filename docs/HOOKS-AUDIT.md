# Claude Code Hooks Audit — ADMESH-Domains

**Scope:** Read-only inventory of all Claude Code hooks visible from this repo's environment, classified into upstream-relevant (file on `domattioli/DomI#64`) and local-only.

**Snapshot date:** 2026-05-15
**DomI reference commit:** d11ca39 (per `domattioli/ADMESH-Domains#54`); full hook spec on `domattioli/DomI#60`.
**Issue:** [`domattioli/ADMESH-Domains#54`](https://github.com/domattioli/ADMESH-Domains/issues/54)

---

## 1. Inventory

### 1.1 Repo-scope (`.claude/settings.json`)

| Key | Contents |
|---|---|
| `permissions.allow` | `Bash(gh api *)`, `Bash(curl -s …ADMESH/Home.md)`, `WebFetch(domain:github.com)`, `Bash(python -m pytest tests/ -q)`, `Bash(python scripts/build_site.py)`, `Bash(mv .claude/settings.local.json .claude/settings.json)`, `Bash(cat)`, `Bash(git add *)` |
| `hooks` | **(none)** |
| `statusLine` | **(none)** |

No hooks are defined at repo scope. All guardrails come from user scope.

### 1.2 User-scope (`~/.claude/settings.json`)

| Event | Matcher | Hook | Type |
|---|---|---|---|
| `SessionStart` | — | `~/.claude/hooks/gsd-check-update.js` (node) | GSD |
| `SessionStart` | — | `~/.claude/hooks/gsd-session-state.sh` | GSD |
| `PreToolUse` | `Write\|Edit` | `~/.claude/hooks/gsd-prompt-guard.js` (node) | GSD |
| `PreToolUse` | `Write\|Edit` | `~/.claude/hooks/gsd-read-guard.js` (node) | GSD |
| `PreToolUse` | `Write\|Edit` | `~/.claude/hooks/gsd-workflow-guard.js` (node) | GSD |
| `PreToolUse` | `Bash` | `~/.claude/hooks/gsd-validate-commit.sh` | GSD |
| `PostToolUse` | `Bash\|Edit\|Write\|MultiEdit\|Agent\|Task` | `~/.claude/hooks/gsd-context-monitor.js` (node) | GSD |
| `PostToolUse` | `Read` | `~/.claude/hooks/gsd-read-injection-scanner.js` (node) | GSD |
| `PostToolUse` | `Write\|Edit` | `~/.claude/hooks/gsd-phase-boundary.sh` | GSD |
| `Stop` | — | `~/.claude/stop-hook-git-check.sh` | non-GSD (generic git-clean stop reminder) |
| `statusLine` | — | `~/.claude/hooks/gsd-statusline.js` (node) | GSD |

### 1.3 Repo scripts invoked by session hooks

| Path | Invoked by | Purpose |
|---|---|---|
| `scripts/instructions_on_start.sh` | DomI's `session_start.sh` (when installed) | Branch banner + DomI pin drift check (`sync-from-domi/check_pin.sh`); HARD-STOP on drift codes 1/3 |
| `scripts/cloud-startup.sh` | Cloud VM bootstrap | Fresh clone, Node.js install, CLAUDE.md preservation |
| `scripts/instructions.sh` | `source` before `claude` invocation | Defines `CLAUDE_INSTRUCTIONS` env var (hard stops, decision tree) |

No `.githooks/` directory. No `scripts/hooks/` directory.

---

## 2. Gap analysis vs DomI prescribed surface

DomI commit d11ca39 prescribes five hooks. Coverage status here:

| Event | DomI hook | Present locally? | Coverage notes |
|---|---|---|---|
| `SessionStart` | `session_start.sh` (runs `instructions_on_start.sh`) | **Indirect** | `instructions_on_start.sh` exists in `scripts/`. No `SessionStart` entry in `.claude/settings.json` invokes it — relies on the DomI plugin shipping `session_start.sh` or the operator sourcing it. Not gated by the repo. |
| `PreToolUse:Bash` | `branch_guard.sh` (blocks `claude/*` branches, `--no-verify`, force-push, colon-rename) | **No (functional gap)** | `gsd-validate-commit.sh` covers commit-message format; it does not gate branch names, force-push, or `--no-verify`. CLAUDE.md's Branch Policy ("Two branches only") is therefore enforced by convention only. |
| `PreToolUse:Bash` | `commit_msg_guard.sh` (conventional commit format) | **Partial (different impl)** | `gsd-validate-commit.sh` likely overlaps. Behavior, exit codes, and override env vars are not documented in this repo and may diverge from DomI's spec. |
| `PreToolUse:Write\|Edit` | `secret_path_guard.sh` (blocks writes to secret paths) | **Partial (different impl)** | `gsd-prompt-guard.js` / `gsd-read-guard.js` / `gsd-workflow-guard.js` provide GSD-flavored gating. None is documented as a secret-path matcher with a known deny-list. |
| `Stop` | `stop_introspect.sh` (`/introspect` reminder) | **No (functional gap)** | `~/.claude/stop-hook-git-check.sh` blocks Stop on uncommitted changes / push-pending state — that is git hygiene, not the `/introspect` retrospective reminder DomI prescribes. |

**Drift summary:** the user-scope GSD hooks predate DomI's prescribed surface. They overlap on commit/write guards but leave three functional gaps (branch policy, secret paths, `/introspect` reminder) and one indirect coverage (SessionStart runs `instructions_on_start.sh` only if the DomI plugin is installed; the repo doesn't trip-wire it).

---

## 3. Override contract

The issue mandates these two overrides be honored:

| Env var | Expected behavior |
|---|---|
| `CLAUDE_BRANCH_OVERRIDE=1` | Bypass branch-name guards (`claude/*`, two-branch policy) for a single session |
| `CLAUDE_INTERACTIVE=1` | Bypass guards that would block interactive prompts |

Neither variable is read by any hook currently installed (GSD hooks do not document them; the repo has no guard to honor or violate them). **Action:** the DomI-shipped guards must check these on entry — captured in the upstream report.

---

## 4. Classification

### 4.1 Upstream-relevant — file on `domattioli/DomI#64`

These should live in DomI so every consumer repo (ADMESH-Domains, others) gets the same enforcement without each rolling its own:

1. **`branch_guard.sh`** missing — no enforcement of two-branch policy, no `--no-verify` block, no force-push block, no colon-rename block.
2. **`secret_path_guard.sh`** missing as a named, documented guard with a publishable deny-list. Existing GSD guards do not advertise the surface they cover.
3. **`stop_introspect.sh`** missing — no `/introspect` reminder at session end. The `stop-hook-git-check.sh` covers a different concern (uncommitted changes) and should remain orthogonal.
4. **Override-contract honor.** Every DomI guard must check `CLAUDE_BRANCH_OVERRIDE=1` and `CLAUDE_INTERACTIVE=1` and document the precedence. This is policy, not implementation, and belongs upstream.
5. **`commit_msg_guard.sh` vs `gsd-validate-commit.sh` drift.** Either DomI adopts/aliases the GSD hook, or it ships its own and documents how the two coexist. Today the consumer cannot tell which guard ran or what rules applied.
6. **`session_start.sh` self-installation.** DomI should ship a hook entry that points at the repo's `scripts/instructions_on_start.sh` automatically (consumer scripts vary; the wrapper should not). Currently `instructions_on_start.sh` is only reached if the operator sources it or the DomI plugin's own session hook fires.

### 4.2 Local-only

These would be repo-specific (release-track or data-track concerns) and are candidates for `.claude/settings.json` rather than upstream:

1. **None warranted right now.** All current gaps map to behavior consumers share. The repo-specific concerns (PyPI-version-bump check for data-only changes, `MANIFEST.in` exclusion of meshes) are already protected by `release.yml` / `publish-data.yml` workflows and the constitution — adding a duplicate local hook would create drift, not safety.
2. Future candidate: a `PreToolUse:Bash` matcher for `git push` that blocks pushes touching `registry_data/meshes/` (Principle IV — meshes ship via Hub, not PyPI). Defer until justified by an actual regression.

### 4.3 No action

- `gsd-statusline.js`, `gsd-context-monitor.js`, `gsd-read-injection-scanner.js`, `gsd-phase-boundary.sh`, `gsd-check-update.js`, `gsd-session-state.sh`, `gsd-prompt-guard.js`, `gsd-read-guard.js`, `gsd-workflow-guard.js` — GSD-specific quality-of-life hooks. Out of DomI's prescribed surface; leave alone.

---

## 5. Local change set

`.claude/settings.json` is **left untouched** for this audit. Rationale: every gap surfaced is a shared concern that belongs in DomI; duplicating it locally would create drift the moment DomI ships its prescribed hooks. The audit's value is the upstream report.

---

## 6. References

- Issue: `domattioli/ADMESH-Domains#54`
- Upstream inbox: `domattioli/DomI#64`
- Full hook spec: `domattioli/DomI#60`
- DomI reference commit: d11ca39
- Branch policy (repo): `CLAUDE.md` § Branch Policy
- Constitution: `.specify/memory/constitution.md`
