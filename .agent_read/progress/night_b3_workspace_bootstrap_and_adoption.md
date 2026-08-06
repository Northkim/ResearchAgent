# NIGHT-B3 Workspace Bootstrap and Legacy Package Adoption

Date: 2026-08-07

Status: **PASS — OWNER REVIEW REQUIRED**

## Baseline and recovered contracts

Work ran directly on clean `main` at accepted NIGHT-B2 final commit
`d46633a752abc6050b5905eabeac1ba4cdd15c3b`; that commit was the current
history ancestor, no worktree/feature branch was created, and nothing was
pushed. ARCH-D1 commit `e880d40ec73f07198f7b064afd898982a3357e16`, ADR 0022,
B1/B2 commits, the Package compiler/manifest/validator/launcher, Project API and
UoW patterns, and the sole `20260806_0009` Alembic head were inspected before
implementation.

B2 already supplies one canonical `workspace_id` per Project, so
`B3_DATABASE_MIGRATION = NOT_REQUIRED`. Existing migrations were not modified.
ARCH-D1 froze root `project.json` and the versioned Capsule path but did not
freeze a bootstrap HTTP path or integrity envelope; accepted ADR 0023 records
the single B3 route and runtime promotion.

## Cloud descriptor and local identity

`GET /projects/{project_id}/workspace-bootstrap` returns deterministic
`reagent.workspace-bootstrap/v0.1`. The service verifies current Project and
Manifest identity/checksum, typed Manifest entries, project-scoped Instances,
and exact Capsule definitions before returning. The descriptor contains no
token, credential, database URL, local path, Installed Lock or acknowledgement.
Only the deterministic legacy Literature Search instance receives current
Package adoption metadata.

The local `reagent.project-workspace/v0.1` `project.json` binds Project,
Workspace, cloud-origin ID, bootstrap revision/checksum, lifecycle, fixed
relative control paths, secret policy, creation time and descriptor checksum.
It is written after staging and validation and is never silently overwritten.
Runtime JSON schemas for bootstrap, Workspace identity and the minimal Capsule
registry reject unknown fields.

## Bootstrap, adoption and safety

The repository `python reagent_local.py` supports:

- `bootstrap <target> --descriptor <file> [--json]`;
- `adopt <legacy-package> <workspace> [--descriptor <file>] [--json]`;
- `workspace status <workspace> [--json]`.

Bootstrap creates only root policy/CLI, `project.json`, cached bootstrap/Desired
Manifest, a checksum-bound empty Capsule registry and `capsules/`. It stages in
the destination parent, fsyncs, validates and atomically publishes. Identical
replay returns `ALREADY_BOOTSTRAPPED`; conflicts and partial targets preserve
existing files.

Adoption accepts a directory or ZIP, validates the frozen legacy UUIDv5 mapping,
Package/Workflow/Capsule identities, Package/manifest/immutable checksums,
required launch/report helpers and exact Package mutable policy. It rejects
absolute/traversal/colliding paths, ZIP slip, symlinks, hardlinks, special
files, excessive archives, credentials and target drift. It copies through
same-filesystem staging into the ARCH-D1 Capsule path, revalidates the copy and
unchanged source, then atomically records local adoption. Existing outputs,
memory, Progress drafts/reports/receipts and harmless bounded `.DS_Store` files
are preserved. Package code is never executed during adoption.

The original standalone and adopted Capsule both retain
`python reagent_local.py run .`; Package checksums and download/Progress/Proxy
contracts are unchanged. A published copy with a failed registry write is
recoverable by exact replay; no implicit merge or overwrite exists.

## Qualification

An isolated PostgreSQL 18.1 cluster used loopback port `56439` and only
databases containing `reagent_night_b3` (the dedicated B1/B2 compatibility
database names also retained their test-required phase markers). `.env`,
ProjectDB and the owner persistent database were not read or accessed.

Evidence:

- focused Workspace/Package/API contracts: `19 passed`;
- combined Project Workspace, Package, LocalProject, Progress, Local Session,
  Proxy and API regression: `408 passed`;
- PostgreSQL repository suite: `42 passed, 2 gated migration skips`, with the
  two migration gates then run separately: `2 passed`;
- B3 PostgreSQL descriptor reconstruction/reload: passed before and after a
  physical cluster restart;
- full backend with all PostgreSQL/migration URLs: `633 passed, 4 skipped`;
  only the four pre-existing external integration/live gates remained;
- frontend TypeScript, Vitest (`14 passed`), ESLint and production build:
  passed; the first sandboxed Turbopack build was environment-blocked by an
  internal port bind and the required unsandboxed rerun passed;
- `compileall`, runtime JSON parsing, Alembic heads/current/check and
  `git diff --check`: passed;
- manual fictional temporary-directory drills: new bootstrap/idempotency,
  legacy adoption/source hash/idempotency, and injected descriptor/copy failure
  recovery all passed; no Installed Lock or acknowledgement appeared.

## Boundary and commits

No database migration, `.env`/credential read, external research network,
OpenAlex call, frontend source change, Hosted execution, sync, generic Capsule
installer, Installed Lock, acknowledgement, Progress aggregation, Artifact
handoff, Idea Discovery, Skill/Resource product, user Workspace, runtime
database/log or push was created.

Commits:

- `f24499e` — `NIGHT-B3a: expose workspace bootstrap identity`;
- `b027eb3` — `NIGHT-B3b: bootstrap workspaces and adopt legacy packages`;
- final qualification/documentation commit:
  `NIGHT-B3c: qualify workspace adoption compatibility` (hash is recorded by
  final Git evidence rather than self-referenced here).

The next gate is owner review. NIGHT-B4 is not authorized by this record.
