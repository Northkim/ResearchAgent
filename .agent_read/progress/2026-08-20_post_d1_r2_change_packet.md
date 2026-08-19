# Engineering change packet — Post-D1 R2

> Completing this packet does not authorize implementation. The Owner's
> 2026-08-20 Post-D1 Consolidated Repair Program separately authorizes the
> bounded implementation described here.

## 1. Objective

Repair the shared Owner-decision, Harness lifecycle, local-first Progress, resume,
and normal Local orchestration roots recorded as R2 without changing scientific
Artifact authority or published Capsule bytes in place.

## 2. Owner intent

The researcher makes natural scientific decisions after seeing bounded evidence.
ReAgent records each decision against exact immutable state, the managed Harness
ends cleanly when its phase is complete, Local state survives Cloud/session
failure, and one normal command performs safe coordination. Fine-grained commands
remain operator tools.

## 3. User problem

During D1, the Owner had to inspect internal JSON, echo SHA-256 tokens, interrupt
Harness sessions, manually upload/recover Progress, and repeat orchestration
commands. A resumed Literature session also lost an earlier screening disposition.
These are shared authority and lifecycle defects, not independent copy defects.

## 4. Current baseline

- Git root: `/Volumes/tb/个人资料/暑研/UCInspire26/MetaResearchAgent/ResearchAgent`
- Branch / HEAD: `main` / `5949af798d91227194b2bbd4c2f61acbbcd9d21d`
- Status: clean; one worktree.
- Repository Alembic sole head: `20260820_0036`.
- Protected Owner database: still `20260819_0034`; not an R2 target.
- Accepted forward publications include Literature 0.4 / Capsule 0.6, Idea 0.3 /
  Capsule 0.4, Initial Writing 0.5 / Capsule 0.7, Review 0.4 / Capsule 0.6,
  Writing Revision 0.7 / Capsule 0.9, and Experiment 0.7 / Capsule 0.10.
- The four accepted D1 bounded repairs are regression locks.

## 5. Authoritative sources

1. The Owner-authorized Post-D1 Consolidated Repair Program.
2. `.agent_read/progress/2026-08-20_final_d1_defect_ledger.md`.
3. The preserved Experiment Product Design Intent in the D1 record (R3 applies
   it; R2 defines reusable decision/lifecycle primitives only).
4. `docs/PROJECT_DEVELOPMENT_PLAN.md`, accepted ADRs, the Owner Decision
   Register, and immutable publication rows/bytes.
5. Current public paths in `backend/project_workspaces/workspace_cli.py` and
   installed Capsule runtimes.

## 6. Conflicts

- Published Writing/Review/Revision runtimes own exact approval validation but
  expose checksum-token prompts. A root coordinator may call those exact writers;
  editing their published source bytes in place is prohibited.
- Literature 0.4 stores only checkpoint booleans and final output checksums.
  Candidate-screening dispositions remain conversational before finalization.
  Therefore exact decision restoration requires a forward-additive Literature
  Definition/Capsule, not a launcher-only claim.
- Generic Experiment methodology and execution lifecycle are intentionally R3.
  R2 may provide the reusable decision primitive and preserve the existing exact
  controlled-run approval, but cannot close Generic Experiment acceptance early.
- No authority conflict requires an Owner decision. The authorized program
  explicitly requires additive publication when immutable semantics change.

## 7. Scope

### R2A — shared natural decision bridge

- Reuse installed runtime validators and runner-owned approval writers for
  Initial Writing, Review, and Writing Revision.
- Render concise evidence/checkpoint summaries before natural
  `Approve / Revise / Explain / Abort` actions.
- Bind approved decisions internally to the exact runtime checkpoint/input state.
- Preserve existing approved records as resume checkpoints and idempotent replay.

### R2B — managed Harness, Progress, cancellation, and high-level run

- Launch Codex through a bounded managed `codex exec` adapter so phase completion
  returns control to the coordinator normally.
- Make public `run` compose sync, exact Artifact reconciliation/materialization,
  pending Progress recovery, current-phase evaluation, Harness launch, finalization,
  and bounded upload.
- Extend central upload-only recovery to every supported local Workflow whose
  exact report can be evaluated without rerunning science.
- Convert Ctrl+C into a bounded cancellation result without raw nested traceback.

### R2C — durable Literature/Idea human decisions

- Publish the smallest forward-additive Literature/Idea revisions required to
  persist exact screening/selection decisions before Harness exit and restore
  them before Agent inference.
- Advance only new-project recommendations/preset pins after publication
  qualification; historical Workflow Instances remain pinned and unchanged.
- Use one additive migration if publication rows/preset persistence require it.

## 8. Non-goals

- Generic Experiment implementation/evidence admission (R3).
- Frontend information hierarchy/copy cleanup beyond the checkpoint interaction
  required for exact decisions (R6).
- Literature query strategy or iterative evidence composition (R4).
- Any automatic/latest Artifact binding, browser Workspace access, hosted runtime,
  second Agent runtime, or scientific-content generation in qualification.
- Owner database migration or protected D1 Project mutation.

## 9. Domain semantics

- Conversation text is not authority. A decision becomes authoritative only when
  the supported coordinator validates current exact state and the runtime-owned
  writer persists its checksummed record.
- Every displayed checkpoint is derived from the same exact object that the
  decision writer validates.
- `Approve` advances exactly one checkpoint. `Revise`, `Explain`, and `Abort` do
  not fabricate approval or final Artifact state.
- A terminal local report without a verified Cloud receipt is `pending_sync`, not
  failed science and not permission to rerun science.
- Resume reads exact durable decisions and validated outputs before invoking an
  Agent.

## 10. State transitions

| Before | Event / authority | After | Idempotency and retry evidence |
|---|---|---|---|
| checkpoint prepared, no decision | Owner natural action through coordinator | exact approved record, or unchanged/revision/abort state | checkpoint checksum + Workflow Instance + current exact inputs; retry reads existing record |
| exact approval already exists | resume / coordinator | next incomplete phase | validator proves exact record; no new approval |
| Harness phase active | Agent finishes bounded phase | durable local phase output, Harness exited | subprocess completion plus exact local validators |
| Harness phase active | Owner cancels | interrupted, local valid state preserved | bounded exit; no terminal upload |
| terminal report, no receipt | normal invocation / coordinator | pending upload attempted | report ID/checksum is upload idempotency authority |
| upload unavailable/unknown | transport failure | report preserved pending | next invocation retries same envelope/report; no science rerun |
| verified receipt | replay | no change | receipt/report identity prevents duplicate Progress/Artifact |
| public run invoked | Owner | sync → exact materialization → recovery → next phase | each existing sub-operation retains its own exact idempotency proof |
| Literature screening decision prepared (forward publication only) | Owner action | checksummed durable disposition snapshot | candidate-set checksum + decision identity; resume rejects drift |

Failure is fail-closed on input/checkpoint drift, ambiguous local ownership,
unverified receipt, or immutable-package mismatch. Retry never reconstructs a
decision from chat history.

## 11. Artifact impact

No Artifact schema changes in R2A/R2B. Existing v4/v3/v5 publishers and exact
Artifact bytes remain unchanged. R2C is expected to preserve the selected-paper-
library/v1 and selected-research-idea/v1 schemas; if durable decisions cannot be
represented as local Workflow memory without changing the Artifact, this packet
must be amended before implementation.

## 12. API impact

R2A/R2B prefer no new Cloud API. Existing exact binding, Progress upload/history,
Workspace sync, and controlled-run approval routes remain authority. A small local
coordinator decision API is process-local, not a browser-to-filesystem API. Any
new Cloud decision endpoint or DTO requires a packet amendment and API/security
tests.

## 13. Persistence impact

R2A/R2B: none expected. Local exact approval/report/receipt files already carry
the required durable state. R2C may require one additive migration solely for new
immutable publication rows and new-project pins; no mutable Owner research row is
rewritten.

## 14. Frontend impact

R2 primary checkpoint rendering may initially be terminal-local because current
scientific checkpoint objects are Local-only and the browser cannot read/write the
Workspace. Browser status continues to project bounded Cloud Progress only.
Full subtractive frontend hierarchy is R6. No frontend must claim a decision was
accepted before an exact durable receipt exists.

## 15. Security impact

- Harness environment continues to remove Provider/database/API credentials.
- Natural prompts never expose checksums by default; exact identities may remain
  under operator diagnostics.
- No arbitrary executable, shell interpolation, browser filesystem bridge, or
  Cloud access to complete local research bytes.
- Test harnesses are deterministic and make no real Provider calls.

## 16. Cloud/local boundary impact

Cloud coordinates exact bindings and receives bounded Progress/Artifact metadata.
Local Workspace stores complete checkpoints, approvals, drafts, and research bytes.
Local durable commit always precedes Cloud synchronization. Cloud outage cannot
erase or invalidate already-valid local science.

## 17. Compatibility and versioning

- R2A/R2B: unchanged-compatible coordinator behavior; historical Capsule bytes
  and identities stay byte-identical.
- R2C: forward-additive Workflow Definition/Capsule versions only. Historical
  Literature 0.4/0.6 and Idea 0.3/0.4 remain installable and unchanged.
- The accepted Review optional-evidence and Revision subset publications are
  regression locks and not republished by R2.

## 18. Migration impact

- R2A/R2B: `MIGRATION_REQUIRED = NO`.
- R2C: expected at most one forward migration if new immutable publication and
  preset pins cannot be represented in source-only recommendation state. It must
  pass marked PostgreSQL upgrade/downgrade/re-upgrade and preserve one sole head.
- The Owner database is not upgraded during R2 qualification.

## 19. Files expected to change

R2A/R2B bounded expectation:

- `backend/project_workspaces/workspace_cli.py`
- at most one new coordinator helper under `backend/project_workspaces/`
- at most four focused backend test files
- governance packet/report/ADR files

R2C bounded expectation after its pre-write publication audit:

- source builders under `backend/workflow_packages/` and
  `backend/project_workspaces/production_workflows.py`
- at most one migration and one migration test
- at most four publication/runtime tests

Budget per subphase: <= 12 production files, <= 8 test files, <= 3,000 net
production lines. Material expansion requires a packet amendment and phase split.

## 20. Rejected alternatives

- Treating chat approval as authority without a durable exact writer.
- Asking researchers to echo checksums.
- Editing installed/published Capsule bytes or historical migrations.
- Inferring a prior Literature disposition from final labels or Agent memory.
- Adding a second Agent runtime or Cloud executor.
- Rerunning completed science to recover an upload.
- Hiding low-level commands by deleting operator diagnostics.

## 21. Test design

- Exact natural approval for Writing outline/draft, Review scope/result, Revision
  plan/result; revise/abort/drift negatives and idempotent replay.
- Fake managed Harness proves bounded invocation, normal completion, no relaunch
  after terminal state, clean cancel, and environment scrubbing.
- Pending terminal Progress survives upload failure and uploads exactly once on
  the next public run without Harness launch.
- Public run composes sync/refresh/materialize safely, including R1 A→B and
  unchanged-sibling invariants.
- Forward Literature/Idea interrupt/resume fixtures persist the same exact Owner
  decision fingerprint and reject candidate/input drift.
- All four D1 regression locks on every subphase.
- Marked PostgreSQL/public Workspace/browser only where a subphase crosses those
  boundaries; never the Owner database/Workspace.

## 22. Acceptance criteria

- Natural Owner decisions create exactly one runner-owned exact approval.
- Human-readable evidence precedes every supported approval action.
- No normal checksum echo, manual Progress upload, or Ctrl+C completion.
- Terminal Harness completion returns to the coordinator and syncs once.
- Network failure leaves durable pending state and replay performs upload-only.
- Resume restores the same exact decisions and validated outputs.
- One public run performs safe preparation with no implicit binding.
- Forward Literature screening/Idea selection decisions survive a new Harness
  session exactly.
- No historical publication, Owner state, Artifact schema, or D1 lock regresses.

## 23. Rollback conditions

Before publication, revert only the isolated R2 commit. After an additive R2C
publication exists, rollback is another forward repair; never delete published
rows or rewrite migration history. No rollback may remove accepted Owner state,
local approvals, Artifacts, or Progress.

## 24. Stop conditions

Stop with a named status if implementation requires chat to become authority, an
in-place publication edit, implicit Artifact selection/merge, browser Workspace
access, a second execution engine, Owner data mutation, scientific rerun for
sync, unresolved migration/versioning, or scope beyond the subphase budget. A
new high/core defect stops progression to the next subphase.

## 25. Owner decisions

Already accepted: the consolidated repair program, natural approvals, local-first
Progress, durable resume, one normal Local operation, exact Artifact authority,
forward-only publication, and the Experiment Product Design Intent. No additional
Owner decision is required for R2A/R2B. R2C is authorized only within the
forward-additive, unchanged-Artifact-schema boundary above.

## Authorization gate

- Packet status: `READY_FOR_IMPLEMENTATION_REVIEW`
- Packet approval: supplied by the Owner's consolidated repair authorization.
- Explicit implementation authorization: `AUTHORIZED_WITHIN_BOUNDED_R2_SUBPHASES`
- Remaining blockers: none for R2A/R2B; R2C must complete its exact publication
  identity audit before source changes.
