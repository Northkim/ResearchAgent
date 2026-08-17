# Engineering change packet — GEN-C generic Experiment publication

## 1. Identity and status

- Change ID / title: GEN-C / Generic Experiment publication and public Local Workspace path
- Author / date / baseline: Codex / 2026-08-17 / `da25a05ea8bd35817273f0d5b55718967720a3f2`
- Packet status: OWNER_AUTHORIZED_FOR_IMPLEMENTATION
- Implementation authorization: User explicitly authorized GEN-C only in the phase directive.

## 2. Intent and baseline

- Objective: immutably publish generic Experiment 0.6, Capsule 0.9, the exact reference Capability Skill, and `experiment-record/v4`; expose the existing Local Workspace sync/run/resume path through typed generic checkpoints.
- Current behavior: Experiment 0.5 / Capsule 0.8 / v3 is the frozen sklearn reference slice. GEN-A and GEN-B are separate commits and provide unpublished generic contracts and coordinator seams.
- Authorities: `docs/PROJECT_DEVELOPMENT_PLAN.md`, ADR 0043, the Owner phase directive, and the frozen GEN-A/GEN-B contracts.

## 3. Decisions and scope

- No source conflict was found. Owner authority fixes domain-agnostic Core, reviewed Capability authority, controlled-local execution, and the 0.6/0.9/v4 identities.
- In scope: additive forward publication, one migration, exact Capsule compiler/sync routing, one existing public command path, durable methodology/capability checkpoints, production v4 registry projection, and isolated qualification.
- Non-goals: GEN-D, frontend/API presentation, Cloud Artifact-presentation persistence, Path B, Full Research preset changes, D1 changes, dependency installation, or scientific execution.
- Deferred: downstream Writing/Review/Revision v4 consumption and final browser UX.

## 4. Contract behavior

- Domain semantics: Core models exact objective, generic methodology, Capability assessment/selection, approval/readiness, bounded handoff, evaluation lineage, result review, and v4 finalization. Capability-specific specification/evaluation remains opaque.
- State: public execution persists an exact local checkpoint receipt and resumes from local files, not chat history. Expected Owner/action boundaries are typed, not generic crashes.
- Artifact: adds production `experiment-record/v4`; v2/v3 remain unchanged.
- API: no new endpoint or response schema. Existing catalog/sync APIs expose the new immutable DB rows.
- Persistence: exactly one additive publication migration; no lifecycle schema change.

## 5. Product and safety boundaries

- Frontend: none.
- Security/privacy: no dynamic plugin discovery, network download, PATH scanning for scientific runtimes, dependency installation, secret persistence, or hostile-code sandbox claim.
- Cloud/local: Cloud stores immutable metadata and exact pins; Workspace receives the exact Capsule. Runtime paths and checkpoint bytes remain local.

## 6. Compatibility and delivery

- Classification: additive immutable Workflow/Capsule/Skill/Artifact publication.
- Migration: `20260817_0028`, reversible to `0027`, fail-closed on identity conflict.
- Historical versions: 0.4/0.7/v2 and 0.5/0.8/v3 are read-only regression subjects.
- Rollback: downgrade only the new 0.6/0.9 Skill pin/publication rows; never mutate historical rows.

## 7. Implementation budget

- Expected production/migration files: two new forward modules; additive edits to publication/compiler registry, sync, Workspace CLI, Artifact registry; one migration (at most 8).
- Tests: at most 5. Governance: this packet/progress report and context update (2).
- Total tracked files <=15 and net change <=2800 lines.
- Any checksum-bound edit, missing safe seam, required UI/API expansion, or budget overrun stops implementation.

## 8. Alternatives and verification

- Rejected: editing frozen v3 registry source, reusing the 0.5 runtime as generic Core, mutable plugin registry, dynamic discovery, new runner, preset advancement, or scientific dependency installation.
- Evidence: unit/integration tests; fake Harness and runner labeled separately; one real Codex methodology checkpoint; E4 isolated PostgreSQL migration; E5 Local Workspace sync/materialize/run/resume; historical checksum/archive regressions.
- Acceptance: exact immutable publication; generic unsupported result; supported reference selection; typed durable checkpoint; exact public sync; v4 controlled non-ML finalization; sole Alembic head 0028; no historical drift.
- Stop conditions: `PUBLICATION_EXTENSION_SEAM_GAP`, `IMMUTABLE_IDENTITY_CONFLICT`, `GEN_C_SCOPE_EXPANSION`, `HISTORICAL_IMMUTABILITY_REGRESSION`, or unsafe PostgreSQL isolation.

## 9. Authorization gate

- Packet approval: Owner phase directive supplies exact target contracts and acceptance gates.
- Explicit implementation authorization: GEN-C ONLY; work directly on `main`.
- Remaining blockers: none at packet creation.

## Implementation and verification record

### Implemented

- Published exact Definition `reproduction-experiment-local-experimental@0.6.0`
  and Capsule `0.9.0` through additive migration `20260817_0028`.
- Published the exact reviewed reference Capability Skill and exact pin; the
  synthetic non-ML Capability remains test-only.
- Added a forward Capsule compiler/runtime and routed the existing Workspace
  sync/run command to exact 0.6/0.9 pins.
- Added typed durable methodology/Capability checkpoints and resume without
  chat-history authority or startup runtime probing.
- Added a forward production registry seam for typed generic
  `experiment-record/v4`; the frozen historical registry source is unchanged.
- Left Full Research, D1, GEN-D, Path B, frontend/API presentation, Cloud
  lifecycle persistence, and scientific dependencies untouched.

### Exact publication identity

- Definition checksum:
  `sha256:5e91401ee48979ff1e61453c8e304565c9c35ab317d511fdb458b82347dff517`
- Capsule ID: `capsule-2a40aa6dd4668a734bb83c48fcbac088`
- Capsule checksum:
  `sha256:2a40aa6dd4668a734bb83c48fcbac0886659d7a4281b96d4b84296ce728a21fe`
- Skill checksum:
  `sha256:23a0c47e2acffafe6c8f821b049e7a645f4bc4e0d844bfc754bd078c0f4173b9`

### Verification evidence

- E4 PostgreSQL: a newly initialized, generated-name, marker-protected
  PostgreSQL 18 database upgraded base→0028; `5 passed` publication/reference
  assertions; 0028→0027 removed only 0.6 and preserved exact 0.5/v3; re-upgrade,
  `alembic check`, and server restart/readback returned exact final checksums.
  The named database was dropped, only `postgres`/`template1` remained in that
  isolated cluster, the server stopped, and its temporary directory was
  permanently removed. No Owner database was addressed.
- E5 controlled public Workspace: exact catalog recommendation, Instance create,
  bootstrap/sync, Skill pin install, selected-Idea binding/materialization,
  preflight, fake-Harness `DESIGN_APPROVAL_REQUIRED`, and byte-identical durable
  resume passed. This is fake Harness evidence, not Real Codex evidence.
- E7 real Codex: installed Codex, invoked through the test-only noninteractive
  adapter, read the exact isolated selected Idea and generic Capability set,
  wrote Methodology v0.2, preserved the real unresolved interpretation choice,
  and stopped at `METHODOLOGY_DECISION_REQUIRED`; JUnit reported `1 passed` in
  227.722 seconds. No preparation directory or experiment execution occurred.
- E2 fake runner/non-ML: the GEN-B synthetic lifecycle proves non-Python runtime,
  zero/multiple Resource and dependency shapes, one-use approval/handoff,
  textual Capability evaluation, result review, and generic v4 finalization.
- Aggregate non-database backend partitions: `946 passed, 5 skipped`. The normal
  GEN-C/GEN-A/GEN-B slice is `34 passed, 1 skipped`; the skip is the explicit
  opt-in E7 test that passed separately. Historical affected slice is `67
  passed` under the reviewed macOS no-egress boundary. Final isolated database
  slice is `5 passed`.
- Compile-from-source, dependency/import scan, package/archive validation,
  `git diff --check`, and sole Alembic head `20260817_0028` passed.

### Historical integrity

Experiment 0.5 Definition/Capsule remain exactly
`sha256:23b6e3cae5746c8589927d2380595df61d01c6fb3f487cf47e09753f3ef8b600`
and
`sha256:5e02c832357355b6036b7e21cfbae3061306b16268d04ee75c764c56c759bd98`.
Every recovered Capsule 0.8 source blob and migration 0027 blob matches the
GEN-B baseline. Historical 0.4 no-egress, truthful failure, v2, and exactly-once
tests passed. No historical publication byte changed.

### Evidence assessment

Acceptance is PASS for the authorized controlled-local publication scope.
Evidence levels are E4 for migration, E5 for the controlled public Workspace,
E7 for the real Codex methodology checkpoint, and E2 for fake-runner scientific
lifecycle completion. Verifier independence is LIMITED because implementation
and verification occurred in the same agent session. There is deliberately no
real scientific execution, sklearn runtime qualification, final browser UX, or
long-lived Owner Workspace evidence.
