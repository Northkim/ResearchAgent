# Step 1 Architecture Analysis

Date: 2026-07-20
Status: Proposal for review; no production code authorized or created
Source of truth: `docs/PROJECT_DEVELOPMENT_PLAN.md`

## 1. Purpose and scope

This document proposes the deliverables and boundaries for Step 1, **Define Architecture**. It focuses on the foundation needed for Agent Runtime, reusable workflows, persistent state, skills, artifacts, and later web deployment.

This step should define contracts and invariants. It should not build the full web platform, commit to distributed microservices, or implement production integrations.

## 2. Architecture goals and non-goals

### Goals

- Allow an execution to stop and resume from durable state.
- Represent research procedures as versioned, reusable workflow definitions.
- Keep agent, workflow, memory, skill, and artifact responsibilities separate.
- Make LLMs, tools, storage, queues, and web frameworks replaceable through ports.
- Support multiple projects, workflow runs, and agent sessions without assuming one global agent.
- Make every important state transition and generated artifact observable and traceable.
- Provide a path from a local prototype to a deployable platform without redesigning the domain.

### Non-goals for the first implementation

- A complete multi-tenant SaaS product
- A general-purpose distributed workflow orchestrator
- Autonomous execution without permission, resource, or safety controls
- Early microservice decomposition
- A sophisticated vector-memory or knowledge-graph subsystem before retrieval needs are measured
- Production code during this planning task

## 3. Proposed system shape

Start with a **modular monolith** for backend capabilities and a separately buildable web frontend. Run the API and background worker as separate processes when needed, but let them share one versioned backend package and one domain model.

```text
Web UI / CLI / API clients
           |
      API boundary
           |
Application services -----------------------------------+
  | Agent Runtime | Workflow Engine | Skill Execution   |
  | Memory        | Artifacts       | Run Control       |
           |                                           |
      Domain model                                      |
           |                                           |
         Ports: state, events, LLM, tools, artifacts    |
           |                                           |
Infrastructure adapters: PostgreSQL, object storage,    |
Redis/queue, model providers, tool sandboxes, telemetry +
```

Dependency direction should point inward:

1. Domain types and rules depend on no framework or infrastructure package.
2. Application services depend on domain types and port interfaces.
3. Adapters implement ports and may depend on external libraries.
4. API, worker, and CLI entry points compose application services with adapters.
5. The web frontend talks to versioned APIs and never reads backend storage directly.

This separation keeps early local adapters possible while preserving a migration path to durable platform services.

## 4. Proposed repository structure

The following is the target structure to scaffold only after Step 1 is approved:

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
│   ├── src/reagent/
│   │   ├── domain/
│   │   ├── application/
│   │   │   ├── agent_runtime/
│   │   │   ├── workflows/
│   │   │   ├── memory/
│   │   │   ├── skills/
│   │   │   └── artifacts/
│   │   ├── ports/
│   │   ├── adapters/
│   │   │   ├── persistence/
│   │   │   ├── llm/
│   │   │   ├── tools/
│   │   │   ├── artifacts/
│   │   │   └── telemetry/
│   │   └── entrypoints/
│   │       ├── api/
│   │       ├── worker/
│   │       └── cli/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── contract/
├── web/
│   ├── src/
│   └── tests/
├── workflows/
│   ├── schemas/
│   └── examples/
└── tests/
    └── e2e/
```

The module boundaries matter more than the exact directory names. Do not split these modules into independently deployed services until scaling, ownership, or isolation requirements justify the operational cost.

## 5. Core interface proposals

Interfaces should be asynchronous where operations can involve models, tools, or storage. They should exchange typed domain objects and explicit error types rather than framework request objects or raw provider responses.

### Agent Runtime

```text
AgentRuntime.start(command) -> ExecutionHandle
AgentRuntime.resume(execution_id, resume_token?) -> ExecutionHandle
AgentRuntime.request_cancel(execution_id, reason) -> None
AgentRuntime.inspect(execution_id) -> ExecutionSnapshot
```

The runtime coordinates work but does not own database, provider, or queue implementation details. Starting the same idempotency key twice must not create two logical executions.

### Workflow Engine

```text
WorkflowValidator.validate(definition) -> ValidationResult
WorkflowEngine.start(definition_ref, inputs, context) -> WorkflowRun
WorkflowEngine.advance(run_id) -> TransitionResult
WorkflowEngine.resume(run_id, checkpoint_id) -> TransitionResult
```

The engine owns dependency resolution, lifecycle transitions, retry policy evaluation, and checkpoint boundaries. A node delegates capability execution to the runtime or skill executor.

### Skills and tools

```text
SkillRegistry.resolve(skill_ref) -> SkillDefinition
SkillExecutor.execute(invocation, execution_context) -> SkillResult
ToolGateway.invoke(tool_call, policy_context) -> ToolResult
```

A skill is a reusable, versioned capability description. A tool is a concrete external action. Authorization, timeout, resource limits, and idempotency must be part of invocation context.

### Persistence and artifacts

```text
ExecutionRepository.get(execution_id) -> ExecutionSnapshot
ExecutionRepository.save(snapshot, expected_version) -> SaveResult
CheckpointStore.put(checkpoint) -> CheckpointRef
CheckpointStore.latest(execution_id) -> Checkpoint | None
ArtifactRepository.create(metadata, content_ref) -> ArtifactVersion
ArtifactRepository.get(artifact_id, version?) -> ArtifactVersion
MemoryRepository.append(entry) -> MemoryEntry
MemoryRepository.query(scope, query) -> list[MemoryEntry]
```

`expected_version` provides optimistic concurrency control. Metadata belongs in durable relational storage; large artifact bytes should be referenced through content-addressed or object storage rather than embedded in execution rows.

### Models, events, and observability

```text
ModelGateway.generate(request, policy_context) -> ModelResponse
EventPublisher.publish(domain_events) -> None
TelemetrySink.record(event) -> None
```

Provider-specific model responses should be normalized at the adapter boundary while preserving a restricted raw reference for debugging. Domain events describe facts; telemetry describes operational measurements. They may share correlation identifiers but serve different retention and reliability needs.

## 6. Core data model proposals

All identifiers should be opaque and stable. Mutable aggregate records should carry `created_at`, `updated_at`, and an integer `version`. Every execution-related record should carry correlation identifiers for project, workflow run, and execution.

| Entity | Essential fields | Key invariants |
|---|---|---|
| Project | `id`, `name`, `status`, `owner_scope` | Isolation boundary for materials, memory, runs, and artifacts |
| ResearchMaterial | `id`, `project_id`, `kind`, `content_ref`, `checksum`, `metadata` | Content is immutable; revisions create new versions |
| WorkflowDefinition | `id`, `version`, `input_schema`, `nodes`, `output_schema` | Published versions are immutable; graph must validate |
| WorkflowNode | `id`, `kind`, `needs`, `skill_ref`, `input_mapping`, `policy` | Unique within a definition; dependencies must exist |
| WorkflowRun | `id`, `project_id`, `definition_id`, `definition_version`, `status`, `inputs` | Always pins an immutable workflow version |
| NodeRun | `id`, `workflow_run_id`, `node_id`, `attempt`, `status`, `input_ref`, `output_ref` | One lifecycle per attempt; retries create a new attempt |
| AgentSession | `id`, `project_id`, `role`, `configuration_ref`, `status` | Never model one global agent; role/config are versioned refs |
| Execution | `id`, `workflow_run_id`, `agent_session_id`, `status`, `cursor`, `version` | State changes follow the lifecycle and optimistic locking |
| Checkpoint | `id`, `execution_id`, `sequence`, `state_ref`, `state_hash`, `created_at` | Append-only, ordered, and integrity-verifiable |
| SkillDefinition | `id`, `version`, `input_schema`, `output_schema`, `required_permissions` | Published versions are immutable |
| ToolInvocation | `id`, `execution_id`, `node_run_id`, `idempotency_key`, `status`, `request_ref`, `result_ref` | Retry-safe; secrets and sensitive payloads are not logged inline |
| MemoryEntry | `id`, `project_id`, `scope`, `kind`, `content_ref`, `source_refs`, `created_at` | Provenance is retained; project boundary is mandatory |
| Artifact | `id`, `project_id`, `kind`, `logical_name` | Logical identity is separate from immutable versions |
| ArtifactVersion | `artifact_id`, `version`, `content_ref`, `checksum`, `producer_execution_id`, `metadata` | Append-only and traceable to its producer |
| ExecutionEvent | `id`, `execution_id`, `sequence`, `type`, `payload`, `occurred_at` | Append-only and monotonically ordered per execution |

Initial lifecycle vocabulary should be small and explicit:

- Workflow/Execution: `pending -> running -> waiting | succeeded | failed | cancelled`
- Node attempt: `pending -> ready -> running -> succeeded | failed | skipped | cancelled`
- Cancellation is requested first and becomes terminal only when the active boundary acknowledges it.
- A waiting execution records a machine-readable reason such as user input, approval, scheduled retry, or external dependency.

## 7. Workflow definition proposal

Use a declarative YAML authoring format validated against a versioned schema and normalized into domain objects. YAML is for authors; persisted execution should use the normalized model and pin its schema and workflow versions.

```yaml
api_version: reagent/v1alpha1
kind: Workflow
metadata:
  id: literature-search
  version: 1.0.0
inputs:
  topic:
    type: string
nodes:
  - id: search
    uses: paper-search@1
    with:
      query: "${inputs.topic}"
    policy:
      timeout_seconds: 120
      max_attempts: 3
      checkpoint: after_success
  - id: synthesize
    needs: [search]
    uses: literature-synthesis@1
    with:
      papers: "${nodes.search.outputs.papers}"
outputs:
  report: "${nodes.synthesize.outputs.report}"
```

Validation must reject duplicate node IDs, missing dependencies, cycles, incompatible input/output mappings, unavailable skill versions, invalid retry policies, and unknown schema versions.

Execution semantics should start conservatively:

- Directed acyclic graphs only; loops and dynamic graph expansion are deferred.
- Independent ready nodes may run concurrently, subject to policy limits.
- Side-effecting tools use stable idempotency keys.
- Infrastructure delivery may be at least once; logical state transitions and tool effects must therefore be idempotent.
- A successful node transition and its checkpoint must be durably coordinated before downstream nodes become ready.
- Resumption loads the latest valid checkpoint, verifies its version/hash, and re-evaluates only incomplete work.
- Workflow upgrades affect new runs only unless an explicit, tested migration exists.

## 8. Technology choices to evaluate

These are recommended defaults, not accepted decisions.

| Concern | Initial recommendation | Rationale and boundary |
|---|---|---|
| Backend language | Python 3.12+ | Strong AI/research ecosystem; use type checking and keep domain code framework-independent |
| Domain validation | Dataclasses plus Pydantic at I/O boundaries | Avoid spreading serialization/framework behavior through the domain |
| API | FastAPI | Matches the product plan and supports typed asynchronous APIs |
| Durable database | PostgreSQL with SQLAlchemy and Alembic | Transactions, JSON metadata, optimistic locking, and mature migrations |
| Artifact bytes | Local filesystem adapter in development; S3-compatible object storage later | Same `ArtifactRepository` contract for local and deployed environments |
| Background work | In-process executor first behind a scheduler/queue port | Validate workflow semantics before adopting Celery, Temporal, or another operational platform |
| Cache/coordination | Redis only when a measured queue, cache, rate-limit, or lease need appears | PostgreSQL remains the durable source of truth |
| LLM access | Vendor-neutral `ModelGateway` with provider adapters | Prevent provider payloads and SDK types from entering core modules |
| Frontend | TypeScript and Next.js/React | Matches the product plan; consumes versioned APIs and event streams |
| Live monitoring | Server-Sent Events first; WebSockets only for bidirectional needs | Execution monitoring is primarily server-to-client |
| Testing | pytest, property/state-transition tests, adapter contract tests, and end-to-end resume tests | Recovery and lifecycle invariants are higher risk than basic CRUD |
| Quality | Ruff plus a strict Python type checker; frontend lint/type checks | Fast, automatable boundaries for a multi-module codebase |
| Observability | Structured logs and OpenTelemetry-compatible traces/metrics | Correlate project, workflow, node, model, tool, and artifact activity |

Do not select a durable workflow product before proving whether the custom workflow semantics are central product value or replaceable orchestration. The application ports should allow that decision later.

## 9. Persistence, security, and operational rules

- PostgreSQL should be the authority for execution lifecycle and metadata; caches must be rebuildable.
- State changes should use transactions and optimistic concurrency. Consumers must tolerate duplicate delivery.
- Checkpoints and events are append-oriented; mutable projections may be rebuilt from authoritative records where practical.
- Every storage query must be scoped by project and, when multi-tenancy is introduced, tenant.
- Credentials are referenced through a secret manager or runtime environment and never serialized into workflows, checkpoints, memory, events, or artifacts.
- Tool execution must declare permissions and run with time, network, filesystem, and resource limits appropriate to risk.
- Human approval should be a first-class waiting state for consequential actions.
- Raw model/tool payload retention should be configurable, redacted, access-controlled, and bounded by policy.
- Artifact and memory entries retain provenance to source materials, tool calls, and producer executions.

## 10. Initial implementation plan

### Phase A: Complete Step 1 documentation

1. Confirm product assumptions and answer the open questions below.
2. Record accepted choices as decision records.
3. Create the system context/container view and dependency rules.
4. Specify domain entities, identifiers, lifecycle state machines, and invariants.
5. Publish the `v1alpha1` workflow schema and one literature-search example.
6. Specify runtime, workflow, persistence, skill, model, artifact, and event contracts.
7. Define checkpoint consistency, idempotency, cancellation, retry, and recovery semantics.
8. Define threat boundaries, data retention, telemetry, and test strategy.

### Phase B: Scaffold the foundation after architecture approval

1. Create the backend package, quality configuration, and module boundaries.
2. Implement framework-independent domain types and state-transition tests.
3. Implement port protocols and in-memory adapters.
4. Parse and validate one workflow definition.
5. Execute a deterministic, side-effect-free workflow with checkpoints.
6. Demonstrate interruption and resumption in an integration test.

### Phase C: First vertical slice

1. Add PostgreSQL persistence and migration support.
2. Add one controlled model adapter and one paper-search skill adapter.
3. Produce a versioned report artifact with provenance.
4. Expose run creation, inspection, cancellation, and event streaming through the API.
5. Add a minimal monitoring page only after backend lifecycle behavior is stable.

## 11. Step 1 acceptance criteria

Step 1 is complete when:

- Module ownership and allowed dependency directions are documented.
- Core entities, identifiers, relationships, lifecycle states, and invariants are unambiguous.
- Runtime, workflow, skills, persistence, model, artifact, and event interfaces have typed conceptual contracts.
- A versioned workflow schema and valid literature-search example exist.
- Retry, timeout, cancellation, checkpoint, idempotency, and resume behavior are specified.
- Persistence authority, transaction boundaries, and artifact storage boundaries are documented.
- Security, data isolation, secret handling, and observability requirements are recorded.
- Major accepted choices have decision records and rejected alternatives are traceable.
- A test plan includes state-transition, adapter contract, failure injection, and interruption/resume scenarios.
- The project owner has approved the architecture before production scaffolding begins.

## 12. Open questions requiring owner confirmation

The following answers materially affect the architecture and should be resolved before implementation:

1. Is the first usable release single-user/local, team-hosted, or multi-tenant SaaS? Recommended default: local/team-hosted first, while retaining `project_id` and future `tenant_id` boundaries.
2. Which research workflow is the first vertical slice? Recommended default: literature search to sourced report, because it exercises materials, tools, memory, provenance, and artifacts without code-execution isolation.
3. Must active runs survive process or machine restarts in the first prototype? Recommended default: yes for process restarts through durable checkpoints; cross-region availability is deferred.
4. Which model providers and deployment constraints must be supported first? Recommended default: one provider adapter plus a deterministic fake, with no provider-specific types in core code.
5. Are uploaded materials expected to contain confidential or regulated data? Recommended default: treat them as private, avoid raw-content logs, and make retention/deletion policy explicit.
6. Is arbitrary user code execution required in the first release? Recommended default: no; begin with allow-listed tools and design a sandbox boundary before enabling code execution.
7. Should workflows permit loops, branching decided by models, or dynamic node creation initially? Recommended default: static DAGs with conditional edges later; defer unbounded dynamic graphs.

Until these questions are answered, the proposals above are safe planning defaults, not permanent commitments.
