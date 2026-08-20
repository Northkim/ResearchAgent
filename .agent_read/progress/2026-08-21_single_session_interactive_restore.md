# Single-session interactive Codex restore (2026-08-21)

Status: **IMPLEMENTED; deterministic PTY qualification PASS; real-owner
interactive acceptance pending**

## 1. Regression root cause

`a0c39b6` routed Literature through headless `codex exec --ephemeral` phases
(`MVP-LS2 AUTO_PLANNING_STAGE` / `AUTO_SYNTHESIS_STAGE`), printing the raw
Harness transcript and silently entering DEMO. `cdb4573` restored attached
interactive Codex TUIs but still split one round into planning, screening, and
finalization TUIs that closed and reopened at each checkpoint.

## 2. Restored model

`run_workflow` (Literature pins 0.5.0/0.7.0 and 0.6.0/0.8.0) now calls the new
`_run_literature_interactive_round`, which mirrors the reviewed single-session
mechanism in the installed Literature Capsule (`_run_interactive_codex`):

one `run` -> one attached Codex TUI (`codex --sandbox workspace-write
--ask-for-approval on-request --no-alt-screen -C <capsule>` with stdin/stdout/
stderr inherited) -> `MVP-LS2 INTERACTIVE_ONE_ROUND` prompt supplied
automatically -> search-plan discussion -> Owner `proceed` -> Codex writes
`search_plan.md` + `query_plan.json` and sets `PLAN_CONFIRMED` -> the bounded
Provider controller thread runs the exact queries while Codex stays open ->
`SEARCH_COMPLETED` -> candidate screening in the same session -> `finish` ->
Codex writes the four outputs, context, report draft, `FINALIZED`, exits once
-> ReAgent validates, finalizes the Progress Report, uploads with a fresh
session, stores the receipt, and marks `UPLOADED`.

Owner dwell cannot trigger a Harness timeout: the interactive child has no
wall-clock kill; Provider HTTP and Cloud operations keep their bounded
timeouts. Ctrl+C marks `INTERRUPTED`, revokes the scoped session, terminates
the attached child safely, and preserves durable state; an in-Codex abort
returns `EXECUTION_INTERRUPTED` without publishing.

## 3. NORMAL/DEMO

The plain Cloud command defaults to NORMAL and fails closed (`NORMAL_REQUIRED`)
when the backend offers DEMO. Explicit `--mode demo` is the only Demo path. The
KNN backend currently runs the `isolated-controlled-test` profile (DEMO); the
authoritative real-owner profile is `local-development` (the default), which
serves NORMAL when the real OpenAlex proxy is configured. No NORMAL -> DEMO
fallback exists.

## 4. Cross-workflow boundary

Root in-process Writing/Review/Writing-Revision (`_writing`, `_review`,
`_revision`) and Generic Experiment Harness (`advance_generic_harness_workflow`
via `run_generic_harness`) harness calls now use the attached interactive Codex
mode instead of headless `codex exec`, restoring the user-facing TUI boundary
while preserving each Workflow's reviewed phase/approval contracts. Idea
Discovery already runs its capsule-owned interactive single-TUI launcher and is
unchanged.

## 5. Tests

- `test_literature_interactive_harness.py`: one-session selection (exactly one
  interactive invocation, `INTERACTIVE_ONE_ROUND`, no AUTO_ stages), automatic
  prompt handoff, explicit-`finish` requirement, owner-abort safety, stdin
  attachment and no wall-clock timeout, NORMAL fail-closed.
- `test_literature_checkpoint_lifecycle.py`: public-workspace run uses exactly
  one attached interactive session end-to-end to `UPLOADED`.
- `interactive_e2e_driver.py`: workspace-root mode now drives the fake Codex
  CHECKPOINT conversation (proceed/continue/finish); the old multi-phase
  ReAgent approval contract was removed.
- `test_owner_real_research_gate.py` (loopback, real adapter, NORMAL) passes:
  one PTY session, plan -> Provider -> screening -> finish -> upload ->
  Idea materialization.

Full backend: `1140 passed`, `80 skipped`, `1 deselected` (pre-existing spawn
lock test passes standalone), `18` environment-only PostgreSQL setup errors
(`REAGENT_TEST_DATABASE_URL` absent; unrelated to this change). Frontend:
typecheck, lint, and all 85 vitest tests pass.

## 6. Owner action (KNN)

The KNN root CLI is the `cdb4573`-era self-updating source; one
`python reagent_local.py sync .` refreshes it to this commit. The KNN
Literature Capsule holds accidental DEMO planning state; the supported one-time
recovery is `--restart-round` (reviewed `_reset_round`, clears only unreported
round-1 mutable state). Then the plain Cloud command runs NORMAL single-session
Literature Search. Real-owner acceptance is pending.
