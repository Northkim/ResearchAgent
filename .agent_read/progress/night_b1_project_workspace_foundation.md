# NIGHT-B1 Project Workspace Foundation Persistence

Date: 2026-08-06

Status: **PASS — OWNER REVIEW REQUIRED**

## Baseline and scope

The phase began on clean `main` at
`e880d40ec73f07198f7b064afd898982a3357e16` (`ARCH-D1: define project
workspace and workflow capsule contracts`). The obsolete dedicated worktree
was absent. The earlier worktree-gate block made no change and is not evidence.

Only the ARCH-D1 cloud persistence foundation was implemented. APIs,
frontend, Project Manifest mutation, Workspace files/bootstrap, sync, Capsule
delivery/installation, Progress contracts/behavior, Idea Discovery, Artifact
handoff/bytes, Resources, Skills, Provider behavior, production and R3D were
not implemented.

## Migration and entities

Migration `20260806_0008` directly follows sole prior head
`20260806_0007`. It adds exactly these four tables:

- `local_workflow_definitions`;
- `local_workflow_definition_versions`;
- `local_workflow_capsule_versions`;
- `project_workflow_instances`.

The namespace is separate from Hosted `workflow_definitions`, WorkflowRun,
StepRun and Artifact provenance. It stores no credentials, Provider keys,
local absolute paths, device state, execution state, concrete outputs or
Artifact bytes. The instance model deliberately has no unique constraint on
project plus Workflow Definition, so future same-type instances remain valid.

Downgrade removes only these four structures and leaves legacy rows unchanged.

## Deterministic compatibility

The accepted built-in seed is:

- stable workflow key: `LITERATURE_SEARCH`;
- Workflow Definition ID: `literature-search-local-experimental`;
- Workflow version: `0.3.0`;
- contract checksum:
  `sha256:efd338d84b33665da25118c7dce6927f62b231ff3bc73527f4132c7bcb410e7f`;
- compatibility Capsule version: `0.5.0`;
- Capsule ID: `capsule-0f827b56ed6c5ecf6634f5eee0171ead`;
- Capsule definition checksum:
  `sha256:0f827b56ed6c5ecf6634f5eee0171ead2b050910ed1c9223ad64c9d135267611`;
- trust: `TRUSTED_BUILT_IN_UNSIGNED`.

The two checksums reuse the accepted
`backend.workflow_packages.serialization.canonical_hash` implementation and
the committed Package schema/template/generator/Workflow constants. No
historical project Package checksum is recomputed or reinterpreted.

Legacy instance identity uses namespace
`85a011a0-88cd-54b9-a649-7ccc9ed2d966` and exact name rule
`legacy-workflow-instance/v1|project=<project_id>|workflow=LITERATURE_SEARCH`.
It excludes Package identity/checksum, timestamps, name and topic. Frozen
vectors cover all-zero and all-`f` project UUID payloads.

## Seed, backfill, repository and UoW

Migration and application reconciliation seed one reviewed built-in Workflow
Definition, its exact reviewed version, and one reviewed compatibility Capsule.
Equivalent content is idempotent; conflicting immutable content fails closed.

Every supported legacy LocalProject receives one deterministic active Workflow
Instance. A Project with a current Package receives the Capsule and legacy
Package compatibility reference; a Project without a Package remains valid
with nullable Capsule fields. Existing LocalProject fields and Progress rows
are not changed. Unsupported workflow values fail closed. No Hosted, Progress,
Artifact, local-session or execution row is created.

`WorkflowFoundationRepository` and `SQLAlchemyUnitOfWork` provide exact ID,
stable-key, definition-version, Capsule-version and Workflow-instance reads,
definition and project listings, canonical adds, conflict detection and
transaction rollback. Current LocalProject product services still use their
original repository and do not dual write.

## PostgreSQL qualification

A dedicated PostgreSQL 18.1 cluster bound only to `127.0.0.1` used two
databases containing `reagent_night_b1`. It did not use ProjectDB, the owner
V0.1 database or `.env`.

Qualified paths:

- empty base-to-`20260806_0008` upgrade;
- populated `20260806_0007` upgrade with Package/no-Package and Unicode legacy
  values;
- exact legacy SQL-value preservation;
- deterministic seed and UUIDv5 backfill;
- `0008 -> 0007 -> 0008` with stable identities and no duplicates;
- repository and UoW rollback;
- repeated reconciliation and immutable-content conflicts;
- physical PostgreSQL stop/start on the same data directory and repository
  reload;
- sole head/current `20260806_0008`; `alembic check` reported no drift.

Only the dedicated resources were used and stopped/removed during closure.

## Test evidence

- Phase 1 domain/service tests: `5 passed`.
- Phase 1 migration test: `1 passed`.
- Phase 1 PostgreSQL repository tests: `5 passed`.
- complete database tests: `41 passed`, zero skip.
- existing LocalProject tests: `11 passed`.
- Workflow Package tests: `75 passed`.
- Progress Report tests: `38 passed`.
- Local Session tests: `4 passed`.
- Cloud API Proxy/OpenAlex non-live tests: `233 passed`.
- full backend: `608 passed, 4 skipped`.
- compileall: exit 0.
- Alembic heads/current/check: sole `20260806_0008`, no drift.

The four full-suite skips are pre-existing integration tests requiring
separately authorized destructive E2E configuration or live OpenAlex. No new
or relevant PostgreSQL test skipped.

## Reliability and boundary audit

Credential reads, `.env` reads, external-network attempts, live Provider
calls, ProjectDB access, owner-database access, frontend changes, API route
changes, Workspace/sync implementation, Idea Discovery, Artifact-byte storage,
arbitrary Skill execution, third-party Capsule execution and Hosted execution
row creation were all zero.

Tracked-change scans found no password, token, bearer header, credential,
owner path, Package ZIP, database/data directory, runtime log, temporary file
or real research data.

## Commits and gate

- `b342e0ab686890694b0e95006ef0991b060d9afe` —
  `NIGHT-B1a: add local workflow foundation schema`;
- `4332ad2c936e12117832b46a8ebd1a16a12ac2d8` —
  `NIGHT-B1b: add workflow foundation repositories and backfill qualification`;
- the third and final commit is `NIGHT-B1c: qualify project workspace
  persistence foundation`; its exact self-referential Git identity is captured
  by final closure evidence rather than embedded in its own content.

`NEXT_PHASE_GATE = READY_FOR_OWNER_REVIEW` applies only to reviewing NIGHT-B1.
`IMPLEMENTATION_AUTHORIZED_FOR_LATER_PHASES = false`.

```text
NIGHT_B1_IMPLEMENTATION = PASS
WORKSPACE_FOUNDATION_PERSISTENCE = PASS
WORKFLOW_DEFINITION_PERSISTENCE = PASS
WORKFLOW_DEFINITION_VERSION_PERSISTENCE = PASS
CAPSULE_VERSION_PERSISTENCE = PASS
WORKFLOW_INSTANCE_PERSISTENCE = PASS
DETERMINISTIC_LEGACY_MAPPING = PASS
LEGACY_LITERATURE_SEARCH_SEED = PASS
LEGACY_PROJECT_BACKFILL = PASS
LEGACY_PRODUCT_BEHAVIOR_UNCHANGED = PASS
POSTGRESQL_QUALIFICATION = PASS
MIGRATION_DOWNGRADE_REUPGRADE = PASS
BACKEND_REGRESSION = PASS
PROHIBITED_SCOPE_ACTIVITY = ZERO
NEXT_PHASE_GATE = READY_FOR_OWNER_REVIEW
IMPLEMENTATION_AUTHORIZED_FOR_LATER_PHASES = false
```
