# Phase 7B — Backend Product Readiness

- Date: 2026-07-21
- Status: Completed
- Environment: `reagent-dev`
- Scope: Runtime events, complete approval lifecycle, frontend query APIs, and execution dispatch boundary

## Outcome

Phase 7B makes the existing backend a usable foundation for frontend development without changing the frozen ownership or dependency direction.

```text
FastAPI routes / DTOs
          |
          v
Application services --> ExecutionDispatcher
          |                    |
          |                    v
          |             SyncExecutionDispatcher
          |                    |
          +--------------------v
                         AgentRuntime
                              |
                    Workflow Engine + Skills
                              |
                              v
                     UnitOfWork repositories
                              |
                   InMemory / PostgreSQL adapters
```

No frontend, authentication provider, cloud deployment, queue, Redis worker, or message broker was added.

## Event integration design

`AgentRuntime` now creates `ExecutionEvent` records through `UnitOfWork.events`; it does not import PostgreSQL or an adapter. The Runtime assigns the next contiguous run-stream sequence and includes project, run, agent-session, optional StepRun, request, and correlation metadata.

The emitted v1 events are:

- `WORKFLOW_STARTED` after Domain start transitions are applied
- `STEP_STARTED` when a ready Skill Step becomes running
- `SKILL_EXECUTED` for normalized Skill success or failure
- `CHECKPOINT_CREATED` for Runtime execution-boundary checkpoints
- `APPROVAL_REQUESTED` when a Workflow approval gate is reached
- `WORKFLOW_COMPLETED` with the final output field set
- `WORKFLOW_FAILED` with redacted error metadata

Runtime commits are the atomic boundary. For example, a successful Skill result stages the completed StepRun, `SKILL_EXECUTED`, the after-Skill checkpoint and `CHECKPOINT_CREATED`, and the working-memory revision before one `UnitOfWork.commit()`. Failure and waiting transitions follow the same pattern. The creation-time baseline checkpoint is persisted without an execution event so the execution timeline begins with `WORKFLOW_STARTED`.

The existing in-memory event adapter still validates streams before publishing any staged data. PostgreSQL writes all staged run, checkpoint, approval, memory, and event rows in the existing SQLAlchemy transaction.

## Approval lifecycle

When Workflow Engine returns `WaitingApproval`, Runtime:

1. applies the Engine decision through `WorkflowExecutionCoordinator`, producing `WAITING_FOR_APPROVAL` state and a checkpoint;
2. creates an `ApprovalRequest` associated with the exact project, run, StepRun, attempt, and policy;
3. computes a canonical SHA-256 fingerprint over the planned workflow approval action;
4. sets the configured expiry deadline and persists the pending request;
5. emits `APPROVAL_REQUESTED`, records the waiting checkpoint, and commits once;
6. returns the durable waiting result.

`ApprovalDecisionService` validates the current waiting StepRun and request association. Approval also requires the current fingerprint. The service stages `APPROVED`, `REJECTED`, or `EXPIRED`, then submits an `ExecutionRequest` through the dispatcher. With the current Sync adapter, Runtime commits the approval mutation together with the run/Step/checkpoint transition:

- `APPROVED` resumes, completes the approval Step, and continues the workflow;
- `REJECTED` cancels the waiting run;
- a decision attempted at or after `expires_at` marks the request `EXPIRED` and cancels the run.

Approval expiry is enforced on decision access. There is intentionally no scheduler yet to proactively expire untouched requests.

## Query APIs

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/runs` | Newest-first run page; optional `status`, `offset`, and `limit` (`1..100`) |
| `GET` | `/runs/{id}/events` | Complete execution stream ordered by exact sequence |
| `GET` | `/approvals` | Newest-first approval page; optional `status`, `offset`, and `limit` |
| `GET` | `/workflows` | Stable catalog of immutable definitions already persisted by run creation |

Run and approval pages include `total`, `offset`, and `limit`. Event DTOs expose frontend-oriented `type` and `timestamp` fields plus sequence, severity, payload, and correlation identities. Query routes use application read services and repository ports; they do not access ORM models or sessions.

The frozen persistence abstractions were extended with run page/count, approval page/count, and workflow-definition listing operations. Both InMemory and SQLAlchemy adapters implement them.

## Dispatcher abstraction

`ExecutionDispatcher.submit(ExecutionRequest)` is the application execution boundary. `ExecutionRequest` carries the WorkflowRun identity and optional typed approval outcome.

`SyncExecutionDispatcher` is the current implementation and awaits `AgentRuntime.run()` in the caller process. Resume and approval application services depend on `ExecutionDispatcher`, so FastAPI no longer chooses or invokes Runtime execution directly. A future worker dispatcher can replace the Sync adapter through `ApplicationContainer.dispatcher_factory` without moving workflow or approval business logic into routes.

This phase deliberately does not add a queue, worker claim/lease, durable dispatch row, or Redis.

## Files created

- `backend/application/execution/__init__.py`
- `backend/application/execution/dispatcher.py`
- `backend/application/services/queries.py`
- `backend/application/tests/__init__.py`
- `backend/application/tests/test_dispatcher.py`
- `backend/api/routers/workflows.py`
- `backend/api/schemas/queries.py`
- `.agent_read/progress/backend_product_readiness.md`

## Files modified

- `backend/agent_runtime/runtime/agent_runtime.py`
- `backend/agent_runtime/tests/test_agent_runtime.py`
- `backend/application/__init__.py`
- `backend/application/services/__init__.py`
- `backend/application/services/approvals.py`
- `backend/application/services/workflow_runs.py`
- `backend/application/views.py`
- `backend/api/app.py`
- `backend/api/composition.py`
- `backend/api/dependencies.py`
- `backend/api/routers/__init__.py`
- `backend/api/routers/approvals.py`
- `backend/api/routers/runs.py`
- `backend/api/schemas/__init__.py`
- `backend/api/schemas/approvals.py`
- `backend/api/tests/test_api.py`
- `backend/database/repositories/approval.py`
- `backend/database/repositories/workflow.py`
- `backend/persistence/adapters/in_memory.py`
- `backend/persistence/ports/approval_repository.py`
- `backend/persistence/ports/workflow_repository.py`
- `.agent_read/context.md`

## Tests and verification

Coverage added for the requested scenarios:

- workflow start, Skill result, completion, and failure event emission
- automatic ApprovalRequest creation plus `APPROVAL_REQUESTED`
- approval resume, rejection cancellation, and expiry cancellation
- run list/filter/pagination, event timeline, approval list/filter, and workflow catalog
- API submission through `ExecutionDispatcher` and direct Sync adapter behavior

Commands:

```text
conda run --no-capture-output -n reagent-dev pytest -q backend
# 66 passed, 7 skipped

conda run --no-capture-output -n reagent-dev python -m compileall -q backend
# passed
```

The seven skipped tests are PostgreSQL integration tests gated by `REAGENT_TEST_DATABASE_URL`; no external database was configured for this Phase 7B run. The new SQL query methods compile but have not yet been exercised through end-to-end HTTP/PostgreSQL tests. An import-boundary scan found no database/SQLAlchemy/ORM imports in application services, API routers, DTO schemas, or dependencies; only the composition root imports the concrete database adapter.

## Remaining limitations

- Authentication, authorization, project membership, multi-tenant access checks, and approval-role enforcement are absent. Current list endpoints are not actor-scoped.
- `SyncExecutionDispatcher` still performs execution inline in the HTTP request. There is no queue, worker claim/lease/fencing, durable dispatch request, retry clock, execution timeout boundary, or live event stream.
- Approval expiry is enforced only when a decision is attempted; no background expiry dispatcher exists.
- Frozen persistence ports are synchronous. PostgreSQL calls still need an explicit thread boundary or a separately reviewed async repository contract before high-concurrency traffic.
- The workflow catalog contains definitions persisted as part of run creation. There is no independent publication/review lifecycle, and create-run still accepts an inline Workflow definition.
- Execution events are an audit stream, not a transactional notification outbox. Retention, redaction policy administration, consumers, and live delivery are deferred.
- API tests use InMemory adapters. HTTP-to-PostgreSQL query and approval/event transaction tests remain to be added.
- Only deterministic fake Skills are composed; no LLM/provider, upload pipeline, or artifact byte storage is available.
- Retry timing remains advisory and Runtime is sequential within each run.

## Recommendation

The backend is ready for frontend implementation against the current development API contracts: a frontend can list/create runs, view status and ordered events, discover/respond to approvals, and browse known workflows.

It is not ready for production deployment. The next recommended step is a thin frontend vertical slice using these endpoints while backend work adds project ownership and authentication/authorization first, followed by a durable worker implementation of `ExecutionDispatcher`, explicit synchronous-I/O isolation, and HTTP-to-PostgreSQL integration tests.
