# Engineering change packet — GEN-D Owner UX and Cloud presentation

## 1. Identity and status

- Change ID / title: GEN-D / Generic Experiment Owner UX and Cloud presentation
- Author / date / baseline: Codex / 2026-08-17 / `11fc22159203513332779d15679a01e4fdda314a`
- Packet status: OWNER_AUTHORIZED_FOR_IMPLEMENTATION
- Implementation authorization: the Owner explicitly authorized GEN-D only.

## 2. Intent and baseline

- Objective: make published Experiment 0.6 understandable to a research Owner and
  report/render an exact bounded `experiment-record/v4` presentation companion.
- Current behavior: 0.6/0.9/v4 is exact and recommended, but Workflow Detail is a
  generic orchestration page and Cloud has no result presentation payload.
- Authorities: project plan, ADRs 0026/0028/0043, ODR-009/010/011, the GEN-D
  directive, and frozen GEN-A–C contracts.

## 3. Decisions and scope

- Conflicts: none. Browser-local writes remain prohibited; Local owns Artifact
  bytes; Cloud may receive bounded typed presentation metadata only.
- Persistence decision: `ADD_TYPED_ARTIFACT_PRESENTATION_PERSISTENCE`. The
  existing exact Artifact Reference is the correct carrier, but currently lacks
  schema/checksum/payload fields. Add one generic nullable, all-or-none,
  first-write-immutable presentation companion to that row. Do not add a table.
- In scope: exact reporting API, strict v0.2 validation, Artifact-list projection,
  task-first Experiment 0.6 detail/results UX, generic primitives, and controlled
  browser qualification.
- Non-goals: Path B implementation, downstream v4 consumers, Full Research pins,
  D1, Terminal redesign, scientific dependencies/execution, or historical UX
  reinterpretation.
- Deferred: browser approval mutations, arbitrary local output preview, final
  Companion architecture, and Writing/Review/Revision compatibility.

## 4. Contract behavior

- Domain semantics: primary UX shows objective, start choice, scientific design,
  preparation/readiness, exact-run explanation, evidence, limitations, and next
  action. Technical identities remain in one secondary disclosure.
- Transition: absent presentation → exact first report → immutable present.
  Exact replay is idempotent; changed presentation, wrong Artifact checksum/type,
  invalid schema/content/size, or cross-Project identity fails closed. There is no
  delete/update transition.
- Artifact impact: `experiment-record/v4` bytes remain local and unchanged;
  `reagent.artifact-presentation.experiment-record/v0.2` binds exact Artifact ID
  and checksum.
- API impact: add one bounded PUT reporting operation and include the optional
  validated companion in existing Artifact metadata responses.
- Persistence impact: four nullable generic presentation columns on
  `local_artifact_references`, with all-or-none and checksum constraints.

## 5. Product and safety boundaries

- Frontend: specialize only exact Experiment 0.6; historical and non-Experiment
  instances keep the existing detail page. Outputs renders v4 content directly.
- Security/privacy: <=65,536 canonical bytes; strict primitive shapes; reject
  code/HTML, private paths, credentials, logs, non-finite values, arbitrary file
  paths, and wrong/stale binding. No Artifact/package/source bytes are accepted.
- Cloud/local: Local explicitly reports metadata; Cloud validates and stores it;
  browser only reads Cloud state and never writes Workspace files.

## 6. Compatibility and delivery

- Classification: additive compatible Artifact metadata/API response extension
  plus Experiment-0.6-only frontend specialization.
- Migration: exactly one additive `20260817_0029`, reversible to 0028.
- Historical: 0.4/0.7/v2, 0.5/0.8/v3, and 0.6/0.9/v4 publication bytes are
  immutable and not edit targets.
- Rollback: remove only new nullable presentation columns and forward UI/API code;
  never rewrite Artifact or historical publication rows.

## 7. Implementation budget

- Production files <=10: Artifact contracts/port/service, ORM/repositories,
  Artifact API schema/router, Workflow Detail, and Outputs.
- Migration files: 1. Test files <=3. Governance files <=2.
- Total tracked files <=16; net changed/added lines <=3000.
- Any Capsule 0.9 source edit, Path B implementation, downstream consumer, or
  material file expansion stops as `GEN_D_SCOPE_EXPANSION`.

## 8. Alternatives and verification

- Rejected: Hosted `ArtifactORM.metadata_json` (wrong architecture); Progress
  context metadata (wrong immutable identity); raw Artifact upload; new
  Experiment-only table; browser Workspace reads; modifying Capsule 0.9.
- Verification: contract/API/in-memory tests; disposable PostgreSQL
  0028→0029→0028→0029; frontend fixtures for non-ML and sklearn shapes;
  typecheck/lint/build; controlled real-API browser interactions/screenshots;
  historical detail/Outputs/Activity regressions; compile/diff/checksum scans.
- Acceptance: exact immutable binding, safe primitives, absent/present preview,
  clear first-page Path A/B truth, lifecycle/evidence separation, one local action
  area, responsive/accessibility baseline, and no historical/D1/downstream drift.
- Stop conditions: unsafe carrier semantics, migration conflict, browser-local
  mutation, historical byte change, scope expansion, or unavailable browser gate.

## 9. Authorization gate

- Packet approval: the detailed Owner GEN-D directive fixes the product and
  persistence decision criteria.
- Explicit implementation authorization: GEN-D ONLY, direct on `main`.
- Remaining blockers: none at packet creation.

## Implementation and verification record

### Implementation

- Selected `ADD_TYPED_ARTIFACT_PRESENTATION_PERSISTENCE`: four nullable,
  all-or-none columns extend the existing exact Artifact Reference row. No new
  Experiment table or raw Artifact byte carrier was added.
- Added one immutable `PUT` report path for
  `reagent.artifact-presentation.experiment-record/v0.2`. Exact replay is
  idempotent; changed, stale, cross-Artifact, malformed, oversized, credential,
  code, log, HTML, and private-path content fails closed.
- Specialized only exact Experiment 0.6 Workflow Detail. The first content is
  the research objective and the first decision is the truthful Path A/Path B
  choice. Path B is visible, disabled, and does not route to 0.4.
- Added domain-neutral methodology, preparation, Resource/runtime, exact-run,
  evidence, review, local-handoff, and Technical details sections. Outputs now
  renders bounded v4 findings rather than an Artifact shell.
- Added safe PROSE, SCALAR, TABLE, SERIES, FIGURE_REFERENCE, and
  OUTPUT_REFERENCE rendering. SERIES includes an accessible table fallback.
- Corrected the production readiness head from stale `0026` to `0029` and
  requires the already-published exact Experiment 0.6/Capsule 0.9 pair.

### Verification packet

- `VERIFIER_INDEPENDENCE = LIMITED`.
- E1/E3: presentation contract/service/API negative and replay tests pass;
  Workspace clients omit absent optional presentation fields and retain exact
  historical descriptors.
- E4: marker-protected disposable PostgreSQL
  `reagent_qualification_53d76b71dfc84c9d8881d7c3f5c67caf` upgraded
  base→0029, passed Alembic check, 0029→0028→0029, schema constraints,
  persistence/readback, and cleanup: `20 passed`.
- Frontend: `17 files / 50 tests`, typecheck, ESLint, and production build pass.
  Non-ML categorical and sklearn-shaped fixtures use the same renderer.
- Backend non-database-required partition: `970 passed, 63 skipped`; the two
  legacy mandatory-PostgreSQL modules were intentionally excluded from this
  partition and the affected PostgreSQL slice passed separately.
- Historical macOS no-egress Experiment 0.4 slice: `9 passed`. Generic
  Workspace regression: `4 passed`. Capsule/source/migration files compare
  byte-for-byte with `HEAD`; no historical publication file changed.
- Compileall, `git diff --check`, sole Alembic head `20260817_0029`, and
  sklearn/KNN/Wine/NumPy terminology scan of generic presentation code pass.

### Evidence limitation

The real controlled backend/frontend started against a marked disposable
database and seeded fresh, methodology-required, unsupported, and completed-v4
states. The required in-app Browser runtime then reported no available browser
session. Per the Browser and evidence policies, component tests are not a
substitute for E6. The disposable application processes, database, and runtime
directories were removed. Final verification status is
`BLOCKED_ENVIRONMENT` / `PASS_WITH_UNQUALIFIED_LEVELS`, not an unqualified
GEN-D completion PASS. Owner UX and long-lived Workspace evidence are also not
claimed.
