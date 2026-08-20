# R6 change packet: subtractive Owner UX, labels, and information hierarchy

## 1. Objective

Close the remaining H-group D1 findings through shared role/output/activity
projections and a subtractive frontend hierarchy, after R1–R5 semantics have
stabilized. Preserve every exact scientific, publication, Cloud/local, and
approval boundary.

## 2. Owner intent

The Post-D1 Consolidated Repair Program explicitly authorizes R6. Primary Owner
surfaces should show achieved research outcomes, one current or remaining task,
typed Outputs, and concise evidence; exact IDs, checksums, receipts, round
internals, and local mechanics remain secondary.

## 3. User problem

Owner-facing names and state are currently derived in several places. Cloud and
Local ordinals can diverge, Local code guesses Writing role from version numbers,
forward v3/v4/v5 Outputs fall back to generic labels, Project-level sync appears
as per-Workflow invalidity, history mixes current Workflow stage with old report
status, retired Workflows compete with active work, and completed research
previews/layout do not foreground useful content.

## 4. Current baseline

- Branch: `main`
- HEAD: `321d1955fc5e73ac7cf66fd3d793743b9dca8444`
- Worktree: clean; one worktree
- Alembic sole head: `20260820_0039`
- Current forward pins remain Literature 0.6/0.8, Idea 0.4/0.5, Experiment
  0.8/0.11, Initial Writing 0.5/0.7, Review 0.4/0.6, and Writing Revision
  0.7/0.9.
- Review presentation v0.1, manuscript presentation v0.1, and all scientific
  Artifact schemas are immutable historical identities.
- Protected Owner D1 Project/database remains read-only evidence and is not a
  repair fixture.

## 5. Authoritative sources

- Post-D1 Consolidated Repair Program R6
- Authoritative D1 defect ledger H-group rows
- ODR-009, ODR-010, ODR-011, ODR-013, ODR-014
- ADRs 0044, 0048, 0049, 0050, and the R1–R5 completion records
- Published Definition Version `compatibility.writing_role`
- Exact installed Capsule descriptor paths (`workflow/real-writing.json`,
  `workflow/writing-revision.json`) for offline Local role authority
- Current Progress aggregation and UI companion validators

## 6. Conflicts

- D1 E9 observed a large duplicated/translucent Overview hero. Current source has
  no duplicate DOM or pseudo-element, and R5 controlled screenshots do not show
  the defect. This remains `QUALIFICATION_EVIDENCE_REQUIRED`: R6 will use a
  long-topic controlled visual regression and make only an evidenced CSS/layout
  correction. A non-reproduction will not erase the D1 occurrence.
- Historical Review presentation v0.1 omits v3 `category`, `summary`, and
  `recommended_action`. Those bytes cannot be replaced. R6 will preserve v0.1
  read compatibility and add v0.2 only for newly reported/backfilled Artifacts.
- Existing immutable Review/Revision scientific contracts are not in conflict;
  presentation remains UI-only.

## 7. Scope

- `D1-WORKFLOW-ORDINAL-01`
- `D1-WRITING-ENTRY-01`
- `D1-WRITING-UX-02`
- `D1-WORKSPACE-UX-01`
- `D1-OVERVIEW-PRIORITY-01`
- `D1-OUTPUT-LABEL-01`
- `D1-RETIRED-UX-01`
- `D1-PROGRESS-HISTORY-01`
- `D1-REVIEW-PRESENTATION-01`
- `D1-OUTPUTS-LAYOUT-01`
- `D1-PRESENTATION-CONTINUITY-01`
- `D1-OVERVIEW-VISUAL-01` as an explicit reproduction/audit gate

## 8. Non-goals

- No Workflow state-machine, exact binding, materialization, Harness, approval,
  Progress upload, scientific Artifact, Project/Skill lifecycle, or Generic
  Experiment architecture change.
- No Owner database backfill and no automatic mutation of the protected D1 row.
- No new browser access to Local files, no manuscript/review byte upload, and no
  new explanatory-documentation wall.
- No rewrite of Review presentation v0.1 or historical Capsule/migration bytes.

## 9. Domain semantics

- `writing_role` in published Definition compatibility is Cloud role authority.
  Offline Local role authority is the exact immutable workflow descriptor path,
  not semantic-version comparison.
- Initial Writing and Writing Revision are distinct roles and never share an
  ordinal namespace. Repeated same-role Workflows use one deterministic exact-ID
  ordering across Cloud and Local; active named roles remain unnumbered while
  retired/replaced identity is communicated by lifecycle/history.
- A Project manifest mismatch is Project sync state. An unchanged exact installed
  Capsule remains valid; a newly desired Capsule is simply not yet installed.
- Historical Progress-report status belongs to that exact report/round and must
  not be labelled as the current Workflow stage.
- Presentation absence never changes Artifact completion or authority.

## 10. State transitions

| Before | Event / authority | After | Retry / idempotency | Evidence |
|---|---|---|---|---|
| Prior Project acknowledgement, unchanged installed Capsule | Cloud manifest adds another Workflow | Existing Capsule retains its research action; Project shows one sync notice; new Capsule says not installed | Sync remains exact/idempotent | acknowledgement Capsule identities |
| Multiple same-family instances | Read Cloud/Local list | Same deterministic exact-ID ordinal mapping | read-only | immutable instance IDs |
| Explicit Writing role | Read projection/package | Initial Writing or Writing Revision without cross-role ordinal | read-only | compatibility or descriptor identity |
| Missing bounded presentation, exact local Artifact available | supported artifact refresh/high-level replay | one exact companion reported; science is not rerun | exact replay returns same companion | Artifact ID/checksum + presentation checksum |
| New Review v3 presentation | report exact v0.2 companion | concise issue identity/category/problem/action/status available | immutable replay | exact v3 Artifact + companion checksum |

## 11. Artifact impact

No scientific Artifact bytes, schemas, identities, checksums, bindings, or
lineage change. Review presentation v0.2 is a new optional, bounded, exact
Artifact-bound UI companion. v0.1 remains readable and immutable. Manuscript
presentation v0.1 remains unchanged and supports idempotent independent backfill.

## 12. API impact

Progress response remains additive-compatible. If needed, expose an exact
`workflow_role` projection derived from Definition compatibility; do not expose
version guesses. Existing routes and mutations remain unchanged. Presentation
report accepts the new exact pair `review-report/v3` + review presentation v0.2
while retaining v0.1.

## 13. Persistence impact

No new table or column. Existing Artifact-bound presentation storage is reused.
One Artifact still has at most one immutable companion; an existing v0.1 is not
upgraded in place.

## 14. Frontend impact

- Shared role-aware Detail/Board/Overview/Activity labels.
- One Project sync notice; unchanged Workflows retain truthful state.
- Completed revised manuscript outcome remains prominent while remaining
  Experiment work is separately labelled.
- Active Workflows primary; retired history collapsed and counted separately.
- Historical Activity labels exact report status/round, not current stage.
- Review issues prioritize ID, category, severity, one-line problem, requested
  revision, and current report-time status; long limitations collapse.
- Outputs use a responsive two-column/content-first layout with stable status.
- Writing input cards use Selected; materialization copy says verified inputs.

## 15. Security impact

Presentation remains bounded by size, exact keys, path/credential/log rejection,
and exact Artifact checksum. No complete manuscript/Review, local path, log,
credential, or Workspace content enters Cloud. Technical IDs remain secondary.

## 16. Cloud/local boundary impact

Cloud projections describe Cloud and last exact acknowledgement only. They do
not inspect Local bytes. Presentation generation/backfill runs through the
existing Local command and exact Artifact validator; the browser never writes a
Workspace.

## 17. Compatibility and versioning

- Scientific contracts/publications: unchanged-compatible.
- Progress/API projection: additive-compatible, schema identity retained unless
  exact serializer tests prove a version increment is required.
- Review presentation: compatible new v0.2; v0.1 accepted/read-only.
- Historical Workflow labels remain based on explicit role where available;
  generic historical Writing is not reclassified without authority.

## 18. Migration impact

`MIGRATION_REQUIRED = NO`. Alembic remains `20260820_0039`.

## 19. Files expected to change

Production target, at most 16 files and 2,500 net production lines:

- shared Owner label/projection helper plus Progress contracts/aggregation/API;
- `workspace_cli.py` for offline role labels and presentation v0.2 generation;
- presentation validator/service registry;
- frontend types, Workflow Detail/Board, Overview, Activity, Outputs,
  presentation renderer, and CSS;
- at most eight direct backend/frontend/E2E test files;
- R6 governance records.

## 20. Rejected alternatives

- Version-number role inference: rejected; it caused the D1 defect.
- Per-page label conditionals: rejected; projections would drift again.
- Treat every stale manifest revision as invalidating every Workflow: rejected;
  exact unchanged Capsule acknowledgement proves otherwise.
- Replace historical presentation v0.1: prohibited.
- Backfill via browser or Cloud Artifact-byte access: prohibited.
- Add explanatory paragraphs instead of hierarchy/layout changes: rejected.

## 21. Test design

- E1/E2: exact role authority, deterministic ordinals, output labels, stale
  Project acknowledgement, historical report rendering, v0.1/v0.2 presentation
  validators, real-secret/path negatives.
- E3: Progress projection with active+retired Revision and Project-level sync.
- E5: completed v4 presentation backfill through public refresh without Harness
  or scientific rerun; replay idempotency.
- E6: controlled final-state Project with completed v5, unresolved Experiment,
  active/retired Revision, Review issues, Outputs, Activity, long Project topic,
  and Project sync after new Workflow.
- Run all four D1 regression locks.

## 22. Acceptance criteria

- All scoped ledger reproductions pass at their required controlled level.
- No version inference or Cloud/Local ordinal mismatch remains.
- Initial Writing and Writing Revision remain role-distinct and unnumbered.
- One Project sync notice does not mark unchanged completed Workflows stale.
- Completed v5 outcome and remaining Experiment work are both clear.
- Forward Outputs are typed across Board/Overview/Activity.
- Retired history is preserved but secondary.
- Review issue presentation is substantially more scannable.
- Missing v4 presentation backfills without scientific rerun.
- No migration/publication/scientific authority/D1 Owner-state change.

## 23. Rollback conditions

Revert the unpublished R6 commit if it changes Workflow readiness, selects an
Artifact, makes presentation authoritative, hides retired provenance, overwrites
v0.1, or regresses any R1–R5/D1 lock. Do not mutate accepted owner data as a
rollback mechanism.

## 24. Stop conditions

- `HISTORICAL_CONTRACT_CONFLICT` if v0.1 or a published Capsule would need edit.
- `REPAIR_SCOPE_EXPANSION` above 16 production files/2,500 production lines or if
  persistence/migration becomes necessary.
- `QUALIFICATION_EVIDENCE_REQUIRED` if the Overview visual defect cannot be
  reproduced and no safe source root is identified; preserve it as unresolved
  rather than guessing.
- `NEW_PRODUCT_DEFECT` for any new high/core regression.
- Stop for browser-to-Workspace access, implicit selection, or exact-boundary
  weakening.

## 25. Owner decisions

ODR-011 and the explicit R6 authorization settle the task-first/subtractive
direction. ODR-009/010 settle presentation and Cloud/local boundaries. No new
Owner decision is required for the bounded implementation.

Packet status: `READY_FOR_IMPLEMENTATION_REVIEW`.

Implementation authorization: `AUTHORIZED_BY_POST_D1_PROGRAM`.
