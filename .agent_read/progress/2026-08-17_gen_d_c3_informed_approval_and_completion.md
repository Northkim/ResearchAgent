# GEN-D-C3 informed approval, result review, and completion closure

Date: 2026-08-17
Baseline: `389de6f4fbaf976431ea5d50bf79e37d93d9fbb5` on `main`
Packet status: COMPLETE
Implementation authorization: explicit Owner instruction for GEN-D-C3

## 1. Objective

Apply evidence-before-approval ordering to exact Run Approval and Owner Result
Review, remove misleading Local continuation from genuinely finalized
Experiment 0.6 state, and safely suppress duplicated canonical result blocks.

## 2. Owner intent

Keep the accepted task-first Current Task hierarchy while making its long-form
review actions navigational. Mutating Run Approval must follow the full exact
run summary. Exact result review remains Local and follows the complete bounded
scientific presentation. No architecture or authority change is authorized.

## 3. User problem

The C2 top card can approve before the Owner reads the complete exact-run
summary. Result Review lacks an explicit evidence-before-review handoff.
Finalized fixtures still advertise an active Local command, and canonical
result status blocks appear twice when also present in the presentation.

## 4. Current baseline

- Branch `main`; clean tree; one worktree.
- HEAD `389de6f4fbaf976431ea5d50bf79e37d93d9fbb5`.
- Alembic sole head `20260817_0030`.
- Experiment 0.6, Capsule 0.9, experiment-record/v4, presentation v0.2,
  and controlled-local Run Approval v0.1 remain immutable.

## 5. Authoritative sources

- Owner GEN-D-C3 instruction and `EVIDENCE_BEFORE_APPROVAL = YES`.
- Project plan and source-of-truth policy.
- ODR-011 task-first frontend decision.
- ADR 0044 Artifact-bound presentation and ADR 0045 controlled-local approval.
- Accepted GEN-D-C2 implementation and E6 evidence.

## 6. Conflicts

None. Current “Review result” is a non-mutating anchor. No Cloud/browser Owner
Result Review authority exists; exact review/finalization remains in the Local
generic coordinator. The existing Local Workflow command is therefore the only
truthful final review handoff and must appear after scientific content.

## 7. Scope

- Make top Run Approval and changed-plan actions focus the exact summary.
- Move existing approve/reject mutations after the full summary.
- Make top Result Review action focus results; place the Local review handoff
  after findings and limitations.
- Derive finalized display from exact checkpoint/action/stage projection rather
  than summary wording and omit Local Workflow when no Local continuation exists.
- Suppress only explicitly known canonical `(kind, label)` presentation blocks
  already rendered by Generic Experiment Detail.

## 8. Non-goals

No backend, lifecycle, API, persistence, migration, contract, Capability,
Resource, Runtime, package, publication, Path B, downstream, Full Research,
Terminal, or D1 changes. No new browser Result Review mutation.

## 9. Domain semantics

Long review content precedes final action. Top task actions navigate and move
focus. Run approve/reject retain the exact R1 authority. `RESULT_REVIEW_REQUIRED`
requires Local continuation after result inspection. An Artifact with no result
review checkpoint, a `COMPLETED` stage, and browser-only `REVIEW_RESULT` is a
finalized display state with no Local next action.

## 10. State transitions

Navigation changes no durable state. REQUESTED → APPROVED/REJECTED remains the
existing checksum-bound idempotent mutation after summary review. Superseded
request refreshes the existing approval projection; no old request authorizes a
new plan. Result review/finalization remains Local. No transition is added for
finalized display.

## 11. Artifact impact

None. Presentation payload is neither modified nor persisted again. Detail-only
filtering suppresses known duplicated canonical display blocks.

## 12. API impact

None. Existing observe/approve/reject calls are reused unchanged.

## 13. Persistence impact

None.

## 14. Frontend impact

Generic Experiment 0.6 only: focusable review targets, post-summary approval
controls, post-result Local review handoff, completed-state closure, and safe
canonical display de-duplication. The shared renderer retains its default
behavior for Outputs.

## 15. Security impact

No new data or authority. Top navigation performs no mutation. Browser approval
still never executes Local research. Local paths/checksums remain secondary.

## 16. Cloud/local boundary impact

Unchanged: Cloud records Run Approval; Local consumes and executes. Exact Owner
Result Review/finalization remains Local.

## 17. Compatibility and versioning

Unchanged-compatible frontend presentation. Historical 0.4/0.5 and published
0.6/0.9/v4 bytes remain untouched.

## 18. Migration impact

None; Alembic remains `20260817_0030`.

## 19. Files expected to change

- `frontend/components/workflow-detail.tsx`
- `frontend/app/globals.css`
- `frontend/tests/workflow-board.test.tsx`
- `frontend/tests/e2e/gen-d-c1-controlled.spec.ts`
- `scripts/gen_d_c1_controlled_fixtures.py`
- `.agent_read/context.md`
- this progress record

Budget: two production frontend, three test/fixture, two governance files; seven total;
under 900 net changed/added lines; zero backend or migrations.

## 20. Rejected alternatives

- New Cloud Result Review endpoint: unauthorized authority/persistence expansion.
- Treat every process completion as final: contradicts result-review checkpoint.
- Label-based filtering across arbitrary content: too fragile; use exact known
  canonical kind/label pairs only.
- Keep duplicate top and bottom approval controls: violates informed approval.

## 21. Test design

- Component E1: navigation is non-mutating and moves focus; mutation controls
  follow all exact-run evidence; changed-plan navigation; result decision after
  findings/limitations; finalized command omission; non-final Local handoff;
  canonical count one; adapter primitives preserved; historical paths unchanged.
- Controlled browser E6: real FastAPI/Next.js/disposable PostgreSQL/system Chrome
  for run approval, changed plan, result review, finalized non-ML/reference shape,
  and genuine result-review Local continuation.
- Verifier independence: LIMITED.

## 22. Acceptance criteria

All C3 completion gates pass, screenshots exist, E6 passes, no architecture or
persistence changes occur, and main is committed and clean.

## 23. Rollback conditions

Revert only these unpublished frontend/test/governance changes if action order,
focus, exact approval mutation, result rendering, or completion truth regresses.

## 24. Stop conditions

Stop for any required backend/lifecycle/persistence authority, migration,
historical byte change, unavailable release-blocking E6, scope expansion,
browser-to-Workspace mutation, or loss of exact approval binding.

## 25. Owner decisions

All required decisions are explicit in GEN-D-C3. No remaining Owner decision is
required before implementation.

## Implementation result

- The Run Approval Current Task now exposes only a non-mutating focus link.
  Existing controlled-local approve/reject mutations render once, after every
  bounded exact-run summary field.
- Superseded-plan recovery refreshes the exact active request and exposes a
  non-mutating “Review updated run” focus action before the same approved
  controls.
- Result Review now focuses the scientific result from the Current Task and
  places the truthful Local Owner-review/finalization handoff after findings,
  tables/series, outputs, warnings where present, and limitations.
- Finalized state is derived from the exact completed/browser-review projection,
  not merely ProcessOutcome or free-text wording. A real remaining local
  checkpoint still retains the Local Workflow area.
- Detail-only display filtering suppresses only four explicit canonical
  `(kind, label)` blocks already rendered by Core. Adapter findings and all six
  presentation primitives remain unchanged; Outputs keeps the unfiltered shared
  renderer.
- Focus targets are programmatically focusable with a visible outline, preserving
  keyboard and DOM evidence-before-action order.

## Qualification evidence

- Frontend Vitest: `17` files / `60` tests passed.
- Focused Generic Experiment tests: `21/21` passed.
- TypeScript, ESLint, production Next.js build, Python fixture compile, and
  `git diff --check` passed.
- Repository-native Playwright E6: `5/5` passed with real FastAPI, Next.js,
  system Chrome, and marked disposable PostgreSQL.
- The first E6 attempt exposed a controlled-fixture mismatch: fixtures labeled
  “Finalized” still projected `LOCAL_SETUP_REQUIRED`. Product code correctly
  retained Local continuation. The fixture was corrected to acknowledge its
  exact current Workspace installation, while the result-review checkpoint
  remains the required completed-process/local-continuation counterexample.
- Fourteen bounded screenshots are retained under ignored test results at
  `frontend/test-results/gen-d-c3-e6/screenshots/`.
- Qualification database
  `reagent_qualification_1d958912871e48ab943e323e5db0f64e` was dropped after
  the passing run. The earlier failed-run database was also dropped.
- Alembic remains `20260817_0030`; no backend production or migration file
  changed. Historical Experiment 0.4/0.5 and non-Experiment browser routes
  passed in the same E6 suite.
- Verifier independence remains `LIMITED`; evidence reaches controlled-browser
  E6 for the authorized path.
