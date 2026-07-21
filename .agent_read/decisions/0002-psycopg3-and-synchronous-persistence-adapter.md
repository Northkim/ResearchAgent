# 0002: Use psycopg 3 with the frozen synchronous persistence ports

- Status: Accepted
- Date: 2026-07-21
- Supersedes: None

## Context

Phase 6 requires an async-capable PostgreSQL driver, while the frozen Phase 5 repository and Unit-of-Work ports are synchronous and Agent Runtime must not change behavior. An async-only SQLAlchemy adapter cannot implement those interfaces without adding event-loop bridges or changing every port method.

## Decision

Use psycopg 3 as the PostgreSQL driver. Psycopg 3 supports both synchronous and asynchronous connections through the same dependency.

Implement the frozen repositories with SQLAlchemy synchronous `Session` and `Engine` objects. Also expose an `AsyncEngine` factory using the psycopg async dialect for future API/worker composition, but do not introduce a second async repository contract in Phase 6.

## Consequences

- Agent Runtime can receive `SQLAlchemyUnitOfWork` without importing SQLAlchemy or changing its current calls.
- Repository contract tests can compare InMemory and PostgreSQL behavior directly.
- The installed driver already supports future asynchronous composition.
- Calling the current synchronous repositories directly on an API event loop would block it. The API layer must use an appropriate thread boundary or introduce a separately reviewed async application/persistence contract before high-concurrency deployment.
- No Domain, Workflow Engine, Skill System, or Runtime lifecycle rule changes.

## Alternatives considered

- `asyncpg` with `AsyncSession` was not selected because its coroutine methods cannot satisfy the frozen synchronous ports.
- Adding both `asyncpg` and a separate synchronous driver was rejected as unnecessary dependency duplication.
- Running async database operations through an internal event-loop bridge was rejected because it is fragile when Agent Runtime already executes within an event loop.
