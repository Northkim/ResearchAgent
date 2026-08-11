# Owner Manual Test Infrastructure Defect Repair — Controlled Database Isolation

Date: 2026-08-11

Status: PASS — OWNER MAY RESUME THE EXISTING LITERATURE TEST

## Classification

- `OWNER_TEST_DEFECT_ID = CONTROLLED_TEST_DATABASE_ISOLATION`
- `OWNER_TEST_SEVERITY = P1_TEST_ISOLATION`
- `OWNER_TEST_DEFECT_REPAIR = PASS`
- `MIGRATION_REQUIRED = NO`

This is test-harness and operator-documentation hardening only. It does not
change Workflow semantics or Artifact, Skill, Resource, Progress, database, or
owner Project/Workspace contracts.

## Root cause

Manual `make controlled-start` intentionally resolves `REAGENT_DATABASE_URL`
from the exported environment or ignored repository `.env`. Playwright H1/F1F
qualification then targeted the already-running frontend/backend and used the
real Create Project API without overriding that runtime database. Its teardown
removed only temporary local Workspace files. The Cloud Project rows therefore
remained in `reagent_local_v01`.

Separately, the shared PostgreSQL fixture trusted any explicit
`REAGENT_TEST_DATABASE_URL` at migration head before issuing
`TRUNCATE ... CASCADE`. Dedicated migration-cycle tests likewise trusted their
URL variables. No generated disposable identity or persisted marker proved
that the selected database was safe to destroy.

## Repair

- Added a single fail-closed disposable PostgreSQL identity validator.
- Protected `reagent_local_v01`, `ProjectDB`, and `reagent` are rejected before
  connection; arbitrary names containing `test` are also rejected.
- Allowed targets must match `reagent_qualification_<32 hex>`, contain the
  exact marker schema/name/identity row, and report the same connected database.
- Runtime and destructive-test URLs are independently connected and verified
  against the same per-execution identity.
- Destructive shared, Proxy, OpenAlex Proxy, and dedicated migration fixtures
  invoke the guard before truncation, downgrade, or test mutation.
- The isolated qualification helper creates, marks, migrates, runs, revalidates,
  terminates connections to, and drops only one exact generated database.
- Current local, H1, and F1F Playwright tests have a before-all database safety
  preflight. The Make E2E and full PostgreSQL backend entries use the helper.
- Manual `make controlled-start` remains unchanged and accepts the explicitly
  selected persistent owner database.

## Owner database proof

Bounded read-only snapshots of `reagent_local_v01` showed:

- Project count before: 8
- Project count after: 8
- owner Project present before: YES
- owner Project present after: YES
- `H1 controlled product journey` rows before: 2
- `H1 controlled product journey` rows after: 2
- generated qualification databases remaining: 0

The real owner Project and both H1 forensic marker Projects were left untouched.

## Qualification

- protected-name and startup-config tests: `21 passed`;
- full backend on a generated PostgreSQL database: `789 passed, 14 existing skips`;
- current local/H1/F1F Playwright route: `4 passed`;
- frontend Vitest: `17 files / 34 tests passed`;
- frontend ESLint: passed;
- compileall, shell syntax, Alembic sole head and `git diff --check`: passed.

The successful backend and browser qualification databases were each printed,
marker-verified, and dropped. A deliberately rejected owner-database fixture
attempt failed before connection/mutation. No new skip was introduced.

## Owner recovery

The owner controlled backend/frontend restart reached `/ready` during
qualification cleanup, but the tool-managed process session did not persist;
its stale runtime records were removed with the bounded `make stop`. The owner
only needs the normal `make controlled-start` restart. No client download,
sync, re-bootstrap, Project recreation, Workspace recreation, or search replay
is needed. The next action is `OWNER_RESUME_EXISTING_LITERATURE_TEST`.
