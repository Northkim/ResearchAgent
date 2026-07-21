# Phase 7A — Application Layer and Backend API Foundation

- Date: 2026-07-21
- Status: Completed
- Environment: `reagent-dev`
- Scope: Application services, FastAPI adapter, dependency composition, and no-service API tests

## Outcome

Phase 7A exposes the existing deterministic Agent Runtime through a transport-neutral application layer and a FastAPI boundary. No Domain, Workflow Engine, Skill System, Agent Runtime, persistence port, ORM model, repository adapter, or migration contract changed.

```text
FastAPI routers + Pydantic DTOs
              |
              v
Framework-independent application services
              |
              v
Domain / Agent Runtime / frozen persistence ports
              |
              v
Composition-selected InMemory or SQLAlchemy adapter
```

## Files created

### Application layer

- `backend/application/__init__.py`
- `backend/application/commands.py`
- `backend/application/errors.py`
- `backend/application/views.py`
- `backend/application/services/__init__.py`
- `backend/application/services/_shared.py`
- `backend/application/services/workflow_runs.py`
- `backend/application/services/approvals.py`

### API layer

- `backend/api/__init__.py`
- `backend/api/app.py`
- `backend/api/composition.py`
- `backend/api/dependencies.py`
- `backend/api/routers/__init__.py`
- `backend/api/routers/health.py`
- `backend/api/routers/runs.py`
- `backend/api/routers/approvals.py`
- `backend/api/schemas/__init__.py`
- `backend/api/schemas/common.py`
- `backend/api/schemas/runs.py`
- `backend/api/schemas/approvals.py`
- `backend/api/tests/__init__.py`
- `backend/api/tests/test_api.py`

## Files modified

- `environment.yml`
- `.agent_read/context.md`
- `.agent_read/progress/api_foundation.md` (this report)

## Environment changes

Added only Phase 7A direct dependencies:

- FastAPI 0.139.2
- Pydantic 2.13.4
- Uvicorn 0.51.0
- HTTPX2 2.7.0 (current Starlette TestClient transport)

The existing Python, pytest, SQLAlchemy, Alembic, and psycopg requirements remain unchanged.

## Application contract

### CreateWorkflowRunService

- constructs immutable Domain Workflow/WorkflowStep entities from a framework-neutral command
- validates the static DAG and references with the existing WorkflowValidator
- validates runtime inputs through the Domain coordinator
- creates a `CREATED` WorkflowRun, primary AgentSession, initial StepRuns, and baseline checkpoint
- atomically persists the aggregate and baseline checkpoint
- returns the existing run only when a repeated project/idempotency key carries the exact same Workflow definition, inputs, actor, and agent profile; drift returns a conflict

### GetWorkflowRunService

- reconstitutes a detached execution through `WorkflowRepository`
- attaches authoritative checkpoints through `CheckpointRepository`
- returns an application read view, never an ORM model

### ResumeWorkflowRunService

- verifies the run exists
- delegates all execution/decision/skill/domain behavior to AgentRuntime
- preserves Runtime idempotent terminal replay and approval/retry yield behavior

### CancelWorkflowRunService

- uses Domain `ExecutionCoordinator.cancel_execution`
- records before-terminal and terminal checkpoints
- writes with the repository expected persistence version

### ApprovalDecisionService

- validates the persisted ApprovalRequest association with the currently waiting StepRun
- enforces action fingerprint matching for approval
- preserves decision idempotency
- stages the ApprovalRequest update and lets AgentRuntime commit it in the same UnitOfWork transaction as the workflow transition, checkpoint, and memory changes

## API contract

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | Liveness only; does not require a database |
| POST | `/runs` | Validate and persist an unstarted run (`201`) |
| GET | `/runs/{id}` | Return aggregate status and Step attempts |
| POST | `/runs/{id}/resume` | Run until completion, failure, retry yield, or approval yield |
| POST | `/runs/{id}/cancel` | Apply canonical Domain cancellation |
| POST | `/approvals/{id}/approve` | Resolve fingerprinted request and resume atomically |
| POST | `/approvals/{id}/reject` | Reject request and cancel the waiting run atomically |

Pydantic request models forbid unknown fields. Application errors map to stable JSON codes with `404`, `409`, `422`, or `503`. ORM models and database sessions are not exposed.

## Dependency injection and composition

- `ApplicationContainer` owns the UoW factory and allow-listed Skill Registry.
- Each persistence request receives one UnitOfWork shared by its Runtime and all five services.
- The default container reads `REAGENT_DATABASE_URL` and selects `SQLAlchemyUnitOfWork`; missing configuration leaves `/health` available while persistence endpoints return `503`.
- Tests inject a fresh InMemoryUnitOfWork over one shared InMemoryDatabase per test.
- UoW cleanup rolls back uncommitted work and closes SQL sessions after the response.

## Tests and verification

API tests cover:

1. health without persistence configuration
2. run creation and retrieval
3. deterministic linear Runtime completion
4. exact command idempotency and drift conflict
5. terminal resume idempotency
6. approval resolution and continued execution
7. Domain-owned cancellation
8. invalid Workflow handling (`422`)
9. unknown run handling (`404`)

Commands:

```text
conda run -n reagent-dev pytest -q backend/api/tests
# 9 passed

conda run -n reagent-dev pytest -q backend
# 54 passed, 7 skipped

conda run -n reagent-dev python -m compileall -q backend
# passed
```

The 7 skipped tests are PostgreSQL integration tests gated by `REAGENT_TEST_DATABASE_URL`; no external service was used in Phase 7A verification. An import-boundary scan found no SQLAlchemy/database/Session/ORM imports in application services, API routers, DTO schemas, or dependencies. OpenAPI contains exactly the seven required paths.

## Remaining limitations

- Runtime pauses on approval but does not automatically create the ApprovalRequest consumed by the approval endpoint. Tests seed the existing frozen port to verify resolution semantics.
- Runtime does not append ExecutionEvents, so there is no durable progress/event query API yet.
- Project/user ownership, authentication, authorization, approval-role enforcement, and multi-tenant access control are absent.
- Resume is inline request work. There is no queue, worker claim/lease, durable dispatch, timeout boundary, or live progress channel.
- Frozen repository ports are synchronous and are currently called from async route operations; this may block the event loop with PostgreSQL under load.
- There are no run-list, approval-list, event-history, workflow-catalog, upload, artifact-content, or readiness endpoints.
- API tests use InMemory adapters only; HTTP-to-PostgreSQL integration remains to be added.
- Only deterministic fake skills are composed. There are no real LLM or external capability providers.

## Recommendation

The backend contract is sufficient to start a thin frontend shell for creating a supplied Workflow definition, viewing one run, resuming/cancelling it, and resolving a known approval ID.

It is not ready for the full product frontend or production traffic. Phase 7B should first add atomic Runtime event emission and ApprovalRequest creation, approval/run discovery endpoints, project/user authorization, a deliberate thread boundary for synchronous UoW work, and a background worker/claim model for long-running resumes.
