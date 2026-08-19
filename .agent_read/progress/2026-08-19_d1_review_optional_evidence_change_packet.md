# D1-REVIEW-CONTRACT-01 bounded repair change packet

> Packet completion does not authorize implementation. The Owner's 2026-08-19 instruction separately authorizes this exact repair and recovery.

## 1. Objective
Make forward `review-report/v3` honor optional Review evidence while every actually bound or used Artifact remains exact, then finalize the approved D1 Review without substantive rerun.

## 2. Owner intent
Omitted manuscript provenance remains manuscript provenance, not Review evidence; affected support is unavailable/not independently verifiable and cannot be silently bound.

## 3. User problem
The contextual v3 validator passes Review bindings to the v4 manuscript validator as a complete source set, so valid limited-scope Review cannot publish.

## 4. Current baseline
`main` at `759e6decde50ceab24127d97b74da73b9575820c`, clean, one worktree, Alembic `20260818_0033`; D1 Review 0.4/0.6 has an exact approved result but no v3 Artifact or terminal Progress.

## 5. Authoritative sources
Current Owner instruction; plan and ODR-006/007/009/010/011; ADR 0039/R1 closure; immutable migration 0032 publication; current v3 validator and Workspace root recovery path.

## 6. Conflicts
Accepted optional-input semantics conflict with contextual set equality. Owner intent resolves semantics; historical Capsule bytes remain immutable and require an application/launcher compatibility seam.

## 7. Scope
One v3 optional-support validator, one exact approved-result recovery dispatch, focused tests, and required governance updates.

## 8. Non-goals
No Review regeneration, issue/manuscript/binding/frontend change, Revision creation, migration/version publication, or other D1 repair.

## 9. Domain semantics
Manuscript is required/exact; supplied optional sources must match manuscript lineage; support equals actual bindings; omitted sources are unavailable and forbidden as issue evidence/audit authority.

## 10. State transitions
`approved result + no output` --root run--> deterministic v3 --> one COMPLETED Progress --> backlog upload/receipt. Artifact/report identity makes retry idempotent; mismatch fails before publication; Harness launch is forbidden.

## 11. Artifact impact
One deterministic v3 from existing approved state; no manuscript/source/schema/historical-byte change.

## 12. API impact
None; existing Progress upload, Artifact promotion, projection, and receipt APIs are reused.

## 13. Persistence impact
None; no migration or row surgery.

## 14. Frontend impact
None; existing Completed projection is reused.

## 15. Security impact
Required/optional identities, issue-evidence membership, content address, and approvals remain fail closed; omitted evidence gains no authority.

## 16. Cloud/local boundary impact
Local approved bytes remain authority; Cloud receives bounded existing metadata/Progress only; browser never writes Workspace.

## 17. Compatibility and versioning
Unchanged-compatible correction; Definition 0.4, Capsule 0.6, migration 0032, and checksums remain byte-identical.

## 18. Migration impact
None; sole head stays `20260818_0033`.

## 19. Files expected to change
At most 3 production, 2 test, and 2 governance files; no migration; <=700 net lines. Material expansion stops for approval.

## 20. Rejected alternatives
Binding Idea, editing approved bytes/0032/Capsule, weakening generic binding, SQL publication, or Harness relaunch.

## 21. Test design
Four required contract cases; exact approved no-output fixture with launch sentinel, one upload, replay, unchanged bytes; immutable publication and affected regressions.

## 22. Acceptance criteria
All Owner-stated unchanged-byte/binding, omission, exact validation, exactly-once publication/Progress, Completed, no-Revision, and unrelated-Workflow requirements.

## 23. Rollback conditions
Before recovery revert only unpublished source/tests; never rewrite accepted owner Artifact, Progress, receipt, or Cloud acknowledgement.

## 24. Stop conditions
Stop for omitted-source use, identity/approved-byte drift, Capsule/migration mutation, Harness launch, Cloud conflict, or scope expansion.

## 25. Owner decisions
The Owner explicitly authorized this bounded contract repair and exact D1 recovery; no decision remains open.

## Authorization gate
`READY_FOR_IMPLEMENTATION_REVIEW`; `AUTHORIZED_FOR_D1_REVIEW_CONTRACT_01_ONLY`; no remaining pre-implementation blocker.

## Verification record
- Independence `LIMITED`. E1: all four contextual cases passed.
- E5 synthetic public root-run reproduced old failure, then published/uploaded once without Harness; replay was idempotent.
- Affected evidence: 174 tests plus 15 publication/preset/public-Workspace tests passed; the loopback case required its declared network permission.
- Compileall, diff check, immutable publication checks, and Alembic `20260818_0033` passed.
- E8 real D1: checksum-verified root client recovered via exact `run`. A stale runner with no Harness child was gracefully interrupted; its managed lock was never deleted.
- Exactly one local/Cloud v3 (`sha256:3947ffc512983121aeacf1ef7fbd4e42cae2507827d4b5b455a0f25d94e30cc8`), one accepted COMPLETED Progress, one receipt, no replay duplicate, and Review `Completed`.
- Preserved hashes: manuscript `e88f9de96fccc635a49f92c882c602e3022856eb7aca96303cd83e5ac00d1c80`; provenance `d3fdf59a1e9059d37a58c86b11e29a38fb6c1ef30ff09356605e96883130c014`; result `433a59f233675311cfab3e6445f5c6281c11991397101efcef23eb416749d3a8`; Owner review `edd81a907ae4195f340053bb044261c5b89458e448cfe021588d3931c76f5c4b`.
- Bindings remain manuscript + Literature; Idea/Experiment unbound; no Revision. E6/E7 not required or claimed. Status `PASS_AT_DECLARED_LEVEL`.
