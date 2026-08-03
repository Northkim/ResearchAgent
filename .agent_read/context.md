# ReAgent Compressed Project Context

Last updated: 2026-08-03

## Current governing route — Phase R0 teacher-aligned boundary freeze

The owner accepted the committed Teacher Design Alignment Audit verdict:

> **FUNDAMENTALLY_DIFFERENT_PRODUCT**

Accepted ADR 0009 now governs the initial V1 product boundary. The teacher PDF
`Meta-Research-Agent-架构.pdf` is the highest product authority. Initial V1 is:

```text
cloud management and supply
  -> versioned downloadable local Workflow Package
  -> existing Claude Code or Codex Agent Harness performs research
  -> local outputs and Progress Report
  -> explicit cloud upload, history, and progress projection
```

The cloud owns project, Skill, Workflow/package, package/download, Progress
Report, progress-view, credential, API-proxy, returned-artifact, and continuity
metadata responsibilities. The local folder is authoritative for concrete
research-task state: instructions, pinned versions, prompts, inputs, outputs,
context, local artifacts, Progress Reports, and continuation information. An
existing Claude Code, Codex, or equivalent Agent Harness reads those files,
interacts with the user, invokes tools/proxy calls, performs the research, and
writes outputs/progress. ReAgent does not develop a replacement Harness for
initial V1.

State authority is split explicitly:

- **Local Task State:** active research progress, working context, local
  outputs/tool artifacts, continuation state, and local Progress Reports before
  upload.
- **Cloud Project State:** project/package/Workflow/Skill/template identity and
  versions, checksums/download history, uploaded Progress Report history,
  progress projection, proxy usage/accounting, and cloud-stored uploads/returned
  artifacts.

PostgreSQL may be authoritative for Cloud Project State only in the V1 product
boundary. Current server `WorkflowRun`, `StepRun`, checkpoint, memory revision,
and `ExecutionEvent` state remains preserved internal-test or optional Hosted
Mode infrastructure; it is not the V1 source of concrete Local Task State.

The existing Hosted AgentRuntime is preserved as an internal deterministic test
Harness and optional future Hosted Mode. It is non-default, outside the
teacher-aligned initial V1 path, and frozen from further product development
without separate owner reauthorization. Existing code, migrations, immutable
Workflow hashes, tests, evidence, and the hosted demo are not deleted.

ADR status after R0:

- ADR 0009: **Accepted** — teacher-aligned initial V1 boundary;
- ADR 0007: **Deferred by ADR 0009 — Optional Hosted Mode**;
- ADR 0008: **Deferred by ADR 0009 — Optional Hosted Mode**;
- ADR 0006 / Optional Evaluation Module: **Deferred**;
- ADR 0005 remains accepted only for its limited multilingual SearchPlan and
  safe-diagnostic scope; every real relevance Judge remains deferred.

Hosted LLM execution, hosted OpenAlex research execution, automatic relevance
evaluation, full-pool evaluation, and Phase 9C hosted activation are deferred.
Grounded prompts, summary/evidence/claim/citation/report contracts,
abstract-only rules, provenance validators, checksums, and synthetic fixtures
remain candidates for local Workflow/Skill packages and deterministic upload
validation.

### Hosted-work freeze

Do not continue V1 product development of:

- backend research execution;
- browser-triggered research run/resume;
- Hosted AgentRuntime productionization;
- real hosted LLM activation;
- new hosted research-provider adapters;
- hosted worker/queue/lease;
- automatic relevance Judge;
- full-pool retrieval/evaluation benchmarks;
- server-side research-report, approval, or execution-timeline UX expansion;
- Phase 9C-2B activation or production Hosted Mode.

The freeze permits repository-safety bug fixes, deterministic tests,
preservation, and extraction/repackaging of reusable schemas or validators.

### Current implementation milestone — R3A contract/security review complete; owner decisions pending

R1 remains accepted with warnings for the bounded Codex experiment. Freshness
and runtime non-use are owner-attested, file/checksum gates passed, the moved
folder carries concrete task state, and Claude Code remains untested. Executed
R1 bytes remain historical `progress-report/v0.1` evidence and are not changed.

R2A implements the teacher-aligned cloud Progress Report boundary under
`backend/progress_reports/`. Native `progress-report/v0.2` has immutable
contracts, deterministic non-cyclic content/report identity, exact raw
context-before/context-after checksums, full pins and output metadata. A
deterministic v0.1 normalizer retains original bytes and records assumptions,
unavailable fields and evidence limitations without fabricating a context
transition.

Explicit upload validates an immutable envelope and untrusted bytes, stores the
exact original with `ArtifactContentStorage`, appends normalized/validation/
chain metadata, detects incomplete, continuity, identity and branch conflicts,
and reconstructs a deterministic HTML-escaped project progress projection.
Exact replay is idempotent; conflicting/invalid evidence cannot replace
accepted progress. FastAPI exposes upload, history, report, original-byte and
projection reads. The credential-free standard-library client validates
offline and makes one bounded explicit request without changing the package.

Migration `20260803_0003_progress_reports` adds distinct uploaded-report and
projection tables. It does not repurpose hosted `ExecutionEvent`, checkpoint,
memory or run tables. The upload service and route have no AgentRuntime,
ExecutionDispatcher, OpenAlex, LLM or structured-generation call and no
run/resume/local-context-mutation behavior. Concrete task authority stays in
the local folder.

Future generated packages use package-template `0.2.0` and native Progress
Report v0.2 while preserving package-schema compatibility. They include a
self-contained snapshot/finalize helper and dynamic report/output/chain
validation. Their upload status is `UPLOAD_ACCEPTANCE_PENDING`.

R2A-C audited the complete R2A change set against the implemented contracts,
normalizer, local package helper, upload service, chain validator, projection,
API composition and persistence mappings. The reviewed changes remain confined
to Progress Report contracts/normalization, ingestion/security/chain/projection,
API and repository integration, one additive migration, the explicit offline
client, future package v0.2 support, fictional tests and project documentation.
No frontend file or executed local Package evidence is included. Native
identity remains non-cyclic (`report_content_checksum` -> `report_id` ->
`report_checksum`), raw context bytes are hashed before and after a local round,
and v0.1 normalization leaves unavailable transition and pin fields unset.

R2B then exercised the committed path with a fresh fictional external package,
the explicit CLI, real loopback HTTP/FastAPI, a new dedicated PostgreSQL 18.1
cluster, separate live/test databases, persistent artifact storage, and actual
backend plus PostgreSQL restart. ProjectDB was neither present nor accessed.
Both native v0.2 reports were accepted as a valid chain and retained byte for
byte; v0.1 compatibility retained exact bytes without fabricating context,
Workflow, Harness-session or pin fields. Sequential, concurrent and
post-restart replays were idempotent. Safe identity, branch, predecessor and
context conflicts remained immutable rejected evidence and never changed the
accepted projection; unsafe content was rejected before retention.

The external package's 29-path manifest was identical before/after every cloud
operation. A complete canonical HTTP history/projection snapshot was exactly
identical across FastAPI and PostgreSQL stop/start, all nine original objects
verified by receipt afterward, and the artifact manifest was unchanged. SQL
counts for ExecutionEvent, checkpoint, memory revision, Workflow run/step run
and provider operations remained zero. Concrete task authority therefore stayed
inside the local folder.

R2B verification passes 1 Progress Report PostgreSQL test and 13 PostgreSQL
persistence tests without skips, 38 focused Progress Report tests, 3 focused
boundary tests, 43 Workflow Package tests, and 297 full-backend tests. Four
unrelated explicitly gated hosted/live integration tests remain skipped.
Compilation succeeds; Alembic has sole current head `20260803_0003` and no
drift. R2 state is now `UPLOAD_ACCEPTED`; R2 is complete with warnings.

R3A statically audited current proxy/provider/authentication infrastructure and
defined a proposed local-Harness Cloud API Proxy boundary without changing
production code. Reusable candidates include canonical JSON/checksum helpers,
provider ports and normalized failures, fake providers, the bounded OpenAlex
adapter behind a new boundary, immutable artifact storage and provider budget/
idempotency concepts. Current OpenAlex execution remains Hosted Mode through
`ExecutionDispatcher -> AgentRuntime -> research Skills`; current SQL
`ProviderOperation` is foreign-keyed to Hosted `WorkflowRun` state and cannot be
relabelled as a Package proxy record. No authenticated principal, project
ownership enforcement or multi-user authorization service exists.

The proposed `reagent.cloud-api-proxy/v0.1` contract binds project, exact
Package/Workflow, capability, Harness, request content, authorization scope and
limits with non-cyclic deterministic identity. Exact replay reuses one durable
operation; changed content under the same key conflicts before provider use;
ambiguous timeouts require an explicit status read. The cloud may perform one
bounded allowlisted provider operation and return untrusted data/provenance. It
must not choose queries, rank papers, synthesize research, call a research LLM,
write local state/Progress Reports, resume a Workflow, accept arbitrary URLs or
chain calls.

Exactly one first capability is recommended for owner review:
`paper.search/v0.1`, bounded scholarly metadata discovery initiated by the
local Harness, with no full text/PDF, ranking, synthesis or LLM. The recommended
MVP access model is a short-lived project/Package capability token stored
outside the Package. Both are proposals. Authentication/issuance, lifetime/
revocation, authenticated project/Package authorization, multi-user isolation,
signing/replay controls, exact limits/budgets, provider eligibility and data
retention/deletion remain `SOURCE_UNDECIDED`. Proposed ADR 0010 remains
**Proposed**.

R3B is a future fake-adapter implementation/acceptance only; R3C is a separately
authorized supervised live-provider acceptance after current provider terms,
auth, rate, cost and retention review. Neither has started. Therefore
`R3B_IMPLEMENTATION_GATE = CLOSED` pending owner decisions.

The optional Next.js **Uploaded Local Progress Reports** view remains deferred,
Claude Code remains untested, automatic Progress Report upload remains absent,
cloud cannot independently prove no-op context bytes without snapshots, and a
missing-predecessor child remains permanently rejected without automatic
re-evaluation or an explicit recovery endpoint. Hosted-work freeze and the
state-authority split remain intact. The next action is owner review of the R3A
decision packet.

### Required reading for future Codex tasks

Before planning product or architecture work, read in this authority order:

1. `Meta-Research-Agent-架构.pdf` directly;
2. `.agent_read/decisions/0009-teacher-aligned-initial-product-boundary.md`;
3. `docs/audits/TEACHER_DESIGN_REQUIREMENT_LEDGER.md` and
   `docs/audits/TEACHER_DESIGN_ALIGNMENT_AUDIT.md`;
4. this context and the current relevant progress report;
5. earlier ADRs and historical plans only where they do not conflict.

## Historical route — Phase 9C-2A (preserved, no longer the V1 mainline)

The following Phase 9C record is preserved as implementation and governance
history. Its provider-activation route is deferred by ADR 0009 and must not be
read as current V1 authorization.

Phase 9C-2A prepared the owner decision package for one future bounded live
grounded-report acceptance. ADR 0008 is **Proposed** and authorizes nothing.
The proposed experiment uses exactly three privately approved real papers,
Anthropic `claude-sonnet-5`, three summary/evidence calls, one claim synthesis,
one report call, and at most one mechanical repair. Proposed Class D live caps
are six logical calls, eight attempts, 60k input/20k output tokens, 15 minutes,
USD 0.75 reservation, and USD 1.00 hard cap. Current authorized spend remains
USD 0.00.

The proposed Phase 9C-2B transport is an injected direct-HTTP implementation of
the existing inactive Anthropic transport protocol using the repository's
existing HTTPX dependency. No new SDK dependency is proposed. It would be
absent from default composition and read `ANTHROPIC_API_KEY` only at an
explicit live backend boundary after separate implementation authority.

Source revalidation confirms that transport injection is necessary but not
sufficient: the current application call boundary rejects configured live
provider names, records generation as non-live with synthetic idempotency
identity, and passes a permissive generic object schema. Phase 9C-2B must add a
narrow opt-in live policy/composition path, live ProviderOperation identity,
and operation-specific supported JSON Schemas while preserving the immutable
V3 workflow and network-free default.

Current policy requires confirmed ZDR for the exact account/workspace/model/
endpoint/features. Standard retention is possible only through an explicit
owner exception that revises the policy. Real title/abstract transmission,
account/key, region, exact private sample, reviewer, budget, network, storage,
retention, implementation, and execution remain unapproved and blocking.
No real paper is identified in committed documentation. Public provider
contracts were rechecked 2026-08-03; exact account ZDR, region, tier, key,
limits, and contractual terms remain unresolved.

Phase 9C-2A changed documentation only. It did not modify source, workflows,
dependencies, migrations, runtime data, or secrets; did not call an LLM or
OpenAlex; and did not generate a real report. Next milestone:
**collect missing account/retention evidence before owner approval or revision
of ADR 0008**. Phase 9C-2B is not permitted yet.

## Verified Phase 9C-1 substrate

Phase 9C-1 implements the accepted Fake/synthetic grounded-report substrate.
Immutable `guided-literature-review@3.0.0` has hash
`c103aa95290ed13407cf5fa5e9984bcd9cd0efb7cc5451176b73c6fbcf1cb0ec`;
V2 remains unchanged at
`af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`.
The static V3 path binds exact approval and abstract-only synthetic sources,
performs one fixture-driven summary/evidence call per paper, one claim
synthesis, one report composition, fail-closed provenance, and publishes 13
checksum-bound artifacts including `literature_corpus.json`.

The provider-independent structured-generation port and an inactive,
transport-injected Anthropic `claude-sonnet-5` adapter substrate exist. Normal
V3 validation uses only `SyntheticGroundedProvider`; no SDK, key lookup,
network, real abstract, OpenAlex call, relevance label, or spend is present.
The one-repair, ProviderOperation, budget, private checkpoint, restart, and
zero-call replay boundaries are implemented.

The Optional Evaluation Module remains **DEFERRED**. Phase 9C-2 remains blocked
on a separate owner decision for exact provider/model/account/key, ZDR and
retention, real-abstract transmission, exactly three real papers, non-zero
budget, isolated storage, report language, and live acceptance gates.

The owner changed V1 priority from real relevance-Judge calibration to the first
real Grounded Literature Report. The automated-relevance work is retained as:

> **Optional Evaluation Module — DEFERRED**

ADR 0006 is Deferred, not rejected or accepted for execution. Its Fake Judge,
contracts, aggregation, audit queue, tests, evidence, calibration design, and
blank review packets remain preserved. No real Judge, label, full-pool
screening, Judge spend, or deletion is authorized.

ADR 0007 is **Accepted with limited implementation scope** and defines an
abstract-only path:

real OpenAlex → exact owner-approved 3–5 papers → immutable
`GroundedReportInput` → staged per-paper summary/evidence → cross-paper claims
→ citation-aware Markdown report → blocking provenance → immutable artifacts
and `literature_corpus.json` → API/UI/restart.

Source inspection showed that `guided-literature-review@2.0.0` and its pinned
skills are Fake-oriented; a real adapter swap alone is insufficient. The
proposal is a new immutable `guided-literature-review@3.0.0` and v2 grounded
skills while preserving the V2 hash
`af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`.

Anthropic `claude-sonnet-5` is accepted only as the first Phase 9C-1 adapter
target under Fake/synthetic network-free tests. No SDK installation, provider
account, key, real call, ZDR/region configuration, real-abstract processing, or
spend is approved. Current LLM budget is USD 0.00. Automatic fallback and
provider comparison remain prohibited.

Approved Phase 9C-1 scope: immutable V3 while preserving V2; exactly 3–5
approved abstract-only papers; summary/evidence per paper, one synthesis/claim,
one report, at most one repair; grounded contracts; deterministic `[P1]`
labels; fail-closed publication; immutable report/corpus artifacts; Fake and
synthetic network-free tests; evaluation module Deferred.

Phase 9C-2 blockers remain: provider account/key, ZDR/retention, permission to
transmit abstracts, non-zero budget, exactly three-paper live sample, local
retention duration, and live acceptance gates. Real OpenAlex reports, fallback/
comparison, full text/PDF, relevance judging, and downstream Idea/Writing
remain unauthorized.

No real LLM/OpenAlex call, report, abstract summary, relevance label, database,
runtime-data, production source, workflow, migration, frontend, or dependency
change occurred in Phase 9C-0.

Next permitted milestone: **implement Phase 9C-1** within the accepted
Fake/synthetic network-free scope. Real calls require a separate Phase 9C-2
owner decision.

## Project authority

- Highest product source: teacher PDF `Meta-Research-Agent-架构.pdf`
- Accepted V1 boundary: `.agent_read/decisions/0009-teacher-aligned-initial-product-boundary.md`
- Current owner-approved sequence: `docs/PROJECT_DEVELOPMENT_PLAN.md`
- Accepted audit: `docs/audits/TEACHER_DESIGN_ALIGNMENT_AUDIT.md`
- Historical hosted architecture contract: `.agent_read/progress/architecture_contract.md`
- Historical foundational decision: `.agent_read/decisions/0001-foundational-architecture.md`, retained where it does not conflict with ADR 0009
- Development environment: `environment.yml`, Conda environment `reagent-dev`

The current repository remains a modular-monolith hosted prototype with
framework-independent core logic and reusable infrastructure. Initial V1
product identity is now the teacher-aligned cloud/local-folder/existing-Harness
system; the current Hosted AgentRuntime path is optional/internal, not default.

## Environment standard

- Python 3.11; verified 3.11.15
- pytest 8.4; verified 8.4.2
- SQLAlchemy 2.x; verified 2.0.51
- Alembic; verified 1.18.5
- psycopg 3 sync/async PostgreSQL driver; verified 3.3.4
- FastAPI 0.139.2 and Pydantic 2.13.4 for the HTTP/DTO boundary
- Uvicorn 0.51.0 as the ASGI server and HTTPX2 2.7.0 for API contract tests
- Node.js 25.2.1 and npm 11.6.4 for the verified frontend toolchain
- Next.js 16.2.10, React 19.2.4, TypeScript 5, Tailwind CSS 4, and TanStack React Query 5.101.3 for the web prototype
- conda-forge only for the resolved environment
- Current verification: `conda run -n reagent-dev pytest -q backend`
- Frontend verification: `npm test`, `npm run lint`, and `npm run build` from `frontend/`
- No Redis, LLM SDK, agent framework, or external service is required by the test suite

## Completed phases

### Phase 1: Domain Core

Implemented in `backend/domain/`:

- Workflow, WorkflowStep, WorkflowRun, StepRun, AgentSession, Checkpoint, ArtifactMetadata
- explicit legal lifecycle transitions and terminal-state protection
- pure mutation/checkpoint `ExecutionCoordinator`
- retry attempts, approval wait/resume, cancellation, checkpoint integrity and recovery

### Phase 2: Workflow Engine

Implemented in `backend/workflow_engine/`:

- immutable `WorkflowDefinition`, `StepDefinition`, `RetryPolicy`, execution snapshots, outcomes, and Engine decisions
- `WorkflowValidator` for duplicate IDs, missing dependencies, cycles, step rules, and static references
- deterministic one-node scheduler using definition order and stable step ID fallback
- recursive exact-reference resolver for `${inputs.name}` and `${nodes.step.outputs.field}`
- pure `WorkflowEngine` returning `StepReady`, `WaitingApproval`, `RetryScheduled`, `WorkflowCompleted`, `WorkflowFailed`, cancellation, approval-completion, or no-action decisions
- `WorkflowExecutionCoordinator` integration that validates optimistic versions and applies decisions through the Domain coordinator
- retry backoff metadata, approval pause/resume, retry checkpoint recovery, output completion, stale snapshot detection, and fail-fast propagation

The Engine itself does not mutate domain state or perform I/O. The integration coordinator is the only Workflow Engine module that applies decisions through Domain APIs.

### Phase 3: Skill System

Implemented in `backend/skill_system/`:

- immutable semantic-versioned `SkillDefinition`, `SkillReference`, `SkillMetadata`, asynchronous `Skill` protocol, and scoped `SkillExecutionContext`
- dependency-free immutable object schemas with nested string, integer, number, boolean, array, and object validation
- explicit version-aware `SkillRegistry` with deterministic listing and duplicate-version rejection
- asynchronous `SkillExecutor` that accepts `StepReady`, verifies the pinned reference and resolved inputs, validates input/output schemas, and returns immutable `SkillResult`
- normalized typed skill errors and JSON-safe result serialization
- deterministic `mock_paper_search` and `mock_summary` skills, registered through an explicit allow list

The executor never applies Workflow Engine decisions and exposes no lifecycle mutation, persistence, network, LLM, file, or tool gateway. No Domain or Workflow Engine source file was changed in Phase 3.

### Phase 4: Agent Runtime Execution Loop

Implemented in `backend/agent_runtime/`:

- asynchronous deterministic `AgentRuntime.run()` orchestration over existing Domain, Workflow Engine, and Skill System contracts
- complete handling for `StepReady`, `WorkflowCompleted`, `WaitingApproval`, `RetryScheduled`, `WorkflowFailed`, `WorkflowCancelled`, `ApprovalCompleted`, and `NoAction`
- explicit ready/running/completion Domain operations with normalized Skill failure evaluation delegated back to Workflow Engine
- immutable per-attempt `AgentExecutionContext` built from workflow inputs, resolved step inputs, latest verified checkpoint, and project/run-scoped working memory
- append-only revisioned in-memory `MemoryStore` with provenance/source references
- idempotent in-memory checkpoint-boundary index over authoritative Domain checkpoints
- checkpoint boundaries before every skill execution, after every skill result, before terminal transitions, and at approval/retry/recovery boundaries
- deterministic yield/resume semantics for approval and retry waits, plus terminal no-op replay

No Domain, Workflow Engine, or Skill System source file changed in Phase 4. Agent Runtime coordinates when those components are called; Engine still owns DAG/retry decisions, Skill System owns capability execution, and Domain still owns legal state transitions.

### Phase 5: Persistence Layer Foundation

Implemented in `backend/persistence/` and integrated into `backend/agent_runtime/`:

- framework-independent `WorkflowRepository`, `CheckpointRepository`, `MemoryRepository`, and `ArtifactRepository` ports
- `UnitOfWork` abstraction spanning all repositories with explicit commit and rollback
- immutable `WorkflowExecutionRecord` mapping that reconstructs detached Domain `ExecutionState`, WorkflowRun, AgentSession, and all StepRun attempts
- append-only `CheckpointRecord` and `MemoryRevision` persistence models
- repository-level `persistence_version` with expected-version validation and typed `StaleStateError`
- deterministic transactional `InMemoryDatabase`/`InMemoryUnitOfWork` adapters with atomic validation-before-apply commits
- duplicate execution idempotency-key and immutable artifact/checkpoint identity protection
- Runtime injection through `UnitOfWork` only; Runtime production code does not import persistence adapters
- boundary commits before Skills and terminal transitions, and atomic aggregate/checkpoint/memory commits after results
- Runtime restore by `workflow_run_id`, with checkpoint verification and continuation through a new Runtime/UoW instance

The former in-memory MemoryStore and CheckpointStore implementations were removed from Agent Runtime and moved behind persistence ports/adapters. Compatibility modules now expose only port/model contracts.

### Phase 5.5: Production Persistence Readiness

Implemented across `backend/execution_events/`, `backend/domain/`, and `backend/persistence/`:

- immutable, project-scoped `ExecutionEvent` records with schema-versioned JSON payloads, severity, request/correlation/causation metadata, and exact workflow-run sequence numbers
- stable v1 event types for workflow start, step start, Skill result, checkpoint creation, approval request, workflow completion, and workflow failure
- append-only `ExecutionEventStore` port with optimistic append, global event identity, ordered reads, latest-sequence queries, and cursor-based replay
- `ApprovalRequest` Domain aggregate with `PENDING`, `APPROVED`, `REJECTED`, and `EXPIRED` lifecycle states
- approval action fingerprints, project/run/step association, policy/role data, expiry, resolver identity, decision idempotency key, reason, JSON metadata, and independent row version
- `ApprovalRepository` with detached reconstruction, persistence-version checks, fingerprint lookup, deterministic run queries, and pending-request recovery
- transactional in-memory event and approval adapters integrated into the existing Unit of Work, including rollback and concurrent stream/version validation

Agent Runtime was intentionally not changed in Phase 5.5. Event emission and creation/resolution of approval requests remain future application-coordinator integration work; the ports now make those transitions implementable atomically with workflow state, checkpoints, memory, and artifacts.

### Phase 6: PostgreSQL Persistence Layer

Implemented in `backend/database/` with migration configuration in `alembic.ini`:

- sync and async psycopg 3 SQLAlchemy engine factories plus frozen-port sync Session factory
- persistence-only SQLAlchemy ORM models; no ORM type crosses into Domain, Workflow Engine, Skill System, Agent Runtime, or persistence ports
- normalized immutable workflow-definition JSON plus canonical SHA-256 content hash
- mappings for workflow definitions/runs, primary agent sessions, ordered StepRun attempts, normalized checkpoints/boundary records, working-memory revisions, artifacts, approvals, and append-only execution events
- `SQLAlchemyUnitOfWork` implementing all six repositories in one PostgreSQL transaction
- SQLAlchemy mapper optimistic concurrency for WorkflowRun and ApprovalRequest persistence versions
- database uniqueness/concurrency constraints for run idempotency, event sequence, checkpoint sequence/identity, memory revision, StepRun attempt/order, artifact version, and project-scoped associations
- Alembic baseline revision `20260721_0001` with reversible upgrade/downgrade and metadata drift check
- reusable adapter contract suite executed against both InMemory and PostgreSQL, plus real Runtime restart recovery

Psycopg 3 was selected because it provides both sync and async connections while the frozen repository ports remain synchronous. The SQL adapter uses sync Sessions; an AsyncEngine factory is verified for future API/worker composition. See `.agent_read/decisions/0002-psycopg3-and-synchronous-persistence-adapter.md`.

### Phase 7A: Application Layer and Backend API Foundation

Implemented in `backend/application/` and `backend/api/`:

- framework-independent commands, read views, stable application errors, and five use-case services for create/get/resume/cancel/approval decisions
- exact create-command idempotency checks, static Workflow validation, Domain-owned cancellation, and baseline checkpoint persistence for newly created runs
- atomic approval resolution: the staged ApprovalRequest update is committed by the same UnitOfWork transaction as Runtime run/step/checkpoint/memory changes
- FastAPI DTOs and endpoints for health, run creation/query/resume/cancel, and approval/rejection
- a composition root that selects `SQLAlchemyUnitOfWork` from `REAGENT_DATABASE_URL`, registers the current deterministic fake skills, and builds request-scoped Runtime/application services
- request-scoped UoW cleanup and transport-only exception mapping (`404`, `409`, `422`, `503`) without exposing ORM models
- InMemory API contract tests covering create/get, complete resume, idempotent resume, exact request idempotency, approval resume, cancellation, invalid definitions, not-found behavior, and health without infrastructure

The API routers and DTOs do not import SQLAlchemy, database adapters, ORM models, or database sessions. Only the composition root selects a concrete database adapter.

### Phase 7B: Backend Product Readiness

Implemented across `backend/agent_runtime/`, `backend/application/`, `backend/api/`, and persistence adapters:

- Agent Runtime now appends the seven frozen `ExecutionEventType` values at actual execution boundaries through `UnitOfWork.events`; event sequence, state mutation, checkpoint, memory, and approval writes share Runtime commits
- the execution stream starts with `WORKFLOW_STARTED`; Runtime-created step/result/terminal checkpoints produce `CHECKPOINT_CREATED`, and Skill success/failure and workflow completion/failure produce their typed audit events
- `WaitingApproval` now creates a fingerprinted, expiring `ApprovalRequest`, emits `APPROVAL_REQUESTED`, records the waiting checkpoint, and commits all wait-state data atomically
- approve resumes the exact fingerprinted action, while reject and on-command expiry cancel the run; the ApprovalRequest resolution is staged before dispatch and committed by Sync Runtime with workflow state
- query services and HTTP DTOs expose paginated/status-filtered runs, ordered event timelines, paginated/status-filtered approvals, and the catalog of persisted immutable Workflow definitions
- `ExecutionDispatcher`/`ExecutionRequest` separate application/API execution submission from Runtime; `SyncExecutionDispatcher` is the current inline adapter and is replaceable by a future worker dispatcher
- both InMemory and SQLAlchemy repository implementations support the new run/approval/catalog queries without exposing ORM models above the adapter boundary

The API layer remains transport-only. Resume and approval services depend on `ExecutionDispatcher`, Runtime still owns orchestration, Workflow Engine still owns scheduling/approval decisions, and all persistence goes through the existing Unit of Work.

### Phase 8A: Frontend Vertical Slice

Implemented in `frontend/` without changing backend behavior:

- Next.js App Router application with TypeScript, Tailwind CSS, and a root TanStack React Query provider
- centralized typed API client in `frontend/api/client.ts`; React components never call `fetch` directly
- same-origin `/backend/*` browser requests forwarded by a configurable Next.js rewrite to `REAGENT_API_URL`, avoiding a new FastAPI CORS dependency
- dashboard with available workflows, recent runs, run status, and pending-approval count
- workflow catalog with a guided approval/search/summary prototype definition, editable initial inputs, and create-then-execute interaction
- run detail with polled run status, deterministic step progress, ordered execution timeline, and explicit resume action for yielded runs
- approval queue with pending/all filtering, optional reviewer reason, approve/reject actions, and cache invalidation across runs, approvals, and event timelines
- frontend component tests covering workflow-list rendering, run-status rendering, event-timeline ordering/content, and approval interaction

The frontend is a separate consumer of the frozen HTTP contract. It has no imports from backend modules and does not own workflow, approval, or execution business rules.

### Phase 8B: Reproducible End-to-End Demo Integration

Implemented across `demo/`, `backend/demo/`, `backend/integration/`, Docker/Make infrastructure, and the existing frontend:

- frozen `guided-literature-review@1.0.0` demo definition with canonical SHA-256 hash `2e58bc1702f0393230c7f0e76d64f4b35684b709abf0597352498d508f45457f`
- adapter-level, transaction-bound seed command that validates the Workflow DAG and pinned deterministic fake Skills, publishes exactly one immutable definition, and fails on identity/content drift
- PostgreSQL, one-shot migration, one-shot seed, FastAPI, and standalone Next.js Compose services with health-gated dependencies and a named database volume
- repository-root Make lifecycle for configuration, startup, status/logs, seed replay, reset, shutdown, and all backend/frontend/integration/browser tests
- real HTTP-to-PostgreSQL test covering migration, idempotent seed, run creation, approval wait, HTTP approval, completion, ordered events, final output, application reconstruction, and no-op replay
- real Playwright/Chrome scenario covering the visible create -> approval -> approve -> completion -> timeline -> reload-persistence path without API mocks
- backend-owned catalog bootstrap replaced the frontend-only fallback definition; completed run output is now visible on the run page
- `DEMO.md` documents local Conda and Docker workflows, exact lifecycle commands, manual walkthrough, troubleshooting, reset behavior, and limitations

No frozen Domain, Workflow Engine, Skill System, Runtime lifecycle, or persistence port contract changed. The demo publisher is an administrative PostgreSQL adapter entrypoint because the frozen `WorkflowRepository` intentionally has no definition-publication operation. No ADR was required.

### Phase 9A-0: First Real Research Vertical Slice Contract

Documentation-only architecture/product contract completed in `.agent_read/progress/real_research_vertical_slice_contract.md`:

- proposed immutable `guided-literature-review@2.0.0` sequential DAG from query validation through real search, deterministic normalization/ranking, approval, permitted source retrieval, grounded synthesis, report generation, and artifact persistence
- frozen conceptual schemas for ResearchQuery, PaperRecord, SourceContent, RankedPaper, CitationReference, EvidenceUnit, GroundedClaim, ResearchReport, and ProviderUsage
- provider-neutral PaperSearchProvider, SourceContentProvider, LLMProvider, and ArtifactContentStorage boundaries
- claim -> evidence -> paper -> citation validation gates and immutable artifact set (`papers.json`, selected papers, source content, summaries, evidence, `report.md`, provenance, usage)
- additive application/API/frontend plan for catalog-pinned run creation, candidate approval preview, report/citation display, artifact retrieval, and provider usage
- normalized provider failures, durable budget reservation, restart behavior, four-level test plan, conditional provider recommendations, milestones, and acceptance gates

Proposed ADR `.agent_read/decisions/0003-real-research-provider-and-artifact-boundaries.md` is **not accepted**. It documents two verified implementation blockers: provider calls need a durable pre-call operation/budget ledger, and approval-node inputs must be resolved by Workflow Engine so Runtime can fingerprint the exact paper selection without taking over reference resolution. The proposal adds ports and one UoW repository but does not change Domain lifecycle or module ownership.

Provider/model capabilities, pricing, rate limits, authentication, and terms were not checked online because Phase 9A-0 prohibited external-service calls. OpenAlex and OpenAI are conditional initial recommendations only; owner approval and current official-document verification remain required before real adapter work.

### Phase 9A-1: Contract Substrate and Local Artifact Storage

Implemented the provider-independent substrate for
`guided-literature-review@2.0.0` without a real provider, network call, SDK, or
credential:

- immutable, canonical-JSON research contracts for queries, papers, source
  scope, ranking, citations, evidence, grounded claims, reports, provider
  identity/usage/budgets/operations, and provenance manifests;
- a pure fail-closed provenance validator connecting report labels ->
  CitationReference -> selected PaperRecord and GroundedClaim -> EvidenceUnit
  -> checksum-matched SourceContent, with version, DOI, source-scope, artifact
  checksum, and unsettled-provider-operation gates;
- framework-independent PaperSearchProvider, SourceContentProvider, LLMProvider,
  and ArtifactContentStorage ports plus network-free deterministic synthetic
  provider adapters;
- injected-root LocalFilesystemArtifactStorage with default composition root
  `runtime_data/artifacts`, relative keys, traversal/symlink rejection,
  immutable atomic-create semantics, idempotent replay, and read-time SHA-256
  verification;
- ProviderOperationRepository added to UnitOfWork, InMemory and SQLAlchemy
  adapters, fail-closed reservation/settlement services, and Alembic revision
  `20260721_0002`;
- `WaitingApproval.resolved_inputs`, Engine-owned approval reference resolution,
  and Runtime fingerprints binding workflow/run/step/expiry, resolved candidate
  selection, artifact checksum, role, and pinned Skill versions;
- deny-by-default Skill capabilities, an optional rich SkillExecutionOutput,
  ProviderUsage/artifact propagation, provider-error normalization, and the
  minimal enum/string/numeric constraints needed by research Skills;
- an application-facing artifact gateway that writes immutable bytes first,
  stages existing ArtifactMetadata through UnitOfWork, lists run artifacts, and
  verifies content before reads.

ADR 0003 is accepted only for the additive UnitOfWork provider-operation
repository, Engine-resolved approval inputs, ArtifactContentStorage boundary,
adapter/composition-owned SDK clients, and durable auditable usage/budget
state. It does not select any provider, model, price, key, or live mode. Domain
lifecycle and frozen module ownership did not change.

### Phase 9A-1.5: PostgreSQL Persistence Acceptance Gate

Migration `20260721_0002` and the SQL ProviderOperation adapter are now
accepted against the dedicated local PostgreSQL 18.1 database
`reagent_9a1_acceptance`; `ProjectDB` was never targeted. Verification covers
base/head/downgrade/re-upgrade, two clean Alembic drift checks, schema
constraints/indexes, shared InMemory/SQL lifecycle semantics, budget
reservation and both settlement policies, project-scoped idempotency,
persistence/domain optimistic versions, cross-repository rollback, restart
visibility, actual usage and sanitized diagnostics, project/run/step foreign
keys, and the unsettled-operation provenance gate.

One narrow application-service defect was corrected: failure settlement now
accepts and persists already-normalized diagnostic metadata. Migration `0002`,
persistence ports, lifecycle states, and frozen ownership were unchanged. With
all PostgreSQL and isolated HTTP-test switches enabled, the full backend result
is `123 passed, 0 skipped`; the dedicated database remains at Alembic head for
owner inspection.

### Phase 9A-2: Deterministic Fake-Provider Guided Literature Review v2

Implemented and accepted on 2026-07-27:

- immutable `guided-literature-review@2.0.0`, canonical definition hash
  `af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`,
  with ten auditable steps from query validation through publication;
- nine exact `research.*@1.0.0` Skills using only injected fake Paper Search,
  Source Content, LLM, ProviderOperation, and ArtifactContentStorage
  capabilities;
- three synthetic selected papers, exact fingerprinted approval of paper IDs
  plus immutable `selected_papers.json` checksum, and an application integrity
  check before approval resolution;
- durable zero-cost ProviderOperation reservation before every fake call,
  RUNNING transition before invocation, and settled usage after invocation;
- eight immutable artifacts: `papers.json`, `selected_papers.json`,
  `source_content.json`, `paper_summaries.json`, `evidence.json`, `report.md`,
  `provenance.json`, and `usage.json`;
- fail-closed provenance linking four GroundedClaims to three EvidenceUnits,
  abstract-only SourceContent, three approved PaperRecords, three citations,
  report labels `[P1]`–`[P3]`, version evidence, artifact checksums, and nine
  settled ProviderOperations;
- catalog-pinned run creation, artifact/content and sanitized provider-usage
  APIs, plus frontend input, candidate review, report/citation/artifact/usage,
  reload, and mobile-width coverage.

No migration was required; Alembic head remains `20260721_0002`. No real
provider, model, price, credential, SDK, network call, worker, authentication,
Redis, S3, or Docker remediation was added. Frozen ownership remained intact,
ADR 0003 remains governing, and no new ADR was needed.

Acceptance used only `reagent_9a2_acceptance` and isolated roots under
`/private/tmp`; `ProjectDB` and `reagent_9a1_acceptance` were not modified.
Final backend result with all PostgreSQL switches enabled: `130 passed, 0
skipped`. Frontend: `5 passed`, lint success, production build success.
Playwright real-stack result: `2 passed`, including the complete v2 path.

The next milestone is supervised selection and verification of the first real
Paper Search Provider boundary. It must not add a real LLM yet. Entry requires
owner decisions on primary/fallback provider, credentials, abstract policy,
recorded fixtures, request/cost caps, attribution and retention, followed by
current official-provider documentation review.

## Domain contract refinements in Phase 2

- `WorkflowStep` now carries `retry_backoff`, `retry_initial_seconds`, and `retry_max_seconds` in addition to `max_attempts`.
- `StepRun` can receive resolved immutable inputs only while transitioning to `READY`.
- Domain `ExecutionCoordinator.start_execution` no longer marks root nodes ready.
- Completing a StepRun no longer derives downstream readiness or workflow outputs.
- Domain coordinator now exposes explicit `mark_step_ready`, `complete_workflow`, and `fail_execution` mutation operations.
- Ready-node selection, input/output resolution, completion decisions, and retry scheduling policy now belong exclusively to Workflow Engine services.

These changes remove overlapping scheduling rules and preserve the frozen dependency direction: Workflow Engine depends on Domain, while Domain does not import Workflow Engine.

## Verification status

Command: `conda run --no-capture-output -n reagent-dev pytest -q backend`

Phase 8B fast-backend verification passes with 67 tests and 8 explicitly environment-gated PostgreSQL tests skipped; compilation passes. With both PostgreSQL variables set to a dedicated local PostgreSQL 18.1 database and destructive reset explicitly enabled, the complete backend suite passes all 75 tests. The demo seed was invoked twice after that suite and returned the same hash with `status: unchanged` both times.

Frontend verification passes with 4 Vitest files/5 tests, ESLint, and the Next.js 16.2.10 production build. Playwright executed the complete real UI/FastAPI/PostgreSQL path in system Chrome: one test passed in 3.9 seconds after the final screenshot additions. The test attaches five reviewable page captures and verifies timeline sequence, deterministic output, reload persistence, and a 390-pixel mobile-width no-overflow condition.

The Compose YAML and initialization shell syntax were checked, but Docker/Compose was not installed in the validation environment. `make demo-config-check` therefore failed at `docker: No such file or directory`; image builds, Compose model validation, clean Compose startup, health state, reset/restart, and Compose-hosted Playwright were not executed and must not be inferred as passing.

Phase 9A-1.5 validation used PostgreSQL 18.1 through `reagent-dev` and the
isolated `reagent_9a1_acceptance` database. The expanded SQL adapter suite
passes 13 tests, and the full backend suite passes 123 tests with zero skips
when both database variables and isolated-reset opt-in are set. Python
compilation passes, `alembic heads` returns only `20260721_0002`, and both
pre/post migration-replay drift checks report no upgrade operations. Frontend
tests were not rerun because no HTTP endpoint, frontend source, package, or
shared generated API type changed.

## Current limitations and risks

- General workflow publication/catalog administration is not implemented. The Phase 8B demo publisher is intentionally restricted to one hash-pinned fixture and verifies its pinned fake Skill references.
- The Skill schema model remains an intentionally small object-schema subset. It now supports enums plus basic string/numeric bounds, but not unions, full JSON Schema import/export, or cross-field rules.
- Skill execution now has explicit deny-by-default provider/artifact capabilities and usage/artifact results, but it still has no Runtime-enforced deadline/cancellation facade, authorization policy, or general memory gateway.
- InMemory adapters remain test-only. PostgreSQL is now the durable adapter, but worker leases/claims, `not_before` dispatch, and explicit row-lock policies are not implemented.
- The SQL adapter stores immutable Workflow definitions as normalized JSONB with a canonical hash. The catalog API lists definitions already persisted by run creation; independent publication, review state, and catalog administration are not implemented.
- Repository ports remain synchronous. Direct use from an async API event loop requires a thread boundary or a future separately reviewed async persistence contract.
- Retry delay is decision metadata only; the next explicit `run()` call resumes without a clock-based dispatcher or persisted `not_before` enforcement.
- Runtime creates approvals automatically and the API exposes discovery and decisions, but approval-role authorization and proactive expiry scheduling are not implemented. Expiry is enforced when a decision is attempted.
- Execution events are durable audit-stream contracts, not a delivery outbox; post-commit notification delivery, consumer deduplication records, and retention policy remain unimplemented.
- ArtifactRepository continues to store metadata only; local immutable bytes now use ArtifactContentStorage, but S3/object storage, atomic cross-resource commit, orphan-content collection, download APIs, and retention enforcement remain unimplemented.
- The Phase 7B API is request/response only. `SyncExecutionDispatcher` executes inline until a terminal/yield state; no worker queue, lease, durable dispatch record, timeout facade, progress stream, or cancellation signal exists.
- No authentication/authorization, project/user repository, LLM provider, upload API, or external artifact byte storage exists. List APIs are not yet protected or scoped by an authenticated actor.
- API endpoints currently call frozen synchronous repository ports from async path operations. This is correct functionally but can block the event loop under PostgreSQL load; add an explicit worker-thread execution boundary or separately reviewed async ports before production concurrency.
- The real HTTP integration test resets its explicitly opted-in isolated database. Compose provisions `reagent_test`, but non-Compose runs still require the operator to create a safe isolated PostgreSQL database.
- Current modules remain task-mandated `backend/...` paths rather than the eventual `backend/src/reagent/...` packaging layout.
- V1 remains sequential and does not support conditions, loops, dynamic graphs, or multi-agent scheduling.
- The UI remains a development prototype: it has no authentication/authorization, project switcher, persisted user preferences, formal accessibility audit, localization, telemetry, or cross-browser suite.
- Frontend mutations currently use fixed prototype actor/project identities. These must come from an authenticated project/user context before multi-user use.
- Run and approval freshness uses polling. Server-sent events/WebSockets, offline behavior, notification delivery, and background worker progress remain future work.
- Fake mode remains the default and deterministic. The opt-in OpenAlex Paper
  Search adapter passed one supervised real-provider acceptance on 2026-07-28;
  SourceContent and LLM remain fake and paper identity remains unverified.
- The backend catalog contains the seeded immutable demo definition, but there is still no general workflow publication/review lifecycle.
- Docker/Compose could not be executed in the Phase 8B validation host. Its dependency graph and files are implemented but require validation on a Docker-capable machine.
- The in-app browser surface was unavailable. Visual QA used five real Playwright screenshots from system Chrome; loading, empty, and failure components are covered by implementation/unit inspection rather than a separate manual interactive browser session.
- The deterministic Guided Literature Review v2 Skills/DAG, artifact APIs/UI,
  provider-independent contracts, local storage, provider-operation
  persistence, provenance validation and approval binding are implemented.
  Phase 9B-1 adds only OpenAlex discovery; no real SourceContent, LLM,
  independent verifier, DOI fallback or full text exists.
- ADR 0003 remains governing. ADR 0004 is Accepted only for OpenAlex primary
  discovery and future candidate roles; no real LLM/model, S2/Crossref adapter,
  live credential, S3 backend or retention enforcement has been selected.
- The dedicated Phase 9A-1.5 database is intentionally retained at head for inspection; it is test-only and must not be mistaken for a production database.

## Phase 9B-0: Paper Search Provider evidence review

Documentation-only evidence review completed on 2026-07-27 with
`PASS_WITH_WARNINGS`. Current official OpenAlex, Semantic Scholar Academic Graph
and Crossref REST contracts, independent coverage/metadata/search research,
PRISMA-S, PaperQA2, OpenScholar, and the teacher-recommended Academic Research
Skills repositories were reviewed. No provider API was called and no runtime,
dependency, database, migration or application source was changed by Phase 9B-0.

At Phase 9B-0 completion ADR 0004 was **Proposed**. The owner subsequently
accepted its limited OpenAlex-only implementation scope for Phase 9B-1. Its
layered target remains:

```text
OpenAlex discovery
→ Semantic Scholar selected/ambiguous verification and enrichment
→ Crossref agency-aware DOI fallback
```

The B0 unresolved decisions were intentionally surfaced rather than silently
decided; Phase 9B-1 resolved only the OpenAlex role, zero-cost supervised caps,
abstract-only scope, synthetic committed fixtures and attribution.

## Phase 9B-1: Supervised OpenAlex Paper Search adapter

ADR 0004 is **Accepted with limited scope**. Implemented:

- `OpenAlexPaperSearchProvider` behind existing `PaperSearchProvider`;
- injected HTTP/configuration and explicit fake-default/openalex-opt-in
  composition (`REAGENT_PAPER_SEARCH_PROVIDER`,
  `REAGENT_OPENALEX_LIVE_ENABLED`, `REAGENT_OPENALEX_API_KEY`);
- versioned `SearchPlan`, `SearchExecution`, `SearchStatistics` contracts and
  immutable `search_plan.json`, `search_execution.json`,
  `search_statistics.json`;
- deterministic OpenAlex Work → current `PaperRecord` mapping, exact DOI/ID
  dedup, advisory title/year clusters, untrusted-content validation;
- free-credit `/rate-limit` preflight, max 3 discovery attempts, 15-second
  timeout, max 20 candidates, full-workflow request cap 12, monetary budget 0;
- durable live `ProviderOperation` reservation/RUNNING/settlement/replay
  behavior and sanitized failures;
- provider-aware downstream fake SourceContent/Fake LLM report wording and
  OpenAlex attribution without changing the immutable v2 workflow.

Verification on 2026-07-27:

- fast backend: `137 passed, 18 skipped`;
- isolated `reagent_9b1_acceptance`: PostgreSQL contracts, fake-v2 HTTP
  regression and OpenAlex-shaped network-free HTTP vertical slice:
  `16 passed, 0 skipped`;
- compileall exit 0; Alembic head remains `20260721_0002`;
- live OpenAlex smoke/full path: **not executed** because no owner-supplied key,
  query and live retention authorization were provided;
- frontend regressions were not run because API DTOs, shared frontend types and
  visible route/component behavior did not change.

No migration, dependency, frontend source, Semantic Scholar, Crossref, real
SourceContent, real LLM, full text, worker, authentication or Docker change was
added. `ProjectDB`, `reagent_9a1_acceptance`, and
`reagent_9a2_acceptance` were not modified. The dedicated
`reagent_9b1_acceptance` and `/tmp/reagent_9b1_pg_artifacts.Xo4fgn` are retained
for review.

## Phase 9B-1 Live Acceptance

Supervised real OpenAlex acceptance completed on 2026-07-28 with **PASS**:

- query `persistent research agents`, years 2020–2026, one page/max 20；
- final live gate `1 passed in 8.97s`；
- final result：20 normalized candidates、3 technically selected、exact
  approval、FakeSourceContent、FakeLLM、`publishable=true` provenance、
  11 checksum-verified artifacts、restart/reload/idempotent completed resume；
- final run has 9 `SUCCEEDED/SETTLED` operations and zero unsettled；OpenAlex
  used 2 requests、0 retries、`$0.001` free provider credit、0 out-of-pocket；
- three bounded live discovery attempts were used across diagnosis/final
  acceptance，6 total OpenAlex calls、0 retries、`$0.003` free credit；
- verified live remediations：discard credential-bearing httpx exception
  context；use escaped term-level Boolean AND instead of a whole-topic exact
  phrase；clamp 20-candidate rank scores to `[0,1]`；
- credential leakage audit：tracked files、database、events/diagnostics、
  artifacts 和 reports 全部 no；
- retained DB：`reagent_9b1_live_acceptance`（15 MB）；
- retained ignored root：
  `runtime_data/acceptance/openalex-live/run.0wOip3`（564 KiB）；
- `ProjectDB` and prior acceptance databases untouched；no commit。

Evidence：
`.agent_read/progress/openalex_live_acceptance.md`。

Next permitted milestone：**Phase 9B-2 human-reviewed OpenAlex discovery
evaluation and retention review**。保持 OpenAlex supervised/opt-in、
FakeSourceContent/FakeLLM、abstract-only；在 evaluation 证明具体 gap 前不实现
Semantic Scholar、Crossref 或真实 LLM。

## Phase 9B-2A: OpenAlex evaluation harness and retention policy

2026-07-28 已实现 provider-evaluation infrastructure，未执行 live pilot：

- pure package：`backend/research/evaluation/`；
- immutable topic/candidate/judgment/adjudication/run/metric contracts；
- 12-topic tracked engineering set：
  `evaluation/topics/openalex_v1.json`；
- candidate-pool generator 复用现有 `PaperSearchProvider`、
  `ProviderOperationService`、`ProviderExecutionPolicy` 和
  `ArtifactContentStorage`；
- evaluation-only append-only/checksum-chained ProviderOperation journal
  implements the existing repository port under the ignored run root；reserve、
  RUNNING、settlement independently fsync，restart/tamper/unsettled fail closed；
- per-topic immutable manifests/checksums、settled-operation evidence 和
  completed-manifest resume；完整 manifest 存在时不重复 provider call；
- JSON/CSV human review sheets、identity-bound import、human adjudication
  source-hash validation；
- deterministic Precision@5/10、nDCG@10、metadata/dedup/operations/manual
  burden 和 Cohen kappa；invalid Recall、CANNOT_JUDGE 或 partial labels 返回
  unavailable，不伪造 denominator；
- deterministic evaluation artifacts/report；report 不复制 full abstracts，
  区分 measured judgments、Class D thresholds、limitations 和 inference；
- single CLI：`python -m backend.research.evaluation`；live generation 默认
  拒绝，必须显式 `--live`，单批最多 3 topics；
- proposed review/retention/topic policies 位于
  `docs/evidence/OPENALEX_*`。

本阶段没有新增 migration/schema、API/frontend、dependency、Semantic
Scholar、Crossref、real LLM/full text。默认 output root
`runtime_data/evaluations/openalex/` 继续 ignored；没有 live candidate pool、
abstract、judgment 或 credential 生成/提交。

验证：focused evaluation `22 passed`；完整 network-free backend
`161 passed, 18 skipped`；compileall exit 0；isolated PostgreSQL adapter
regression `14 passed`，Alembic current/head `20260721_0002`、check no drift。
Live pilot not executed；frontend tests not required。

一次 SQL composition probe 证明 production `provider_operations` FK 必须绑定
真实 WorkflowRun，因此 evaluation harness 没有伪造 lifecycle row，改用
journaled existing port。Probe database `reagent_9b2a_harness_test` retained at
head（8,820,415 bytes，business rows zero）；不得误作产品数据库。

当前阶段：**Phase 9B-2A implementation complete；human-reviewed evaluation
尚未开始**。下一允许里程碑只有：owner 批准 reviewers、retention 和 thresholds
后执行 **Phase 9B-2B bounded three-topic candidate-pool pilot + two-human
review/adjudication**。在结果产生并 review 前不得推荐 S2、Crossref 或 real LLM。

## Phase 9B-2B-1: Three-topic OpenAlex pilot

2026-07-28 bounded live pilot completed with **PASS_WITH_WARNINGS** and stopped
at `WAITING_FOR_HUMAN_REVIEW`:

- evaluation ID `openalex-three-topic-pilot-v1`;
- selected existing topics: `cs-machine-unlearning`,
  `social-algorithmic-management`,
  `nonenglish-chinese-digital-humanities`;
- six requests total (three free-credit preflights + three Works pages), zero
  retries, `$0.003` provider-reported free credit, zero owner out-of-pocket;
- first two topics normalized 20 candidates each; Chinese/Unicode topic returned
  one record which was rejected by the frozen safe field-length gate, leaving
  an empty third pool; no replacement was fabricated;
- all three ProviderOperations `SUCCEEDED/SETTLED`, zero unsettled;
- replay returned `resumed` and kept request count 6;
- two independent blank JSON/CSV packets plus blank adjudication template and
  checksum manifest generated under ignored private storage;
- shared review set: 40 candidates; no label, judgment, adjudication or quality
  metric generated;
- abstract previews expire 2026-08-11 UTC; pools/journal expire 2026-08-27 UTC;
- focused evaluation `24 passed`; full backend `163 passed, 18 skipped`;
  compileall exit 0; no PostgreSQL/frontend test required.

Current state: **WAITING_FOR_HUMAN_REVIEW**. Next permitted milestone is only
**Phase 9B-2B-2 — import two human judgment files, independent human
adjudication, then metric report**. Do not implement S2, Crossref, real LLM or
full text.

## Phase 9B-2C-0: Automated silver evaluation and multilingual search contract

2026-07-29 documentation/evidence/architecture contract completed. The proposed
prototype objective is now:

**Automated silver-label relevance evaluation with targeted human audit.**

This proposal does not create expert ground truth and does not assess scientific
method, credibility, novelty, venue quality, causal validity, claim truth, or
overall merit. The higher-rigor two-human blind method is deferred due to scope
and reviewer availability, not declared incorrect. Existing blank reviewer A/B
packets remain retained and untouched.

Proposed ADR:

`.agent_read/decisions/0005-automated-relevance-judge-and-multilingual-search.md`
— status **Proposed**, not Accepted.

The contract freezes conceptual immutable judgment/audit schemas, a five-label
preview-only rubric, two pointwise prompt versions, limited mirrored pairwise
consistency, conservative automated dispositions, targeted/random human audit,
raw versus audited silver metrics, provider-independent judge/prompt registry,
reuse of ArtifactContentStorage + evaluation journal + ProviderOperationService,
fail-closed cost limits, and deterministic multilingual QueryVariant/
MultilingualSearchPlan provenance, exact DOI/ID merge, advisory title/year
clusters, and coverage diagnostics.

Conditional provider recommendation is to calibrate OpenAI `gpt-5.6-terra` and
compare a bounded subset with Anthropic `claude-sonnet-5`; this is Class D policy
and not approval. `gpt-oss-20b` is the local/open-weight comparison. Current
authorized judge budget remains USD 0.00.

The Chinese topic remains one provider result and zero candidates. Current
evidence records a generic field-length rejection but not the field or measured
length, so the exact triggered field/limit is unavailable. The later plan adds
safe field-specific diagnostics and fixtures without loosening the boundary or
fabricating a candidate.

No real judge implementation/call, no multilingual search execution, no
translation, no OpenAlex call, no label/import/adjudication/metric, no backend/
frontend/migration/workflow/dependency/database change, and no packet deletion
occurred in Phase 9B-2C-0.

Open owner decisions: adopt silver labels; provider/model/version/key; monetary,
call, token, runtime and failure budgets; repetitions/pairwise policy; confidence
threshold; random audit/cap; treatment of partial and non-English cases;
abstract-preview retention; machine translation; Chinese/English query variants;
silver gain mapping; packet cleanup; and whether expert gold is deferred or
cancelled.

Next permitted milestone: **approve or revise ADR 0005**. Automated judge and
multilingual SearchPlan implementation remain separate later milestones. Do not
implement a real judge until ADR 0005 and provider/model/cost/retention policies
are approved.

## Phase 9B-2C-1: Multilingual SearchPlan and safe diagnostics

ADR 0005 is now **Accepted with limited scope**. Accepted implementation scope:
explicit immutable owner-approved QueryVariants, separate per-variant
ProviderOperations, exact DOI/OpenAlex-ID merge, no fuzzy automatic merge,
query provenance, coverage diagnostics, and safe future field-rejection
diagnostics. Blank reviewer A/B packets remain retained and untouched.

Implemented under the evaluation boundary:

- `reagent-query-variant/v1` and
  `reagent-multilingual-search-plan/v1` canonical contracts;
- four manual Chinese/English variants in
  `evaluation/topics/openalex_chinese_multilingual_v1.json`;
- deterministic definition-order execution, immutable artifacts, exact merge,
  conflict/advisory reporting, and replay without duplicate provider calls;
- field/normalized-length/configured-limit/hash/80-character safe preview
  diagnostics without relaxing validation or storing full rejected values;
- multilingual provenance in new evaluation candidates/review exports;
- evaluation CLI `generate-multilingual`, explicit `--live` only.

Live evaluation `openalex-chinese-multilingual-v1-live` used eight OpenAlex
requests, settled four operations, and produced 20 merged candidates: original
Chinese 1 received/0 normalized/1 safely rejected; Chinese synonym 0; English
pivot 20 normalized from one bounded page; bilingual 0. All declared candidate
languages were English. There were zero exact merges, advisory clusters,
identity conflicts, or cap exclusions. This is coverage/normalization evidence,
not relevance or scientific-quality evidence. Replay was network-free.

The historical Phase 9B-2B-1 rejection remains details unavailable; new evidence
does not backfill it. Retained ignored roots are
`openalex-chinese-multilingual-v1` (local transport failure evidence) and
`openalex-chinese-multilingual-v1-live` (successful acceptance). No database was
created.

Verification: focused research `90 passed`; full backend
`173 passed, 18 skipped`; compileall exit 0. No SQL-specific or frontend tests
were required. No workflow definition, dependency, migration, frontend, API DTO,
real judge, translation, relevance label, or secondary provider changed.

Deferred ADR scope remains: every real AutomatedRelevanceJudge, judge provider/
model/adapter/call/key/non-zero budget, confidence/random-audit threshold,
machine translation, unrestricted query expansion, and real judge prompt.

Next permitted milestone: **automated-relevance-judge substrate using only a
Fake Judge**, including immutable contracts, aggregation input boundary, and
audit-queue scaffolding. Do not implement a real judge until that substrate is
verified and provider/model/cost policies are explicitly approved.

## Phase 9B-2C-2: Fake automated relevance Judge substrate

The synthetic-only automated-silver architecture is implemented. Immutable
contracts cover requests, pointwise judgments, mirrored pairwise consistency,
consensus, human-audit requests/results/queue, and separate raw/audited silver
metric families. An immutable prompt registry exposes pointwise A/B and mirrored
pairwise versions under rubric `reagent-topic-relevance/v1`.

`FakeAutomatedRelevanceJudge` is fixture-driven: it does not interpret candidate
text, uses no network/key/model server, returns fixed zero-cost usage, and can
produce configured disagreement, malformed output, timeout/failure, missing
evidence, and pairwise order bias. The orchestrator reuses immutable artifact
storage, the append-only evaluation journal, and ProviderOperationService. It
requires terminal settlement before aggregation and performs no Judge call on
completed replay.

The committed fixture has 20 wholly invented candidates. The standard synthetic
run attempts 40 pointwise calls, records 37 successful judgments, makes two
mirrored pairwise calls, settles 42 operations, produces 7 `AUTO_ACCEPTED`,
3 `AUTO_REJECTED`, and 10 `NEEDS_HUMAN_REVIEW` consensuses, and queues 10
required plus one deterministic random audit. Raw synthetic Precision@5 is 0.8
and Precision@10 is 0.7; these are fixture-path checks, not provider-quality
measurements. Audited metrics are unavailable because no `HumanAuditResult` is
created. Replay produces zero additional Judge calls.

Policy `reagent-silver-aggregation/TEST_POLICY_ONLY/v1` uses synthetic values
0.80 confidence, 10% topic-stratified random audit with at least one eligible
consensus per topic, and maximum burden 20 with explicit
`AUDIT_CAP_EXCEEDED`. None is approved for a real Judge, and ADR 0005 remains
Accepted with limited scope without extension.

No real OpenAlex candidate was loaded or labeled. Existing live pools and blank
reviewer A/B packets remain untouched. OpenAlex/multilingual search, default
Fake paper search, workflow definitions, database schema, API/frontend, and
dependencies are unchanged.

Verification: focused substrate `15 passed`; focused research `105 passed`;
full backend `188 passed, 18 skipped`; compileall exit 0. The network-free CLI
acceptance `synthetic-silver-v1` is retained under the ignored evaluation root
and verified zero-call replay. No PostgreSQL-specific or frontend run was
required.

Open owner decisions remain the real Judge provider/model/snapshot, pinning and
deprecation response, key and non-zero budget, retention, production confidence
and audit thresholds, candidate authorization, calibration subset/design, and
human review responsibility.

Next permitted milestone: **design and owner-approve a bounded real-Judge
calibration contract and subset**. Do not execute calibration or judge the full
live pool until provider/model/budget/retention and calibration inputs are
explicitly approved.

## Phase 9B-2C-3A: Bounded real-Judge calibration contract

The Fake Judge substrate remains verified. Phase 9B-2C-3A completed a
documentation/evidence/owner-approval contract only. It originally produced
Proposed ADR `.agent_read/decisions/0006-bounded-real-judge-calibration.md`;
Phase 9C-0 subsequently changed its current status to **Deferred** without
rewriting the design below.

Proposed design:

- one primary hosted calibration candidate: Anthropic
  `claude-sonnet-5`, selected as a Class D reproducibility proposal because its
  current canonical ID has an explicit fixed-snapshot contract;
- OpenAI `gpt-5.6-terra` remains the fallback with an unresolved distinct dated
  pin; local `gpt-oss-20b` remains a separate mostly-English engineering option;
- 12 private real candidates: four from each of two English topics and four
  from one multilingual topic, plus three synthetic adapter canaries;
- pointwise prompt A/B for all 15 request candidates and three preselected real
  pairs in both orders;
- one primary human reference for all real cases and a secondary checker for all
  non-English/uncertain/disputed cases plus 25% of remaining English cases;
- supporting-span containment, schema/identity/usage/cost verification,
  ProviderOperation settlement, and zero-call replay;
- 36 logical calls, 42 maximum attempts, 90,000 input and 9,984 output tokens,
  15 minutes, conservative token estimate USD 0.41976, proposed hard cap USD
  0.75;
- hosted requests limited to topic/rubric/schema, title, at most 500 normalized
  preview characters, minimal year/venue, and pseudonymous ID;
- ZDR required; request/response content retained at most 14 days under a
  private ignored root; no raw HTTP body.

All sample, budget, threshold, retry, reviewer, and retention values are
**Proposed Class D policy** and unapproved. Current authority remains USD 0.00.
The owner has not authorized hosted abstract-preview processing or confirmed
ZDR, so real execution is blocked.

No real provider adapter/source, dependency, workflow, migration, frontend,
database, or runtime data changed. No LLM/OpenAlex call, real candidate
selection/label, human import, or real metric occurred. Existing live pools and
blank reviewer A/B packets remain untouched.

Open blocking owner decisions: whether to calibrate; provider/model/exact ID;
key and ZDR organization/region; hosted preview permission/length; 12+3 sample;
primary/secondary reviewers; A/B and pairwise counts; USD/token/runtime/retry
limits; pass/warning gates; multilingual cases; retention; and whether a
comparison model is allowed. Full-pool judgment remains prohibited after
calibration unless separately authorized.

Historical next milestone was approval/revision of ADR 0006. Current route is
governed by the Phase 9C-0 section at the top of this file; bounded calibration
remains deferred and may not execute.
