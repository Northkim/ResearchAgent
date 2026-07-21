# 0001: Foundational application architecture

- Status: Accepted
- Date: 2026-07-20
- Supersedes: None

## Context

ReAgent needs a durable Agent Runtime and Workflow foundation that can start as a manageable implementation and later support a web platform, multiple agent sessions, provider integrations, and semantic retrieval. The core must not become coupled to HTTP, a model vendor, SQLAlchemy, file storage, or a particular queue.

## Decision

Use a modular monolith with ports and adapters. The initial execution model is one primary Agent Session per versioned static-DAG Workflow Run, coordinated by sibling Workflow Engine and Agent Runtime application services. Skills are immutable versioned extensions registered through a Skill System.

Use FastAPI at the backend HTTP boundary, PostgreSQL through SQLAlchemy 2.x with Alembic migrations as the durable state authority, and Next.js with TypeScript for the frontend. Store large materials and artifacts through a file/object-storage port. Use structured PostgreSQL memory plus versioned file-based project context, with pgvector deferred behind a future retrieval/embedding port.

The detailed normative boundaries and lifecycle rules are defined in `.agent_read/progress/architecture_contract.md`.

## Consequences

- The first implementation can run as one backend codebase while API and worker entry points remain separately runnable.
- Domain and application code require explicit provider, repository, file, event, tool, and execution ports.
- PostgreSQL, not process memory or a context file, is authoritative for lifecycle state and recovery.
- V1 favors deterministic, sequential node execution within each run; future parallel and multi-agent behavior can extend existing run/session records.
- Provider, queue, object-storage, authentication, and vector-search products can be chosen later without changing core contracts.
- Module boundaries require contract, state-transition, and recovery tests in addition to endpoint tests.

## Alternatives considered

- Microservices were rejected for the initial system because they add distributed transactions and operational cost before scale or ownership boundaries are known.
- A framework-centric layered backend was rejected because it would couple runtime and workflow behavior to FastAPI and persistence details.
- A single unversioned agent loop was rejected because it cannot reliably resume, audit, or evolve workflows.
- File-only execution state was rejected because it does not provide safe concurrent transitions, relational integrity, or robust recovery.
- Selecting a durable workflow product now was deferred until ReAgent-specific orchestration semantics are validated.
