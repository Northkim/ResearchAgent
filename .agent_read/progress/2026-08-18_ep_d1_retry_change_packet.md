# EP-D1 retry engineering change packet

> Completing this packet does not authorize implementation. The Owner's
> 2026-08-18 EP-D1 retry instruction separately authorizes this bounded work.

## 1. Objective

Publish the forward Local Workspace chain from exact materialized
`experiment-record/v5` through Initial Writing, Review, and a new causal Writing
Revision without changing the five-Workflow product model.

## 2. Owner intent

Make materializable v5 bounded scientific evidence usable by the reviewed local
Writing and Review methods while keeping Cloud coordination, exact Artifact
handoff, Codex Harness execution, and Owner checkpoints intact.

## 3. User problem

Historical downstream versions accept only `experiment-record/v2`; their frozen
schemas cannot preserve v5 validity, sufficiency, claim boundaries, limitations,
or exact evidence-block grounding.

## 4. Current baseline

`main` at `7258665b862391a80d9f22283dd9052db0e9f4bd`, clean, one worktree,
Alembic sole head `20260818_0031`. GEN-D and EP-D0 are accepted; D1 is paused.

## 5. Authoritative sources

- `docs/PROJECT_DEVELOPMENT_PLAN.md` and active Owner instructions.
- Historical reviewed contracts and runtimes in
  `backend/artifact_references/research_flow_contracts.py` and
  `backend/workflow_packages/{real_writing,real_review,writing_revision}_*.py`.
- v5 authority in `generic_experiment_v5_contracts.py` and EP-D0 publication.
- Exact binding/materialization and Workspace authorities under
  `backend/project_workspaces/`.

## 6. Conflicts

The immutable reservation in `research_flow_contracts.py` names v3. It is stale
planning authority and checksum-bound; it will remain unchanged. A new forward
module will publish the Owner-approved v5 lineage. No scientific-semantics
conflict was found.

## 7. Scope

New version-specific downstream schemas, compiler overlay, registry wiring,
role-aware additive publication, one migration, exact Workspace/CLI routing, and
focused E1-E5/E7 qualification.

## 8. Non-goals

No frontend, EP-D2, Full Research preset, D1, Path B, Terminal redesign, Cloud
research execution, new provider, or presentation authority.

## 9. Domain semantics

Historical two-checkpoint Writing/Review/Revision methods remain authoritative.
Forward claims additionally bind exact v5 evidence blocks and preserve process
outcome, evaluation validity, evidence status, claim-boundary references, and
limitations. Descriptive observations remain distinct from bounded scientific
claims.

## 10. State transitions

Each role retains INPUT_REVIEW through its historical planning/scope approval,
Harness work, final Owner review, immutable finalization, and COMPLETED states.
Retries recover durable Capsule files; completed finalization is idempotent. Review
creates a separate exact Revision instance through the existing generic manifest
operation; it never mutates the parent Draft.

## 11. Artifact impact

Add incompatible forward successors `manuscript-draft/v4`, `review-report/v3`,
and `manuscript-draft/v5`. Historical validators and bytes remain unchanged.

## 12. API impact

No new API. Existing explicit instance creation, exact binding, materialization,
Progress, and Artifact publication APIs are reused.

## 13. Persistence impact

One additive publication migration after 0031; no ORM schema or content storage.

## 14. Frontend impact

None.

## 15. Security impact

No network widening or new secrets. Inputs stay read-only and exact; no sibling
reads, presentation lookup, browser Workspace writes, raw logs, or private paths.

## 16. Cloud/local boundary impact

Cloud stores coordination and Artifact metadata only. Full manuscript/review bytes,
materialized v5, reasoning, checkpoints, and final packages remain Local.

## 17. Compatibility and versioning

Three new incompatible Artifact versions and three additive Definition/Capsule
versions. Initial Writing 0.5 and Review 0.4 may be role recommendations;
Writing 0.6 stays revision-only through `default_project_setup=false`.

## 18. Migration impact

Additive Definition, Capsule, Skill pin, requirement, and Artifact-contract
publication only. Downgrade removes only exact forward identities.

## 19. Files expected to change

At most 12 production/migration files, six tests, and two governance records;
18 tracked files and 3,200 net lines total. Expected seams: one forward contract
module, one forward compiler/publication module, Artifact registry, production
catalog/service, sync, CLI, one migration, focused tests, context/progress.

## 20. Rejected alternatives

Mutating historical v2/v3 code; consuming Cloud presentation; automatic latest
selection; converters; sibling reads; a second binding system; hosted execution.

## 21. Test design

E1 validators and claim grounding; E2 compiler/runtime and recovery; E3 exact
binding/application; E4 disposable PostgreSQL migration; E5 public Workspace with
injected Harness; E7 real Codex to first genuine Owner checkpoint for all roles.
Historical closure and checksums are regression gates.

## 22. Acceptance criteria

All three publications exist, v5 is the only forward Experiment role, evidence
qualification survives every hop, causal Revision is exact and new, public Local
Workspace and recovery pass, real Codex stops truthfully, historical identities
pass, repository is committed and clean.

## 23. Rollback conditions

Before publication, revert only this packet's forward files. After immutable
publication, use a new forward repair version; never rewrite published identities.

## 24. Stop conditions

Stop on semantic-contract gap, historical checksum drift, identity conflict,
role-recommendation gap, migration/persistence expansion, unavailable required
verification, or scope above 18 files/3,200 lines.

## 25. Owner decisions

The Owner explicitly authorized EP-D1 retry, exact v5 evidence authority, the
three reserved forward identities, one additive migration, role-aware publication,
and the stated budget. No further Owner decision is currently required.

## Verification record

- E1/E2: forward validators, exact v5 claim grounding, wrong-version negatives,
  compiler overlays, injected-Harness full chain, checkpoint recovery, one final
  Artifact per instance, and terminal replay rejection pass.
- E3/E5: a fresh disposable Project/Workspace passed supported sync, explicit exact
  binding, refresh/materialization, copied public CLI preflight, and repeated
  `NO_CHANGE` sync for all three roles.
- E4: marked database `reagent_qualification_509852ebedd14777a457beb40d25a3f7`
  passed fresh upgrade, publication/checksum/role assertions, Alembic check,
  downgrade/re-upgrade, restart/readback, conflict rejection, and cleanup.
- E7: real Codex stopped at exact Outline, Review Scope, and Revision Plan Owner
  checkpoints. It preserved unavailable/planned/limited evidence and an unresolved
  Review issue; no Owner decision or finalization was supplied.
- Historical Writing 0.3, Review 0.3, Revision 0.4, Experiment v5 Workspace,
  production publication, and controlled-local approval regressions pass.

Verifier independence is LIMITED: the implementing agent ran the verification;
real Codex supplied independent interactive checkpoint behavior. No E6, Owner D1,
or full-Q1 claim is made.
