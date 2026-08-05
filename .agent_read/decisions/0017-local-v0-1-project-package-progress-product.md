# ADR 0017: Local V0.1 Project, Package, and Progress Product

- **Status:** Accepted
- **Date:** 2026-08-05
- **Scope:** ReAgent V0.1 localhost-only product integration
- **Governing decisions:** ADR 0009, ADR 0010, and ADR 0016

## Context

MVP-A0 proved the Package compiler, explicit Progress Report ingestion and
projection, fake Proxy, and persistence independently, but found no connected
teacher-aligned product. The default Next.js interface instead presented the
preserved Hosted WorkflowRun prototype. There was no local project list/create
boundary, Package generation/download API or page, Progress projection/history
page, supported startup sequence, standalone TypeScript configuration, or
local-product end-to-end test.

The teacher architecture requires cloud-managed project and Package metadata,
a downloaded local folder as authoritative concrete task state, an existing
Harness such as Codex to perform research, and explicit Progress Report upload.
It does not authorize the cloud to start or resume the research task.

## Decision

V0.1 adds an independent local project domain and `local_projects` persistence
table for Cloud Project State. A project stores its identity, name,
owner-declared fictional/public topic, the fixed Literature Search Workflow,
timestamps, and the current deterministic Package receipt. It has no Hosted
WorkflowRun foreign key or execution lifecycle.

Project APIs create/list/get project metadata and generate, inspect, and
download the existing deterministic Literature Search Package. The product
Package compiler binds the owner topic into the immutable research-request
input. Server-side Package storage is under an explicitly configured external
artifact root; the stored ZIP checksum is verified before download. Project or
Package actions never invoke a Provider, LLM, AgentRuntime,
ExecutionDispatcher, WorkflowRun, or research synthesis.

Project responses and the Progress page reuse the existing Progress Report
history and `ProjectProgressService` projection. No second progress model,
automatic report generation, or automatic upload is introduced.

The primary Next.js path is `/projects`, with create, detail, Package, Progress,
and local-guide routes. Literature Search is the sole Workflow choice. The
historical Hosted routes remain preserved, are removed from primary navigation,
and display `Legacy Hosted Mode — not part of V0.1`.

`make dev` and `make stop` manage only FastAPI and Next.js on loopback.
PostgreSQL remains a documented local prerequisite to prevent the application
scripts from stopping or deleting an unrelated service. Runtime files remain
outside Git and the scripts do not read `.env`.

## Consequences

- Migration `20260805_0006` is the sole current head and adds only
  `local_projects`.
- PostgreSQL is authoritative for project/Package metadata and uploaded
  progress; downloaded folders remain authoritative for concrete task state.
- Package generation is deterministic for a project identity and topic, and a
  generated Package can be moved and validated independently.
- Progress upload remains explicit and the existing v0.2 Progress Report
  contract is unchanged.
- Hosted execution source and regression coverage remain available only as
  labelled legacy/internal behavior, not the V0.1 product path.
- OpenAlex remains experimental and disabled by default; fake Provider use is
  limited to controlled demonstrations.
- Claude Code, public deployment, production security, multi-user operation,
  additional Workflows/Providers, and R3D remain deferred.
- MVP-I prepares `V0_1_STATE = OWNER_ACCEPTANCE_PENDING`; it does not itself
  constitute owner acceptance.

## Alternatives considered

- Reuse `WorkflowRun` as the project record: rejected because it would make
  Hosted execution state the primary local-product boundary and risk starting
  or resuming research.
- Store local outputs and active context in PostgreSQL: rejected because the
  downloaded folder is authoritative for concrete research state.
- Create a new Progress model: rejected because the accepted Progress Report
  history and projection already provide the required product data.
- Automatically manage PostgreSQL in `make dev`: rejected because a safe
  generic script cannot identify or stop only an owner-intended database
  service across environments.
- Delete the Hosted prototype: rejected because historical source and tests can
  remain safely contained without becoming the primary product.
