# Persistence Layer Foundation

- Date: 2026-07-20
- Status: Completed
- Phase: 5 — Persistence Ports and In-Memory Adapters
- Environment: `reagent-dev`
- Architecture: `.agent_read/progress/architecture_contract.md`
- Database integration: intentionally deferred

## Persistence architecture

Phase 5 introduces a provider-neutral persistence boundary:

```text
Agent Runtime
      |
      v
UnitOfWork + Repository Ports
      |
      v
InMemoryUnitOfWork / future SQLUnitOfWork
      |
      v
InMemoryDatabase / future PostgreSQL
```

Agent Runtime imports `backend.persistence.ports` and immutable persistence models only. Adapter selection remains application-composition/test responsibility.

## Repository design

### WorkflowRepository

Responsibilities:

- stage a new or updated complete execution aggregate
- reconstruct detached WorkflowRun, primary AgentSession, and StepRun attempts
- retrieve by WorkflowRun ID
- retrieve by project-scoped idempotency key
- expose a repository `persistence_version`
- require `expected_version` for updates

`WorkflowExecutionRecord` explicitly maps mutable Domain entities into immutable record values and back. Domain checkpoint records are attached separately through CheckpointRepository so checkpoint streams remain append-only.

### CheckpointRepository

Responsibilities:

- idempotently append integrity-verified Domain checkpoints
- persist the application boundary that caused each checkpoint write
- return the latest unique Domain checkpoint
- list unique checkpoints in Domain sequence order
- list all boundary records when one checkpoint has multiple semantic labels

Checkpoint boundaries moved from Agent Runtime's concrete in-memory store into the persistence model. `DOMAIN_TRANSITION` captures checkpoints created internally by a coordinator call when only the final checkpoint has a more specific Runtime label.

### MemoryRepository

Responsibilities:

- idempotently initialize project/run working context
- retrieve latest immutable context
- append a merged revision with producer and source references
- list complete revision history

Historical revisions remain immutable; context updates replace only the active view, not prior records.

### ArtifactRepository

Responsibilities:

- save immutable `ArtifactMetadata`
- retrieve by artifact ID
- list project-scoped artifact versions deterministically

Artifact bytes and file/object storage remain outside this repository.

## Unit of Work design

`UnitOfWork` groups:

- workflow execution records
- checkpoint records
- memory revisions
- artifact metadata

It provides explicit `commit()` and `rollback()`. The in-memory implementation stages repository changes in a transaction-local immutable snapshot. Commit validates every dirty stream before applying any change, so a stale workflow/checkpoint/memory write cannot partially publish other repository changes.

`InMemoryUnitOfWork` is reusable after commit/rollback and refreshes its local transaction view from shared `InMemoryDatabase` committed state.

## Optimistic concurrency

The persistence boundary uses an independent integer `persistence_version`:

- inserts require `expected_version=None` and create version 1
- updates require the exact current version and create `expected_version + 1`
- commit validates the expected version against shared committed state
- mismatches raise `StaleStateError` before any dirty repository is applied

This is intentionally separate from `WorkflowRun.row_version`. A persistence transaction can change StepRun attempts, checkpoints, or memory without a WorkflowRun lifecycle transition, so WorkflowRun's own row version is not a sufficient aggregate concurrency token.

Checkpoint and memory streams also compare their committed record/revision counts to reject concurrent append conflicts. Project-scoped workflow idempotency keys are checked both while staging and again at commit.

## In-memory adapter design

`InMemoryDatabase` contains only committed immutable records. Multiple `InMemoryUnitOfWork` instances can share it to simulate:

- process/application restart
- detached aggregate reconstruction
- concurrent readers/writers
- atomic commit and rollback

The adapter does not retain caller-owned mutable ExecutionState references. Every read reconstructs a new Domain object graph.

## Runtime integration changes

`AgentRuntime` now requires an injected `UnitOfWork` and accepts either:

- a new `ExecutionState`, or
- a persisted `workflow_run_id`

For persisted IDs, Runtime:

1. loads a detached execution through WorkflowRepository
2. attaches ordered checkpoints from CheckpointRepository
3. verifies latest checkpoint integrity
4. records the current persistence version
5. resumes Engine/Domain execution from that reconstructed state

Runtime commits at recovery boundaries:

- initial aggregate/context/checkpoint
- initialized run
- StepRun READY checkpoint
- StepRun RUNNING before Skill dispatch
- Skill success/failure with checkpoint and memory revision
- approval/retry wait and recovery
- before terminal transition
- terminal state/checkpoint

The `_commit` path stages the execution aggregate, synchronizes all Domain checkpoints, and commits workflow/checkpoint/memory changes through one UnitOfWork. On any repository/commit error it rolls back staged state and propagates the typed failure.

The old Agent Runtime `MemoryStore` and `InMemoryCheckpointStore` implementations were deleted. Agent Runtime compatibility packages expose only `MemoryRepository`, `CheckpointRepository`, and persistence record types.

## Files created

```text
backend/persistence/
├── __init__.py
├── adapters/
│   ├── __init__.py
│   └── in_memory.py
├── models/
│   ├── __init__.py
│   ├── _immutability.py
│   ├── checkpoint_record.py
│   ├── execution_record.py
│   └── memory_record.py
├── ports/
│   ├── __init__.py
│   ├── artifact_repository.py
│   ├── checkpoint_repository.py
│   ├── errors.py
│   ├── memory_repository.py
│   ├── unit_of_work.py
│   └── workflow_repository.py
└── tests/
    ├── __init__.py
    └── test_persistence.py
```

## Existing files modified

- `backend/agent_runtime/__init__.py`
- `backend/agent_runtime/checkpoint/__init__.py`
- `backend/agent_runtime/context/execution_context.py`
- `backend/agent_runtime/memory/__init__.py`
- `backend/agent_runtime/runtime/agent_runtime.py`
- `backend/agent_runtime/tests/test_agent_runtime.py`
- `.agent_read/context.md`
- `.agent_read/progress/persistence_foundation.md` (this report)

## Files removed

- `backend/agent_runtime/checkpoint/checkpoint_store.py`
- `backend/agent_runtime/memory/memory_store.py`

Their implementation responsibility now belongs to `backend/persistence/adapters/in_memory.py`.

## Tests

Five Persistence Foundation tests cover:

1. save and detached restore of a complete workflow execution
2. retry-checkpoint recovery after a simulated adapter/application restart
3. idempotent terminal Runtime resume through a fresh UnitOfWork
4. stale concurrent update rejection using expected persistence versions
5. rollback of staged workflow, checkpoint, memory, and artifact changes

The six Phase 4 Agent Runtime tests were migrated to explicit in-memory adapter composition. Retry recovery and terminal idempotency now use fresh Runtime/UoW instances over shared committed state.

Commands:

```text
conda run --no-capture-output -n reagent-dev pytest -q backend
conda run --no-capture-output -n reagent-dev python -m compileall -q backend
```

Latest result: `37 passed`; compilation passes under Python 3.11.15.

## Architecture changes

No frozen architecture decision changed. This phase instantiates the accepted ports/adapters, PostgreSQL authority, optimistic concurrency, checkpoint recovery, and Unit of Work boundaries without selecting an ORM representation yet.

The independent repository `persistence_version` refines implementation of aggregate concurrency; it does not replace Domain lifecycle `row_version` fields.

## Remaining limitations

- InMemoryDatabase is process-local, synchronous, and not thread/process safe.
- There is no SQLAlchemy mapping, SQL transaction, Alembic migration, PostgreSQL driver, or integration environment.
- Workflow definitions remain immutable Python values inside in-memory records; SQL storage needs normalized JSON/version/hash mapping.
- ApprovalRequest, execution logs/events, outbox delivery, idempotency-command records, retry `not_before`, leases, and worker claims are not persisted yet.
- ArtifactRepository stores metadata only; content bytes and storage promotion semantics are deferred.
- MemoryRepository implements working context only; long-term entries, source tables, retention, and pgvector are deferred.
- Ports are synchronous for the first adapter. Async database/worker integration may require an async UoW variant without changing Domain behavior.
- Repository contract tests currently target the deterministic adapter; PostgreSQL must run the same semantics plus database-specific isolation tests.

## Recommended next step

The project is ready to implement SQLAlchemy/PostgreSQL behind these ports:

1. add SQLAlchemy 2.x and a PostgreSQL driver to the development environment
2. define tables/mappings for immutable workflow versions, workflow runs, agent sessions, StepRun attempts, checkpoints, memory revisions, and artifact metadata
3. implement `SQLUnitOfWork` and repository adapters without importing them into Runtime or Domain
4. create an Alembic baseline migration with unique idempotency/version/sequence constraints
5. run the existing repository contract suite against PostgreSQL
6. add transaction-isolation, stale-update, rollback, restart-reconstruction, and checkpoint-integrity integration tests

Before an API phase, add ApprovalRequest and append-only execution-event/outbox repositories so every visible lifecycle transition is durable and auditable.
