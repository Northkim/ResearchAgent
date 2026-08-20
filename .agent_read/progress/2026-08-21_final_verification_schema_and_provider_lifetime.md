# Final verification: restored-path schema contract and Provider capability lifetime (2026-08-21)

Status: **VERIFIED with two minimal repairs; real-owner NORMAL acceptance pending**

## 1. Restored-path synthesis schema contract (REPAIR)

The previous schema repair lived only in the old multi-phase coordinator
(`_advance_literature_checkpoint_workflow` staging); the restored
`_run_literature_interactive_round` used the Capsule's `_interactive_instruction`,
which names the four output files but does not direct Codex to the authoritative
schemas. The immutable schema files (`workflow/schemas/candidate-papers.schema.json`,
`selected-papers.schema.json`, `selected-paper-library.schema.json`,
`progress-report.schema.json`, `round-control.schema.json`) are present in the
Capsule and readable by the live session, and `validate_package.py` enforces the
same contracts — but the instruction did not bind Codex to them.

Repair: `_literature_interactive_instruction` appends an AUTHORITATIVE OUTPUT
CONTRACTS directive to the Capsule instruction, mapping each schema to its
target file, naming `validate_package.py` as the authoritative validator, and
requiring identical generation/validation contracts. No Capsule bytes changed.

## 2. Provider capability lifetime (REPAIR)

Previously the scoped search session opened before the TUI and was revoked only
after the TUI exited — the capability existed for the whole TUI lifetime.
`_bounded_literature_provider_controller` now creates the session only when a
durable PLAN_CONFIRMED batch is observed, executes the bounded queries, and
revokes the session immediately (before SEARCH_COMPLETED is published), while
the same Codex TUI stays open. No capability exists during plan discussion,
candidate discussion, or finalization. The optional additional query reuses the
same flow with a fresh session; the local plan validator keeps the global
3-query bound. NORMAL refreshes the short-lived (2-minute) exact-scope consent
with the Owner's already-supplied confirmation before each activation, so a slow
plan discussion cannot expire the authorization.

## 3. `--restart-round` semantics

Source + new tests prove RESET_AND_RUN: the Owner confirms at the prompt, the
reset completes (`_reset_round`), and the same command then proceeds into the
run. If the backend is DEMO-only and the request is NORMAL, the reset completes
first and the command then fails closed with `NORMAL_REQUIRED`, leaving the
Capsule cleanly reset (mode None, NOT_STARTED) for a retry. No Codex process is
created before the reset completes.

## 4. Workflow interaction contracts

Git history confirms: Literature single-session TUI (`9db9d9e`), Idea Discovery
single-session TUI (`795ab45`), Initial Writing/Review/Writing-Revision
multi-phase attached-TUI with approvals (`7d842aa` `real_writing_runtime.py` /
`real_review_runtime.py` `run()`), Generic Experiment multi-phase harness with
approvals (`6b94e75` `advance_generic_harness_workflow`), Literature
Consolidation single attached TUI (`literature_consolidation.py::run`). The root
in-process headless bridge (`f8754bb` for writing/review/revision; generic
harness since introduction) was restored to attached TUIs in `180b441`.

## 5. NORMAL backend configuration

`scripts/dev-start.sh` maps `REAGENT_STARTUP_MODE=development` to
`REAGENT_DEPLOYMENT_PROFILE=local-development` and `controlled` to
`isolated-controlled-test`; the controlled profile forces DEMO
(`local_sessions.py::_service` enforced_search_mode). NORMAL requires the
OpenAlex Proxy adapter, enabled by `REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED=1`
with `REAGENT_OPENALEX_API_KEY` exported server-side (name only; values not
read). Verification without a search: GET
`/projects/{id}/local-sessions/execution-mode` returns `mode: NORMAL`. The
current runtime is NOT running; the last run was controlled (`/ready` probe),
so CURRENT_KNN_RUNTIME_READY_FOR_NORMAL = NO until dev-start.sh is rerun in
development mode.

## 6. Tests

- `test_literature_interactive_harness.py`: single-session test now asserts the
  schema directive + schema files on the actual restored path and Provider
  event ordering open -> execute -> close -> SEARCH_COMPLETED; abort-before-plan
  asserts zero session opens; two new restart-round tests prove RESET_AND_RUN
  and reset-before-NORMAL_REQUIRED.
- Focused: 16 passed (Literature lifecycle + interactive). Sync/portability/
  owner-checkpoint/generic-harness: 48 passed, 1 deselected. Loopback e2e
  (NORMAL owner gate, writing/review, experiment): 3 passed.
- Full backend: 1142 passed, 80 skipped, 1 deselected, 18 environment-only
  PostgreSQL setup errors (`REAGENT_TEST_DATABASE_URL` absent; unrelated).
