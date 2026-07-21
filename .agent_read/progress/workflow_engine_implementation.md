# Workflow Engine Implementation

- Date: 2026-07-20
- Status: Completed
- Phase: 2 — Pure Workflow Engine
- Environment: `reagent-dev`
- Architecture: `.agent_read/progress/architecture_contract.md`
- Preparation: `.agent_read/progress/workflow_engine_preparation.md`

## Implemented components

### Workflow definitions and policy

- Immutable `WorkflowDefinition` and `StepDefinition`
- Immutable `RetryPolicy` with fixed, linear, and exponential backoff metadata
- Conversion from existing Domain `Workflow` and `WorkflowStep`
- Tuple-preserved definition order and immutable nested configuration

### Validation

- workflow/schema identity and non-empty definition checks
- duplicate step IDs
- missing and duplicate dependencies
- self-dependencies and cyclic DAGs
- supported skill/approval step rules
- pinned `skill_id@version` syntax
- timeout and checkpoint policy validation
- undefined workflow-input references
- malformed node/output references
- hidden references to non-ancestor nodes
- invalid workflow output references

### Decisions and snapshots

- Immutable `ExecutionSnapshot` and `StepRunSnapshot`
- `StepReady`
- `WaitingApproval`
- `RetryScheduled`
- `WorkflowCompleted`
- `WorkflowFailed`
- `ApprovalCompleted`
- `WorkflowCancelled`
- `NoAction`

Every actionable decision carries run/workflow identity and expected optimistic versions. Step-specific decisions also carry current attempt and step-row information as needed.

### Scheduling and resolution

- deterministic definition-order scheduling with step-ID fallback
- exactly one active node per run in v1
- explicit CREATED-to-READY transition requirement
- dependency-success checks
- deadlock and inconsistent snapshot detection
- recursive literal/reference input resolution
- `${inputs.<name>}` support
- `${nodes.<ancestor>.outputs.<field>}` support
- type-preserving immutable resolved values
- final workflow output resolution

### Retry, approval, failure, and recovery

- retryable failure evaluation without sleeping or dispatching
- deterministic capped backoff metadata
- retry exhaustion to terminal failure
- explicit approval-node waiting decisions
- typed approved/rejected/expired outcomes
- approved checkpoint resume and approval-node completion
- rejection/expiry cancellation decisions
- retry-checkpoint recovery into a new immutable attempt
- fail-fast propagation and cancellation of remaining non-terminal steps

### Coordinator integration

- `WorkflowEngine` only reads snapshots and returns decisions.
- `WorkflowExecutionCoordinator` converts Domain workflows/snapshots, checks stale decisions, and applies decisions through Domain `ExecutionCoordinator`.
- Domain no longer owns DAG readiness, workflow output resolution, or completion scheduling.
- No circular dependency was introduced: `backend/domain` does not import `backend/workflow_engine`.

## Files created

```text
backend/workflow_engine/
├── __init__.py
├── exceptions/
│   ├── __init__.py
│   └── engine_errors.py
├── models/
│   ├── __init__.py
│   ├── _immutability.py
│   ├── decisions.py
│   ├── definitions.py
│   ├── outcomes.py
│   ├── retry_policy.py
│   └── snapshots.py
├── services/
│   ├── __init__.py
│   ├── execution_coordinator.py
│   ├── reference_resolver.py
│   ├── scheduler.py
│   ├── validator.py
│   └── workflow_engine.py
└── tests/
    ├── __init__.py
    └── test_workflow_engine.py
```

## Existing files modified

- `backend/domain/models/workflow_step.py`
- `backend/domain/models/step_run.py`
- `backend/domain/services/execution_coordinator.py`
- `backend/domain/tests/test_execution_coordinator.py`
- `.agent_read/context.md`
- `.agent_read/progress/workflow_engine_implementation.md`

## Design decisions

1. The Engine receives read-only snapshots rather than mutable Domain entities.
2. Definition models are separate immutable Engine inputs and convert from Domain definitions at the boundary.
3. Engine decisions never mutate state; a separate integration coordinator applies them.
4. Definition tuple order is authoritative. Step ID is a stable tie-breaker.
5. A CREATED eligible node produces a decision marked `requires_ready_transition`; Domain records READY and checkpoints before dispatch.
6. Exact whole-value references are supported. Interpolated strings and arbitrary expressions are rejected.
7. Node-output references must point to a declared transitive ancestor, preventing undeclared hidden dependencies.
8. JSON arrays are represented as immutable tuples inside decisions/snapshots.
9. RetryPolicy calculates delay metadata only. Scheduling/waiting belongs to a later execution dispatcher.
10. Approval security remains outside the pure Engine; the Engine requires typed outcomes and never self-approves.
11. Invalid snapshot shape, duplicate attempts, multiple active steps, and incomplete deadlocks produce failure decisions rather than undefined scheduling.

## Domain contract changes

- Added retry backoff fields to `WorkflowStep`.
- Added resolved-input assignment when `StepRun` enters READY.
- Removed automatic root readiness from Domain start.
- Removed automatic downstream readiness and workflow completion from StepRun completion.
- Added explicit Domain mutations for marking ready, completing a workflow, and failing an execution.

These changes are backward-incompatible for callers that relied on Phase 1's automatic coordinator behavior. They intentionally implement the frozen ownership rule that Workflow Engine—not Domain—owns scheduling decisions.

## Tests

The full suite contains 17 passing tests:

- 5 Domain Core regression tests
- 12 Workflow Engine tests

Workflow Engine coverage includes:

1. Linear DAG input resolution and completion
2. Diamond DAG deterministic branch ordering
3. Cyclic DAG rejection
4. Missing dependency rejection
5. Duplicate ID and invalid-reference rejection
6. Retry scheduling and backoff metadata
7. Retry exhaustion
8. Approval pause and approved resume
9. Recovery from retry checkpoint
10. Deterministic capped RetryPolicy
11. Pure decision/no mutation behavior
12. Missing execution-state invariant failure

Commands:

```text
conda run --no-capture-output -n reagent-dev pytest -q backend
conda run --no-capture-output -n reagent-dev python -m compileall -q backend
```

Latest pytest result before documentation update: `17 passed in 0.05s`.

## Limitations

- No Skill System exists, so skill IDs and versions cannot be resolved against a registry.
- No input/output skill schemas exist beyond workflow-level input checks and runtime output presence.
- Retry delay is not persisted or dispatched.
- Durable approval identity/fingerprint and authorization are missing.
- Decisions and transition batches have no repository transaction or event-log implementation.
- There is no condition language, parallel node execution, loop, dynamic graph, or multi-agent assignment.
- Engine definitions currently convert from Domain models in memory; no YAML parser/schema loader exists.
- No package metadata or `src/reagent` layout migration was performed.

## Recommended next step

Implement the pure Skill System contract with no real integrations:

1. Immutable versioned `SkillMetadata` with input/output schemas.
2. Side-effect, permission, retry-safety, timeout, and idempotency declarations.
3. Asynchronous framework-independent `Skill` protocol.
4. Explicit allow-listed `SkillRegistry` with duplicate/version checks.
5. Scoped `SkillContext` interfaces and normalized immutable `SkillResult`.
6. Deterministic fake skills and contract tests.
7. A thin dispatcher that accepts `StepReady` and returns a normalized outcome without letting a Skill mutate workflow state.

Do not add real LLM providers, arbitrary plugin imports, external APIs, databases, or queues in the next step.
