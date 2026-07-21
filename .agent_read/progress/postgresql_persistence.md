# PostgreSQL Persistence Layer

- Date: 2026-07-21
- Status: Completed
- Phase: 6 — SQLAlchemy 2.x and PostgreSQL Adapters
- Environment: `reagent-dev`
- Migration head: `20260721_0001`
- PostgreSQL verification: isolated PostgreSQL 18.1 test cluster

## Outcome

Phase 6 implements durable PostgreSQL adapters behind every frozen Phase 5/5.5 persistence port. Agent Runtime can execute and recover through `SQLAlchemyUnitOfWork` without importing SQLAlchemy. Domain, Workflow Engine, Skill System, Agent Runtime behavior, and all persistence port signatures remain unchanged.

```text
Agent Runtime
      |
      v
Frozen UnitOfWork / Repository Ports
      |
      v
SQLAlchemyUnitOfWork + SQL repositories
      |
      v
SQLAlchemy 2.x + psycopg 3
      |
      v
PostgreSQL
```

## Environment changes

`environment.yml` now contains only the previously required runtime/test packages plus:

- `sqlalchemy=2` — verified 2.0.51
- `alembic` — verified 1.18.5
- `psycopg=3` — verified 3.3.4

Psycopg 3 is async-capable while also exposing the synchronous connection required by the frozen synchronous ports. Both a sync Engine factory and verified AsyncEngine factory are provided. The accepted rationale is recorded in `.agent_read/decisions/0002-psycopg3-and-synchronous-persistence-adapter.md`.

## Database package

```text
backend/database/
├── __init__.py
├── engine.py
├── serialization.py
├── unit_of_work.py
├── orm/
│   ├── __init__.py
│   ├── base.py
│   └── models.py
├── repositories/
│   ├── __init__.py
│   ├── _helpers.py
│   ├── workflow.py
│   ├── checkpoint.py
│   ├── memory.py
│   ├── artifact.py
│   ├── approval.py
│   └── events.py
├── migrations/
│   ├── __init__.py
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── __init__.py
│       └── 20260721_0001_initial_persistence.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_postgresql_persistence.py
```

## Schema summary

The migration creates ten application tables:

| Table | Responsibility |
|---|---|
| `workflow_definitions` | Immutable normalized Workflow JSON, schema version, and canonical SHA-256 hash |
| `workflow_runs` | Externally visible aggregate state plus independent optimistic `persistence_version` |
| `agent_sessions` | Primary runtime participant with future multi-session-compatible ownership |
| `workflow_step_runs` | Ordered, append-compatible attempt history with stable ordinal |
| `checkpoints` | Unique immutable Domain checkpoint identity and run sequence |
| `checkpoint_records` | Append-only application boundary labels for checkpoints |
| `memory_revisions` | Append-only project/run working-context revisions |
| `artifacts` | Immutable artifact metadata and producer provenance |
| `approval_requests` | Durable approval lifecycle, fingerprint, decision data, and optimistic version |
| `execution_events` | Append-only ordered execution audit stream with typed JSON payload |

Important constraints include:

- unique project/run idempotency key
- unique run/Step/attempt, Step idempotency key, and deterministic Step ordinal
- unique run/checkpoint sequence and global checkpoint identity
- unique run/checkpoint-record sequence and boundary identity with `NULLS NOT DISTINCT`
- unique project/run/memory revision
- unique project/logical-artifact/version
- unique run/event sequence and global event ID
- project/run, run/session, and run/Step composite foreign keys preventing cross-scope references
- positive/nonnegative checks for attempts, sequences, versions, revisions, ordinals, and sizes
- indexes for run status, Step status, approval pending/fingerprint lookup, artifact logical history, and event stream time queries

Supporting `workflow_definitions` and `agent_sessions` are included because reconstructing the existing `ExecutionState` requires them even though the Phase 6 minimum mapping list focused on execution tables.

## ORM mapping strategy

- ORM classes live only in `backend/database/orm/`; they are not Domain entities.
- Domain enums are stored as stable string values.
- Structured values use PostgreSQL JSONB; checkpoint canonical state remains text plus SHA-256 integrity hash.
- Immutable Workflow definitions are explicitly serialized/deserialized through adapter code and content-hashed. Python Workflow objects are never pickled or stored as executable objects.
- Repository reads reconstruct detached Domain entities through the existing persistence records.
- WorkflowRun and ApprovalRequest mapper version columns use SQLAlchemy optimistic version checks with application-controlled next versions.
- The SQL Unit of Work stages all repository changes, flushes them in foreign-key dependency order, and commits once. SQLAlchemy stale-row failures and named PostgreSQL sequence constraints are translated to frozen `StaleStateError`; identity conflicts become `DuplicateEntityError`.
- ORM relationships are intentionally not exposed or used as aggregate APIs; repository adapters control reconstruction and write ordering.

## Repository coverage

Implemented adapters:

- `SQLAlchemyWorkflowRepository`
- `SQLAlchemyCheckpointRepository`
- `SQLAlchemyMemoryRepository`
- `SQLAlchemyArtifactRepository`
- `SQLAlchemyApprovalRepository`
- `SQLAlchemyExecutionEventStore`
- `SQLAlchemyUnitOfWork`

Semantics preserved from InMemory adapters include detached reconstruction, exact expected versions, idempotent immutable writes, deterministic ordering, checkpoint and memory append behavior, approval recovery, event cursors/replay, commit, and rollback.

## Alembic status

Created:

- root `alembic.ini`
- adapter-aware migration environment reading `REAGENT_DATABASE_URL`
- initial migration `20260721_0001_initial_persistence.py`

Verified on PostgreSQL 18.1:

1. upgrade base -> `20260721_0001`
2. `alembic check`: no metadata drift
3. downgrade `20260721_0001` -> base
4. re-upgrade base -> `20260721_0001`
5. final `alembic check`: `No new upgrade operations detected`

PostgreSQL transactional DDL was active for each migration operation.

## Contract tests

A reusable suite in `backend/persistence/tests/adapter_contracts.py` runs the same scenarios against InMemory and SQLAlchemy adapters:

- all-repository commit and detached round trip
- transaction rollback
- event ordering/replay plus pending approval recovery and resolution
- optimistic concurrent WorkflowRun update rejection

PostgreSQL-only tests additionally verify:

- migration head and all expected tables
- psycopg AsyncEngine connectivity
- Agent Runtime terminal recovery through a fresh SQL Unit of Work

Commands and results:

```text
conda run --no-capture-output -n reagent-dev pytest -q backend --ignore=backend/database/tests
# 45 passed

REAGENT_TEST_DATABASE_URL=<migrated-postgresql-url> \
  conda run --no-capture-output -n reagent-dev pytest -q backend
# 52 passed

conda run --no-capture-output -n reagent-dev python -m compileall -q backend
# passed
```

PostgreSQL integration tests skip when `REAGENT_TEST_DATABASE_URL` is absent, preventing accidental connection to a developer or production database.

## Files created

- `alembic.ini`
- all files under `backend/database/` listed above
- `backend/persistence/tests/adapter_contracts.py`
- `backend/persistence/tests/test_adapter_contracts.py`
- `.agent_read/decisions/0002-psycopg3-and-synchronous-persistence-adapter.md`
- `.agent_read/progress/postgresql_persistence.md`

## Files modified

- `environment.yml`
- `.agent_read/context.md`

No Domain, Workflow Engine, Skill System, Agent Runtime, or persistence-port source file changed.

## Architecture impact

No frozen architecture decision changed. Phase 6 implements the accepted SQLAlchemy/PostgreSQL adapter boundary. Choosing psycopg 3 and retaining synchronous repository implementations is an adapter-level refinement documented in ADR 0002.

## Remaining limitations and risks

- Current repository ports are synchronous. An async HTTP endpoint must use a thread boundary or a future reviewed async persistence contract; it must not block the event loop directly.
- Runtime lifecycle transitions are not yet wired to automatically append ExecutionEvents or create/resolve ApprovalRequests.
- Project/user persistence, membership, authentication, authorization, and API idempotency-command records remain unimplemented.
- Approval expiry scheduling, retry `not_before`, worker lease/claim/fencing, and a queue/dispatcher are not implemented.
- Execution events are an audit stream, not a transactional delivery outbox.
- Artifact bytes/object promotion, retention, deletion audit, backups, and external object storage remain deferred.
- Integration tests require a disposable migrated PostgreSQL database; container/Testcontainers automation is deferred.
- Production pool sizing, statement timeouts, TLS, credentials/secrets management, backup, monitoring, and deployment configuration remain environment responsibilities.

## Recommendation

The backend API layer is ready to start, because application code now has a durable transaction boundary and tested restart/concurrency behavior without exposing ORM models.

The first API work should create application use cases and composition for run start/query/resume, approval query/decision, event history, and artifact metadata. It should not expose production execution yet: first wire Runtime state changes to approval/event persistence, add project/user authorization boundaries, and choose an explicit sync-thread or reviewed async repository execution model.
