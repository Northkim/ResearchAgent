# D1-REVISION-LIFECYCLE-01 bounded recovery change packet

> Completing this packet does not authorize implementation. The Owner's
> 2026-08-20 instruction separately authorizes this exact bounded repair.

## 1. Objective

Treat one exact, runner-owned Writing Revision Plan approval as a completed
lifecycle checkpoint so the public Workspace runner resumes at draft completion /
Owner review instead of rerunning planning and rejecting the existing approval.

## 2. Owner intent

Preserve the existing approved plan, validated revised manuscript, issue
dispositions, inputs, and causal lineage; record one exact final Owner review and
publish/upload the resulting v5 Artifact and terminal Progress exactly once.

## 3. User problem

Writing Revision 0.7 / Capsule 0.9 validates the current durable state, but its
single-pass Capsule runner always launches planning and then calls `_approve_plan`,
which treats an existing exact approval as a terminal error. The public root runner
does not currently dispatch this valid resume state before launching the Capsule.

## 4. Current baseline

`main` at `b8b5bcfde3f5c58d77bfe247c07a1d3782ed5f6f`, clean, one worktree,
Alembic sole head `20260819_0034`. D1 Revision
`wfi-7f5a9b0453485cada13412f8cb468073` is active 0.7/0.9 and locally
materialized. Its exact plan, plan approval, revised draft, claims, citations, and
issue accounting validate; Owner review, v5 Artifact, and terminal Progress are
absent.

## 5. Authoritative sources

Owner instruction and D1 evidence; project plan; ODR-008/009/010/011; ADR 0040
and 0048; immutable Revision 0.7 / Capsule 0.9 bytes; the installed Capsule
validator/runtime; public root runner in `workspace_cli.py`.

## 6. Conflicts

The public runner's single-pass control flow conflicts with the durable checkpoint
contract in ADR 0040. The existing approval and draft pass their published 0.9
validator. No immutable-content or product-intent conflict remains.

## 7. Scope

One exact root-run recovery dispatch for active Writing Revision 0.7/0.9, one
focused public-run regression, long-lived D1 recovery through the normal root
command, and governance handoff updates.

## 8. Non-goals

No Revision planning/drafting regeneration, Artifact/schema/Capsule/Definition
change, migration, frontend change, binding change, issue-disposition change,
upstream Workflow mutation, or repair to any other D1 finding.

## 9. Domain semantics

A valid plan approval binds the current plan, prior manuscript, causal Review,
issue set, and exact supporting context. It is a completed prior lifecycle phase,
not an instruction to seek another approval. A complete validated draft resumes at
exact final Owner review. Partial/ambiguous phase-two state fails closed.

## 10. State transitions

`exact plan approval + complete validated draft + no Owner review/terminal report`
--normal root run + exact Owner finalization--> `one Owner review + one v5 Artifact
+ one COMPLETED report` --existing backlog upload--> `Cloud Completed`.
Replay uses the existing report/Artifact identities and launches no Harness. If an
exact Owner review already exists after a crash, recovery verifies and reuses it.

## 11. Artifact impact

No schema change. One `manuscript-draft/v5` is produced from the already validated
draft only after exact Owner review. Existing upstream Artifact bytes are unchanged.

## 12. API impact

None. Existing Progress upload, Artifact admission/promotion, presentation, and
projection APIs are reused.

## 13. Persistence impact

None. No migration or direct database mutation.

## 14. Frontend impact

None. Existing projections render Completed after normal acknowledgement.

## 15. Security impact

Recovery requires regular unlinked files, the installed Capsule's exact input,
plan, approval, draft, claim/citation/accounting validators, and unchanged
role/Artifact/checksum lineage. Ambiguous partial state fails closed.

## 16. Cloud/local boundary impact

Local Workspace remains authority for approval, manuscript, Artifact, and Progress
bytes. Cloud receives only the established bounded report, Artifact metadata, and
presentation. Browser does not write Workspace state.

## 17. Compatibility and versioning

Unchanged-compatible public-run recovery dispatch. Published Definition 0.7,
Capsule 0.9, their checksums, and all historical versions remain byte-identical.

## 18. Migration impact

None; sole head remains `20260819_0034`.

## 19. Files expected to change

- `backend/project_workspaces/workspace_cli.py`
- one focused test under `backend/project_workspaces/tests/`
- this packet and `.agent_read/context.md`

Budget: at most 2 production/test files plus 2 governance files and 600 net lines.
Any Capsule, migration, frontend, or Artifact-contract file is scope expansion.

## 20. Rejected alternatives

Mutating Capsule 0.9; publishing a replacement that strands current durable state;
deleting/recreating approval; rerunning planning/drafting; editing the manuscript;
manual Progress/Artifact creation; direct SQL; or accepting incomplete phase-two
files.

## 21. Test design

Create a controlled 0.7/0.9 Capsule, let its runner create an exact plan approval
and complete draft but reject final Owner review, then invoke the public root run
with a Harness-launch sentinel. Assert unchanged checkpoint bytes, one exact Owner
review/Artifact/report/upload, no Harness, exact issue dispositions, and idempotent
replay. Run affected Revision, backlog, publication/checksum, compile, diff, and
Alembic-head checks; then recover the authorized long-lived D1 Workspace.

## 22. Acceptance criteria

All Owner-stated byte-preservation, exact-once finalization/upload, Completed state,
idempotency, and unrelated-Workflow requirements.

## 23. Rollback conditions

Before D1 recovery, revert only unpublished root-client/test changes. After accepted
recovery, never rewrite the Owner review, Artifact, Progress, receipt, or Cloud
projection; any further correction is forward-only.

## 24. Stop conditions

Stop for invalid approval/input/draft/accounting, partial ambiguous phase-two state,
unexpected existing terminal state, Harness launch on the complete-draft path,
upstream byte drift, duplicate Cloud identity, migration need, or scope expansion.

## 25. Owner decisions

The Owner explicitly confirmed the lifecycle defect and authorized this bounded
repair plus normal-path recovery. No additional decision is required.

## Authorization gate

`READY_FOR_IMPLEMENTATION_REVIEW`; `AUTHORIZED_FOR_D1_REVISION_LIFECYCLE_01_ONLY`.

## Verification record

Verifier independence is `LIMITED`: the implementing Codex session ran the checks.
The controlled public-root regression starts from a Capsule-runner-created exact
plan approval and complete draft, rejects final review, and then proves that root
recovery skips the Harness, preserves every prior checkpoint byte, records one Owner
review, creates one v5 Artifact and one terminal report, uploads once, and replays
without another prompt or duplicate. Focused affected tests passed 95 with four
declared PostgreSQL skips; the sole sandbox loopback denial passed separately 1/1
with loopback permission. The narrow contract/recovery batch passed 12/12. Python
compileall, diff check, historical publication tests, and Alembic sole head 0034
passed.

The committed root client was then installed through the normal Owner bootstrap
endpoint, preserving the prior root client outside the managed Workspace. A stale
pre-fix runner was proven to hold only the final-review prompt and was interrupted
without changing the protected plan, approval, draft, claims, citations, or issue
accounting. The normal public root command resumed the exact approved state without
launching a Harness, recorded one exact Owner review, produced one
`manuscript-draft/v5`, finalized one COMPLETED report, and received one verified
Cloud receipt. Cloud registered Artifact
`artifact-b3d844ba10575ee18e55f445b9dc333e` with content checksum
`sha256:0f9d00878424940c34c53cef1e6981d11c7f36bea347eb58d37c8fb8faf53e5f`.
The Project projection and `workflow list` both report Writing Revision Completed.
An immediate public-command replay produced no prompt and left local and Cloud
Artifact/Progress counts at exactly one. RR-001 remains ADDRESSED; RR-002 and RR-003
remain NOT_ADDRESSED. Package validation passes, and the prior plan, approval, draft,
claims, citations, accounting, bindings, and upstream Artifact identities remain
byte-identical.
