# D1-REVISION-CONTRACT-01 bounded forward repair change packet

> Packet completion does not authorize implementation. The Owner's 2026-08-19 instruction separately authorizes this exact repair and D1 recovery.

## 1. Objective
Publish the smallest forward Writing Revision correction that treats causal Review support as an exact subset of inherited manuscript context, then replace the blocked D1 Revision through existing supported Project/Workspace paths without launching its Harness.

## 2. Owner intent
Preserve exact manuscript lineage and exact causal Review authority. A Review may omit optional evidence; Revision may inherit that source as manuscript context, but omission must not become Review verification.

## 3. User problem
Writing Revision 0.6 / Capsule 0.8 requires equality between Revision support context and `review-report/v3.supporting_artifacts`. The D1 Review validly used Literature only, while the parent manuscript and created Revision also carry Research Idea, so startup fails closed.

## 4. Current baseline
`main` at `02d303a6df78168e566a2b868fd2a1fa6d304582`, clean, one worktree, Alembic `20260818_0033`. D1 Revision `wfi-20d46c8419fe5fa3809fb3a57a26f39b` has no Progress or output Artifact.

## 5. Authoritative sources
Current explicit Owner instruction; plan; ODR-002/006/008/009/010/011; ADR 0039 and 0040; immutable migration 0032 publication; live D1 bindings, manuscript v4, Review v3, materialization plan, and Capsule 0.8 validator.

## 6. Conflicts
Owner-approved optional Review evidence conflicts with immutable Capsule 0.8 equality semantics. The historical publication remains authoritative for its bytes, so the conflict is resolved only through additive Definition/Capsule publication. No intent ambiguity remains.

## 7. Scope
One forward Revision Definition/Capsule publication, current role-aware creation/sync/foundation wiring, focused contract/application/migration tests, and supported D1 retire/create/sync/materialize recovery.

## 8. Non-goals
No Artifact schema change, Review/Initial Writing change, content regeneration, frontend redesign, input-lifecycle repair, Experiment repair, Harness run, or unrelated D1 finding.

## 9. Domain semantics
The exact causal manuscript is mandatory. Every actual causal Review support reference must be present in Revision with identical role/ID/checksum. Revision context may additionally contain exact parent-manuscript sources. Review issue evidence remains limited to manuscript plus actual Review support. Same-role conflicts fail closed.

## 10. State transitions
New Review actions create Revision 0.7 / Capsule 0.9 idempotently from exact parent/review identity. For D1: active blocked 0.6 Revision --supported retire--> retained historical instance; exact Review action replay --supported create--> one active 0.7 Revision; sync/materialize --> locally ready. Failures retain the old instance and upstream Artifacts; retry uses exact manifest revision and deterministic version-aware identity.

## 11. Artifact impact
`manuscript-draft/v5` remains unchanged. No current D1 manuscript, Review, Literature, Idea, binding bytes, or output is mutated; no Revision output is created.

## 12. API impact
No route or DTO change. Existing retire, Review-to-Revision create, sync-plan/download, Artifact refresh/materialization, and read APIs are reused.

## 13. Persistence impact
One schema-free additive publication migration for Definition 0.7 / Capsule 0.9 and the same five exact requirements. Existing rows and Projects are unchanged until an explicit supported Project mutation.

## 14. Frontend impact
None in this repair. Existing role-aware Writing Revision rendering consumes the new published pin.

## 15. Security impact
Exact Project, role, Artifact ID/checksum, prior-manuscript lineage, Review-support membership, and issue-evidence membership remain fail closed. No browser Workspace write, implicit selection, Cloud Artifact bytes, or owner-data copy is introduced.

## 16. Cloud/local boundary impact
Cloud creates exact metadata/bindings; Local sync installs the new immutable Capsule and verified-copy materialization prepares exact inputs. Local scientific bytes remain authoritative.

## 17. Compatibility and versioning
Incompatible validator-semantic correction via additive Writing Revision Definition `0.7.0` and Capsule `0.9.0`; output remains compatible `manuscript-draft/v5`. Definition 0.6 / Capsule 0.8 and migration 0032 remain byte-identical and supported as historical state.

## 18. Migration impact
Exactly one forward schema-free migration `20260819_0034`; sole head advances from `20260818_0033` to `20260819_0034` after qualification and Owner DB upgrade.

## 19. Files expected to change
At most 10 production files, 1 migration, 4 tests, and 3 governance files; no frontend. Expected areas: the additive Revision publication, contextual Artifact validation, forward foundation, Project application, Workspace sync/client, focused workflow/database/project tests, context/progress/ADR.

## 20. Rejected alternatives
Mutating Capsule 0.8/migration 0032; root-only semantic override of a published Capsule; binding Idea into Review; dropping inherited Idea; weakening exact binding globally; SQL surgery; rerunning Review; auto-latest.

## 21. Test design
Required six subset/conflict/omitted-evidence/manuscript cases; new package identity/checksum and old-byte golden; Review-to-Revision exact inherited bindings/idempotency; disposable PostgreSQL publication/upgrade/downgrade/re-upgrade; public Workspace sync/materialization without Harness; real D1 exact recovery.

## 22. Acceptance criteria
All Owner-stated contract cases pass; old publications remain exact; new active D1 Revision has the four exact bindings, no Experiment, valid receipts/materialization, Ready to run, no Progress/output/Harness, no duplicate active Revision, and upstream bytes unchanged.

## 23. Rollback conditions
Before Owner migration/recovery, revert only unpublished source/tests. After publication/recovery, never rewrite migration rows, accepted upstream state, retired historical Revision, or exact bindings; use forward repair only.

## 24. Stop conditions
Stop for historical checksum drift, Artifact/schema mutation, implicit selection, sibling private reads, inability to replace through supported routes, unexpected D1 Progress/output, owner-byte drift, migration expansion, or Harness launch.

## 25. Owner decisions
The Owner explicitly accepted subset semantics and authorized this bounded forward repair and D1 recovery. No product decision remains open.

## Authorization gate
`READY_FOR_IMPLEMENTATION_REVIEW`; `AUTHORIZED_FOR_D1_REVISION_CONTRACT_01_ONLY`; no remaining pre-implementation blocker.

## Implementation and verification record

Implemented additive Writing Revision Definition `0.7.0` / Capsule `0.9.0` and a
strict `manuscript-draft/v5` contextual compatibility validator. The new Capsule and
Cloud validator require exact prior-manuscript/causal-Review lineage, exact identity
for every actual Review support role, and issue evidence limited to actual Review
scope, while allowing additional exact parent-manuscript context. Review-to-Revision
creation remains deterministic and idempotent and now targets the new publication.

E1 contract/package evidence passed the six required subset, equality, conflict,
omitted-evidence, missing/mismatched manuscript, and different-source-manuscript
cases. Capsule startup with Review `{Literature}` and Revision context
`{Literature, Research Idea}` passed. E3 application tests proved one exact 0.7/0.9
Revision and inherited context when Review omitted Research Idea. E4 marked
PostgreSQL qualification passed clean upgrade, additive readback, downgrade/re-upgrade,
Foundation idempotency, current Project creation, and exact removal of the disposable
database. The service readiness head advances with the same additive migration.
Historical forward Capsule and Review optional-evidence regressions passed.

E8 real D1 recovery completed through supported product paths. The Owner database
upgraded normally from `20260818_0033` to `20260819_0034` with pre/post Project,
Workflow, Artifact, binding, Progress, projection, and Skill-association counts
unchanged. The blocked 0.6/0.8 Revision was retired at manifest revision 4; exact
Review-to-Revision creation produced one active 0.7/0.9 instance at revision 5, and
an exact replay returned that same instance. Normal Workspace sync, Artifact refresh,
and materialization installed and prepared the four exact manuscript, Review,
Literature, and Research Idea inputs. All four input byte checksums and receipts match
the current materialization plan checksum. Experiment remains absent. The recovered
Revision reports `LOCALLY_MATERIALIZED` / `RUN`, with zero Progress reports and zero
Revision Artifacts; no Harness or scientific Workflow was run. Protected upstream
Artifact identities and checksums remained unchanged.

Verifier independence: LIMITED. The same implementing agent executed the focused
repository-native checks; evidence is reproducible from this packet and the named
tests, but no independent second verifier was used.
