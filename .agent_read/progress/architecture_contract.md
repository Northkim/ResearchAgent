# ReAgent Architecture Contract

- Contract version: 1.0
- Status: Final for initial implementation
- Date: 2026-07-20
- Product source of truth: `docs/PROJECT_DEVELOPMENT_PLAN.md`
- Supersedes as implementation guidance: `.agent_read/progress/architecture_analysis.md`

This document is the implementation contract for the first ReAgent architecture. The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative. A future implementation may refine internal names, but it must preserve the responsibilities, dependency rules, state invariants, and persistence boundaries defined here unless an accepted architecture decision explicitly supersedes this contract.

## Contract baseline

The following decisions are accepted:

- Backend architecture: modular monolith using ports and adapters.
- Initial agent model: one primary agent session per workflow run, coordinated by a Workflow Engine and a Skill System.
- Extension model: data structures and contracts must permit multiple agent sessions later without redesigning workflow, memory, or artifact ownership.
- Workflow model: immutable, versioned, static directed acyclic graphs for v1.
- Backend/API: Python with FastAPI at the HTTP boundary.
- Durable database: PostgreSQL through SQLAlchemy 2.x, with Alembic migrations.
- Frontend: Next.js with TypeScript, communicating only through versioned backend APIs.
- Memory: structured PostgreSQL records plus versioned file-based project context; semantic retrieval through pgvector is deferred.

The architecture analysis remains useful background, but where it differs from this document, this contract controls implementation.

## 1. Final Repository Architecture

### 1.1 Target directory structure

This is the approved target shape. It describes future implementation and is not created by this architecture-only task.

```text
ResearchAgent/
├── AGENTS.md
├── README.md
├── docs/
│   ├── PROJECT_DEVELOPMENT_PLAN.md
│   └── architecture/
│       ├── system-context.md
│       ├── domain-model.md
│       ├── workflow-specification.md
│       ├── runtime-lifecycle.md
│       └── security-and-observability.md
├── .agent_read/
│   ├── AGENT.md
│   ├── context.md
│   ├── decisions/
│   └── progress/
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/
│   ├── src/reagent/
│   │   ├── domain/
│   │   │   ├── common/
│   │   │   ├── projects/
│   │   │   ├── workflows/
│   │   │   ├── agents/
│   │   │   ├── memory/
│   │   │   └── artifacts/
│   │   ├── application/
│   │   │   ├── orchestration/
│   │   │   ├── agent_runtime/
│   │   │   ├── workflow_engine/
│   │   │   ├── skill_system/
│   │   │   ├── memory/
│   │   │   └── artifacts/
│   │   ├── ports/
│   │   │   ├── repositories/
│   │   │   ├── llm/
│   │   │   ├── tools/
│   │   │   ├── files/
│   │   │   ├── events/
│   │   │   └── execution/
│   │   ├── adapters/
│   │   │   ├── persistence/
│   │   │   ├── llm/
│   │   │   ├── tools/
│   │   │   ├── files/
│   │   │   ├── events/
│   │   │   └── telemetry/
│   │   └── entrypoints/
│   │       ├── api/
│   │       ├── worker/
│   │       └── cli/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── contract/
├── frontend/
│   ├── src/
│   └── tests/
├── workflows/
│   ├── schemas/
│   └── examples/
└── tests/
    └── e2e/
```

### 1.2 Module responsibilities

| Module | Responsibility | Explicit non-responsibility |
|---|---|---|
| `domain` | Entities, value objects, lifecycle states, invariants, domain errors, and domain events | HTTP, ORM mappings, provider SDKs, filesystem access, queues |
| `application/orchestration` | Use-case coordination and transaction boundaries; coordinates Workflow Engine, Agent Runtime, memory, artifacts, and execution dispatch | Business invariants owned by domain; infrastructure implementation |
| `application/workflow_engine` | Validate definitions, calculate ready nodes, apply DAG and retry rules, and produce legal state transitions | Executing skills, calling models, reading SQL directly |
| `application/agent_runtime` | Build bounded agent context, manage one primary agent session, execute the selected workflow step, and normalize results | DAG scheduling, HTTP concerns, direct provider/storage access |
| `application/skill_system` | Register, resolve, authorize, and invoke versioned skills | Workflow scheduling and provider-specific tool logic |
| `application/memory` | Query and update scoped short-term, working, and long-term memory through ports | Direct vector, SQL, or file implementation |
| `application/artifacts` | Create immutable artifact versions, provenance, and retrieval references | Storing large bytes in domain objects or workflow rows |
| `ports` | Framework-independent contracts required by application services | Adapter composition or provider SDK types |
| `adapters` | Implement ports for PostgreSQL, file/object storage, LLMs, tools, events, and telemetry | Defining domain policy |
| `entrypoints/api` | FastAPI request validation, authentication context, authorization invocation, response mapping, and event streaming | Domain policy and direct ORM queries |
| `entrypoints/worker` | Claim dispatched work, invoke application use cases, heartbeat, and controlled shutdown | Owning workflow semantics |
| `entrypoints/cli` | Local development and administrative entry point through the same application use cases | Separate business logic |
| `frontend` | Next.js user experience for projects, workflows, runs, approvals, and artifacts | Direct database or file-storage access |
| `workflows` | Versioned schemas and reviewed built-in workflow definitions | Executable Python logic |

### 1.3 Dependency direction

```text
Next.js frontend
       |
       v
FastAPI entrypoint -----------------------+
       |                                  |
       v                                  v
Application ExecutionCoordinator     Adapter composition
       |                                  |
       +--> Workflow Engine               |
       +--> Agent Runtime                 |
       +--> Memory Service                |
       +--> Artifact Service              |
       |                                  |
       v                                  |
Domain model + outbound ports <-----------+
       ^
       |
Skill Executor --> registered Skill --> scoped outbound ports
```

Allowed dependencies:

1. `domain` may depend only on the Python standard library and deliberately selected domain-only utilities.
2. `ports` may depend on `domain`; port signatures MUST NOT expose FastAPI, SQLAlchemy, provider SDK, or queue types.
3. `application` may depend on `domain` and `ports`. Application submodules communicate through defined interfaces, not each other's private state.
4. `workflow_engine` and `agent_runtime` are siblings. The `ExecutionCoordinator` invokes both; neither may import the other's implementation.
5. `skill_system` may depend on domain and ports. Individual skills MUST NOT import the Workflow Engine, Agent Runtime internals, FastAPI, or persistence adapters.
6. `adapters` may depend on domain, ports, and external libraries. Adapters MUST NOT be imported by domain or application modules.
7. `entrypoints` may depend on application contracts and adapter composition. They MUST NOT bypass application services to mutate repositories.
8. `frontend` may depend only on published HTTP/event contracts and generated or shared transport schemas, never backend Python modules.
9. Circular imports across modules are prohibited.

The v1 backend remains one deployable codebase. API and worker MAY run as separate processes, but they share the same application package and PostgreSQL state. Microservice extraction is deferred until scaling, isolation, or ownership evidence justifies it.

## 2. Agent Runtime Contract

### 2.1 Runtime responsibility and lifecycle

For v1, a `WorkflowRun` owns exactly one primary `AgentSession`. The schema permits additional sessions later by making sessions separate records associated with the run and by avoiding a global singleton agent.

An agent session has these lifecycle states:

```text
CREATED -> INITIALIZING -> ACTIVE <-> WAITING -> COMPLETED
                           |   |          |
                           |   +--------> FAILED
                           +------------> CANCELLING -> CANCELLED
```

The workflow run lifecycle in Section 9 is authoritative for externally visible run status. Agent-session status describes the runtime participant and must remain consistent with the owning run.

### 2.2 Agent start input

The application-level start command MUST contain:

| Field | Requirement |
|---|---|
| `request_id` | Correlation identifier for logs and tracing |
| `idempotency_key` | Prevents duplicate logical runs for repeated client requests |
| `actor_user_id` | User initiating the run; used for authorization and audit |
| `project_id` | Mandatory project isolation scope |
| `workflow_id` and `workflow_version` | Exact immutable workflow definition to execute |
| `workflow_inputs` | JSON-compatible values validated against the workflow input schema |
| `agent_profile_ref` | Versioned model, prompt-policy, budget, and capability configuration |
| `material_ids` | Optional project-scoped uploaded materials available to the run |
| `approval_policy` | Project or run-level policy identifying actions that require human approval |

Secrets, provider credentials, raw database handles, and arbitrary executable code MUST NOT appear in this command.

### 2.3 Agent output

Starting a run returns an `ExecutionHandle` containing:

- `workflow_run_id`
- `agent_session_id`
- current lifecycle `status`
- pinned `workflow_id` and `workflow_version`
- `created_at`
- status and event-stream references at the transport layer

Each executed step returns a normalized `StepExecutionResult` containing:

- outcome: `SUCCEEDED`, `FAILED`, `WAITING`, or `CANCELLED`
- schema-validated output values or references
- created artifact references
- proposed memory updates with provenance
- model/tool usage metadata
- redacted diagnostic metadata
- typed error information when not successful

The final run result contains workflow outputs, final artifact references, terminal status, timestamps, and an execution summary. Large content MUST be referenced as an artifact rather than embedded in run rows or API responses.

### 2.4 Context loading mechanism

The runtime constructs an immutable `AgentExecutionContext` for each node attempt. Context is loaded in this order:

1. System safety and execution policy.
2. Versioned agent profile and allowed capabilities.
3. Project instructions and the latest approved file-based project context revision.
4. Pinned workflow definition, current node contract, and validated run inputs.
5. Current checkpoint, completed dependency outputs, and active retry metadata.
6. Selected working-memory records for the project and run.
7. Selected long-term memory and source references relevant to the current node.
8. Referenced research-material metadata and content excerpts permitted by policy.

Every context item MUST include a source/provenance reference and project scope. A context-budget policy MUST select or summarize content deterministically enough to reproduce why an item was included. The runtime passes only the required subset to an LLM or skill.

`.agent_read/` is developer-session memory and MUST NOT be loaded into research-agent execution context. Product-level file context belongs to the project's managed file storage, for example a versioned `memory/context.md` artifact.

### 2.5 Memory interaction

- The runtime accesses memory only through `MemoryService`/`MemoryRepository` ports.
- Skills receive a project- and run-scoped memory facade with explicit read/write capability.
- Memory writes are proposals until validated, attributed, and committed by the application layer.
- A memory update MUST include scope, kind, content or content reference, producer, source references, and timestamp.
- Memory updates MUST NOT silently overwrite historical knowledge. Corrections create a new version or superseding entry.
- LLM providers never receive direct storage access.

### 2.6 State update mechanism

Mutable run and session records use integer versions for optimistic concurrency. One logical state transition is committed through an application unit of work:

1. Load the run and expected state version.
2. Validate the requested domain transition.
3. Stage artifact/file content and calculate checksums when needed.
4. Commit step state, run/session state, checkpoint metadata, artifact metadata, memory entries, approval requests, and execution-log events in one PostgreSQL transaction where they belong to the same transition.
5. Publish asynchronous notifications after commit; delivery may be at least once, so consumers must deduplicate by event ID.

File bytes cannot share a PostgreSQL transaction. They MUST be written to a temporary/staged location first and promoted or referenced only after checksum verification. Failed transactions leave only collectible staged/orphan files, never visible artifact versions.

### 2.7 Runtime behavior

When an agent starts:

1. Authenticate the actor and authorize access to the project, materials, workflow, and agent profile.
2. Resolve the idempotency key; return the existing handle if the logical request already exists.
3. Validate the workflow schema, input schema, pinned versions, skills, and policies.
4. Create `workflow_run`, primary `agent_session`, initial node state, initial checkpoint, and audit event transactionally.
5. Move the run from `CREATED` to `INITIALIZING` and dispatch executable work.
6. Load bounded context and move to `RUNNING` only when initialization succeeds.

During execution:

1. The coordinator claims the run using a lease or optimistic version.
2. The Workflow Engine selects the next ready node.
3. Approval policy is evaluated before any protected action.
4. The Agent Runtime builds context and asks the Skill System to execute the node.
5. The result is validated against the node output schema.
6. State, artifacts, memory, logs, and a checkpoint are committed.
7. The engine re-evaluates the graph until it reaches a waiting or terminal state.

V1 executes at most one node at a time within a run. Separate workflow runs MAY execute concurrently. The DAG and step-run records preserve a future path to parallel ready-node execution.

When execution stops:

- Successful completion persists final outputs and a terminal checkpoint before `COMPLETED` is visible.
- Approval or user-input waits persist a checkpoint and wait reason before releasing the worker.
- Retryable failure persists the attempt and next eligible retry time before releasing the worker.
- Non-retryable or exhausted failure persists a redacted typed error, terminal checkpoint, and `FAILED` event.
- Cancellation first enters `CANCELLING`; the active boundary stops safely, records whether side effects began, checkpoints, and then enters `CANCELLED`.
- Leases and in-process resources are released in every path. Recovery MUST rely only on durable records, never retained process memory.

## 3. Workflow Engine Contract

### 3.1 Workflow schema

A workflow is authored as YAML, validated against a versioned schema, normalized to JSON-compatible domain values, and persisted with an immutable definition version.

Required top-level fields:

| Field | Meaning |
|---|---|
| `api_version` | Workflow schema version, initially `reagent/v1alpha1` |
| `kind` | Must be `Workflow` |
| `metadata.id` | Stable logical workflow identifier |
| `metadata.version` | Immutable semantic version |
| `metadata.name` | Human-readable name |
| `inputs` | JSON-schema-compatible input definitions |
| `nodes` | Non-empty list of step definitions |
| `outputs` | Mapping from workflow output names to completed node outputs |

Published `(workflow_id, version)` pairs are immutable. Editing creates a new version. A run pins both the workflow version and schema version for its entire lifetime.

### 3.2 Step schema

Each step MUST define:

| Field | Requirement |
|---|---|
| `id` | Unique within the workflow; stable for that version |
| `kind` | `skill` or `approval` in v1 |
| `needs` | List of predecessor node IDs; empty for root nodes |
| `uses` | Exact `skill_id@version` for `skill` nodes |
| `with` | Input mapping from workflow inputs or predecessor outputs |
| `timeout_seconds` | Positive execution timeout for a skill attempt |
| `retry` | `max_attempts` and bounded backoff policy |
| `checkpoint` | Checkpoint policy; `after_success` is mandatory in v1 |
| `approval` | Approval prompt, role/policy key, and expiry for approval nodes |

`outputs` are defined by the referenced skill's output schema. Arbitrary Python, templates with code execution, loops, dynamic node creation, and model-generated graph mutation are not allowed in v1.

### 3.3 Example workflow

```yaml
api_version: reagent/v1alpha1
kind: Workflow
metadata:
  id: literature-search
  version: 1.0.0
  name: Literature search to reviewed report
inputs:
  topic:
    type: string
    minLength: 3
nodes:
  - id: search
    kind: skill
    needs: []
    uses: paper-search@1.0.0
    with:
      query: "${inputs.topic}"
    timeout_seconds: 120
    retry:
      max_attempts: 3
      backoff: exponential
      initial_seconds: 1
      max_seconds: 30
    checkpoint: after_success

  - id: approve_sources
    kind: approval
    needs: [search]
    approval:
      policy: project_reviewer
      prompt: Review the selected sources before synthesis.
      expires_after_seconds: 86400
    checkpoint: after_success

  - id: synthesize
    kind: skill
    needs: [approve_sources]
    uses: literature-synthesis@1.0.0
    with:
      topic: "${inputs.topic}"
      papers: "${nodes.search.outputs.papers}"
    timeout_seconds: 600
    retry:
      max_attempts: 2
      backoff: exponential
      initial_seconds: 2
      max_seconds: 30
    checkpoint: after_success
outputs:
  report: "${nodes.synthesize.outputs.report_artifact}"
```

### 3.4 DAG representation and validation

The normalized definition stores nodes keyed by ID plus inbound dependency lists. The engine may derive outbound adjacency and a topological order in memory. Publication validation MUST reject:

- duplicate or invalid node IDs
- missing dependencies
- self-dependencies and cycles
- unknown step kinds or workflow schema versions
- missing or incompatible skill versions
- invalid input/output references or schemas
- non-positive timeouts and invalid retry bounds
- approval steps without a resolvable approval policy
- workflow outputs that cannot be produced

Topological order is deterministic: ties use definition order, then node ID as a stable fallback.

### 3.5 Execution rules

1. A node becomes `READY` only after every `needs` node is `SUCCEEDED` or `SKIPPED` under a future explicitly defined policy.
2. V1 has no conditional branching, so built-in execution does not create `SKIPPED` nodes; the state is reserved for compatible future extension.
3. V1 claims and executes one ready node per run at a time.
4. A skill node resolves an exact skill version and validates mapped inputs before execution.
5. Each attempt has a stable attempt number and a derived idempotency key containing run, node, and logical operation identity.
6. A node becomes `SUCCEEDED` only after output validation and durable transition commit.
7. Downstream nodes cannot become visible as ready before the upstream checkpoint commits.
8. All nodes successful plus valid workflow outputs causes the run to complete.
9. Workflow upgrades affect new runs only. In-flight definition migration requires a future explicit migration contract.

### 3.6 Checkpoints and recovery

Checkpoints are append-only and MUST be written:

- after run initialization
- after every successful node
- before entering any waiting state
- when scheduling a retry
- before a terminal state becomes externally visible

A checkpoint includes workflow and schema versions, run/session state versions, node/attempt states, current cursor, validated output references, working-memory revision references, artifact references, pending approval or retry metadata, sequence number, parent checkpoint, and integrity hash.

On recovery, the coordinator loads the latest internally consistent checkpoint, verifies its hash and pinned versions, reconciles it with committed step-run rows, and executes only incomplete work. A `RUNNING` attempt without a committed success transition is treated as interrupted. It may be retried only through the node retry/idempotency policy.

### 3.7 Error handling

Errors use a stable taxonomy:

| Error class | Retry behavior | Example |
|---|---|---|
| `ValidationError` | Never | Invalid workflow input or skill output |
| `AuthorizationError` | Never | User or skill lacks permission |
| `PolicyError` | Never until policy/approval changes | Protected tool without approval |
| `NotFoundError` | Never by default | Missing pinned workflow or material |
| `TransientProviderError` | Retry within policy | Rate limit or temporary model outage |
| `ToolTimeoutError` | Retry only if operation is idempotent | Search request timeout |
| `PermanentSkillError` | Never | Unsupported input or deterministic failure |
| `InvariantViolation` | Fail and alert | Illegal state transition or corrupted checkpoint |
| `CancellationRequested` | Do not retry | User/system cancellation |

Retries create new attempt records; they do not overwrite earlier attempts. V1 defaults to failing the workflow after a node exhausts retries. Sensitive provider payloads and secrets MUST be redacted from persisted errors.

## 4. Skill System Contract

### 4.1 Skill interface

Every skill implements the conceptual interface:

```text
Skill.metadata() -> SkillMetadata
Skill.execute(request: SkillRequest, context: SkillContext) -> SkillResult
```

`execute` is asynchronous. It receives JSON-compatible validated inputs plus scoped gateways, cancellation/deadline information, idempotency key, correlation identifiers, and policy context. It returns validated values and references; it does not mutate workflow state directly.

`SkillResult` contains:

- `status`
- schema-valid output values
- artifact creation requests or references
- proposed memory updates
- tool/model usage records
- redacted diagnostics
- typed error when unsuccessful

### 4.2 Skill metadata

`SkillMetadata` MUST include:

- stable `id` and immutable semantic `version`
- human-readable `name` and `description`
- input and output schemas
- required permissions and capabilities
- side-effect classification: `none`, `read_external`, `write_external`, or `execute_code`
- idempotency support declaration
- default timeout and retry safety
- implementation entry point and compatibility with the skill API version

Published skill versions are immutable. Behavioral or schema changes require a new version.

### 4.3 Registration and discovery

- A `SkillRegistry` is populated at application composition time from configured built-in or installed skill packages.
- Registration key is `(skill_id, version)`. Duplicates fail startup rather than selecting one silently.
- Discovery reads declarative metadata and allow-listed entry points. It MUST NOT import arbitrary project-uploaded code.
- Workflow publication verifies that all referenced skill versions are registered and schema-compatible.
- Registry contents can be inspected through an application query and later exposed through an authorized API.

### 4.4 Skill execution model

1. The Workflow Engine identifies the exact skill reference.
2. The Skill System resolves metadata and checks input schema, permissions, approval policy, timeout, and retry safety.
3. It constructs a least-privilege `SkillContext` containing only allowed LLM, tool, memory, file, and artifact ports.
4. The skill executes cooperatively with cancellation and deadline signals.
5. The Skill System validates and normalizes the result before returning it to the runtime.
6. The application layer commits state and side-effect records; the skill cannot mark its node successful itself.

New skills require a new implementation package/module, metadata, schemas, tests, and registry configuration. They do not require changes to Workflow Engine or Agent Runtime core code. A new capability type requires a new port or policy and therefore an architecture review; ordinary implementations of existing ports do not.

## 5. Memory Architecture

Memory is project-scoped by default and is accessed only through the memory application service. Execution state and research knowledge are distinct even if both use PostgreSQL.

| Layer | Contents | Durable storage | Update rule | Access |
|---|---|---|---|---|
| Short-term memory | Current node inputs, dependency outputs, attempt data, context-selection record, temporary reasoning summary, execution cursor | PostgreSQL run/step state and checkpoints; bounded in-process context during one attempt | Rebuilt per attempt; persisted only as redacted structured state/checkpoint references | Coordinator, Workflow Engine, Agent Runtime; skills receive only their scoped subset |
| Working memory | Current project objectives, active plan, hypotheses, decisions, summaries, and current research state | Structured PostgreSQL memory entries plus a versioned file-based project context such as `memory/context.md` | Append or create a new revision with provenance; approved context revisions replace the active pointer but not history | Project members by role, Agent Runtime, Memory Service, and explicitly authorized skills |
| Long-term memory | Historical findings, citations, source-grounded claims, prior run summaries, reusable knowledge, and artifact provenance | PostgreSQL metadata/entries plus artifact/file storage; pgvector column/index later | Append/supersede with source references and confidence/status; never silent overwrite | Project members and project-scoped retrieval service; skills/LLM receive selected results only |

Rules:

- PostgreSQL is authoritative for execution state, active context revision pointers, metadata, provenance, and access scope.
- File-based context is a human-readable, portable project-memory representation, not a lock, queue, or source of truth for concurrent execution state.
- Every persistent memory item MUST include `project_id`, scope, kind, producer, timestamps, and source references where applicable.
- Memory selected for an LLM MUST be traceable to stored entries and filtered by project permissions and context budget.
- Long-term entries SHOULD distinguish `draft`, `verified`, and `superseded` knowledge.
- Deletion and retention operations must remove or tombstone associated vector entries when pgvector is introduced.
- `.agent_read` remains development-process memory and is not part of product memory.

## 6. Storage Architecture

### 6.1 PostgreSQL responsibility

PostgreSQL is the durable system of record for:

- users, project ownership, and membership metadata
- project configuration and active memory-context revision pointers
- immutable workflow definitions and versions
- workflow runs, step attempts, agent sessions, lifecycle states, and optimistic versions
- checkpoints, retry schedules, approval requests, idempotency keys, and event/audit metadata
- memory metadata, structured knowledge, provenance, and future embedding columns
- artifact and uploaded-material metadata, checksums, logical versions, and storage references
- structured, redacted execution logs and correlation identifiers

PostgreSQL MUST NOT store large uploaded files, report bodies, arbitrary binary artifacts, secrets, or unbounded raw model payloads directly in core tables.

### 6.2 File and object storage responsibility

The file-storage port owns:

- uploaded research materials
- versioned project context files
- generated reports and paper drafts
- exported datasets, experiment results, and generated code archives
- large redacted model/tool payloads retained under policy

Every stored object has an opaque storage reference, checksum, media type, size, project scope, and immutable version metadata in PostgreSQL. Local filesystem storage MAY implement the port for development. A production deployment SHOULD use S3-compatible object storage. Backend services, not the frontend, issue authorized reads or time-limited access references.

### 6.3 Future vector memory

Semantic retrieval is implemented later through a separate `EmbeddingProvider` port and pgvector-backed adapter. Vector records associate an embedding with a memory/material chunk ID, embedding model/version, checksum, and project scope. PostgreSQL text/metadata filters run before or with vector similarity to prevent cross-project retrieval.

Changing an embedding model creates a new embedding version; it does not overwrite earlier vectors until a controlled re-index completes. Core correctness MUST NOT depend on vector search: exact IDs, metadata, source references, and checkpoints remain usable without pgvector.

### 6.4 Storage consistency

- Database rows reference immutable content checksums.
- Writes use stage -> verify -> database commit -> promote/garbage-collect semantics.
- API responses expose artifact IDs, not raw storage paths.
- Backups must pair PostgreSQL metadata with referenced object versions.
- Logs and artifacts have explicit retention classes; deletion is audited.

## 7. Database Initial Schema

The schema is conceptual; naming may be adjusted consistently during implementation. Primary keys SHOULD be opaque UUIDs, timestamps use timezone-aware UTC values, flexible validated payloads use JSONB, and mutable aggregates use an integer `row_version` for optimistic concurrency.

### Required and supporting entities

| Entity | Purpose | Important fields | Relationships |
|---|---|---|---|
| `users` | Human identity for ownership, authorization, approval, and audit | `id`, `email`, `display_name`, `status`, `created_at`, `updated_at` | Owns projects; joins projects through memberships; resolves approvals |
| `projects` | Primary data-isolation and research-workspace boundary | `id`, `owner_user_id`, `name`, `description`, `status`, `active_context_artifact_id`, `settings_json`, `row_version`, timestamps | Belongs to owner; has materials, workflows/runs, sessions, memory, artifacts, logs |
| `project_memberships` | Future-safe team authorization without redesigning projects | `project_id`, `user_id`, `role`, timestamps | Many-to-many users/projects; unique pair |
| `research_materials` | Metadata and provenance for uploaded inputs | `id`, `project_id`, `logical_name`, `version`, `storage_ref`, `checksum`, `media_type`, `size`, `metadata_json`, `uploaded_by`, timestamps | Belongs to project and uploader; referenced by runs/memory/artifacts |
| `workflows` | Immutable versioned workflow definitions | `id`, `workflow_key`, `version`, `schema_version`, `name`, `definition_json`, `definition_hash`, `status`, `created_by`, timestamps | Logical key has versions; runs pin one exact workflow row |
| `workflow_runs` | Externally visible execution aggregate | `id`, `project_id`, `workflow_id`, `status`, `inputs_json`, `outputs_json`, `idempotency_key`, `wait_reason`, `error_code`, `row_version`, `created_by`, timestamps | Belongs to project/workflow; has step runs, agent sessions, checkpoints, artifacts, approvals, logs |
| `workflow_step_runs` | Node-level state and immutable attempt history | `id`, `workflow_run_id`, `node_id`, `attempt`, `status`, `input_json`, `output_json`, `idempotency_key`, `started_at`, `finished_at`, `error_code`, `row_version` | Belongs to run; unique run/node/attempt; may produce artifacts/logs |
| `agent_sessions` | Versioned runtime participant state; supports future multiple agents | `id`, `project_id`, `workflow_run_id`, `role`, `agent_profile_ref`, `status`, `state_json`, `row_version`, timestamps | Belongs to project/run; v1 enforces one `primary` session per run |
| `checkpoints` | Append-only durable recovery points | `id`, `workflow_run_id`, `agent_session_id`, `sequence`, `parent_id`, `state_json`, `state_hash`, `created_at` | Ordered per run; references session and optionally previous checkpoint |
| `artifacts` | Immutable versions of generated or managed output | `id`, `project_id`, `logical_artifact_id`, `logical_name`, `version`, `kind`, `storage_ref`, `checksum`, `media_type`, `size`, `producer_run_id`, `producer_step_run_id`, `metadata_json`, timestamps | Belongs to project; optionally produced by run/step; may be active project context |
| `memory_entries` | Structured working and long-term research memory | `id`, `project_id`, `workflow_run_id`, `scope`, `kind`, `status`, `content_text` or `content_ref`, `source_refs_json`, `producer_type`, `producer_id`, `supersedes_id`, timestamps | Belongs to project; optionally run-produced; may supersede another entry |
| `approval_requests` | Durable human-in-the-loop gate | `id`, `project_id`, `workflow_run_id`, `step_run_id`, `policy_key`, `request_fingerprint`, `prompt`, `status`, `requested_at`, `expires_at`, `resolved_by`, `resolved_at`, `decision_reason`, `row_version` | Belongs to run/step; resolved by authorized user |
| `execution_logs` | Append-only, structured, redacted execution/audit events | `id`, `project_id`, `workflow_run_id`, `agent_session_id`, `step_run_id`, `sequence`, `event_type`, `severity`, `payload_json`, `request_id`, `occurred_at` | Correlates all execution entities; ordered per workflow run |

### Key constraints and indexes

- Unique `users.email` after canonicalization.
- Unique `(project_id, user_id)` membership.
- Unique `(workflow_key, version)` and immutable published workflow rows.
- Unique `(project_id, idempotency_key)` for workflow-run creation.
- Unique `(workflow_run_id, node_id, attempt)` and step idempotency key.
- Unique `(workflow_run_id, sequence)` for checkpoints and execution logs.
- Unique v1 primary agent session per workflow run.
- Unique `(project_id, logical_artifact_id, version)` for artifact history.
- Foreign keys or equivalent integrity checks MUST prevent cross-project references.
- Index run status/retry time, project/timestamp queries, unresolved approvals, artifact logical IDs, and memory scope/status/source fields.
- Execution logs and checkpoints are append-only to application code. Retention or archival uses explicit administrative paths.

## 8. LLM Provider Abstraction

### 8.1 Interface

Provider adapters for OpenAI, Claude, and local models implement one provider-neutral `LLMProvider` contract:

```text
LLMProvider.capabilities() -> LLMCapabilities
LLMProvider.generate(request: LLMRequest) -> LLMResponse
LLMProvider.stream(request: LLMRequest) -> AsyncIterator[LLMStreamEvent]
LLMProvider.health_check() -> ProviderHealth
```

All network-facing methods are asynchronous. `stream` may report unsupported through capabilities, but the method contract remains consistent. Embeddings use a separate future `EmbeddingProvider`; they are not added to chat/generation semantics.

### 8.2 Normalized request

`LLMRequest` contains:

- model reference from an approved agent profile
- ordered provider-neutral messages with typed roles/content parts
- optional tools with JSON-compatible input schemas
- optional structured response schema
- generation parameters supported by policy
- maximum output budget and deadline
- project/run/step correlation metadata
- idempotency/retry metadata where supported

Provider credentials are injected into adapters and never appear in the request domain object or persisted checkpoint.

### 8.3 Normalized response

`LLMResponse` contains:

- normalized text/content parts
- normalized tool-call requests
- structured output when requested
- finish reason
- input/output/cached token usage when provided
- model/provider identifiers actually used
- provider request ID for restricted diagnostics
- policy/redaction-safe metadata

Raw SDK response objects MUST NOT cross the adapter boundary. If raw payload retention is enabled, it is redacted, encrypted/access-controlled as required, stored by reference, and excluded from routine logs and memory.

### 8.4 Reliability rules

- The application layer owns retry budget; adapters classify provider errors and respect deadlines.
- Capability negotiation prevents requesting unsupported tools, streaming, or structured output.
- A deterministic fake provider MUST support domain and contract tests.
- Provider-specific prompt transformation occurs in the adapter; core messages remain provider-neutral.
- Usage, latency, and error telemetry carries run/step correlation but no secrets.

## 9. Execution Lifecycle

### 9.1 Canonical workflow-run states

```text
CREATED
   |
   v
INITIALIZING -----> FAILED
   |
   v
RUNNING <-------------------------------+
   |  |  |                              |
   |  |  +--> RETRY_SCHEDULED ----------+
   |  +-----> WAITING_FOR_APPROVAL ------+
   +--------> WAITING_FOR_INPUT ----------+
   |
   +--> COMPLETED
   +--> FAILED
   +--> CANCELLING --> CANCELLED
```

Terminal states are `COMPLETED`, `FAILED`, and `CANCELLED`. They cannot transition to another state; resuming the research requires a new run linked to the prior run.

### 9.2 Transition conditions

| From | To | Condition |
|---|---|---|
| `CREATED` | `INITIALIZING` | Run, session, pinned workflow, and initial checkpoint committed; work claimed |
| `INITIALIZING` | `RUNNING` | Inputs, skills, policies, materials, and initial context validate |
| `INITIALIZING` | `FAILED` | Non-recoverable validation, configuration, or integrity error |
| `RUNNING` | `WAITING_FOR_APPROVAL` | Approval node or protected action reached; approval request and checkpoint committed before side effect |
| `WAITING_FOR_APPROVAL` | `RUNNING` | Authorized approval matches the current request fingerprint and work is dispatched |
| `WAITING_FOR_APPROVAL` | `CANCELLING` | Request rejected, expired under terminal policy, or run cancelled |
| `RUNNING` | `WAITING_FOR_INPUT` | Workflow requires human data that is not approval; request and checkpoint committed |
| `WAITING_FOR_INPUT` | `RUNNING` | Authorized, schema-valid input committed and work dispatched |
| `RUNNING` | `RETRY_SCHEDULED` | Retryable attempt fails and retry budget remains; `not_before` committed |
| `RETRY_SCHEDULED` | `RUNNING` | Retry time reached and work successfully claimed |
| `RUNNING` | `COMPLETED` | Every required node succeeded and final outputs/artifacts/checkpoint committed |
| `RUNNING` | `FAILED` | Non-retryable failure, exhausted retry budget, or invariant violation |
| Any non-terminal | `CANCELLING` | Authorized user, policy, timeout supervisor, or shutdown requests cancellation |
| `CANCELLING` | `CANCELLED` | Active attempt acknowledges cancellation or is safely fenced; terminal checkpoint committed |

Every transition MUST validate the current state and expected `row_version`, produce an execution-log event, and commit before notification. Duplicate transition commands MUST be idempotent. A worker crash does not itself change state; recovery uses lease expiry, attempt records, and checkpoints to choose the next legal transition.

## 10. Human-in-the-loop Design

### 10.1 When approval is required

Approval is mandatory when any of these applies:

- The workflow contains an explicit `approval` node.
- A skill/tool declares `write_external` or `execute_code` and policy requires approval.
- An action publishes, sends, deletes, overwrites, purchases, or otherwise creates consequential external effects.
- A project policy imposes approval for cost, data sensitivity, artifact release, or specified capabilities.
- Runtime policy is stricter than workflow metadata. The stricter rule wins.

Read-only, allow-listed research operations MAY proceed without approval under project policy. An LLM or skill can request approval but can never approve its own action.

### 10.2 Pausing safely

Before a protected side effect, the application creates an `approval_request` containing:

- exact run, node, attempt, actor/policy, and requested action
- human-readable preview of the action and expected effect
- a fingerprint of workflow version, skill version, validated inputs, target, and planned effect
- expiry and permitted approver role

The request, execution checkpoint, audit event, and transition to `WAITING_FOR_APPROVAL` commit together. The worker then releases the run. No protected action may start before the approval transaction commits.

### 10.3 Approval decision and resume

1. An authenticated user submits approve or reject with an idempotency key and optional reason.
2. The application verifies project role, request status, expiry, run state, and optimistic version.
3. It recomputes the request fingerprint. Changed inputs, target, workflow/skill version, or planned effect invalidate the old approval and require a new request.
4. Approval marks the request approved, records the resolver, transitions the run to `RUNNING`, and dispatches the same fingerprinted action.
5. Rejection enters `CANCELLING` and then `CANCELLED` in v1 with reason `APPROVAL_REJECTED`. Conditional rejection branches are deferred.
6. The side-effecting invocation uses a stable idempotency key so worker retries cannot repeat the approved effect logically.

Approval expiry follows explicit workflow/project policy. The v1 default is cancellation, not automatic approval. All requests and decisions remain auditable even if the run is later deleted under a separate retention process.

## 11. Cross-cutting implementation invariants

- Every user, run, memory, artifact, file, checkpoint, approval, and log operation is project-scoped and authorization-checked.
- Domain state can be reconstructed or inspected without a live worker or LLM provider.
- Published workflow and skill versions are immutable.
- External effects use idempotency keys and are recorded before a node is declared successful.
- Checkpoints contain references and compact structured state, not secrets or unbounded content.
- The database is authoritative for lifecycle state; file context is authoritative only for the content of its own immutable revision.
- Logs are structured, redacted, correlated, and append-only at the application level.
- Model providers, file stores, dispatchers, and future vector retrieval remain adapters behind ports.
- Core tests must run with deterministic fake providers and in-memory adapters before external integration tests.
- Multi-agent extension must be possible by adding agent sessions and assignment policy, not by changing project, workflow, memory, or artifact ownership models.

## 12. Implementation boundary and deferred choices

The contract is sufficient to begin the domain/runtime foundation. These deployment choices remain intentionally deferred behind ports and do not block core implementation:

- first real LLM provider and model
- production object-storage product
- production worker/queue technology
- authentication provider and final project-role matrix
- deployment target and whether the first release is local-only or team-hosted
- retention periods and confidential/regulated-data requirements
- exact future pgvector chunking and embedding strategy

The first vertical-slice workflow should be literature search to a sourced, reviewable report unless the product owner selects another workflow. Arbitrary user code execution, dynamic graphs, loops, conditional branches, multi-agent scheduling, and automatic approval remain out of scope for v1.
