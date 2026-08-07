# NIGHT-B6 Typed Artifact Reference and Explicit Materialization

Date: 2026-08-07

Status: **PASS — OWNER REVIEW REQUIRED**

## Baseline and recovered contracts

Work ran directly on clean `main` from accepted NIGHT-B5 final commit
`d5629c21f38bb96e2c8644395b9ce22054f4b038`; the commit was the current
history ancestor. The repository has one worktree and no branch/worktree was
created. ARCH-D1 commit `e880d40ec73f07198f7b064afd898982a3357e16`, ADRs
0022–0025, B1–B5 implementations, current Progress Artifact metadata,
Literature Search outputs, Capsule compatibility, Workspace/Installed Lock,
filesystem protections and API/repository conventions were read before
changes. No `.env`, credential, ProjectDB, owner database, live Provider or
external network was used.

The design has one local-product Artifact Reference model, but its Literature
examples are not a ratified production type. The accepted Literature Search
Capsule has no frozen `artifact_outputs` type declaration. Historical Progress
metadata lacks a reliable Artifact type/schema identity, so it remains
unchanged and is not guessed into canonical Artifact rows.

## Persistence and Progress integration

Additive migration `20260806_0012` directly follows `0011`. It adds:

- `local_artifact_references`, with exact Project, producer Instance,
  producing Progress receipt/report/round, Capsule pin, type/schema/media,
  output path, immutable checksum/size and lifecycle;
- `workflow_artifact_requirements`, keyed by exact Workflow Definition Version
  and requirement key;
- `project_artifact_dependency_bindings`, binding one Project/consumer/input
  slot to one exact Artifact and expected checksum;
- the composite Progress producer key needed for a cross-table exact FK.

Composite Project/Instance, Project/Artifact and Progress/producer FKs prevent
cross-Project and cross-Instance spoofing. Active requirement uniqueness,
idempotency uniqueness, state/cardinality/size checks and deterministic query
indexes are PostgreSQL-native. Downgrade removes only B6 structures and the B6
Progress key. No production row is seeded and no historical Progress row is
rewritten.

Progress upload accepts additive typed declarations. Promotion occurs in the
same UoW only when the exact producer Capsule declares a matching reviewed
output contract and the declaration exactly matches immutable Progress output
metadata. Exact retry returns one canonical Artifact set; changed declarations
raise the existing Progress idempotency conflict and roll back both Progress
and Artifacts. Cloud stores metadata only and never claims to verify bytes.

During full PostgreSQL regression an existing concurrent invalid-first report
race was exposed. Retained rejected audit evidence could incorrectly reserve a
content-addressed identity and reject the later valid canonical report. The
service now treats only accepted rows as authoritative for report-ID/checksum
collision checks while preserving exact rejected retry and every rejected
audit row. The isolated Progress suite and full backend pass with this fix.

## Dependency and API contracts

Consumer requirements declare exact type/schema/cardinality/materialization
policy on an immutable Workflow Definition Version. A binding selects one
specific Artifact; no “latest” lookup exists. Producer and consumer must share
the Project, the consumer must match the declared Definition Version, and the
Artifact must be lifecycle/type/schema/checksum compatible. Retired producer
history remains eligible where bytes still verify. Test-only producer/consumer
fixtures exercise this path; no production type, Idea Discovery ID, Capsule or
Catalog record was created.

Repository/service-driven APIs are:

- `GET /projects/{project_id}/artifacts`;
- `GET /projects/{project_id}/workflow-instances/{instance_id}/artifacts`;
- `POST/GET /projects/{project_id}/workflow-instances/{instance_id}/artifact-dependencies`;
- `GET /projects/{project_id}/workflow-instances/{instance_id}/artifact-materialization-plan`.

Lists use bounded pagination and stable order. The plan proves the complete
consumer → binding → Artifact → producer → Progress/checksum provenance and
contains Workspace-relative paths only.

## Local Index and materialization

`.reagent/artifact-index.json` is the checksummed local source of verified
Artifact bytes. It is intentionally separate from Installed Lock. Refresh
finds the exact producer Capsule, rejects path escape/link/special-file cases,
reads bytes, verifies size/checksum and atomically replaces the Index.

The existing CLI now provides `artifact status`, `artifact refresh`, and
explicit `artifact materialize --workflow-instance`. Materialization requires
the B4 Workspace writer lock, an installed consumer, a verified Index entry and
an exact Cloud plan. It reads source bytes once through `O_NOFOLLOW`, copies to
same-filesystem staging, fsyncs, verifies, publishes without overwrite,
re-verifies and atomically writes a checksummed receipt. No symlink, hardlink,
shared writable state or force overwrite exists. Source bytes are unchanged.
Publish-before-receipt recovery verifies and adopts only the exact target;
other target or receipt drift fails closed.

## Qualification

A dedicated loopback PostgreSQL 18.1 cluster on port `55486` used only
`reagent_night_b6_*` databases. Empty upgrade, populated B5 upgrade, absence of
unsafe legacy promotion, existing Progress preservation, downgrade/re-upgrade,
transaction rollback, repository reload, PostgreSQL restart, sole head/current
`20260806_0012` and Alembic no-drift passed.

Results:

- focused Cloud Artifact/API/Progress/Workspace selection: `70 passed`;
- focused local Index/materialization/security selection: `40 passed`;
- database suite: `52 passed, 4 skipped`;
- post-restart Artifact PostgreSQL suite: `5 passed`;
- migration destructive-preservation test: `1 passed`;
- full backend: `674 passed, 8 skipped`;
- frontend Vitest: `12` files / `19` tests passed;
- frontend typecheck, ESLint and production build: passed;
- backend compileall, Alembic heads/current/check and diff check: passed;
- 20 producer Instances × 50 Artifacts (1,000 rows): bounded page/count used
  no per-Artifact loading and stayed within four SQL statements.

The eight skips are pre-existing gates: four older B1/B2/B4/B5 migration URL
gates not selected by the dedicated B6 URL, destructive E2E database variables,
R3B-1 OpenAlex contract-isolation variables, explicit live OpenAlex authority,
and R3A-2 research-V2 isolation variables. No B6 PostgreSQL or filesystem test
skipped. The first frontend build was sandbox-blocked by Turbopack helper-port
binding; the permitted rerun passed.

Real temporary-directory rehearsals covered test-only producer promotion and
Index verification, exact cross-Workflow copy with distinct inodes and equal
checksums, idempotent repeat, A1/A2 no-auto-latest behavior, retained producer
history, and publish-before-receipt recovery. Source hashes remained unchanged,
Installed Lock remained Capsule-only, and temporary state contained no link.

## Boundary and commits

No production Artifact type, Idea Discovery, Writing, Review, Experiment,
cross-Project sharing, cloud Artifact bytes, top-level Artifact UI, Skills/
Resources product, external resolver, backup, watcher, background sync or
browser local materialization was implemented.

Commits:

- `4d93095` — `NIGHT-B6a: add typed artifact reference persistence`;
- `fa372d5` — `NIGHT-B6b: index workspace artifacts and materialize dependencies`;
- final qualification/documentation commit: `NIGHT-B6c: qualify artifact
  handoff and provenance` (hash is recorded by final Git evidence rather than
  self-referenced here).

The next gate is owner review. NIGHT-B7 is not authorized by this record.
