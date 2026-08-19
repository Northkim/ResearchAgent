# Post-D1 R1B1 accepted binding and optional-evidence decision

Status: **PASS — READY FOR CLEAN R1B1 COMMIT**

Date: 2026-08-20

Authority: R1 in
`.agent_read/progress/2026-08-20_post_d1_repair_program.md`, narrowed by
`.agent_read/progress/2026-08-20_post_d1_r1_change_packet.md` and ADR 0050.

## Scope and ledger disposition

R1B1 closes these root findings while preserving their D1 evidence:

- `D1-FRONTEND-KEY-01`
- `D1-WRITING-BINDING-01`
- `D1-REVIEW-INPUT-LIFECYCLE-01`

R1B2 `D1-UPSTREAM-ZERO-PAPER-01` and R1C package classification remain
unimplemented and must use separate commits. R1B1 changes no Workflow
Definition, Capsule, Artifact schema, scientific validator, scientific output,
or protected D1 row.

## Root correction

One additive Project/Workflow-scoped decision records that the Owner explicitly
continued without the currently unresolved optional evidence. Its checksum
binds the exact active binding set, consumer Definition/version, exact sorted
omission keys, decision, idempotency key, and decision time. A changed binding
makes the old decision non-current without rewriting history.

The materialization plan refuses unresolved required inputs and refuses
unresolved optional evidence until a current decision exists. The shared
Progress projection keeps a not-yet-progressed Workflow in `SELECT_INPUT` until
that gate is satisfied; accepted historical Progress/output states remain
authoritative once work has advanced.

The browser now:

- keys each candidate by requirement plus exact Artifact ID;
- clears local selection only after the dependency mutation succeeds;
- invalidates and re-renders from accepted binding/setup state;
- labels bound evidence `Selected`, not locally runnable;
- retains compact optional-evidence state;
- exposes one explicit `Continue without optional evidence` action;
- withholds materialization until the decision is current.

No automatic selection, latest lookup, placeholder Artifact, or presentation-
based scientific decision was introduced.

## Persistence and migration

Migration `20260820_0035` adds only
`project_workflow_input_setup_decisions`, with exact Project/Workflow foreign
ownership, idempotency uniqueness, checksum constraints, and the single
supported decision enum. Historical migration and publication bytes are
unchanged.

Marked disposable PostgreSQL qualification passed:

- upgrade through 0035;
- repository add/read/list round-trip;
- duplicate-idempotency conflict behavior;
- 0035 → 0034 downgrade;
- 0034 → 0035 re-upgrade;
- `alembic check` with no pending operations;
- identity-verified database cleanup.

The protected Owner database remains at 0034 and was not migrated.

## Qualification evidence

| Evidence | Result |
|---|---|
| Artifact service/API and Progress decision cases | **17 passed** |
| Artifact dependency, Progress, and four D1 repaired-contract regression locks | **177 passed**, plus the one loopback case passed separately with required permission |
| Direct historical Experiment optional-omission public route | **1 passed** |
| PostgreSQL decision persistence and migration cycle | **PASS** |
| Frontend full suite | **20 files / 71 tests passed** |
| TypeScript | **PASS** |
| Source-scoped ESLint | **PASS** |
| Production Next.js build | **PASS** |
| Python compileall | **PASS** |
| `git diff --check` | **PASS** |
| Alembic sole head | **`20260820_0035`** |

The broad Project Workspace suite remained red at **181 passed / 21 failed**.
Its baseline is already red from stale historical publication/version fixtures,
unprovisioned network cases, and unrelated expectations recorded by R0. The one
directly affected supported historical Experiment route was updated to make its
intentional optional-Literature omission explicit and now passes. R1B1 did not
use this phase for broad stale-test cleanup.

## Historical and safety result

- R1A exact replacement/readiness/refresh semantics remain passing.
- Initial Writing Real-provenance terminal recovery remains passing.
- Review optional-evidence publication remains passing.
- Revision causal-support subset semantics remain passing.
- existing Revision Plan approval resume remains passing.
- User Skill and ExperimentCapability boundaries are unchanged.
- complete Local Artifact bytes remain scientific authority.
- no implicit latest/merge or post-materialization input mutation was added.
- protected D1 Project and its Workspace were not used as fixtures.

## New-defect prevention gate

All ten program questions are **NO**. The repair does not weaken an exact
scientific boundary, introduce latest/merge, grant Cloud byte authority, grant
Skill capability authority, rerun completed science, add a manual low-level
Owner command, mutate an immutable publication, alter a D1 regression lock,
weaken a fixture, or add explanatory UI clutter.

Safe next action: begin R1B2 from the clean R1B1 commit and implement only the
forward-additive zero-paper consumer content qualification/publication contract.
