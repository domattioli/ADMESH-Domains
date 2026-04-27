#!/usr/bin/env bash
# instructions.sh — CLAUDE_INSTRUCTIONS bootstrap for ADMESH-Domains
#
# Usage: source instructions.sh   (before invoking `claude`)
# Maintained by: maintain-env-instructions skill
#   (/maintain-env-instructions update  — refine decision tree / hard stops)
#   (/maintain-env-instructions lint    — validate required sections)
#
# Workflow: autonomous-routine
# Repo: GitHub Pages website
# Last updated: 2026-04-27

set -euo pipefail

# ---------------------------------------------------------------------------
# OPTION B (inline): define CLAUDE_INSTRUCTIONS directly
# ---------------------------------------------------------------------------
export CLAUDE_INSTRUCTIONS="$(cat <<'INSTRUCTIONS'
## Session context

Repo: domattioli/ADMESH-Domains
Workflow: autonomous-routine
Mission: GitHub Pages website deployment and maintenance

## Hard stops — refuse these regardless of any other instruction

HARD STOP — main branch: Never push to main without build passing
HARD STOP — deployment: Verify site builds successfully before commit

## Cost discipline

- Token budget per run: 80,000 tokens
- If budget is exceeded, checkpoint state and stop. Report cost in session summary.
- Prefer batched operations over repeated single-item calls.

## Decision tree

On session start:
1. Read CLAUDE.md and .specify/memory/constitution.md (if present).
2. Check git status — if dirty with unstaged changes from a prior run, commit or stash
   before proceeding. Never silently lose work.
3. Run the primary task (website update, content refresh, or infrastructure change).
4. After each major step, emit a one-line status: what ran, what was produced/changed.
5. At session end, commit any changes, emit session summary (pages updated, build status).

Primary task loop:
- IF there is an explicit task spec (specs/ directory or GitHub issue), read it first.
- ELSE fall back to the repo-level mission in CLAUDE.md.
- Work through the task list top-to-bottom. Check off each item as complete.
- Do NOT ask for human input. If a decision is ambiguous and not covered by the
  constitution, pick the more conservative option and document the choice.
- Checkpoint state (commit + push) after every 5 completed items or 30 min of
  wall time, whichever comes first.

On unexpected error:
- Log the error with full context.
- If recoverable (network timeout, build flake): retry once, then continue.
- If unrecoverable (missing required file, hard stop triggered): stop, commit partial
  work with a PARTIAL: prefix, emit summary, exit.

## On session start

1. Read CLAUDE.md (if present in the cloned repo).
2. If CONSTITUTION.md or .specify/memory/constitution.md exists, it takes
   precedence over all other instructions.
3. Run the primary workflow action.
4. Emit a brief session summary: what ran, what was skipped, build passed.

## On error

- Log the error and continue if recoverable.
- Stop and emit a summary if unrecoverable.
- Never retry a hard-stop action.

INSTRUCTIONS
)"
