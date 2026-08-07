# NIGHT-B5 Multi-Workflow Progress and Project Navigation

Date: 2026-08-07

Status: **PASS — OWNER REVIEW REQUIRED**

## Baseline and recovered contracts

Work ran directly on clean `main` from accepted NIGHT-B4 final commit
`63f19b80310108c0d0dc1f4e6e5ea8ba3a3a56f6`; the commit was the current
history ancestor. No worktree or feature branch was created and nothing was
pushed. ARCH-D1 commit `e880d40ec73f07198f7b064afd898982a3357e16`, ADRs
0022 through 0024, B1-B4 implementations, Progress v0.1/v0.2 contracts,
Package/Capsule identity, upload/retry, projection/API conventions, and the
frontend route/component patterns were read before changes. No `.env`,
credential, owner database, ProjectDB, live Provider, or external network was
used.

## Identity and migration

Additive migration `20260806_0011` directly follows `0010`. It adds required
`workflow_instance_id` to `uploaded_progress_reports`, a Project/Instance
composite foreign key, and a deterministic history index. Historical reports
are assigned only to the frozen B1 Literature Search instance after validating
their LocalProject and Package identity. The migration preserves report IDs,
timestamps, stored JSON and exact bytes/checksums, artifact metadata,
idempotency, and every legacy Project/Package row. Missing or ambiguous binding
aborts the migration. Downgrade removes only the B5 field, key, and index.

New uploads validate exact Project/Instance ownership. B4 Capsules resolve by
their persisted Project/Instance artifact; the accepted standalone legacy
Package alone may resolve through its exact current Package binding and frozen
UUIDv5 rule. There is no first-instance fallback. Exact historical replay is
resolved before current Package lookup so response-loss recovery remains valid
even after a current Package replacement. PostgreSQL transaction advisory
locking preserves one canonical projection under concurrent idempotent retry.

## Derived read models and APIs

Workflow projection derives latest report, machine status, summary, stage,
next action, artifact metadata, first/latest activity and report count from
immutable history. Latest order is stable by report time, server time and
report/receipt identity. Retired instances keep independent history.

Project projection loads Project, Instances/Definitions, reports and
installation acknowledgements in fixed query groups rather than per-instance
queries. It returns active/retired counts, status counts, total reports, latest
activity, bounded paginated history and current Manifest revision. Lifecycle,
research progress, desired state and client-reported installation state are
separate; no completion percentage exists.

The frozen reads are implemented at:

- `GET /projects/{project_id}/progress`;
- `GET /projects/{project_id}/workflow-instances/{instance_id}/progress`.

The first supports stable offset/limit pagination and exact instance filter;
the second verifies Project membership. Existing Progress upload/history and
Literature Search result links remain compatible.

## Frontend

Project navigation is exactly Overview, Workflows, Progress and Help. Overview
uses the aggregate read model. Workflows renders Registry/Instance/Manifest/
Progress data, distinguishes same-definition instances with a short stable ID,
and keeps lifecycle/research/desired/install badges independent. Add and retire
reuse the B2 mutations with `base_revision`; a 409 refreshes state and never
starts local sync. Planned fixture behavior is disabled/non-creatable, while
production renders only actual Registry rows (currently Literature Search).

Progress supports exact-instance filtering and pagination and displays only
Artifact metadata. Help explains explicit `python reagent_local.py sync .`,
local file authority, acknowledgement semantics and the lack of backup. The
legacy `/guide` route remains. No empty Artifacts, Resources, Skills, Activity
or Settings navigation was added.

## Qualification

An isolated loopback PostgreSQL 18.1 cluster used port `55485` with dedicated
NIGHT-B1/B2/B4/B5 databases. Evidence:

- focused Progress identity/projection/API/repository tests: passed;
- migration qualification covering empty/populated upgrade, multiple Projects,
  multiple reports, no-progress Project, idempotent helper, fail-closed missing
  instance, downgrade and re-upgrade: passed;
- two-session PostgreSQL same-key/same-payload and same-key/different-payload
  concurrency: passed, including after PostgreSQL restart;
- fixed-query 20-Instance/1,000-report aggregation qualification: passed;
- full backend: `655 passed, 4 skipped`; the skips are exactly the four
  pre-existing destructive/external/live integration gates;
- frontend Vitest: `12` files / `19` tests passed; typecheck, ESLint and
  production build passed;
- backend compileall, sole Alembic head/current `20260806_0011`, Alembic
  no-drift and `git diff --check`: passed.

The first sandboxed loopback/full-suite attempt was environment-blocked before
database work. The first permitted retry used an incorrect guessed role and
was rejected before database mutation; the corrected isolated-loopback rerun
used the cluster's actual local test role and passed. The initial Turbopack
helper-port attempt was also sandbox-blocked; its permitted production-build
rerun passed.

Scenario qualification covered legacy backfill and routes; two same-definition
instances with isolated histories; retired history retention; registry-driven
add/retire plus revision-conflict refresh; and standalone exact retry after
response loss. Literature Search standalone/adopted/synced launch, Package
download, Progress, OpenAlex, B4 sync/Installed Lock/acknowledgement, current
frontend compatibility and Hosted AgentRuntime regressions passed unchanged.

## Boundary and commits

ADR 0025 records the Workflow-instance Progress identity and derived read-model
decision. No Artifact handoff/materialization, Artifact index, Idea Discovery,
Writing, Review, Experiment, Skills/Resources product, external resolver,
backup, background sync, browser local write, Hosted rewrite, new Workflow ID
or executable Capsule was implemented.

Commits:

- `34b480c` — `NIGHT-B5a: bind progress to workflow instances`;
- `f61d49f` — `NIGHT-B5b: add workflow board and project navigation`;
- final qualification/documentation commit: `NIGHT-B5c: qualify project
  workflow progress` (hash is recorded by final Git evidence rather than
  self-referenced here).

The next gate is owner review. NIGHT-B6 is not authorized by this record.
