# NIGHT-B4 Pull Sync, Installed Lock, and Installation Acknowledgement

Date: 2026-08-07

Status: **PASS — OWNER REVIEW REQUIRED**

## Baseline and recovered contracts

Work ran directly on clean `main` at accepted NIGHT-B3 final commit
`d3c1735504f7782af255fe081837edd1dcfb054f`; it was the current history
ancestor. No worktree or feature branch was created and nothing was pushed.
ARCH-D1 commit `e880d40ec73f07198f7b064afd898982a3357e16`, ADRs 0022/0023,
B1/B2/B3 implementations, Package compiler/download/validator, Desired
Manifest, bootstrap descriptor, B3 registry, filesystem utilities, API/UoW
patterns, and sole migration head `20260806_0009` were inspected before
implementation. No `.env`, credential, owner database or ProjectDB was read.

ARCH-D1 freezes sync plan and acknowledgement endpoints, the explicit local
`sync` command, `.reagent/installed-lock.json`, staging/journal/receipt roots,
exact version pins, non-destructive retire, and metadata-only cloud
acknowledgement. ADR 0024 records the runtime realization.

## Cloud persistence and API

Additive migration `20260806_0010` directly follows `0009` and creates:

- `local_workflow_capsule_artifacts`, uniquely binding exact Project,
  Workflow Instance, Capsule version, Package identity, manifest/archive
  checksums, storage key and availability;
- `workspace_installation_acknowledgements`, binding Project/Workspace,
  Manifest revision/checksum, Installed Lock checksum, exact active entries and
  an idempotency key.

The migration backfills accepted current Literature Search Packages only when
their deterministic B1 Workflow Instance binding is complete; inconsistent
legacy state aborts transactionally. Downgrade removes only B4 tables.

`POST /projects/{project_id}/workspace/sync-plan` returns a checksum-bound,
deterministically ordered current Desired Manifest plan. It distinguishes
`NOOP`, `INSTALL_CAPSULE`, `CONFLICT`, `UNAVAILABLE` and
`RETAINED_NOT_DESIRED`. The deterministic legacy instance reuses its accepted
Package; additional Literature Search instances receive unique deterministic
Package/artifact identities. Artifact bytes are read only through the exact
Project/Instance/artifact download route and reverified. Planned Workflows
never generate an archive.

`POST /projects/{project_id}/workspace/sync-ack` accepts only the current
Manifest, exact Project/Workspace and active Capsule pins, schema/checksums and
canonical UUID idempotency. Exact replay returns the same row; changed replay
fails. PostgreSQL uniqueness prevents duplicate concurrent acknowledgement.
Stale revision reports are rejected and never mark the newer revision current.
This record is a client installation report, not server inspection or backup of
local files.

## Local sync, safety, and recovery

The B3 standard-library CLI now supports:

- `sync <workspace> [--api-url <loopback>] [--dry-run] [--json]`;
- enhanced `workspace status` states including `BOOTSTRAPPED_NO_LOCK`,
  `INSTALLED_LOCK_CURRENT`, `ACK_PENDING`, and `ACKNOWLEDGED_CURRENT`.

Only an explicit `sync` mutates local installation state. It validates the
Workspace, takes an OS advisory single-writer lock, retries any pending
acknowledgement, requests a cloud plan, downloads exact artifacts, verifies
archive/package/Project/Instance/Capsule/trust identity, safely extracts into
same-filesystem staging, fsyncs, atomically publishes, and revalidates before
writing the checksum-bound Installed Lock. It does not execute downloaded
content. Traversal, absolute paths, ZIP slip, symlinks, hardlinks, special
files, case collisions, duplicate paths, archive bombs, target replacement and
checksum/identity mismatch fail closed.

The Lock is the only installed-state truth source and binds the immutable
Package contract, not declared mutable outputs/memory/Progress/receipts. B3
registry entries are revalidated once and promoted without download; the
registry remains unchanged legacy evidence and is never dual-written. Retired
Capsules are marked retained and are never deleted. Pin conflict never
overwrites or merges a Capsule.

A checksummed sync journal covers multi-Capsule write boundaries. A Capsule
published before Lock write is recovered by exact revalidation. The pending
ack envelope is atomically saved before transport; failure returns
`ACK_PENDING`, preserves Lock/Capsules and reuses the same idempotency key.
Cloud-success/local-receipt-crash exact replay restores the receipt without a
duplicate row. Revision-N installation remains local if the Manifest advances;
stale acknowledgement is marked and the next plan installs N+1.

## Qualification

An isolated PostgreSQL 18.1 cluster used loopback port `55484` and only
databases containing `reagent_night_b4` plus dedicated B1/B2 compatibility
database names. Evidence:

- complete Workspace/API/sync focused suite: `38 passed`;
- B4 destructive migration qualification: `1 passed`;
- B4 PostgreSQL artifact/ack/reload/concurrency/race tests: `2 passed`, both
  before and after a physical cluster restart;
- full backend with all B1/B2/B4 migration URLs: `647 passed, 4 skipped`;
  skips are only the four pre-existing external/live integration gates;
- empty upgrade, populated B3 backfill, repeated backfill, downgrade,
  re-upgrade, inconsistent-binding rollback, restart, sole head/current and
  Alembic no-drift: passed;
- frontend typecheck, Vitest (`14 passed`), ESLint and production build: passed;
  the sandboxed Turbopack helper-port attempt was environment-blocked and the
  permitted rerun passed;
- backend `compileall`, runtime JSON Schema parsing and `git diff --check`:
  passed.

Supervised fictional temporary-directory drills covered: B3 adopted migration
without download/mutable hash change; missing Capsule install then no-op;
incremental second instance; retire-with-retention; acknowledgement outage and
retry; publication-before-Lock, Cloud-success-before-local-receipt, checksum
failure and Manifest-race recovery. No user Workspace, downloaded user Package,
runtime database, log, credential or real research data was committed.

## Boundary and commits

Unchanged: standalone/adopted Literature Search launch, Package download,
Progress/upload retry, OpenAlex Proxy, frontend source and Hosted AgentRuntime.
No Provider/network research call occurred. No Progress aggregation, frontend
Workflow Board, Artifact handoff, Idea Discovery, Skills/Resources product,
GitHub/Hugging Face resolver, backup or background sync was implemented.

Commits:

- `19f6295` — `NIGHT-B4a: expose capsule sync and acknowledgement contracts`;
- `0e88078` — `NIGHT-B4b: add installed workspace lock and pull sync`;
- final qualification/documentation commit:
  `NIGHT-B4c: qualify sync recovery and compatibility` (hash is recorded by
  final Git evidence rather than self-referenced here).

The next gate is owner review. NIGHT-B5 is not authorized by this record.
