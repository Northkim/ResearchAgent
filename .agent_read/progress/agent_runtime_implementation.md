# Agent Runtime Implementation

- Date: 2026-07-20
- Status: Completed
- Phase: 4 — Deterministic In-Memory Agent Runtime
- Environment: `reagent-dev`
- Architecture: `.agent_read/progress/architecture_contract.md`
- Inputs: completed Domain Core, Workflow Engine, and Skill System

## Runtime architecture

`AgentRuntime` is an asynchronous application orchestrator. Its control flow is:

```text
ExecutionState
      |
      v
WorkflowExecutionCoordinator.decide()
      |
      +--> StepReady --------> SkillExecutor --------> SkillResult
      |                              |                      |
      |                              +-- no state mutation -+
      |                                                     |
      +<-------- Workflow failure/retry evaluation <---------+
      |
      v
explicit Domain coordinator operations
      |
      v
Domain checkpoint + runtime boundary record + memory revision
```

Responsibility remains separated:

- Workflow Engine decides which node is ready, whether a failure retries, and whether the workflow is complete/failed/waiting/cancelled.
- Skill System resolves and executes the exact pinned capability and returns normalized data/errors.
- Domain Core validates and applies lifecycle transitions and creates integrity-protected snapshots.
- Agent Runtime controls call order, builds bounded context, records checkpoint intent, updates in-memory working context, and yields at waiting/terminal boundaries.

No component private state is modified directly.

## Implemented components

### AgentRuntime

`AgentRuntime.run(execution, approval_outcome=None)`:

1. idempotently initializes project/run-scoped working context
2. indexes the latest Domain checkpoint as its recovery baseline
3. starts a newly created Domain execution
4. resumes a retry or interrupted attempt from the latest verified checkpoint
5. resolves a typed approval outcome when supplied
6. repeatedly requests and handles Workflow Engine decisions
7. yields a normalized immutable `RuntimeResult` at terminal, approval, input, or retry boundaries

A deterministic decision limit prevents an accidental infinite in-process loop without changing Workflow Engine scheduling semantics.

### Decision handling

- `StepReady`: apply ready transition if required, transition the StepRun to RUNNING, checkpoint, build context, execute the exact Skill, then apply success or evaluate failure.
- `WorkflowCompleted`: checkpoint before terminal visibility, apply Domain completion, and record the terminal checkpoint.
- `WaitingApproval`: apply the waiting transition/checkpoint and yield without auto-approval.
- `RetryScheduled`: apply the failed attempt/retry wait checkpoint and yield; a later `run()` call resumes a new attempt.
- `WorkflowFailed`: checkpoint before terminal transition, apply the typed failure through Domain operations, and yield FAILED.
- `WorkflowCancelled`: checkpoint before cancellation, apply the canonical cancelling/cancelled Domain transitions, and yield CANCELLED.
- `ApprovalCompleted`: apply the approval-step completion and continue graph evaluation.
- `NoAction`: return current state without mutation.

### Execution context

`AgentExecutionContext` is immutable and attempt-scoped. It contains:

- project, run, session, workflow, step, and attempt identifiers
- workflow inputs and Engine-resolved step inputs
- latest working-memory revision
- latest integrity-verified checkpoint ID
- provenance references for workflow version, checkpoint, and StepRun

The developer `.agent_read` directory is never loaded into product runtime context.

### Memory gateway

`MemoryStore` is a minimal project/run-scoped, append-only in-memory adapter:

- `read_context(project_id, workflow_run_id)` returns the latest immutable revision
- `update_context(...)` merges a new top-level revision with producer and source references
- `initialize_context(...)` is idempotent
- `history(...)` preserves earlier revisions

The runtime initializes workflow identity/inputs and adds step outputs after successful Skill completion. This is working-context behavior only; it is not vector or long-term storage.

### Checkpoint integration

Domain `Checkpoint` remains the integrity-protected source of execution snapshots. `InMemoryCheckpointStore` adds idempotent intent metadata without copying lifecycle state.

Recorded boundaries include:

- `BEFORE_SKILL`
- `AFTER_SKILL`
- `BEFORE_TERMINAL`
- `TERMINAL`
- `WAITING_APPROVAL`
- `RETRY_SCHEDULED`
- `RECOVERED`
- initialization, step-ready, and approval-resolution metadata

Runtime records do not replace Domain checkpoints and introduce no database responsibility.

## Complete execution lifecycle

For the tested `mock_paper_search -> mock_summary` workflow:

1. Domain execution starts and moves run/session to RUNNING/ACTIVE.
2. Engine returns `StepReady(search)` with `${inputs.topic}` resolved.
3. Runtime records search READY/RUNNING and a pre-Skill checkpoint.
4. `mock_paper_search@1.0.0` returns validated paper titles.
5. Runtime applies StepRun completion, records the post-Skill checkpoint, and revises working context.
6. Engine returns `StepReady(summary)` with papers resolved from the search output.
7. Runtime repeats the pre/post Skill boundaries for `mock_summary@1.0.0`.
8. Engine returns `WorkflowCompleted` with the resolved workflow summary.
9. Runtime records `BEFORE_TERMINAL`, applies Domain completion, records the terminal checkpoint, and returns `RuntimeResult(COMPLETED)`.

Approval and retry decisions yield control after a checkpoint. Reinvoking `run()` resumes only from the latest consistent checkpoint. Reinvoking it after a terminal result performs no state, memory, or checkpoint mutation.

## Files created

```text
backend/agent_runtime/
├── __init__.py
├── _immutability.py
├── checkpoint/
│   ├── __init__.py
│   └── checkpoint_store.py
├── context/
│   ├── __init__.py
│   └── execution_context.py
├── memory/
│   ├── __init__.py
│   └── memory_store.py
├── runtime/
│   ├── __init__.py
│   ├── agent_runtime.py
│   └── runtime_result.py
└── tests/
    ├── __init__.py
    └── test_agent_runtime.py
```

## Documentation updated

- `.agent_read/context.md`
- `.agent_read/progress/agent_runtime_implementation.md` (this report)

No Domain, Workflow Engine, or Skill System source file changed.

## Integration decisions

1. `run()` is asynchronous because Skill execution is asynchronous.
2. Approval and retry are explicit yield boundaries; the runtime never auto-approves or sleeps.
3. A subsequent `run()` call resumes RETRY_SCHEDULED immediately in Phase 4 because no clock/dispatcher exists; persisted `not_before` enforcement is deferred.
4. The Engine-resolved inputs in `StepReady` remain authoritative and are passed unchanged through the attempt context to SkillExecutor.
5. Skill success maps directly to explicit Domain StepRun completion because Engine has no success-mutation decision; Skill failure is first evaluated by Engine for retry/terminal policy.
6. Runtime checkpoint records explain boundaries, while Domain checkpoints remain authoritative and integrity protected.
7. Terminal and waiting replay is idempotent in one process: repeated calls do not create revisions, execute Skills, or append Domain checkpoints.
8. Memory updates are append-only revisions and do not silently overwrite their history.
9. No architecture contract or accepted ADR was changed; these choices instantiate already frozen orchestration and checkpoint responsibilities.

## Tests

Six Agent Runtime tests cover:

1. complete linear `mock_paper_search -> mock_summary -> COMPLETED` execution
2. deterministic Skill failure mapped to FAILED Domain state
3. retry checkpoint yield and recovery as a new attempt
4. approval pause, repeated no-op wait, and approved resume
5. idempotent replay after terminal completion
6. rejected approval mapped through `WorkflowCancelled` to CANCELLED

Commands:

```text
conda run --no-capture-output -n reagent-dev pytest -q backend
conda run --no-capture-output -n reagent-dev python -m compileall -q backend
```

Latest result: compilation passed; `32 passed` (5 Domain, 12 Workflow Engine, 9 Skill System, 6 Agent Runtime). Python remains 3.11.15.

## Limitations

- ExecutionState, memory revisions, and checkpoint-boundary records are process-local and not reconstructed from a repository.
- Domain transition, Domain checkpoint, memory revision, and runtime boundary metadata lack a real atomic Unit of Work.
- Retry delay metadata is not enforced; resume requires an explicit caller and no queue/lease/clock dispatcher exists.
- Approval has no durable request identity, fingerprint, expiry timer, role authorization, or audit repository.
- Working context is intentionally small; no short/working/long-term retrieval policy, vector memory, or managed file-context adapter exists.
- Skill deadlines, cancellation propagation, permissions, artifacts, proposed memory updates, and tool/model usage are not yet integrated.
- No API, persistence library, PostgreSQL driver, SQLAlchemy mapping, Alembic migration, queue, event log, or telemetry adapter exists.
- Recovery tests use the latest Domain checkpoint plus the still-resident mutable aggregate; full deserialization/reconciliation is a persistence-phase requirement.

## Recommended next step

Implement the persistence boundary before any API:

1. define framework-independent repository and Unit of Work ports for execution aggregates, idempotency lookup, checkpoints, memory revisions, approvals, and execution events
2. implement in-memory adapters and contract tests for atomic save/load, optimistic versions, latest-checkpoint recovery, and idempotent run creation
3. add a mapper/reconstitution service that rebuilds `ExecutionState` and verifies checkpoint hashes/pinned workflow versions
4. only then add SQLAlchemy 2.x models, Alembic migrations, and PostgreSQL integration tests without importing them into Domain, Engine, Skill, or Runtime modules

The Phase 4 linear workflow should become the first persistence integration test and produce the same `RuntimeResult` before and after process reconstruction.
