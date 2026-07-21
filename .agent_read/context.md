# ReAgent Compressed Project Context

Last updated: 2026-07-21

## Project authority

- Product source of truth: `docs/PROJECT_DEVELOPMENT_PLAN.md`
- Frozen architecture contract: `.agent_read/progress/architecture_contract.md`
- Foundational decision: `.agent_read/decisions/0001-foundational-architecture.md`
- Development environment: `environment.yml`, Conda environment `reagent-dev`

ReAgent remains a modular-monolith research-agent platform with framework-independent core logic, versioned static DAG workflows, one primary Agent Session per run in v1, durable checkpoint semantics, and future ports/adapters for infrastructure.

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

## Current limitations and risks

- General workflow publication/catalog administration is not implemented. The Phase 8B demo publisher is intentionally restricted to one hash-pinned fixture and verifies its pinned fake Skill references.
- The Phase 3 schema model is an intentionally small object-schema subset; it does not support unions, enums, constraints, or full JSON Schema import/export.
- Skill execution has no deadline/cancellation facade, permission policy, artifact/memory gateway, or usage telemetry beyond deterministic correlation metadata.
- InMemory adapters remain test-only. PostgreSQL is now the durable adapter, but worker leases/claims, `not_before` dispatch, and explicit row-lock policies are not implemented.
- The SQL adapter stores immutable Workflow definitions as normalized JSONB with a canonical hash. The catalog API lists definitions already persisted by run creation; independent publication, review state, and catalog administration are not implemented.
- Repository ports remain synchronous. Direct use from an async API event loop requires a thread boundary or a future separately reviewed async persistence contract.
- Retry delay is decision metadata only; the next explicit `run()` call resumes without a clock-based dispatcher or persisted `not_before` enforcement.
- Runtime creates approvals automatically and the API exposes discovery and decisions, but approval-role authorization and proactive expiry scheduling are not implemented. Expiry is enforced when a decision is attempted.
- Execution events are durable audit-stream contracts, not a delivery outbox; post-commit notification delivery, consumer deduplication records, and retention policy remain unimplemented.
- ArtifactRepository stores metadata only; bytes/object storage, outbox delivery, and retention policies remain unimplemented.
- The Phase 7B API is request/response only. `SyncExecutionDispatcher` executes inline until a terminal/yield state; no worker queue, lease, durable dispatch record, timeout facade, progress stream, or cancellation signal exists.
- No authentication/authorization, project/user repository, LLM provider, upload API, or external artifact byte storage exists. List APIs are not yet protected or scoped by an authenticated actor.
- API endpoints currently call frozen synchronous repository ports from async path operations. This is correct functionally but can block the event loop under PostgreSQL load; add an explicit worker-thread execution boundary or separately reviewed async ports before production concurrency.
- The real HTTP integration test resets its explicitly opted-in isolated database. Compose provisions `reagent_test`, but non-Compose runs still require the operator to create a safe isolated PostgreSQL database.
- Current modules remain task-mandated `backend/...` paths rather than the eventual `backend/src/reagent/...` packaging layout.
- V1 remains sequential and does not support conditions, loops, dynamic graphs, or multi-agent scheduling.
- The UI remains a development prototype: it has no authentication/authorization, project switcher, persisted user preferences, formal accessibility audit, localization, telemetry, or cross-browser suite.
- Frontend mutations currently use fixed prototype actor/project identities. These must come from an authenticated project/user context before multi-user use.
- Run and approval freshness uses polling. Server-sent events/WebSockets, offline behavior, notification delivery, and background worker progress remain future work.
- The guided demo workflow uses the existing deterministic fake Skills. Real research-provider integration, artifact content/download views, uploads, and citation-oriented result presentation are not implemented.
- The backend catalog contains the seeded immutable demo definition, but there is still no general workflow publication/review lifecycle.
- Docker/Compose could not be executed in the Phase 8B validation host. Its dependency graph and files are implemented but require validation on a Docker-capable machine.
- The in-app browser surface was unavailable. Visual QA used five real Playwright screenshots from system Chrome; loading, empty, and failure components are covered by implementation/unit inspection rather than a separate manual interactive browser session.

## Next recommended phase

Remediation of demo integration: execute `make demo-config-check`, a clean `make demo-start`, service health inspection, Compose-hosted integration/Playwright tests, `make demo-reset`, and a second clean startup on a Docker-capable machine. Once that environment-specific evidence is green, begin the first real research vertical slice rather than expanding the demo surface.
