"""Reusable adapter contract scenarios shared by in-memory and PostgreSQL tests."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from backend.domain.enums import ApprovalRequestStatus, WorkflowRunStatus, WorkflowStepKind
from backend.domain.models import (
    ApprovalRequest,
    ArtifactMetadata,
    Workflow,
    WorkflowStep,
)
from backend.domain.services import ExecutionCoordinator
from backend.execution_events import EventPayload, ExecutionEvent, ExecutionEventType
from backend.persistence.models import CheckpointBoundary
from backend.persistence.ports import StaleStateError, UnitOfWork


class ContractIds:
    def __init__(self, namespace: str) -> None:
        self.namespace = namespace
        self.counts: defaultdict[str, int] = defaultdict(int)

    def __call__(self, prefix: str) -> str:
        self.counts[prefix] += 1
        return f"{prefix}-{self.namespace}-{self.counts[prefix]}"


def contract_clock() -> datetime:
    return datetime(2026, 7, 21, 14, 0, tzinfo=UTC)


def contract_workflow() -> Workflow:
    return Workflow(
        id="adapter-contract-workflow",
        version="1.0.0",
        name="Adapter contract workflow",
        input_schema={"topic": {"type": "string"}},
        steps=(
            WorkflowStep(
                id="search",
                kind=WorkflowStepKind.SKILL,
                uses="mock_paper_search@1.0.0",
                input_mapping={"query": "${inputs.topic}"},
                max_attempts=2,
            ),
        ),
        outputs={"papers": "${nodes.search.outputs.papers}"},
    )


def contract_execution(namespace: str = "contract"):
    ids = ContractIds(namespace)
    coordinator = ExecutionCoordinator(clock=contract_clock, id_factory=ids)
    execution = coordinator.create_workflow_run(
        workflow=contract_workflow(),
        project_id=f"project-{namespace}",
        actor_user_id=f"user-{namespace}",
        idempotency_key=f"request-{namespace}",
        inputs={"topic": "persistent research agents"},
        agent_profile_ref="agent@1.0.0",
    )
    coordinator.start_execution(execution)
    coordinator.mark_step_ready(
        execution,
        step_id="search",
        inputs={"query": "persistent research agents"},
    )
    return execution, coordinator, ids


def save_contract_checkpoints(unit_of_work: UnitOfWork, execution) -> None:
    for checkpoint in execution.checkpoints:
        unit_of_work.checkpoints.save(
            checkpoint,
            boundary=CheckpointBoundary.DOMAIN_TRANSITION,
        )


def exercise_full_repository_round_trip(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    execution, _, _ = contract_execution("round-trip")
    step_run = execution.latest_step_run("search")
    approval = ApprovalRequest(
        id="approval-round-trip",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        step_run_id=step_run.id,
        policy_key="project_reviewer",
        request_fingerprint="sha256:round-trip",
        prompt="Approve the selected sources?",
        requested_action={"capability": "review_sources"},
        requested_by=execution.agent_session.id,
        permitted_approver_role="reviewer",
        requested_at=contract_clock(),
        expires_at=contract_clock() + timedelta(hours=1),
    )
    artifact = ArtifactMetadata(
        id="artifact-round-trip",
        project_id=execution.workflow_run.project_id,
        logical_artifact_id="sources",
        logical_name="sources.json",
        version=1,
        kind="dataset",
        storage_ref="object://sources/1",
        checksum="sha256:round-trip",
        media_type="application/json",
        size=128,
        producer_run_id=execution.workflow_run.id,
        producer_step_run_id=step_run.id,
        metadata={"verified": False},
        created_at=contract_clock(),
    )
    event = ExecutionEvent(
        id="event-round-trip",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        sequence=1,
        event_type=ExecutionEventType.WORKFLOW_STARTED,
        payload=EventPayload(data={"status": "RUNNING"}),
        request_id="request-round-trip",
        occurred_at=contract_clock(),
        agent_session_id=execution.agent_session.id,
    )

    writer = make_unit_of_work()
    assert writer.workflows.save(execution, expected_version=None) == 1
    save_contract_checkpoints(writer, execution)
    writer.memory.initialize_context(
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        context={"goal": "round trip"},
        producer="contract-test",
        source_references=("input:topic",),
    )
    writer.artifacts.save(artifact)
    assert writer.approvals.save(approval, expected_version=None) == 1
    writer.events.append(event, expected_sequence=0)
    writer.commit()
    _close(writer)

    reader = make_unit_of_work()
    restored = reader.workflows.get(execution.workflow_run.id)
    assert restored is not None
    restored.checkpoints.extend(reader.checkpoints.list(execution.workflow_run.id))
    assert restored.workflow_run.status is WorkflowRunStatus.RUNNING
    assert restored.workflow == execution.workflow
    assert restored.latest_step_run("search").id == step_run.id
    assert restored.latest_checkpoint.restore_state() == execution.latest_checkpoint.restore_state()
    assert reader.memory.read_context(
        execution.workflow_run.project_id,
        execution.workflow_run.id,
    )["goal"] == "round trip"
    assert reader.artifacts.get(artifact.id) == artifact
    recovered_approval = reader.approvals.get(approval.id)
    assert recovered_approval is not None
    assert recovered_approval.status is ApprovalRequestStatus.PENDING
    assert reader.events.replay(
        execution.workflow_run.project_id,
        execution.workflow_run.id,
    ) == (event,)
    _close(reader)


def exercise_transaction_rollback(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    execution, _, _ = contract_execution("rollback")
    uow = make_unit_of_work()
    uow.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(uow, execution)
    uow.memory.initialize_context(
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        context={"goal": "must disappear"},
        producer="contract-test",
    )
    uow.rollback()
    _close(uow)

    observer = make_unit_of_work()
    assert observer.workflows.get(execution.workflow_run.id) is None
    assert observer.checkpoints.list(execution.workflow_run.id) == ()
    assert observer.memory.history(
        execution.workflow_run.project_id,
        execution.workflow_run.id,
    ) == ()
    _close(observer)


def exercise_event_and_approval_recovery(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    execution, _, _ = contract_execution("approval-recovery")
    step_run = execution.latest_step_run("search")
    baseline = make_unit_of_work()
    baseline.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(baseline, execution)
    baseline.commit()
    _close(baseline)

    approval = ApprovalRequest(
        id="approval-recovery",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        step_run_id=step_run.id,
        policy_key="project_reviewer",
        request_fingerprint="sha256:approval-recovery",
        prompt="Approve recovery?",
        requested_action={"capability": "resume"},
        requested_by=execution.agent_session.id,
        permitted_approver_role="reviewer",
        requested_at=contract_clock(),
        expires_at=contract_clock() + timedelta(hours=1),
    )
    first_event = ExecutionEvent(
        id="event-approval-recovery-1",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        sequence=1,
        event_type=ExecutionEventType.APPROVAL_REQUESTED,
        payload=EventPayload(data={"approval_request_id": approval.id}),
        request_id="request-approval-recovery",
        occurred_at=contract_clock(),
        agent_session_id=execution.agent_session.id,
        step_run_id=step_run.id,
    )
    second_event = ExecutionEvent(
        id="event-approval-recovery-2",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        sequence=2,
        event_type=ExecutionEventType.CHECKPOINT_CREATED,
        payload=EventPayload(data={"checkpoint_id": execution.latest_checkpoint.id}),
        request_id="request-approval-recovery",
        occurred_at=contract_clock(),
        agent_session_id=execution.agent_session.id,
        causation_id=first_event.id,
    )

    writer = make_unit_of_work()
    writer.approvals.save(approval, expected_version=None)
    writer.events.append(first_event, expected_sequence=0)
    writer.events.append(second_event, expected_sequence=1)
    writer.commit()
    _close(writer)

    restarted = make_unit_of_work()
    pending = restarted.approvals.list_pending_for_run(
        approval.project_id,
        approval.workflow_run_id,
    )
    assert len(pending) == 1
    recovered = pending[0]
    assert restarted.events.replay(
        approval.project_id,
        approval.workflow_run_id,
        after_sequence=1,
    ) == (second_event,)
    recovered.approve(
        resolved_by="reviewer-1",
        decision_idempotency_key="decision-recovery",
        current_fingerprint=recovered.request_fingerprint,
        at=contract_clock() + timedelta(minutes=30),
        reason="Recovered and approved",
    )
    restarted.approvals.save(recovered, expected_version=1)
    restarted.commit()
    _close(restarted)

    observer = make_unit_of_work()
    resolved = observer.approvals.get(approval.id)
    assert resolved is not None
    assert resolved.status is ApprovalRequestStatus.APPROVED
    assert observer.approvals.get_version(approval.id) == 2
    assert observer.events.latest_sequence(
        approval.project_id,
        approval.workflow_run_id,
    ) == 2
    _close(observer)


def exercise_optimistic_concurrency(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    execution, _, _ = contract_execution("concurrency")
    initial = make_unit_of_work()
    initial.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(initial, execution)
    initial.commit()
    _close(initial)

    first = make_unit_of_work()
    second = make_unit_of_work()
    first_execution = first.workflows.get(execution.workflow_run.id)
    second_execution = second.workflows.get(execution.workflow_run.id)
    assert first_execution is not None and second_execution is not None
    first_execution.workflow_run.set_outputs({"writer": "first"})
    second_execution.workflow_run.set_outputs({"writer": "second"})
    first.workflows.update_state(first_execution, expected_version=1)
    second.workflows.update_state(second_execution, expected_version=1)

    first.commit()
    with pytest.raises(StaleStateError):
        second.commit()
    _close(first)
    _close(second)

    observer = make_unit_of_work()
    restored = observer.workflows.get(execution.workflow_run.id)
    assert restored is not None
    assert restored.workflow_run.outputs == {"writer": "first"}
    assert observer.workflows.get_version(execution.workflow_run.id) == 2
    _close(observer)


def _close(unit_of_work: UnitOfWork) -> None:
    close = getattr(unit_of_work, "close", None)
    if callable(close):
        close()
