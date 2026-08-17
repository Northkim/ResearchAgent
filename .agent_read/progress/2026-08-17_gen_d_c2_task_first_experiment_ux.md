# GEN-D-C2 task-first Experiment UX

Date: 2026-08-17
Baseline: `6d8a1fa5fa3f22623f02241463215244ba60b8a6` on `main`
Packet status: READY_FOR_IMPLEMENTATION_REVIEW
Implementation authorization: explicit Owner instruction for GEN-D-C2

## 1. Objective

Correct only the information hierarchy and progressive disclosure of the
published Generic Experiment 0.6 Owner page. The current task and its one
primary action must precede supporting lifecycle details; empty methodology
collections must collapse to one truthful message; results must become primary
during review and completion.

## 2. Owner intent

Preserve the qualified Generic Experiment, controlled-local Run Approval, and
result presentation behavior while making the page task-first. Do not change
the architecture, lifecycle, API, persistence, publication, Path B, downstream
contracts, Full Research preset, Terminal model, or D1.

## 3. User problem

The accepted page renders all lifecycle stages at similar visual priority. It
keeps both Start cards after Path A selection, repeats eleven empty methodology
rows, places current blockers after supporting detail, constrains approval copy
inside a narrow grid, and makes Owners pass prior stages before results.

## 4. Current baseline

- Branch: `main`
- HEAD: `6d8a1fa5fa3f22623f02241463215244ba60b8a6`
- Worktree: clean; one worktree
- Alembic sole head: `20260817_0030`
- Experiment 0.6, Capsule 0.9, experiment-record/v4, and controlled-local Run
  Approval v0.1 remain accepted and immutable.

## 5. Authoritative sources

- Owner GEN-D-C2 instruction
- `docs/PROJECT_DEVELOPMENT_PLAN.md`
- `docs/engineering/SOURCE_OF_TRUTH_POLICY.md`
- ODR-011 in `docs/engineering/OWNER_DECISION_REGISTER.md`
- ADR 0044 and ADR 0045
- Accepted GEN-D-C1 implementation and E6 evidence

## 6. Conflicts

None. The requested task-first hierarchy is consistent with ODR-011. Existing
Cloud-visible checkpoint, action, approval, and Artifact presentation data is
sufficient; no new authoritative data source is required.

## 7. Scope

- Reorder Generic Experiment 0.6 sections around one early Current Task.
- Collapse selected Path A to a compact summary.
- Render only reported methodology fields or one bounded absent-state message.
- Emphasize only the current preparation blocker.
- Make approval and changed-plan cards readable and single-column.
- Prioritize results during result review and completion.
- Preserve current result primitives, Outputs previews, approval mutations, and
  historical/non-Experiment rendering.

## 8. Non-goals

No backend, API, persistence, migration, contract, lifecycle, publication,
Capability, Resource, Runtime, package, Path B, downstream, preset, D1, or
Terminal changes.

## 9. Domain semantics

The current task is derived only from the existing checkpoint/action/approval
projection. Pre-Artifact lifecycle data remains authoritative for stage,
blocker, and next action. Exact v4 plus its presentation companion remains
authoritative for bounded scientific results.

## 10. State transitions

No state transition changes. Path A selection remains view-local. Approval
REQUESTED/APPROVED/REJECTED/SUPERSEDED/CONSUMED semantics and mutation
idempotency remain unchanged. This change only alters ordering, density, and
disclosure.

## 11. Artifact impact

None. experiment-record/v4 and presentation v0.2 are read unchanged.

## 12. API impact

None. Existing hooks and controlled-local approval endpoints are reused.

## 13. Persistence impact

None.

## 14. Frontend impact

Generic Experiment 0.6 only: task-first ordering, compact historical stages,
reported-only methodology, readable action cards, result-first review/final
states. Historical 0.4/0.5 and non-Experiment branches remain untouched.

## 15. Security impact

No new data or mutation. Checksums and local-private provenance remain inside
collapsed Technical details; no browser-to-Workspace write is introduced.

## 16. Cloud/local boundary impact

None. Browser approval remains authorization only; Local Workspace remains the
executor through the existing bounded runner.

## 17. Compatibility and versioning

Unchanged-compatible frontend presentation. All published identities and bytes
remain unchanged.

## 18. Migration impact

None; sole head must remain `20260817_0030`.

## 19. Files expected to change

- `frontend/components/workflow-detail.tsx`
- `frontend/app/globals.css`
- `frontend/tests/workflow-board.test.tsx`
- `frontend/tests/e2e/gen-d-c1-controlled.spec.ts`
- `.agent_read/context.md`
- this progress record

Budget: two production frontend files, two test files, two governance files;
six total tracked files; at most 1,400 net changed/added lines; no backend or
migration files.

## 20. Rejected alternatives

- New lifecycle/backend projection: data already exists and would exceed scope.
- New approval UI/authority: controlled-local v0.1 is already qualified.
- CSS-only reordering: would not truthfully omit empty collections or establish
  accessible DOM order.
- Hiding all prior stages: removes useful context; compact disclosure preserves it.

## 21. Test design

- UNIT/component E1: Start cards vs compact mode, current-task ordering,
  reported-only methodology, each blocker, preparation-complete state,
  approval/changed-plan layout, result-first ordering, no completed Pending wall.
- Regression E1: approval mutation semantics, presentation primitives, Outputs,
  Experiment 0.4/0.5, and non-Experiment routes.
- CONTROLLED_BROWSER E6: real FastAPI/Next.js/disposable PostgreSQL/system Chrome,
  all fourteen required screenshots and accessibility interaction smoke.
- Verifier independence: LIMITED (same agent implements and verifies).

## 22. Acceptance criteria

All GEN-D-C2 completion-gate statements pass; build and E6 pass; screenshots
exist; historical routes remain intact; repository is committed and clean.

## 23. Rollback conditions

Revert only these unpublished frontend/test/governance changes if task-first
ordering misstates lifecycle authority, breaks approval, loses result content,
or changes historical routes. Never rewrite published bytes or durable state.

## 24. Stop conditions

Stop for any required backend/persistence/contract data, scope over 1,400 net
lines or the named file budget, unavailable release-blocking E6, historical
route drift, approval semantic change, or architecture expansion.

## 25. Owner decisions

All required decisions are explicit in the GEN-D-C2 authorization. No remaining
Owner decision is required before implementation.

## Implementation outcome

The Generic Experiment detail page now places one Current Task directly after
the Research Objective. Before selection it contains the two truthful Start
cards; after Path A selection it replaces them with a compact “Start mode ·
Prepared with ReAgent” summary. Checkpoint blockers, approval actions, and result
review now occupy this same early task position.

Methodology renders only reported fields. With no bounded methodology payload,
one truthful not-yet-reported sentence replaces the former eleven-row Pending
matrix. Preparation remains collapsed while methodology/design work is current,
and result review/finalized pages put bounded scientific results before a closed
Experiment history disclosure. Approval, changed-plan, and post-approval cards
use readable horizontal prose and preserve the controlled-local mutation and
execution boundary.

No backend, API, persistence, contract, migration, publication, or lifecycle
source changed.

## Verification packet

- Verification ID: GEN-D-C2-E6 / 2026-08-17
- Verifier independence: LIMITED
- Highest achieved level: CONTROLLED_BROWSER / E6
- Fixture: marked disposable PostgreSQL Project with controlled Experiment 0.6,
  historical Experiment 0.4/0.5, and non-Experiment states
- Browser: repository Playwright 1.61.1, system Chrome channel `chrome`
- Public path: real controlled FastAPI + real Next.js

Requirement coverage:

- Start-before-selection and compact Path A: component E1 + browser E6 PASS.
- Current-task/checkpoint ordering: component E1 + browser E6 PASS for
  methodology, Resource, preparation prerequisite, preparation complete, and
  runtime incompatible.
- Reported-only methodology/no Pending wall: component E1 + browser E6 PASS.
- Approval/changed-plan/post-approval layout and keyboard action: component E1
  + browser E6 PASS; Cloud authorization remained non-executing.
- Result-review/completed result priority: component E1 + browser E6 PASS for
  non-ML and reference-shaped presentations.
- Accessibility: semantic regions, early DOM action order, keyboard activation,
  native details/summary disclosure, visible status text, and chart fallback
  passed component/browser smoke.
- Compatibility: Experiment 0.4, Experiment 0.5, non-Experiment Workflow, FE-M,
  H1, and local V0.1 browser paths PASS.

Executed evidence:

- `npm test -- --run`: 17 files / 60 tests PASS.
- `npm run typecheck`: PASS.
- `npm run lint`: PASS.
- `npm run build`: PASS under normal build permission; the first sandboxed run
  was blocked only because Turbopack could not bind its internal loopback helper.
- Isolated controlled E6: 5/5 Playwright tests PASS in 48.9 seconds.
- Disposable database:
  `reagent_qualification_09fd59cb3b4c411e9ca5cc870141e59f`, created from base,
  upgraded through `20260817_0030`, then identity-reported and dropped.
- Fourteen screenshots:
  `frontend/test-results/gen-d-c2-e6/screenshots/` (ignored qualification output).
- `git diff --check`: PASS.
- Alembic sole head: `20260817_0030`.

Two initial E6 attempts stopped on stale qualification assertions (obsolete C1
rejection copy and a non-exact heading selector). Browser evidence showed the
new product state was correct; only the E2E assertions were corrected. No
product source was patched in response to those runs. The final full isolated
suite passed and dropped its database.

Final verification status: PASS_AT_DECLARED_LEVEL. Controlled browser evidence
does not substitute for Owner-manual UX evidence. D1 remains PAUSED.
