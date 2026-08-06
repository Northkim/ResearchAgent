# NIGHT-B2 Workflow Catalog and Desired Project Manifest

Date: 2026-08-06

Status: **PASS — OWNER REVIEW REQUIRED**

## Baseline and recovered contracts

Work ran directly on clean `main` at B1 anchor
`6a7578b6d6d1da6cb1b97ef0bebf0b599a1ce349`; the anchor was an ancestor, no
worktree or branch was created, and nothing was pushed. ARCH-D1 commit
`e880d40ec73f07198f7b064afd898982a3357e16`, ADR 0022, all Project Workspace
design contracts, the three B1 commits, existing LocalProject/API/UoW/error
patterns, and the sole `20260806_0008` head were read before implementation.

Current local single-user Project routes have no independent account/owner
identity. B2 preserves that established authorization boundary rather than
inventing a parallel authentication system; project/instance scope mismatch
still fails closed. ARCH-D1 did not freeze IDs or executable versions for the
four planned Workflows, so production seed remains Literature Search only.
The catalog model and tests prove `PLANNED` entries are non-creatable without
fabricating future Capsule metadata.

## Persistence and migration

Migration `20260806_0009` directly follows `20260806_0008` and adds:

- `projects`, with one logical `workspace_id` and monotonic current revision;
- `project_desired_manifests`, immutable full snapshots keyed by Project and
  revision with canonical checksum and idempotency identity;
- `project_manifest_entries`, a typed Workflow Instance index over each
  snapshot.

Existing LocalProject rows remain unchanged. Each maps to its frozen B1 UUIDv5
Literature Search instance and one revision-1 Manifest/entry with exact
Workflow `0.3.0` and Capsule `0.5.0` pins. The backfill is deterministic,
idempotent, and fails transactionally if the B1 identity is missing or
conflicting. Downgrade removes only B2 tables/constraint and restores the exact
B1 no-Package nullable Capsule representation before re-upgrade.

## Catalog, instances, revisions and Project bridge

Active endpoints are:

- `GET /workflow-definitions`;
- `GET /workflow-definitions/{workflow_definition_id}`;
- `GET|POST /projects/{project_id}/workflow-instances`;
- `GET /projects/{project_id}/workflow-instances/{instance_id}`;
- `POST /projects/{project_id}/workflow-instances/{instance_id}/retire`;
- `GET /projects/{project_id}/manifest`.

Routers perform DTO/dependency/response mapping only. The application service
validates lifecycle, reviewed exact version/Capsule pins, project scope and
state transitions. Repositories own persistence and PostgreSQL compare-and-
swap. The database model deliberately has no unique Project+Definition rule,
so multiple same-definition instances work.

Create and retire require `base_revision`. A conditional PostgreSQL update on
`projects.current_manifest_revision` atomically advances it once. A stale base
returns HTTP 409 / `MANIFEST_REVISION_CONFLICT` including the current revision.
Failure rolls back the instance/state change, Manifest revision and entries.
Retire preserves identity/history and emits a `RETIRE` desired entry.

Legacy `POST /projects` remains request/response compatible and now atomically
stages LocalProject, canonical Project, frozen UUIDv5 Literature Search
instance, revision-1 Manifest and entry. Injected failure at instance,
Manifest and entry stages left no partial committed object. Existing Package,
Progress, Proxy/OpenAlex, frontend and Hosted behavior was not changed.

## Qualification

A temporary PostgreSQL 18.1 cluster bound only to `127.0.0.1:55439` used
databases named `reagent_night_b2` and `reagent_night_b1_compat`. It did not
use `.env`, ProjectDB or the owner persistent database.

Evidence:

- B2 destructive migration: `1 passed` (empty/populated upgrade, repeated
  backfill, missing-instance rollback, downgrade/re-upgrade);
- focused Workspace/LocalProject tests: `22 passed`;
- PostgreSQL two-session CAS/Project bridge: `1 passed`;
- B1 repository compatibility regression: `5 passed`;
- full backend with B1+B2 migration URLs and general PostgreSQL URL:
  `616 passed, 4 skipped`;
- compileall: exit 0;
- Alembic heads/current: sole `20260806_0009`;
- Alembic check: no new upgrade operations;
- physical PostgreSQL restart/repository reload: revision 1, one instance,
  Workflow `0.3.0`, Capsule `0.5.0` restored unchanged.

The four skips are unchanged separately gated integration tests: destructive
HTTP demo, OpenAlex contract, live OpenAlex, and research-v2 integration. No
new PostgreSQL, B1 or B2 test skipped.

## Boundary and commits

Credential reads, `.env` reads, external-network attempts, live Provider calls,
ProjectDB/owner-database access, frontend changes, Workspace files/sync,
Capsule installation, Installed Lock, Progress aggregation, Artifact handoff,
Idea Discovery, Skills/Resources, cloud LLM/Hosted execution and pushes were
all zero.

Commits:

- `be27695` — `NIGHT-B2a: add desired project manifest persistence`;
- `99da2c8` — `NIGHT-B2b: expose workflow catalog and instance APIs`;
- final qualification/documentation commit:
  `NIGHT-B2c: bridge project creation and qualify revision safety` (its hash is
  recorded by final Git evidence rather than self-referenced here).

The next possible phase is owner review of NIGHT-B2. NIGHT-B3 (Workspace
bootstrap, legacy Package adoption and Workspace identity) is not implemented
or authorized.
