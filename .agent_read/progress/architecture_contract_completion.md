# Architecture Contract Completion

- Date: 2026-07-20
- Status: Architecture contract completed; production implementation not started
- Contract: `.agent_read/progress/architecture_contract.md`

## What was finalized

- Target repository modules and their responsibilities
- One-way dependency rules for domain, application services, ports, adapters, entry points, skills, and frontend
- Single-primary-agent v1 runtime input, output, context, memory, state-update, start, execution, wait, failure, cancellation, and completion behavior
- Versioned static-DAG workflow and step schemas, validation, deterministic execution, checkpoint/recovery, retry, and error rules
- Versioned Skill interface, metadata, registration, discovery, permission, and execution model
- Short-term, working, and long-term memory boundaries and access rules
- PostgreSQL, file/object storage, and future pgvector responsibilities
- Conceptual initial schema including required entities plus supporting step-run, memory, material, membership, and approval records
- Provider-neutral LLM interface for OpenAI, Claude, and local adapters
- Canonical workflow-run lifecycle and legal transitions
- Durable human approval request, pause, fingerprint validation, rejection, and resume behavior
- Initial implementation boundary and explicitly deferred choices

## Important decisions

- Use a modular monolith with ports and adapters.
- Keep Workflow Engine and Agent Runtime as sibling services under an application coordinator.
- Execute one workflow node at a time per run in v1 while preserving future parallel/multi-agent extension points.
- Make PostgreSQL authoritative for all lifecycle and recovery state.
- Treat file context as versioned project memory, not execution coordination state.
- Require immutable workflow/skill versions, pinned runs, optimistic concurrency, append-only checkpoints/logs, and idempotent effects.
- Require explicit approval nodes or policy gates before consequential external actions.
- Keep provider-specific types and SDKs behind adapters.

These accepted choices are recorded in `.agent_read/decisions/0001-foundational-architecture.md`.

## Unresolved questions

These choices are deliberately behind ports and do not block domain/runtime implementation:

1. Which real LLM provider/model should be integrated first?
2. Which queue/worker technology should be used after the local dispatcher?
3. Which production object-storage service and deployment environment are required?
4. Is the first release local/single-user or team-hosted, and which authentication provider/role matrix applies?
5. What privacy classification, retention periods, and deletion obligations apply to uploaded research material and raw provider data?
6. Which users or roles can approve each class of protected action?
7. Should literature search to a sourced report remain the first vertical slice?
8. When should pgvector, conditional branches, parallel nodes, or multi-agent scheduling enter scope?

## Recommended next action

Conduct a short architecture review focused on the unresolved product/security questions, then scaffold the backend domain foundation only. The first implementation should define pure domain models and lifecycle transition tests because every persistence adapter, API, worker, and UI status view depends on these state contracts. Starting there validates the highest-risk recovery and idempotency rules without prematurely coupling the design to FastAPI, SQLAlchemy, or a provider.

## Verification

The architecture task added or changed documentation only. No production directories, source code, frontend/backend files, dependencies, migrations, or configuration were created.
