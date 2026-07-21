# Workflow Engine Preparation

- Date: 2026-07-20
- Status: Design preparation complete; Workflow Engine not implemented
- Depends on: `.agent_read/progress/architecture_contract.md`
- Domain baseline: `.agent_read/progress/domain_core_implementation.md`

## Purpose and scope

The next phase will add a pure, deterministic Workflow Engine over the existing domain entities. It must decide what the workflow may do next; it must not execute skills, call LLMs, access storage, schedule processes, or own transactions.

The `ExecutionCoordinator` remains responsible for applying approved domain transitions and creating checkpoints. The Workflow Engine and Agent Runtime remain sibling services under the future application coordinator.

V1 remains deliberately limited to immutable static DAGs and one active node per Workflow Run. Loops, conditional branching, dynamic graph mutation, parallel nodes within one run, and multi-agent scheduling remain out of scope.

## 1. Workflow Engine responsibilities

The Workflow Engine must:

1. Validate the runtime-relevant parts of an already constructed `Workflow`.
2. Inspect the latest `StepRun` attempt for every workflow node.
3. Enforce that at most one step is active in a v1 run.
4. Select the next eligible node deterministically.
5. Resolve the selected node's input mapping from workflow inputs and completed dependency outputs.
6. Return a typed decision describing the next action without performing that action.
7. Classify step outcomes into success, approval wait, retry, terminal failure, or cancellation transition plans.
8. Identify every transition that requires a checkpoint.
9. Detect deadlocked or internally inconsistent execution state and return an invariant failure rather than silently waiting.
10. Preserve exact workflow, schema, step, skill, and attempt versions in every decision.

The Workflow Engine must not:

- invoke a Skill or LLM
- mutate PostgreSQL, files, or external services
- authorize a user or approve an action
- create worker tasks or sleep until retry time
- contain FastAPI, queue, ORM, or provider types
- create a second lifecycle state machine that disagrees with domain entities

## 2. Interaction with the Domain Layer

### Proposed interaction boundary

The engine should be a pure decision service with conceptual operations:

```text
WorkflowEngine.validate(workflow) -> ValidationResult
WorkflowEngine.next_decision(execution_snapshot) -> EngineDecision
WorkflowEngine.resolve_inputs(workflow, step, execution_snapshot) -> ResolvedInputs
WorkflowEngine.evaluate_outcome(execution_snapshot, step_outcome) -> TransitionPlan
```

Inputs are read-only views of existing `Workflow`, `WorkflowRun`, `StepRun`, and `AgentSession` state. Outputs are immutable decision/value objects. The engine does not call entity transition methods itself.

The future application flow should be:

```text
Application ExecutionCoordinator
        |
        +--> WorkflowEngine.next_decision(snapshot)
        |         |
        |         +--> ReadyStep | ApprovalRequired | RetryDue
        |              WorkflowComplete | WorkflowFailed | NoAction
        |
        +--> Agent Runtime / Skill System for ReadyStep only
        |
        +--> existing domain transitions and checkpoint creation
```

### Existing-code responsibility adjustment

Phase 1's `ExecutionCoordinator` currently contains private helpers for newly ready steps and workflow-output resolution. These were sufficient to prove the domain lifecycle but overlap the frozen Workflow Engine responsibility.

During Workflow Engine implementation:

- move ready-node calculation and input/output reference resolution behind the Workflow Engine contract;
- keep entity mutation, aggregate consistency, and checkpoint construction in `ExecutionCoordinator`;
- do not duplicate the algorithms in both services;
- preserve all existing lifecycle tests while adding engine-specific tests.

This is a responsibility refactor, not a change to the frozen architecture.

## 3. Ready-node selection algorithm

### Preconditions

The engine may select a node only when:

- `WorkflowRun.status` is `RUNNING`;
- the Agent Session is `ACTIVE`;
- no current StepRun is `RUNNING` or `WAITING_APPROVAL`;
- every workflow node has exactly one identifiable latest attempt;
- the workflow/run pinned IDs and versions match.

### Algorithm

1. Build `latest_attempt_by_step_id` by taking the highest attempt number for each workflow step.
2. Reject missing step state, duplicate attempt numbers, or step IDs not present in the pinned Workflow.
3. If all latest attempts are `COMPLETED` or `SKIPPED`, return `WorkflowComplete` after resolving declared workflow outputs.
4. If any latest attempt is `RUNNING` or `WAITING_APPROVAL`, return `NoAction` because v1 permits one active node.
5. Collect candidates whose latest state is `READY` and whose dependencies are all `COMPLETED` or `SKIPPED`.
6. If a node is still `CREATED` but all dependencies are complete, return a transition plan that first marks it `READY`; readiness must not be silently inferred without a state transition/checkpoint decision.
7. Order eligible candidates by their definition order in `Workflow.steps`, then by step ID as a stable fallback.
8. Select exactly one candidate.
9. Resolve its inputs. Return `ReadySkillStep` for a skill node or `ApprovalRequired` for an approval node.
10. If the run is non-terminal, has no active/candidate node, and not all nodes succeeded, return `WorkflowInvariantFailure` with blocked-node diagnostics.

Independent ready nodes remain sequential in v1. The algorithm must avoid relying on dictionary/set iteration order so that recovery produces the same decision.

## 4. Step execution lifecycle

### Skill node

```text
CREATED -> READY -> RUNNING -> COMPLETED
                       |
                       +--> FAILED
                       +--> CANCELLED
```

1. Engine returns the selected step and resolved input values.
2. Application layer transitions `READY -> RUNNING` and dispatches the future Skill Executor.
3. A normalized `StepOutcome` returns success values, typed failure, cancellation, or a protected-action approval request.
4. Engine validates that the outcome belongs to the selected run/node/attempt and evaluates the next transition plan.
5. Application layer applies the plan using domain transitions.
6. Successful output must validate before the step becomes `COMPLETED`.
7. Downstream readiness is evaluated only after the successful checkpoint boundary commits.

### Approval node

```text
CREATED -> READY -> RUNNING -> WAITING_APPROVAL
                                  |
             approved ------------+--> RUNNING -> COMPLETED
             rejected/expired ----+--> CANCELLED
```

An approval node performs no Skill execution. The engine returns an approval requirement; the application creates the future durable approval record and pauses. After an authorized approval is committed, the existing checkpoint-resume path restores the node to `RUNNING`, then the engine returns a plan to mark that approval node `COMPLETED`. Rejection or default expiry cancels the run in v1.

### Input resolution requirements

V1 should support JSON-compatible literal values and whole-value references:

```text
${inputs.<name>}
${nodes.<dependency_step>.outputs.<name>}
```

Resolution must preserve the referenced value's type and recurse through mappings/lists. String interpolation, arbitrary expressions, code evaluation, and references to non-ancestor nodes are prohibited. Missing inputs, missing outputs, malformed expressions, and hidden undeclared dependencies are non-retryable validation failures.

## 5. Checkpoint boundaries

The Workflow Engine does not serialize checkpoints. Every `TransitionPlan` must declare whether a checkpoint is required and why. `ExecutionCoordinator` creates it after applying the complete in-memory transition set.

Required boundaries remain:

- after run initialization
- after every successful step and newly ready-node state update
- before `WAITING_FOR_APPROVAL` or `WAITING_FOR_INPUT`
- when entering `RETRY_SCHEDULED`
- after recovering into a new attempt
- after cancellation fencing
- before `COMPLETED`, `FAILED`, or `CANCELLED` becomes externally visible

No downstream step may be dispatched until the upstream successful transition and checkpoint are durably committed by the future application/repository layer. Engine decisions should carry run row version, step-run row version, workflow version, and checkpoint reason so stale decisions can be rejected later.

## 6. Retry handling

The engine consumes typed failure information and the referenced WorkflowStep retry policy.

1. Non-retryable errors immediately produce a terminal failure plan.
2. Retryable errors compare the current attempt number with `max_attempts`.
3. If budget remains, the current attempt becomes `FAILED`, the run enters `RETRY_SCHEDULED`, and a checkpoint is required.
4. When retry eligibility is reached, resume creates a new StepRun with `attempt + 1`, a stable idempotency key, and `READY` state.
5. Previous failed attempts remain immutable history.
6. If the budget is exhausted, the run enters terminal `FAILED` and downstream nodes never run.

Domain gap to resolve in the first Workflow Engine change: `WorkflowStep` currently models `max_attempts` but not the frozen contract's backoff settings. Add an immutable standard-library `RetryPolicy` value object or equivalent fields for backoff kind, initial seconds, and maximum seconds before implementing retry scheduling calculations. Jitter should be supplied through an injectable deterministic policy; engine tests must not depend on wall-clock randomness.

The engine computes a `retry_not_before` value or retry-delay instruction but never sleeps or enqueues work.

## 7. Approval handling

The Workflow Engine must distinguish:

- explicit approval nodes in v1;
- a future protected Skill action requiring policy approval.

For an explicit approval node, the engine returns:

- workflow/run/node/attempt identity
- approval policy key
- prompt/description when added to the domain model
- pinned workflow and step versions
- checkpoint requirement

The application layer, not the engine, will later verify user identity, role, expiry, idempotency, and request fingerprint. The engine must not accept a plain boolean without a matching approval-request identity.

Implementation gap to preserve: Phase 1 has no `ApprovalRequest` entity or approval fingerprint. Initial Workflow Engine tests may use a typed `ApprovalOutcome` value object, but durable approval authorization must remain explicitly pending rather than being simulated as complete security.

Approval outcomes:

- `APPROVED`: resume the exact fingerprinted node attempt and complete the approval node.
- `REJECTED`: produce cancellation plan with `APPROVAL_REJECTED`.
- `EXPIRED`: default to cancellation, never implicit approval.
- stale/mismatched: reject without changing execution state.

## 8. Failure propagation

Failure behavior is fail-fast in v1 because conditional recovery branches are out of scope.

| Failure | Engine behavior | Run result |
|---|---|---|
| Invalid workflow/input/reference/output | Non-retryable transition plan | `FAILED` |
| Authorization/policy rejection | No execution; application audit required | `FAILED` or approval wait, depending on policy |
| Retryable provider/tool failure with budget | Schedule new attempt after checkpoint | `RETRY_SCHEDULED` |
| Retryable failure with exhausted budget | Preserve attempts and fail | `FAILED` |
| Permanent skill failure | Preserve typed error and fail | `FAILED` |
| Cancellation request | Fence active action then cancel | `CANCELLING -> CANCELLED` |
| Approval rejected/expired | Cancel under v1 policy | `CANCELLING -> CANCELLED` |
| Corrupted/stale checkpoint | Reject resume and raise invariant alert | No silent transition |
| No active/ready node in incomplete DAG | Return blocked-state diagnostics | `FAILED` as invariant violation |

When a run fails or is cancelled, all non-terminal downstream StepRuns should be transitioned to `CANCELLED` or a separately justified terminal state before the terminal checkpoint. The engine must never schedule descendants of a failed dependency.

## Proposed engine decision types

The implementation should define immutable, typed decisions rather than strings:

- `ReadySkillStep`
- `ApprovalRequired`
- `MarkStepReady`
- `ScheduleRetry`
- `WorkflowComplete`
- `WorkflowFailure`
- `CancellationPlan`
- `NoAction`

Every decision should include pinned run/workflow identity and expected row versions. Decision application remains the coordinator's responsibility.

## Required tests before engine completion

1. Linear DAG selection and completion.
2. Diamond DAG deterministic ordering with sequential execution.
3. Dependency blocking and missing-output failure.
4. Literal and nested input-reference resolution with type preservation.
5. Hidden dependency/reference rejection.
6. Explicit approval node pause, approved completion, rejection, and expiry.
7. Retry scheduling, new attempt, backoff calculation, and exhaustion.
8. No duplicate dispatch when an active step exists.
9. Corrupt/stale checkpoint and stale decision rejection.
10. Interrupted active step recovery through a new attempt.
11. Terminal-state immutability and downstream cancellation.
12. Deterministic behavior across repeated evaluation of the same snapshot.

## Readiness conclusion

The domain core is sufficient to begin Workflow Engine implementation. The first engine change should introduce decision/value objects and close the RetryPolicy model gap, then move readiness and reference-resolution responsibility out of private coordinator helpers. No infrastructure dependency is required or permitted for that work.
