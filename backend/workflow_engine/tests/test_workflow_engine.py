"""Workflow Engine decisions, scheduling, retry, approval, and recovery tests."""

from __future__ import annotations

import pytest

from backend.domain.enums import StepRunStatus, WorkflowRunStatus, WorkflowStepKind
from backend.domain.models import Workflow, WorkflowStep
from backend.domain.services import ExecutionCoordinator, ExecutionState
from backend.workflow_engine.exceptions import (
    InvalidReferenceError,
    InvalidWorkflowDefinitionError,
)
from backend.workflow_engine.models import (
    ApprovalCompleted,
    ApprovalOutcome,
    ExecutionSnapshot,
    RetryPolicy,
    RetryScheduled,
    StepDefinition,
    StepReady,
    WaitingApproval,
    WorkflowCompleted,
    WorkflowDefinition,
    WorkflowFailed,
)
from backend.workflow_engine.services import (
    WorkflowEngine,
    WorkflowExecutionCoordinator,
    WorkflowValidator,
)


def create_execution(
    workflow: Workflow,
) -> tuple[ExecutionCoordinator, WorkflowExecutionCoordinator, ExecutionState]:
    domain = ExecutionCoordinator()
    integration = WorkflowExecutionCoordinator(domain_coordinator=domain)
    execution = domain.create_workflow_run(
        workflow=workflow,
        project_id="project-1",
        actor_user_id="user-1",
        idempotency_key=f"request-{workflow.id}",
        inputs={"topic": "persistent agents", "limit": 5},
        agent_profile_ref="research-agent@1.0.0",
    )
    domain.start_execution(execution)
    return domain, integration, execution


def apply_skill_success(
    domain: ExecutionCoordinator,
    integration: WorkflowExecutionCoordinator,
    execution: ExecutionState,
    *,
    expected_step_id: str,
    outputs: dict[str, object],
) -> StepReady:
    decision = integration.decide(execution)
    assert isinstance(decision, StepReady)
    assert decision.step_id == expected_step_id
    integration.apply_decision(execution, decision)
    domain.update_step_state(
        execution, step_id=expected_step_id, target_status=StepRunStatus.RUNNING
    )
    domain.update_step_state(
        execution,
        step_id=expected_step_id,
        target_status=StepRunStatus.COMPLETED,
        outputs=outputs,
    )
    return decision


def test_linear_dag_resolves_inputs_and_completes() -> None:
    workflow = Workflow(
        id="linear",
        version="1.0.0",
        name="Linear workflow",
        input_schema={
            "topic": {"type": "string"},
            "limit": {"type": "integer"},
        },
        steps=(
            WorkflowStep(
                id="search",
                kind=WorkflowStepKind.SKILL,
                uses="paper-search@1.0.0",
                input_mapping={
                    "query": "${inputs.topic}",
                    "options": {"limit": "${inputs.limit}"},
                },
            ),
            WorkflowStep(
                id="synthesize",
                kind=WorkflowStepKind.SKILL,
                uses="synthesize@1.0.0",
                needs=("search",),
                input_mapping={
                    "topic": "${inputs.topic}",
                    "papers": "${nodes.search.outputs.papers}",
                },
            ),
        ),
        outputs={"report": "${nodes.synthesize.outputs.report}"},
    )
    domain, integration, execution = create_execution(workflow)

    initial_status = execution.latest_step_run("search").status
    first = integration.decide(execution)
    assert isinstance(first, StepReady)
    assert first.step_id == "search"
    assert first.requires_ready_transition is True
    assert first.resolved_inputs["query"] == "persistent agents"
    assert first.resolved_inputs["options"]["limit"] == 5
    assert execution.latest_step_run("search").status is initial_status

    integration.apply_decision(execution, first)
    domain.update_step_state(
        execution, step_id="search", target_status=StepRunStatus.RUNNING
    )
    domain.update_step_state(
        execution,
        step_id="search",
        target_status=StepRunStatus.COMPLETED,
        outputs={"papers": ["paper-1", "paper-2"]},
    )

    second = integration.decide(execution)
    assert isinstance(second, StepReady)
    assert second.step_id == "synthesize"
    assert tuple(second.resolved_inputs["papers"]) == ("paper-1", "paper-2")
    integration.apply_decision(execution, second)
    domain.update_step_state(
        execution, step_id="synthesize", target_status=StepRunStatus.RUNNING
    )
    domain.update_step_state(
        execution,
        step_id="synthesize",
        target_status=StepRunStatus.COMPLETED,
        outputs={"report": "artifact-1"},
    )

    completed = integration.decide(execution)
    assert isinstance(completed, WorkflowCompleted)
    assert completed.outputs["report"] == "artifact-1"
    integration.apply_decision(execution, completed)
    assert execution.workflow_run.status is WorkflowRunStatus.COMPLETED


def test_diamond_dag_uses_definition_order_deterministically() -> None:
    workflow = Workflow(
        id="diamond",
        version="1.0.0",
        name="Diamond workflow",
        input_schema={"topic": {"type": "string"}, "limit": {"type": "integer"}},
        steps=(
            WorkflowStep(id="root", kind=WorkflowStepKind.SKILL, uses="root@1.0.0"),
            WorkflowStep(
                id="right",
                kind=WorkflowStepKind.SKILL,
                uses="right@1.0.0",
                needs=("root",),
            ),
            WorkflowStep(
                id="left",
                kind=WorkflowStepKind.SKILL,
                uses="left@1.0.0",
                needs=("root",),
            ),
            WorkflowStep(
                id="join",
                kind=WorkflowStepKind.SKILL,
                uses="join@1.0.0",
                needs=("left", "right"),
            ),
        ),
    )
    domain, integration, execution = create_execution(workflow)

    apply_skill_success(
        domain, integration, execution, expected_step_id="root", outputs={}
    )
    first_branch = integration.decide(execution)
    repeated = integration.decide(execution)
    assert first_branch == repeated
    assert isinstance(first_branch, StepReady)
    assert first_branch.step_id == "right"

    apply_skill_success(
        domain, integration, execution, expected_step_id="right", outputs={}
    )
    apply_skill_success(
        domain, integration, execution, expected_step_id="left", outputs={}
    )
    join = integration.decide(execution)
    assert isinstance(join, StepReady)
    assert join.step_id == "join"


def test_validator_rejects_cyclic_dag() -> None:
    definition = WorkflowDefinition(
        id="cycle",
        version="1.0.0",
        name="Cycle",
        steps=(
            StepDefinition(
                id="a", kind=WorkflowStepKind.SKILL, uses="a@1", needs=("b",)
            ),
            StepDefinition(
                id="b", kind=WorkflowStepKind.SKILL, uses="b@1", needs=("a",)
            ),
        ),
    )
    with pytest.raises(InvalidWorkflowDefinitionError, match="cycle"):
        WorkflowValidator().validate(definition)


def test_validator_rejects_missing_dependency() -> None:
    definition = WorkflowDefinition(
        id="missing",
        version="1.0.0",
        name="Missing dependency",
        steps=(
            StepDefinition(
                id="a",
                kind=WorkflowStepKind.SKILL,
                uses="a@1",
                needs=("unknown",),
            ),
        ),
    )
    with pytest.raises(InvalidWorkflowDefinitionError, match="missing dependencies"):
        WorkflowValidator().validate(definition)


def test_validator_rejects_duplicate_ids_and_invalid_reference() -> None:
    duplicate = WorkflowDefinition(
        id="duplicate",
        version="1.0.0",
        name="Duplicate",
        steps=(
            StepDefinition(id="a", kind=WorkflowStepKind.SKILL, uses="a@1"),
            StepDefinition(id="a", kind=WorkflowStepKind.SKILL, uses="a@1"),
        ),
    )
    with pytest.raises(InvalidWorkflowDefinitionError, match="duplicate"):
        WorkflowValidator().validate(duplicate)

    invalid_reference = WorkflowDefinition(
        id="reference",
        version="1.0.0",
        name="Reference",
        input_schema={"topic": {"type": "string"}},
        steps=(
            StepDefinition(
                id="a",
                kind=WorkflowStepKind.SKILL,
                uses="a@1",
                input_mapping={"query": "${inputs.missing}"},
            ),
        ),
    )
    with pytest.raises(InvalidReferenceError, match="undefined input"):
        WorkflowValidator().validate(invalid_reference)


def test_retry_scheduling_returns_backoff_metadata_without_waiting() -> None:
    workflow = Workflow(
        id="retry",
        version="1.0.0",
        name="Retry",
        input_schema={"topic": {"type": "string"}, "limit": {"type": "integer"}},
        steps=(
            WorkflowStep(
                id="work",
                kind=WorkflowStepKind.SKILL,
                uses="work@1.0.0",
                max_attempts=3,
                retry_backoff="exponential",
                retry_initial_seconds=2,
                retry_max_seconds=10,
            ),
        ),
    )
    domain, integration, execution = create_execution(workflow)
    ready = integration.decide(execution)
    assert isinstance(ready, StepReady)
    integration.apply_decision(execution, ready)
    domain.update_step_state(
        execution, step_id="work", target_status=StepRunStatus.RUNNING
    )

    decision = integration.evaluate_failure(
        execution,
        step_id="work",
        retryable=True,
        error_code="TRANSIENT_PROVIDER_ERROR",
    )
    assert isinstance(decision, RetryScheduled)
    assert decision.current_attempt == 1
    assert decision.next_attempt == 2
    assert decision.delay_seconds == 2.0
    assert decision.backoff == "exponential"
    integration.apply_decision(execution, decision)
    assert execution.workflow_run.status is WorkflowRunStatus.RETRY_SCHEDULED


def test_retry_exhaustion_returns_terminal_failure() -> None:
    workflow = Workflow(
        id="retry-exhausted",
        version="1.0.0",
        name="Retry exhausted",
        input_schema={"topic": {"type": "string"}, "limit": {"type": "integer"}},
        steps=(
            WorkflowStep(
                id="work",
                kind=WorkflowStepKind.SKILL,
                uses="work@1.0.0",
                max_attempts=1,
            ),
        ),
    )
    domain, integration, execution = create_execution(workflow)
    ready = integration.decide(execution)
    assert isinstance(ready, StepReady)
    integration.apply_decision(execution, ready)
    domain.update_step_state(
        execution, step_id="work", target_status=StepRunStatus.RUNNING
    )

    decision = integration.evaluate_failure(
        execution,
        step_id="work",
        retryable=True,
        error_code="TIMEOUT",
    )
    assert isinstance(decision, WorkflowFailed)
    assert decision.retry_exhausted is True
    integration.apply_decision(execution, decision)
    assert execution.workflow_run.status is WorkflowRunStatus.FAILED


def test_approval_pause_and_approved_resume() -> None:
    workflow = Workflow(
        id="approval",
        version="1.0.0",
        name="Approval",
        input_schema={"topic": {"type": "string"}, "limit": {"type": "integer"}},
        steps=(
            WorkflowStep(
                id="approve",
                kind=WorkflowStepKind.APPROVAL,
                approval_policy="project_reviewer",
            ),
        ),
    )
    _, integration, execution = create_execution(workflow)

    waiting = integration.decide(execution)
    assert isinstance(waiting, WaitingApproval)
    approval_checkpoint = integration.apply_decision(execution, waiting)
    assert approval_checkpoint is not None
    assert execution.workflow_run.status is WorkflowRunStatus.WAITING_FOR_APPROVAL

    resolved = integration.resolve_approval(
        execution,
        approval_checkpoint,
        outcome=ApprovalOutcome.APPROVED,
    )
    assert isinstance(resolved, ApprovalCompleted)
    assert execution.latest_step_run("approve").status is StepRunStatus.COMPLETED

    completed = integration.decide(execution)
    assert isinstance(completed, WorkflowCompleted)
    integration.apply_decision(execution, completed)
    assert execution.workflow_run.status is WorkflowRunStatus.COMPLETED


def test_recovery_from_retry_checkpoint_returns_next_attempt_decision() -> None:
    workflow = Workflow(
        id="recovery",
        version="1.0.0",
        name="Recovery",
        input_schema={"topic": {"type": "string"}, "limit": {"type": "integer"}},
        steps=(
            WorkflowStep(
                id="work",
                kind=WorkflowStepKind.SKILL,
                uses="work@1.0.0",
                input_mapping={"topic": "${inputs.topic}"},
                max_attempts=2,
            ),
        ),
    )
    domain, integration, execution = create_execution(workflow)
    ready = integration.decide(execution)
    assert isinstance(ready, StepReady)
    integration.apply_decision(execution, ready)
    domain.update_step_state(
        execution, step_id="work", target_status=StepRunStatus.RUNNING
    )
    retry = integration.evaluate_failure(
        execution,
        step_id="work",
        retryable=True,
        error_code="TRANSIENT",
    )
    assert isinstance(retry, RetryScheduled)
    checkpoint = integration.apply_decision(execution, retry)
    assert checkpoint is not None

    recovered = integration.resume_from_checkpoint(execution, checkpoint)
    assert isinstance(recovered, StepReady)
    assert recovered.attempt == 2
    assert recovered.requires_ready_transition is False
    assert recovered.resolved_inputs["topic"] == "persistent agents"
    assert execution.workflow_run.status is WorkflowRunStatus.RUNNING
    assert execution.latest_step_run("work").attempt == 2


def test_retry_policy_backoff_is_deterministic_and_capped() -> None:
    policy = RetryPolicy(
        max_attempts=5,
        backoff="exponential",
        initial_seconds=2,
        max_seconds=5,
    )
    assert policy.delay_for_next_attempt(2) == 2.0
    assert policy.delay_for_next_attempt(3) == 4.0
    assert policy.delay_for_next_attempt(4) == 5.0


def test_engine_decision_does_not_mutate_domain_state() -> None:
    workflow = Workflow(
        id="pure-decision",
        version="1.0.0",
        name="Pure decision",
        input_schema={"topic": {"type": "string"}, "limit": {"type": "integer"}},
        steps=(
            WorkflowStep(id="work", kind=WorkflowStepKind.SKILL, uses="work@1.0.0"),
        ),
    )
    _, _, execution = create_execution(workflow)
    definition = WorkflowDefinition.from_domain(workflow)
    snapshot = ExecutionSnapshot.from_execution(execution)
    engine = WorkflowEngine()

    before_status = execution.latest_step_run("work").status
    decision = engine.next_decision(definition, snapshot)
    assert isinstance(decision, StepReady)
    assert execution.latest_step_run("work").status is before_status


def test_snapshot_missing_definition_step_returns_invariant_failure() -> None:
    workflow = Workflow(
        id="missing-state",
        version="1.0.0",
        name="Missing state",
        input_schema={"topic": {"type": "string"}, "limit": {"type": "integer"}},
        steps=(
            WorkflowStep(id="first", kind=WorkflowStepKind.SKILL, uses="first@1"),
            WorkflowStep(id="second", kind=WorkflowStepKind.SKILL, uses="second@1"),
        ),
    )
    _, _, execution = create_execution(workflow)
    incomplete_snapshot = ExecutionSnapshot(
        workflow_run_id=execution.workflow_run.id,
        workflow_id=workflow.id,
        workflow_version=workflow.version,
        run_status=execution.workflow_run.status,
        run_row_version=execution.workflow_run.row_version,
        workflow_inputs=execution.workflow_run.inputs,
        agent_session_id=execution.agent_session.id,
        agent_status=execution.agent_session.status,
        agent_row_version=execution.agent_session.row_version,
        step_runs=(
            ExecutionSnapshot.from_execution(execution).step_runs[0],
        ),
    )

    decision = WorkflowEngine().next_decision(
        WorkflowDefinition.from_domain(workflow), incomplete_snapshot
    )
    assert isinstance(decision, WorkflowFailed)
    assert decision.error_code == "INVALID_EXECUTION_STATE"
