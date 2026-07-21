"""Pure domain coordination for workflow-run lifecycle state."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from ..enums import AgentSessionStatus, StepRunStatus, WorkflowRunStatus
from ..exceptions import (
    CheckpointMismatchError,
    DomainValidationError,
    ExecutionNotResumableError,
    InvalidStateTransition,
    StepRunNotFoundError,
)
from ..models import AgentSession, Checkpoint, StepRun, Workflow, WorkflowRun
from ..models._utils import thaw_value, utc_now

Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]

def _default_id_factory(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


@dataclass(slots=True)
class ExecutionState:
    """Transient container for entities coordinated in one domain operation.

    This is not a persistence entity. Future application/repository layers will
    load and commit its member entities through explicit ports.
    """

    workflow: Workflow
    workflow_run: WorkflowRun
    agent_session: AgentSession
    step_runs: list[StepRun]
    checkpoints: list[Checkpoint] = field(default_factory=list)

    def latest_step_run(self, step_id: str) -> StepRun:
        attempts = [step_run for step_run in self.step_runs if step_run.step_id == step_id]
        if not attempts:
            raise StepRunNotFoundError(f"No StepRun exists for workflow step {step_id}")
        return max(attempts, key=lambda step_run: step_run.attempt)

    def current_step_runs(self) -> tuple[StepRun, ...]:
        return tuple(self.latest_step_run(step.id) for step in self.workflow.steps)

    @property
    def latest_checkpoint(self) -> Checkpoint:
        if not self.checkpoints:
            raise CheckpointMismatchError("Execution has no checkpoint")
        return self.checkpoints[-1]


class ExecutionCoordinator:
    """Stateless domain service for execution aggregate transitions.

    It does not execute skills, perform I/O, schedule work, or own persistence.
    """

    def __init__(
        self,
        *,
        clock: Clock = utc_now,
        id_factory: IdFactory = _default_id_factory,
    ) -> None:
        self._clock = clock
        self._id_factory = id_factory

    def create_workflow_run(
        self,
        *,
        workflow: Workflow,
        project_id: str,
        actor_user_id: str,
        idempotency_key: str,
        inputs: Mapping[str, Any],
        agent_profile_ref: str,
    ) -> ExecutionState:
        """Create domain entities for a new, unstarted workflow run."""

        self._validate_inputs(workflow, inputs)
        timestamp = self._clock()
        workflow_run = WorkflowRun(
            id=self._id_factory("run"),
            project_id=project_id,
            workflow_id=workflow.id,
            workflow_version=workflow.version,
            actor_user_id=actor_user_id,
            idempotency_key=idempotency_key,
            inputs=inputs,
            created_at=timestamp,
            updated_at=timestamp,
        )
        agent_session = AgentSession(
            id=self._id_factory("agent"),
            project_id=project_id,
            workflow_run_id=workflow_run.id,
            agent_profile_ref=agent_profile_ref,
            role="primary",
            created_at=timestamp,
            updated_at=timestamp,
        )
        step_runs = [
            self._new_step_run(
                workflow_run=workflow_run,
                step_id=step.id,
                attempt=1,
                inputs={},
                timestamp=timestamp,
            )
            for step in workflow.steps
        ]
        execution = ExecutionState(
            workflow=workflow,
            workflow_run=workflow_run,
            agent_session=agent_session,
            step_runs=step_runs,
        )
        self.create_checkpoint(execution)
        return execution

    def start_execution(self, execution: ExecutionState) -> Checkpoint:
        """Initialize a created run without making scheduling decisions."""

        timestamp = self._clock()
        execution.workflow_run.transition_to(
            WorkflowRunStatus.INITIALIZING, at=timestamp
        )
        execution.agent_session.transition_to(
            AgentSessionStatus.INITIALIZING, at=timestamp
        )

        execution.workflow_run.transition_to(WorkflowRunStatus.RUNNING, at=timestamp)
        execution.agent_session.transition_to(AgentSessionStatus.ACTIVE, at=timestamp)
        return self.create_checkpoint(execution)

    def update_step_state(
        self,
        execution: ExecutionState,
        *,
        step_id: str,
        target_status: StepRunStatus,
        outputs: Mapping[str, Any] | None = None,
        error_code: str | None = None,
        retryable: bool = False,
    ) -> Checkpoint | None:
        """Apply one legal step transition and its aggregate consequences."""

        if execution.workflow_run.status is not WorkflowRunStatus.RUNNING:
            raise InvalidStateTransition(
                "WorkflowRun",
                execution.workflow_run.id,
                execution.workflow_run.status.value,
                f"UPDATE_STEP_{target_status.value}",
            )

        timestamp = self._clock()
        step_run = execution.latest_step_run(step_id)
        step_run.transition_to(
            target_status,
            at=timestamp,
            outputs=outputs,
            error_code=error_code,
        )

        if target_status is StepRunStatus.WAITING_APPROVAL:
            execution.workflow_run.transition_to(
                WorkflowRunStatus.WAITING_FOR_APPROVAL,
                at=timestamp,
                wait_reason=f"approval:{step_id}",
            )
            execution.agent_session.transition_to(
                AgentSessionStatus.WAITING, at=timestamp
            )
            return self.create_checkpoint(execution)

        if target_status is StepRunStatus.FAILED:
            workflow_step = execution.workflow.get_step(step_id)
            if retryable and step_run.attempt < workflow_step.max_attempts:
                execution.workflow_run.transition_to(
                    WorkflowRunStatus.RETRY_SCHEDULED,
                    at=timestamp,
                    wait_reason=f"retry:{step_id}",
                )
                execution.agent_session.transition_to(
                    AgentSessionStatus.WAITING, at=timestamp
                )
            else:
                execution.workflow_run.transition_to(
                    WorkflowRunStatus.FAILED,
                    at=timestamp,
                    error_code=error_code or "STEP_FAILED",
                )
                execution.agent_session.transition_to(
                    AgentSessionStatus.FAILED, at=timestamp
                )
            return self.create_checkpoint(execution)

        if target_status is StepRunStatus.CANCELLED:
            execution.workflow_run.transition_to(
                WorkflowRunStatus.CANCELLING, at=timestamp
            )
            execution.agent_session.transition_to(
                AgentSessionStatus.CANCELLING, at=timestamp
            )
            execution.workflow_run.transition_to(
                WorkflowRunStatus.CANCELLED, at=timestamp
            )
            execution.agent_session.transition_to(
                AgentSessionStatus.CANCELLED, at=timestamp
            )
            return self.create_checkpoint(execution)

        if target_status is StepRunStatus.COMPLETED:
            return self.create_checkpoint(execution)

        return None

    def mark_step_ready(
        self,
        execution: ExecutionState,
        *,
        step_id: str,
        inputs: Mapping[str, Any] | None = None,
        checkpoint: bool = True,
    ) -> Checkpoint | None:
        """Apply an Engine decision that a created step is now ready."""

        if execution.workflow_run.status is not WorkflowRunStatus.RUNNING:
            raise InvalidStateTransition(
                "WorkflowRun",
                execution.workflow_run.id,
                execution.workflow_run.status.value,
                "MARK_STEP_READY",
            )
        execution.latest_step_run(step_id).transition_to(
            StepRunStatus.READY, at=self._clock(), inputs=inputs
        )
        return self.create_checkpoint(execution) if checkpoint else None

    def complete_workflow(
        self,
        execution: ExecutionState,
        *,
        outputs: Mapping[str, Any],
    ) -> Checkpoint:
        """Apply an Engine decision that every required step has succeeded."""

        if not all(
            step_run.status in {StepRunStatus.COMPLETED, StepRunStatus.SKIPPED}
            for step_run in execution.current_step_runs()
        ):
            raise DomainValidationError(
                "Workflow cannot complete while a current step is non-successful"
            )
        timestamp = self._clock()
        execution.workflow_run.set_outputs(outputs)
        execution.workflow_run.transition_to(
            WorkflowRunStatus.COMPLETED, at=timestamp
        )
        execution.agent_session.transition_to(
            AgentSessionStatus.COMPLETED, at=timestamp
        )
        return self.create_checkpoint(execution)

    def fail_execution(
        self,
        execution: ExecutionState,
        *,
        error_code: str,
    ) -> Checkpoint:
        """Apply an Engine invariant/validation failure and fence remaining steps."""

        timestamp = self._clock()
        for step_run in execution.current_step_runs():
            if not step_run.status.is_terminal:
                step_run.transition_to(StepRunStatus.CANCELLED, at=timestamp)
        execution.workflow_run.transition_to(
            WorkflowRunStatus.FAILED,
            at=timestamp,
            error_code=error_code,
        )
        execution.agent_session.transition_to(
            AgentSessionStatus.FAILED, at=timestamp
        )
        return self.create_checkpoint(execution)

    def create_checkpoint(self, execution: ExecutionState) -> Checkpoint:
        """Append an integrity-protected checkpoint of current domain state."""

        checkpoint = Checkpoint.create(
            checkpoint_id=self._id_factory("checkpoint"),
            workflow_run_id=execution.workflow_run.id,
            agent_session_id=execution.agent_session.id,
            sequence=len(execution.checkpoints) + 1,
            state=self._snapshot(execution),
            created_at=self._clock(),
            parent_id=execution.checkpoints[-1].id if execution.checkpoints else None,
        )
        execution.checkpoints.append(checkpoint)
        return checkpoint

    def resume_from_checkpoint(
        self, execution: ExecutionState, checkpoint: Checkpoint
    ) -> StepRun | None:
        """Resume the latest waiting, retry, or interrupted checkpoint."""

        state = self._validate_checkpoint(execution, checkpoint)
        timestamp = self._clock()
        run_status = execution.workflow_run.status

        if run_status is WorkflowRunStatus.WAITING_FOR_APPROVAL:
            waiting_step = self._step_with_status(
                execution, StepRunStatus.WAITING_APPROVAL
            )
            execution.workflow_run.transition_to(WorkflowRunStatus.RUNNING, at=timestamp)
            execution.agent_session.transition_to(AgentSessionStatus.ACTIVE, at=timestamp)
            waiting_step.transition_to(StepRunStatus.RUNNING, at=timestamp)
            self.create_checkpoint(execution)
            return waiting_step

        if run_status is WorkflowRunStatus.WAITING_FOR_INPUT:
            execution.workflow_run.transition_to(WorkflowRunStatus.RUNNING, at=timestamp)
            execution.agent_session.transition_to(AgentSessionStatus.ACTIVE, at=timestamp)
            self.create_checkpoint(execution)
            return None

        if run_status is WorkflowRunStatus.RETRY_SCHEDULED:
            wait_reason = state["workflow_run"].get("wait_reason")
            if not isinstance(wait_reason, str) or not wait_reason.startswith("retry:"):
                raise CheckpointMismatchError(
                    "Retry checkpoint does not identify the failed workflow step"
                )
            step_id = wait_reason.removeprefix("retry:")
            failed_attempt = execution.latest_step_run(step_id)
            if failed_attempt.status is not StepRunStatus.FAILED:
                raise CheckpointMismatchError(
                    f"Retry checkpoint step {step_id} is not in FAILED state"
                )
            workflow_step = execution.workflow.get_step(step_id)
            if failed_attempt.attempt >= workflow_step.max_attempts:
                raise ExecutionNotResumableError(
                    f"Step {step_id} has exhausted its retry attempts"
                )

            execution.workflow_run.transition_to(WorkflowRunStatus.RUNNING, at=timestamp)
            execution.agent_session.transition_to(AgentSessionStatus.ACTIVE, at=timestamp)
            retry_attempt = self._new_step_run(
                workflow_run=execution.workflow_run,
                step_id=step_id,
                attempt=failed_attempt.attempt + 1,
                inputs=thaw_value(failed_attempt.inputs),
                timestamp=timestamp,
            )
            retry_attempt.transition_to(StepRunStatus.READY, at=timestamp)
            execution.step_runs.append(retry_attempt)
            self.create_checkpoint(execution)
            return retry_attempt

        if run_status is WorkflowRunStatus.RUNNING:
            active_steps = [
                step_run
                for step_run in execution.current_step_runs()
                if step_run.status is StepRunStatus.RUNNING
            ]
            if not active_steps:
                return None
            if len(active_steps) > 1:
                raise CheckpointMismatchError(
                    "V1 checkpoint contains more than one active step"
                )
            interrupted = active_steps[0]
            workflow_step = execution.workflow.get_step(interrupted.step_id)
            interrupted.transition_to(
                StepRunStatus.FAILED,
                at=timestamp,
                error_code="INTERRUPTED",
            )
            if interrupted.attempt >= workflow_step.max_attempts:
                execution.workflow_run.transition_to(
                    WorkflowRunStatus.FAILED,
                    at=timestamp,
                    error_code="INTERRUPTED_RETRY_EXHAUSTED",
                )
                execution.agent_session.transition_to(
                    AgentSessionStatus.FAILED, at=timestamp
                )
                self.create_checkpoint(execution)
                raise ExecutionNotResumableError(
                    f"Interrupted step {interrupted.step_id} has no retry remaining"
                )
            retry_attempt = self._new_step_run(
                workflow_run=execution.workflow_run,
                step_id=interrupted.step_id,
                attempt=interrupted.attempt + 1,
                inputs=thaw_value(interrupted.inputs),
                timestamp=timestamp,
            )
            retry_attempt.transition_to(StepRunStatus.READY, at=timestamp)
            execution.step_runs.append(retry_attempt)
            self.create_checkpoint(execution)
            return retry_attempt

        raise ExecutionNotResumableError(
            f"WorkflowRun in {run_status.value} cannot resume from a checkpoint"
        )

    def cancel_execution(self, execution: ExecutionState) -> Checkpoint:
        """Cancel a non-terminal execution through the canonical two-step state."""

        if execution.workflow_run.status.is_terminal:
            raise ExecutionNotResumableError(
                f"Terminal WorkflowRun {execution.workflow_run.id} cannot be cancelled"
            )
        timestamp = self._clock()
        for step_run in execution.current_step_runs():
            if not step_run.status.is_terminal:
                step_run.transition_to(StepRunStatus.CANCELLED, at=timestamp)
        execution.workflow_run.transition_to(
            WorkflowRunStatus.CANCELLING, at=timestamp
        )
        execution.agent_session.transition_to(
            AgentSessionStatus.CANCELLING, at=timestamp
        )
        execution.workflow_run.transition_to(WorkflowRunStatus.CANCELLED, at=timestamp)
        execution.agent_session.transition_to(
            AgentSessionStatus.CANCELLED, at=timestamp
        )
        return self.create_checkpoint(execution)

    def _new_step_run(
        self,
        *,
        workflow_run: WorkflowRun,
        step_id: str,
        attempt: int,
        inputs: Mapping[str, Any],
        timestamp: datetime,
    ) -> StepRun:
        return StepRun(
            id=self._id_factory("step_run"),
            workflow_run_id=workflow_run.id,
            step_id=step_id,
            attempt=attempt,
            idempotency_key=f"{workflow_run.id}:{step_id}:{attempt}",
            inputs=inputs,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def _validate_inputs(self, workflow: Workflow, inputs: Mapping[str, Any]) -> None:
        if not isinstance(inputs, Mapping):
            raise DomainValidationError("Workflow inputs must be a mapping")

        for input_name, specification in workflow.input_schema.items():
            is_required = True
            expected_type: str | None = None
            if isinstance(specification, Mapping):
                is_required = specification.get("required", True) is not False
                raw_type = specification.get("type")
                expected_type = raw_type if isinstance(raw_type, str) else None
            if is_required and input_name not in inputs:
                raise DomainValidationError(
                    f"Missing required workflow input: {input_name}"
                )
            if input_name in inputs and expected_type is not None:
                self._validate_input_type(input_name, inputs[input_name], expected_type)

    @staticmethod
    def _validate_input_type(name: str, value: Any, expected_type: str) -> None:
        type_map: dict[str, type[Any] | tuple[type[Any], ...]] = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": (list, tuple),
            "object": Mapping,
        }
        python_type = type_map.get(expected_type)
        if python_type is None:
            raise DomainValidationError(
                f"Unsupported input type {expected_type!r} for {name}"
            )
        if expected_type in {"integer", "number"} and isinstance(value, bool):
            raise DomainValidationError(
                f"Workflow input {name} must be {expected_type}, not boolean"
            )
        if not isinstance(value, python_type):
            raise DomainValidationError(
                f"Workflow input {name} must be of type {expected_type}"
            )

    def _snapshot(self, execution: ExecutionState) -> dict[str, Any]:
        return {
            "contract_version": 1,
            "workflow": {
                "id": execution.workflow.id,
                "version": execution.workflow.version,
                "schema_version": execution.workflow.schema_version,
            },
            "workflow_run": {
                "id": execution.workflow_run.id,
                "project_id": execution.workflow_run.project_id,
                "status": execution.workflow_run.status.value,
                "row_version": execution.workflow_run.row_version,
                "wait_reason": execution.workflow_run.wait_reason,
                "error_code": execution.workflow_run.error_code,
                "outputs": thaw_value(execution.workflow_run.outputs),
            },
            "agent_session": {
                "id": execution.agent_session.id,
                "status": execution.agent_session.status.value,
                "row_version": execution.agent_session.row_version,
            },
            "step_runs": [
                {
                    "id": step_run.id,
                    "step_id": step_run.step_id,
                    "attempt": step_run.attempt,
                    "status": step_run.status.value,
                    "row_version": step_run.row_version,
                    "outputs": thaw_value(step_run.outputs),
                    "error_code": step_run.error_code,
                }
                for step_run in execution.step_runs
            ],
        }

    def _validate_checkpoint(
        self, execution: ExecutionState, checkpoint: Checkpoint
    ) -> dict[str, Any]:
        if checkpoint.id != execution.latest_checkpoint.id:
            raise CheckpointMismatchError("Only the latest checkpoint may be resumed")
        if checkpoint.workflow_run_id != execution.workflow_run.id:
            raise CheckpointMismatchError("Checkpoint belongs to another WorkflowRun")
        if checkpoint.agent_session_id != execution.agent_session.id:
            raise CheckpointMismatchError("Checkpoint belongs to another AgentSession")

        state = checkpoint.restore_state()
        workflow_state = state.get("workflow", {})
        run_state = state.get("workflow_run", {})
        session_state = state.get("agent_session", {})
        if workflow_state.get("id") != execution.workflow.id or workflow_state.get(
            "version"
        ) != execution.workflow.version:
            raise CheckpointMismatchError("Checkpoint pins another Workflow version")
        if run_state.get("id") != execution.workflow_run.id or run_state.get(
            "status"
        ) != execution.workflow_run.status.value:
            raise CheckpointMismatchError("Checkpoint WorkflowRun state is stale")
        if run_state.get("row_version") != execution.workflow_run.row_version:
            raise CheckpointMismatchError("Checkpoint WorkflowRun version is stale")
        if session_state.get("id") != execution.agent_session.id or session_state.get(
            "status"
        ) != execution.agent_session.status.value:
            raise CheckpointMismatchError("Checkpoint AgentSession state is stale")
        if session_state.get("row_version") != execution.agent_session.row_version:
            raise CheckpointMismatchError("Checkpoint AgentSession version is stale")

        checkpoint_step_states = state.get("step_runs")
        if not isinstance(checkpoint_step_states, list):
            raise CheckpointMismatchError("Checkpoint has no valid StepRun state list")
        checkpoint_steps_by_id = {
            item.get("id"): item
            for item in checkpoint_step_states
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if len(checkpoint_steps_by_id) != len(execution.step_runs):
            raise CheckpointMismatchError("Checkpoint StepRun collection is stale")
        for step_run in execution.step_runs:
            step_state = checkpoint_steps_by_id.get(step_run.id)
            if step_state is None:
                raise CheckpointMismatchError(
                    f"Checkpoint is missing StepRun {step_run.id}"
                )
            if (
                step_state.get("status") != step_run.status.value
                or step_state.get("row_version") != step_run.row_version
            ):
                raise CheckpointMismatchError(
                    f"Checkpoint StepRun {step_run.id} state is stale"
                )
        return state

    @staticmethod
    def _step_with_status(
        execution: ExecutionState, status: StepRunStatus
    ) -> StepRun:
        matches = [
            step_run
            for step_run in execution.current_step_runs()
            if step_run.status is status
        ]
        if len(matches) != 1:
            raise CheckpointMismatchError(
                f"Expected one current step in {status.value}; found {len(matches)}"
            )
        return matches[0]
