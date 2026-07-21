# Production Persistence Readiness

- Date: 2026-07-21
- Status: Completed
- Phase: 5.5 — Execution Events and Approval Persistence Contracts
- Environment: `reagent-dev`
- Architecture: `.agent_read/progress/architecture_contract.md`
- SQLAlchemy/PostgreSQL: intentionally deferred

## Outcome

Phase 5.5 closes the two production-persistence contract gaps identified after Phase 5: append-only execution history and durable human approval gates. Both participate in the existing Unit of Work and have deterministic in-memory adapters. Agent Runtime behavior was not changed.

```text
Application / Agent Runtime (future integration)
                    |
                    v
                UnitOfWork
      +-------------+----------------+
      |                              |
ApprovalRepository          ExecutionEventStore
      |                              |
      +-------------+----------------+
                    v
      InMemory adapters / future SQL adapters
```

## Execution event contract

`ExecutionEvent` is an immutable, project-scoped record with:

- globally unique event identity
- workflow-run association and strict positive sequence
- event type and severity
- schema-versioned, immutable JSON-compatible payload
- request ID plus optional session, step, correlation, and causation IDs
- timezone-aware occurrence timestamp

The v1 taxonomy contains:

- `WORKFLOW_STARTED`
- `STEP_STARTED`
- `SKILL_EXECUTED`
- `CHECKPOINT_CREATED`
- `APPROVAL_REQUESTED`
- `WORKFLOW_COMPLETED`
- `WORKFLOW_FAILED`

`ExecutionEventStore` is append-only. `append(event, expected_sequence=...)` requires a contiguous stream and makes exact duplicate event IDs idempotent while rejecting conflicting content. It also supports global ID lookup, latest sequence, complete ordered reads, and replay after a consumer sequence cursor.

The in-memory event adapter stores streams under `(project_id, workflow_run_id)`. Unit-of-Work commit rechecks the shared committed sequence and globally unique event IDs, so concurrent appenders cannot silently fork or overwrite history.

## Approval contract

`ApprovalRequest` is a mutable Domain aggregate with a single legal transition from `PENDING` to one of:

- `APPROVED`
- `REJECTED`
- `EXPIRED`

The aggregate records:

- approval, project, WorkflowRun, and StepRun identities
- policy key, allowed approver role, requester identity, prompt, and JSON action preview
- fingerprint binding the request to the exact planned action
- request and optional expiry timestamps
- resolver, resolution timestamp, decision idempotency key, reason, and JSON decision metadata
- Domain `row_version`

Approval requires the caller to provide the current action fingerprint. A mismatch prevents approval. Decisions after expiry are rejected until the request is explicitly marked expired. Terminal requests cannot be resolved again.

`ApprovalRepository` maps approval aggregates to detached immutable `ApprovalRecord` values. It provides optimistic persistence versions independent of the Domain row version, lookup by ID or latest matching fingerprint, deterministic run history, and pending-request recovery.

Fingerprint lookup is not a uniqueness constraint: a later request may legitimately repeat the same planned action after an earlier request was rejected or expired. Approval ID remains the persistent identity.

## Unit of Work integration

The Unit of Work now spans:

- workflow executions
- checkpoints
- working-memory revisions
- artifact metadata
- approval requests
- execution-event streams

Approval versions and event sequence counts are validated before any staged repository is published. Commit remains validation-before-apply, and rollback refreshes all six repository views. This prepares a SQL transaction to atomically persist a wait transition, approval request, checkpoint, and audit event.

## Files created

```text
backend/execution_events/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── _immutability.py
│   └── execution_event.py
├── ports/
│   ├── __init__.py
│   └── event_store.py
└── tests/
    ├── __init__.py
    └── test_execution_events.py

backend/domain/models/approval_request.py
backend/persistence/models/approval_record.py
backend/persistence/ports/approval_repository.py
backend/persistence/tests/test_approval_persistence.py
.agent_read/progress/production_persistence_readiness.md
```

## Files modified

- `backend/domain/enums/statuses.py`
- `backend/domain/enums/__init__.py`
- `backend/domain/models/__init__.py`
- `backend/persistence/models/__init__.py`
- `backend/persistence/ports/__init__.py`
- `backend/persistence/ports/unit_of_work.py`
- `backend/persistence/adapters/in_memory.py`
- `backend/persistence/__init__.py`
- `backend/persistence/tests/test_persistence.py`
- `.agent_read/context.md`

## Verification

Commands:

```text
conda run --no-capture-output -n reagent-dev pytest -q backend
conda run --no-capture-output -n reagent-dev python -m compileall -q backend
```

Result: `41 passed`; compilation succeeds under Python 3.11.15.

Coverage added:

1. contiguous event append ordering and out-of-order rejection
2. replay of all seven v1 event types after adapter restart and from a cursor
3. approval, rejection, expiry, terminal-state protection, and fingerprint mismatch
4. pending approval recovery, decision, optimistic update, and detached restore after restart
5. rollback of staged approval and event writes with the existing repositories

## Architecture impact

No frozen architecture decision changed. The implementation instantiates concepts already required by Sections 2.6, 7, 9.2, and 10 of the architecture contract:

- lifecycle transitions can produce ordered audit events
- approval requests can survive worker/process restart
- approval, checkpoint, workflow state, and event writes can share one transaction
- PostgreSQL adapters can enforce sequence, identity, fingerprint lookup, and optimistic-version constraints without leaking ORM types into core modules

Runtime integration was intentionally deferred. Existing Runtime tests and behavior remain unchanged.

## Remaining limitations and SQL requirements

- No SQL tables, ORM mappings, migrations, driver, or database integration environment exists.
- Agent Runtime/Application Coordinator does not yet emit events or create/resolve ApprovalRequests.
- Authorization and permitted-role evaluation remain application-layer responsibilities.
- Expiry data is persisted, but no clock-based expiry dispatcher exists.
- `ExecutionEventStore` provides audit replay, not asynchronous delivery. A transactional outbox and consumer-deduplication contract are still required if events drive notifications or workers.
- In-memory state is not process durable or thread/process safe.
- SQL must enforce unique `(workflow_run_id, sequence)`, global event ID, approval ID, project-scope integrity, optimistic versions, and indexes for pending approvals and run event streams.
- Redaction policy is represented by contract expectations but is not yet an application service.

## Recommendation

The project is ready to begin SQLAlchemy/PostgreSQL implementation. The durable schema now has contracts for every execution-state concept required by the frozen initial schema: runs/sessions/attempts, checkpoints, memory revisions, artifact metadata, approvals, and audit events.

This means SQL table design and Unit-of-Work transaction semantics can be evaluated against executable in-memory contract tests instead of being invented inside ORM code. It does not mean the platform is production-ready: Runtime event/approval wiring, authorization, expiry scheduling, transactional outbox delivery, redaction, and real PostgreSQL integration tests remain required before an execution API is exposed.
