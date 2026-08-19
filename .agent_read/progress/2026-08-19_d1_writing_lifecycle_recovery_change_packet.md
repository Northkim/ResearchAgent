# D1-WRITING-LIFECYCLE-01 bounded recovery change packet

> Completing this packet does not authorize implementation. The Owner's
> 2026-08-19 instruction separately authorizes this exact bounded repair.

## 1. Objective

Restore upload-only recovery for an already-finalized Initial Writing 0.5 /
Capsule 0.7 round by routing readiness through its published Real Writing
provenance semantics instead of Scaffold provenance.

## 2. Owner intent

Preserve the exact reviewed manuscript, Owner decision, input bindings, and
COMPLETED Progress Report, then use the existing backlog path to acknowledge
those immutable local results without launching the Harness again.

## 3. User problem

The shared readiness evaluator accepts the exact local Progress/output chain,
then incorrectly asks forward Initial Writing for `workflow/scaffold.json` and
`reagent.scaffold-input-provenance/v0.1`. The valid Real Writing completion is
therefore labelled `LOCAL_PROGRESS_INVALID` before backlog recovery can run.

## 4. Current baseline

`main` at `47cc511df6456a998910f310ca9bc21bddb60e8d`, clean, one worktree,
Alembic sole head `20260818_0033`. The real D1 Writing Workflow is locally
finalized but has no Cloud acknowledgement; Review has not run.

## 5. Authoritative sources

- Current Owner instruction and D1 evidence.
- `docs/PROJECT_DEVELOPMENT_PLAN.md` and ODR-005/009/010/011.
- ADR 0038 Real Writing provenance and exactly-once Progress semantics.
- Published Initial Writing 0.5 / Capsule 0.7 descriptor
  `workflow/real-writing.json` and provenance schema
  `reagent.real-writing-input-provenance/v0.1`.
- Shared recovery in `backend/project_workspaces/workspace_cli.py`.

## 6. Conflicts

The family-wide fallback to Scaffold provenance conflicts with the exact
published Initial Writing identity. Immutable Capsule bytes and the generic
Progress chain are consistent; no source-of-truth conflict remains.

## 7. Scope

One exact readiness-dispatch correction for Initial Writing 0.5 / Capsule 0.7,
one focused upload-only recovery regression, and the required governance
record updates.

## 8. Non-goals

No repair to Review, Revision, Experiment, Literature, Idea, materialization,
bindings, approvals, Artifact bytes, Progress bytes, frontend, migration, or
any other D1 finding.

## 9. Domain semantics

Forward Initial Writing is REVIEWED_CORE Real Writing. Its package validator
validates `workflow/real-writing.json`, exact Real Writing input provenance,
and materialized bytes. It is not a Scaffold Workflow.

## 10. State transitions

`valid local COMPLETED + Cloud missing` --owner invokes normal root run-->
`existing report/artifact uploaded and exact receipt stored` --> `Completed`.
The report ID/checksum is the idempotency authority. Failure leaves immutable
local state pending and retryable. No Harness transition is legal on this path.

## 11. Artifact impact

None. The existing `manuscript-draft/v4` bytes and checksum remain unchanged;
the existing declaration is promoted through the existing upload envelope.

## 12. API impact

None. Existing Progress upload, Artifact promotion, and projection APIs are
reused.

## 13. Persistence impact

None. No migration or row surgery.

## 14. Frontend impact

None. Existing projections should become truthful after Cloud acknowledgement.

## 15. Security impact

No trust relaxation, network widening, credential handling, or arbitrary-file
acceptance. Exact package, Progress, output, and Real Writing validation remain
fail closed.

## 16. Cloud/local boundary impact

Local manuscript bytes remain authoritative. Cloud receives only the existing
bounded Progress upload and Artifact reference/presentation path already
authorized by the product.

## 17. Compatibility and versioning

Unchanged-compatible dispatch repair. Historical publications and all package
checksums remain immutable.

## 18. Migration impact

None; sole head remains `20260818_0033`.

## 19. Files expected to change

- `backend/project_workspaces/workspace_cli.py`
- one focused test under `backend/project_workspaces/tests/`
- this progress packet and `.agent_read/context.md`

## 20. Rejected alternatives

Editing Capsule files, regenerating the manuscript/report, weakening Scaffold
comparison, manually uploading database rows, special-casing the real D1 IDs,
or launching Writing again.

## 21. Test design

Build/finalize an exact forward Initial Writing Capsule, leave Cloud empty,
invoke the public root run with a Harness-launch sentinel, assert upload-only
completion/receipt, unchanged final bytes, and idempotent no-duplicate replay.
Run focused existing readiness/backlog/forward Writing regressions plus compile,
diff, and Alembic-head checks.

## 22. Acceptance criteria

The Owner's stated unchanged-byte, exactly-once Cloud receipt/projection,
Completed workflow-list, Review-not-run, and unrelated-Workflow requirements.

## 23. Rollback conditions

Before delivery, revert only this source/test repair. Never roll back or rewrite
the recovered Owner Artifact, Progress, receipt, or Cloud acknowledgement.

## 24. Stop conditions

Stop if Real Writing requires Scaffold semantics, existing bytes fail their
published validator, recovery would launch a Harness, Cloud history conflicts,
review state changed, or scope expands beyond the named files.

## 25. Owner decisions

The Owner explicitly confirmed the root cause and authorized this bounded
repair plus recovery. No additional product decision is required.

## Verification record

- Verifier independence: `LIMITED` (implementing agent); the real D1 recovery
  is `LONG_LIVED_WORKSPACE` / E8 evidence and retains the prior Owner-observed
  E9 failure as the trigger.
- `UNIT` / `CONTRACT` / `FAKE_HARNESS`: the new forward Writing fixture proves
  exact Real Writing dispatch, upload-only recovery, a Harness-launch sentinel,
  unchanged final bytes, exact receipt, and idempotent replay.
- Focused affected regression: 85 passed in the sandboxed batch. Its only
  failure was the sandbox denying a temporary loopback bind; that exact
  `PUBLIC_WORKSPACE_COMMAND` test passed 1/1 with loopback permission.
- Python compileall, `git diff --check`, and Alembic sole head
  `20260818_0033` passed.
- Real D1 public path: the checksum-verified downloaded root client ran
  `python reagent_local.py run . --workflow writing-local-experimental` twice.
  The first accepted the existing report/Artifact and stored the acknowledgement;
  the second proved idempotency. Neither invocation launched Writing.
- Cloud result: exactly one accepted report, one promoted
  `manuscript-draft/v4`, `research_status=COMPLETED`, and one verified local
  acknowledgement. Review remains `NOT_STARTED` with zero reports and zero
  Artifacts.
- Preserved local hashes: manuscript
  `e88f9de96fccc635a49f92c882c602e3022856eb7aca96303cd83e5ac00d1c80`,
  Owner review `8c5d81fa7271767a210188107516eeaad823288ddc97523b898296a26c304e51`,
  Progress file `ff685fe22fd99f0518bfa49cdc0ce92dc638b386442ea4b34904c7c0aab934e1`,
  and input provenance
  `a10cb495e08aed95cadcec9e35899d72a7548035f5a71d8efd2b9b7fcc6819e5`.
- Status: `PASS_AT_DECLARED_LEVEL`; no E6/E7 rerun was needed or claimed.
