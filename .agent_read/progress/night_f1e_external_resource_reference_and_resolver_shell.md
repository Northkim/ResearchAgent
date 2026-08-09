# NIGHT-F1E External Resource reference, binding, and local resolver shell

Date: 2026-08-09

Status: PASS — OWNER REVIEW READY

## PLAN_ALIGNMENT

### ORIGINAL_PLAN

The original Meta Research Agent plan did not name Resource as an independent
product module. It did, however, establish the controlling boundary: ReAgent
Cloud coordinates Project/Workflow/Skill/Progress metadata, the Local Workspace
owns complete research files and state, and Codex/Claude Code remains the Agent
Harness. ReAgent Cloud does not execute research.

### EVOLVED_FROZEN_ARCHITECTURE

The accepted HYBRID_WORKSPACE_AND_CAPSULES architecture later made external
assets explicit: GitHub owns code/version history, Hugging Face owns datasets,
models and weights, Cloud stores only exact references/checksums/status, and the
Local Workspace resolves and verifies bytes with local credentials. This is
needed because Experiment must name reproducible code/data/model inputs without
turning ReAgent into Cloud file storage, a GitHub/Hugging Face replacement, or
a remote execution platform.

`ORIGINAL_PLAN_ALIGNMENT = PASS_WITH_ARCHITECTURE_EXTENSION`

`EVOLVED_ARCHITECTURE_ALIGNMENT = PASS`

`ROUTE_DRIFT = false`

F1E adds no live resolver, Provider credential, Resource marketplace, Resource
byte storage, new Workflow, real Experiment, paper reproduction, Skill-system
expansion, Workspace backup, multi-user auth, or Cloud Agent execution.

## Baseline

- branch/start: `main` at `1569977bc97c30b18e926edeb52026e86994ee4b`
- F1D final commit: verified ancestor
- initial worktree: clean; extra worktrees: none
- starting migration: sole `20260806_0016`
- recovered model: `CURRENT_RESOURCE_MODEL = DESIGN_ONLY`
- five production Workflows, Full Research preset, Skill Registry and exact
  F1D pins were present and retained
- no `.env`, owner DB/Workspace, credential, live Provider, GitHub/Hugging Face
  request, feature branch, worktree or push was used

## Resource domain and boundaries

- canonical authorities: Project Resource Reference, exact Workflow Version
  Resource Requirement, exact Workflow Instance Resource Binding
- kinds: SOURCE_REPOSITORY, DATASET, MODEL, CHECKPOINT, GENERIC_FILE
- providers: GITHUB, HUGGING_FACE, LOCAL_TEST
- identity is deterministic and Project-scoped; revision/checksum are immutable
- external revisions must be exact 40/64-character commit identities; floating
  `main`, `master`, `HEAD`, `latest`, branches and mutable tags are rejected
- locators are bounded credential-free provider identities; URLs, protocols,
  server paths, tokens, passwords, shell syntax and arbitrary headers are rejected
- Cloud stores metadata only; no Resource bytes, local absolute path or token
- Resource remains separate from Skill, Artifact, Capsule Installed Lock and
  mutable Workflow memory

## Persistence, API, and UI

- read/create Project Resource APIs and read/create exact Workflow binding APIs
  use the existing Project Workspace router and Unit of Work
- composite database constraints plus service validation reject cross-Project,
  wrong-kind and disallowed-provider bindings
- list responses are bounded, stable and bulk projected; Workflow catalog and
  Instance projections include Resource requirements without per-card requests
- the Workflow Board exposes a scoped Experiment Resource section, exact
  revision, binding state and metadata-only warning
- LOCAL_TEST is hidden from normal UI; no empty top-level Resource navigation
  was added
- Artifact and Resource selectors remain distinct; UI never claims that a
  Cloud-bound reference was downloaded or locally verified

## Local resolver and Resource Index

- generic `reagent_local.py resource list|status|resolve` commands preserve JSON
  output and friendly exact/stable Workflow selectors
- canonical local bytes: `resources/<resource-id>/`
- canonical local truth: `.reagent/resource-index.json`
- Installed Lock remains Capsule-only; Artifact Index remains Artifact-only
- LOCAL_TEST requires `REAGENT_CONTROLLED_RESOURCE_TEST=1` and an explicit
  fixture root; ordinary configuration cannot enable it implicitly
- resolution validates exact marker/revision, traversal, symlink, hardlink,
  special file, casefold collision, canonical order and expected checksum
- same-filesystem staging, atomic publication, reread, atomic index update,
  idempotent replay and publish-before-index recovery are qualified
- bound unresolved/drifted Resource fails run preflight closed; optional unbound
  requirements do not block the Scaffold
- GitHub/Hugging Face resolution returns
  `RESOURCE_RESOLVER_NOT_IMPLEMENTED`; instrumented tests recorded zero network calls

## Experiment 0.3 and immutability

- new Reproduction & Experiment Definition/Capsule 0.3.0 only
- exact F1D pins remain Research Artifact Provenance 0.1.0 and Scaffold Core
  Safety 0.1.0
- optional requirements: source_repository, dataset, model, checkpoint
- existing Experiment 0.1.0/0.2.0 Instances and Capsules are not upgraded or
  modified; new Instances and Full Research preset resolve current 0.3.0
- Literature, Idea, Writing, Review, all prior Experiment versions and both
  production Skill versions remain immutable
- Experiment remains `SCAFFOLD_CORE`, IDEA_EXPERIMENT only,
  `PLACEHOLDER_NOT_EXECUTED`, `actual_results = null`; Resource bytes are never executed
- `experiment-record/v1` was not changed

## Migration and qualification

- revision: `20260806_0017`, down revision `20260806_0016`
- schema: Project Resource References, Workflow Resource Requirements, Workflow
  Instance Resource Bindings
- seeds: Experiment Definition/Capsule 0.3.0, its existing Artifact/Skill pins,
  and four optional Resource requirements
- empty/base through 0017: PASS
- populated 0016 to 0017: PASS
- 0017 to 0016 to 0017: PASS with deterministic identities/checksums
- F1D Skills/pins and old Workflow data survive downgrade/re-upgrade
- Alembic: sole head/current `20260806_0017`; check reports no drift
- PostgreSQL restart/reconnect paths remain covered by the full backend suite

## Qualification results

- F1E/F1D/F1C/F1B/F1A/B7/H2 focused regression: `77 passed`
- F1E Resource shell direct qualification: `7 passed`
- full backend on isolated PostgreSQL 18, with F1E migration gate enabled:
  `766 passed, 13 skipped`
- frontend Vitest: `17 files, 34 tests passed`
- current controlled-product Playwright: `3 passed` (H1 journey and both Local
  V0.1 paths); historical Hosted routes are deliberately absent in H2 controlled mode
- TypeScript: PASS; ESLint: PASS; production build: PASS
- Python compileall: PASS; git diff check: PASS
- GitHub/Hugging Face resolver network calls: `0`

The 13 skips are nine pre-existing dedicated historical migration gates (B1,
B2, B4, B5, B6, B7, F1A, F1B, F1D) and four pre-existing isolated/live
integration gates (destructive demo, OpenAlex contract, live OpenAlex, research
v2). The dedicated F1E migration gate was enabled and passed.

`F1E_NEW_SKIP = 0`

## Manual qualification

- A: Full Research Project selected current Experiment 0.3.0; exact LOCAL_TEST
  metadata/binding resolved into the independent index, preflight passed, and
  the existing full Scaffold chain retained null actual results — PASS
- B: tampering with resolved bytes produced DRIFTED and preflight
  `RESOURCE_DRIFT` — PASS
- C: exact GitHub metadata was accepted while resolve returned NOT_IMPLEMENTED
  and the network call counter remained zero — PASS
- D: exact Hugging Face metadata behaved identically — PASS
- E: existing Experiment 0.2.0 remained pinned with no Resource requirements;
  explicit new/add selection resolves immutable 0.3.0 — PASS

## Performance

One Project with 20 Workflow Instances and 100 Resource References passed
stable two-page listing and Project Progress projection. Requirement caching,
bulk Resource loading for bindings, and existing aggregate projections avoid
per-card/per-binding query loops; no Redis or Celery was introduced.

## Recovery note

Qualification discovered and removed the exact stale temporary F1A PostgreSQL
cluster `/private/tmp/reagent-f1a-pg.cjoUEJ`, left running by an older interrupted
phase. It was not an owner database. All F1E temporary databases, Workspaces,
Playwright reports and panic logs were also removed.

## Deferred

- F1F: complete product-width E2E qualification only
- Resource: real GitHub/Hugging Face resolver, provider credentials/auth,
  large-data cache, cleanup and cross-Project sharing
- still forbidden: real Experiment/paper reproduction, Cloud Resource bytes,
  automatic latest, network resolver fallback and multi-user auth
