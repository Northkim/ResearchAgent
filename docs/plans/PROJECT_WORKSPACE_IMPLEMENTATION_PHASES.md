# Project Workspace Implementation Phases

> **Planning document only.** `IMPLEMENTATION_AUTHORIZED = false`. This is a
> dependency map and acceptance decomposition, not an implementation prompt.

## Phase 1 — architecture/data-model foundation

- **Scope:** additive canonical Project, local Workflow Definition/version,
  Capsule version, and Workflow Instance domain/SQL boundaries; deterministic
  legacy mapping; reviewed Literature Search catalog seed.
- **Dependencies:** ARCH-D1 owner review; existing migrations and LocalProject
  compatibility evidence.
- **Expected subsystems:** domain models, repository/UoW, database models,
  Alembic, composition, focused fixtures/tests; no frontend or Package change.
- **Migration:** first additive revision; copy metadata but do not rewrite/drop
  `local_projects` or historical bytes.
- **Tests/gate:** head/down/up, PostgreSQL no-skip, ID/constraint/concurrency,
  deterministic mapping, existing full regressions and Package launch.
- **Rollback:** downgrade only new tables/seed after proving legacy untouched.
- **Prohibited expansion:** manifest APIs, sync, filesystem writes, new Workflow,
  Hosted reuse, Progress schema change.

## Phase 2 — Workflow registry and Desired Project Manifest

- **Scope:** reviewed catalog reads, immutable manifest/entries, instance
  add/retire and optimistic base-revision service/API.
- **Dependencies:** Phase 1 identities/catalog.
- **Expected subsystems:** manifest domain, repository/UoW, API schemas/routes,
  capability scopes, migrations, contract/security/concurrency tests.
- **Migration:** manifest/entry tables and optional Skill/Resource metadata
  reservations only where exercised.
- **Tests/gate:** exact replay/conflict, concurrent revisions, wrong scope,
  rollback prevention, no execution/Provider effects, legacy routes unchanged.
- **Rollback:** remove only new desired-state rows/routes behind feature flag.
- **Prohibited expansion:** local sync/install, UI Workflow selection, offline
  manifest authoring, automatic merge.

## Phase 3 — Workspace bootstrap and legacy Capsule adoption

- **Scope:** new Workspace bootstrap metadata/validator/CLI status; explicit
  reference adoption of unchanged Literature Search Packages.
- **Dependencies:** Phases 1–2 and design schemas promoted through a separate
  runtime-contract approval.
- **Expected subsystems:** local CLI distribution, Workspace validator,
  bootstrap service/API, compatibility adapter, tests/docs.
- **Migration:** no required new SQL beyond identity/manifest unless bootstrap
  receipts are persisted.
- **Tests/gate:** movable Workspace, legacy Package still directly runnable,
  reference checksum validation, no secret/path leak, no silent move/rewrite.
- **Rollback:** remove new bootstrap artifacts; legacy folder remains runnable.
- **Prohibited expansion:** new Capsule download/install and Idea Discovery.

## Phase 4 — pull-based sync and atomic Capsule installation

- **Scope:** sync plan/ack APIs, CLI state machine, protected staging, archive
  validation, side-by-side atomic install, lock and receipt.
- **Dependencies:** Phases 1–3; approved archive/capability/runtime schemas.
- **Expected subsystems:** sync service/repository/API, local CLI/filesystem
  engine, archive/security utilities, capability issuance, acceptance harness.
- **Migration:** installation acknowledgement table.
- **Tests/gate:** interruption at every boundary, traversal/link/bomb/drift/
  conflict, revision races, idempotent ack, real filesystem/process restart.
- **Rollback:** feature flag; preserve valid installed Capsules and old lock;
  disable further sync rather than delete.
- **Prohibited expansion:** background sync, auto overwrite/delete, arbitrary
  Skills, cloud filesystem writes.

## Phase 5 — multi-instance Progress aggregation

- **Scope:** per-instance projection, compatibility projection from existing
  reports, Project graph/list response and Artifact metadata references.
- **Dependencies:** instance identities and accepted sync observations.
- **Expected subsystems:** Progress domain/ingestion/projection/API, additive
  tables, versioned report mapping, tests.
- **Migration:** local per-instance projection and Artifact reference tables.
- **Tests/gate:** multiple instances/rounds, legacy byte/checksum immutability,
  cross-instance denial, honest cloud uncertainty, replay/restart.
- **Rollback:** retain old Package-scoped projection as authoritative V0.x path;
  remove new derived tables only.
- **Prohibited expansion:** Artifact byte upload, Hosted event reuse, forced
  linear pipeline.

## Phase 6 — frontend framework

- **Scope:** registry-driven wizard/catalog, Overview/Workflows/Progress/Help,
  instance board/detail, sync/error copy and accessibility.
- **Dependencies:** stable Phase 2 and 5 read APIs; Phase 4 status API for actual
  sync actions.
- **Expected subsystems:** Next.js routes/types/client/components, Vitest,
  Playwright, docs.
- **Migration:** none.
- **Tests/gate:** planned items disabled, one active/type UI limit, no Hosted
  primary action, truthful cloud/local labels, responsive/a11y/build/E2E.
- **Rollback:** preserve existing V0.1 LS routes behind local-product route
  switch until parity accepted.
- **Prohibited expansion:** empty future tabs, browser PTY, cloud execution.

## Phase 7 — Idea Discovery Capsule

- **Scope:** one reviewed Capsule using accepted instance/sync/Artifact
  contracts to test extensibility and consume typed Literature Search outputs.
- **Dependencies:** Phases 1–6 and separate owner contract/Provider/Harness
  approval.
- **Expected subsystems:** Capsule definition/template, local Workflow/Skills,
  output/report contracts, dedicated tests/acceptance; minimal catalog seed.
- **Migration:** catalog/version data only unless new schema metadata required.
- **Tests/gate:** independent installation, exact inputs, no LS mutation, local
  Harness checkpoints, bounded Progress, zero Hosted/cloud synthesis.
- **Rollback:** retire desired instance; preserve Capsule/results/history.
- **Prohibited expansion:** other Workflows, arbitrary Skills, production R3D.

## Phase 8 — Artifact handoff

- **Scope:** explicit registry/materialization flow between Literature Search
  and Idea Discovery, schema compatibility and provenance UI metadata.
- **Dependencies:** accepted Idea Discovery input/output contract and Phase 5
  Artifact table.
- **Expected subsystems:** local Artifact index/validator/materializer, Capsule
  dependency resolver, metadata API/UI, tests.
- **Migration:** only if consumer bindings were not included in Phase 5.
- **Tests/gate:** no symlink/shared writes, checksum/schema mismatch, stale/
  missing, atomic copy, cross-project denial.
- **Rollback:** stop new materialization; immutable source/destination remains.
- **Prohibited expansion:** automatic conversion, cloud bytes, general store.

## Phase 9 — structured external Resource metadata/local resolver

- **Scope:** Project Resource metadata and explicit read-only local resolution
  for pinned Git/GitHub and Hugging Face content.
- **Dependencies:** sync security, Artifact references, owner privacy review.
- **Expected subsystems:** Resource domain/API, local resolver adapters, CLI
  status/sync integration, tests/docs.
- **Migration:** Resource binding table if not introduced earlier.
- **Tests/gate:** credential-free locators, immutable revisions, submodule/LFS/
  gated states, no cloud tokens/push, offline behavior.
- **Rollback:** retire binding; never delete external/local bytes.
- **Prohibited expansion:** OAuth/App connectors, background pull, automatic
  push, large-byte proxy.

## Phase 10 — future Skills and cross-device features

- **Scope:** only after separate threat/product decisions: private/imported
  Skill quarantine and review; optional device inventory, encrypted snapshot,
  and explicit transfer.
- **Dependencies:** mature permissions/sandbox/provenance, storage/privacy and
  recovery design, production auth decisions.
- **Expected subsystems:** intentionally undecided.
- **Migration/tests/gate:** separate design and owner ratification required.
- **Rollback:** disable execution/import; preserve metadata/evidence.
- **Prohibited expansion:** silent Skill updates, automatic multi-device merge,
  unencrypted backup, credential transfer, marketplace ranking.

## Recommended maximum reliable first slice

The maximum reliable overnight-sized slice for later owner authorization is
**Phase 1 only, with no API or frontend**:

1. additive domain and SQL records for canonical Projects, local Workflow
   catalog/version, Capsule version, and Project Workflow Instances;
2. one reviewed Literature Search Definition/Capsule compatibility seed;
3. deterministic legacy Project/Package→instance mapping stored outside
   historical report bytes;
4. repositories/UoW/composition plus isolated PostgreSQL migration/down-up and
   full regression tests; and
5. a read-only diagnostic command/test fixture only if it uses existing test
   surfaces—not a new product route.

This slice establishes names and durable identities without touching Package
generation, local files, manifest mutation, Progress semantics, frontend,
Idea Discovery, or runtime execution. Its acceptance gate is a single additive
migration head, exact legacy preservation, no Hosted foreign keys, zero source
of execution side effects, all relevant PostgreSQL tests executed, and full
backend regressions. Failure rolls back the new revision and leaves the current
V0.1 product untouched.

`OVERNIGHT_IMPLEMENTATION_READY = READY_FOR_OWNER_REVIEW` means this bounded
slice is reviewable; it is not implementation authorization and no prompt is
generated here.
