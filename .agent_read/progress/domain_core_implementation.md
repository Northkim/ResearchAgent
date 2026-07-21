# Domain Core Implementation

- Date: 2026-07-20
- Status: Completed
- Phase: 1 — Domain Core Implementation
- Architecture contract: `.agent_read/progress/architecture_contract.md`

## Files created

Repository configuration:

- `.gitignore`

Packages and exports:

- `backend/__init__.py`
- `backend/domain/__init__.py`
- `backend/domain/models/__init__.py`
- `backend/domain/enums/__init__.py`
- `backend/domain/exceptions/__init__.py`
- `backend/domain/services/__init__.py`
- `backend/domain/tests/__init__.py`

Domain implementation:

- `backend/domain/models/_utils.py`
- `backend/domain/models/workflow.py`
- `backend/domain/models/workflow_step.py`
- `backend/domain/models/workflow_run.py`
- `backend/domain/models/step_run.py`
- `backend/domain/models/agent_session.py`
- `backend/domain/models/checkpoint.py`
- `backend/domain/models/artifact_metadata.py`
- `backend/domain/enums/statuses.py`
- `backend/domain/exceptions/domain_errors.py`
- `backend/domain/services/execution_coordinator.py`

Tests:

- `backend/domain/tests/test_execution_coordinator.py`

Updated separately:

- `.agent_read/context.md`
- `.agent_read/progress/domain_core_implementation.md`

## Design decisions

1. Only Python standard-library types are used. There are no framework, ORM, validation-library, or provider imports.
2. `Workflow` and `WorkflowStep` are frozen dataclasses with recursively frozen configuration mappings. Workflow construction validates unique IDs, existing dependencies, acyclicity, supported schema version, and declared output references.
3. `WorkflowRun`, `StepRun`, and `AgentSession` are mutable lifecycle entities with explicit legal-transition maps and optimistic `row_version` increments.
4. The full frozen-contract status vocabulary is retained. `WAITING_APPROVAL`, `RUNNING`, and `SUCCEEDED` compatibility aliases satisfy Phase 1 naming without replacing canonical contract values.
5. `Checkpoint` stores canonical JSON plus SHA-256 integrity hash, sequence, and parent ID. Checkpoint resumption accepts only the latest matching workflow/session/run/step snapshot.
6. `ExecutionCoordinator` is a pure, stateless domain service. `ExecutionState` only groups entities for a domain operation and is not a persistence entity or actual execution engine.
7. Retry recovery never revives a terminal `FAILED` entity. A retryable attempt transitions the run to `RETRY_SCHEDULED`; resume creates a new `StepRun` attempt with a stable logical idempotency key.
8. Approval pause uses `WAITING_FOR_APPROVAL` at run level and `WAITING_APPROVAL` at step level. Authorization and approval fingerprint checks are intentionally deferred to the application layer.
9. The user-requested `backend/domain/` layout was used. This differs from the contract's eventual `backend/src/reagent/domain/` packaging layout and must be resolved explicitly before packaging; no duplicate implementation was created.
10. `.gitignore` excludes environment files, private keys, virtual environments, caches, coverage/build output, local runtime data, and frontend dependencies/build output. It deliberately keeps source, tests, docs, and `.agent_read/` trackable.

## Tests implemented

The standard-library `unittest` suite covers:

1. Normal two-step workflow lifecycle through final declared output.
2. Invalid WorkflowRun, AgentSession, StepRun, and coordinator transitions.
3. Retryable failure, checkpoint recovery into a new attempt, and eventual completion.
4. Approval pause, durable checkpoint, resume, and completion.
5. Ordered checkpoint creation, parent linkage, state restoration, and tamper detection.

Verification commands:

```text
python3 -m unittest discover -s backend/domain/tests -v
python3 -m compileall -q backend
```

Result: 5 tests passed; compilation passed under Python 3.13.5.

## Remaining limitations

- The coordinator does not run skills or LLMs and is not a Workflow Engine.
- No repository or Unit of Work exists, so idempotency uniqueness, transactionality, locking, and durable rehydration are not yet enforceable.
- No execution-log/domain-event entity or approval-request entity was requested in this phase.
- JSON-schema behavior is intentionally limited to required fields and basic scalar/container types without an external validator.
- Step `with` expression evaluation is deferred to the Workflow Engine.
- Workflow output resolution supports only `${nodes.<step>.outputs.<name>}` references.
- Human approval identity, role checks, fingerprinting, expiry, and rejection audit behavior remain unimplemented.
- Artifact content storage and checksum verification are outside the metadata-only domain entity.
- No static type checker or formatter dependency was installed; correctness was checked through type-annotated code, compilation, import inspection, and unit tests.

## Recommended next step

Implement a pure Workflow Engine application/domain service over these entities. Begin with deterministic ready-node selection, input-reference resolution, explicit engine commands/results, one-node-at-a-time `advance`, and state/checkpoint outcomes for success, retry, approval, failure, and cancellation. Add tests for graph ordering, dependency blocking, invalid mappings, retry exhaustion, and restart behavior.

Do not start FastAPI, SQLAlchemy, PostgreSQL, real skill execution, or LLM integration until the Workflow Engine can drive a deterministic fake workflow through interruption and resume.
