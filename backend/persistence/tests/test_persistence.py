"""Recovery, concurrency, idempotency, and transaction contract tests."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime

import pytest

from backend.agent_runtime import AgentRuntime
from backend.domain.enums import StepRunStatus, WorkflowRunStatus, WorkflowStepKind
from backend.domain.models import (
    ApprovalRequest,
    ArtifactMetadata,
    Workflow,
    WorkflowStep,
)
from backend.domain.services import ExecutionCoordinator
from backend.execution_events import EventPayload, ExecutionEvent, ExecutionEventType
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.persistence.models import CheckpointBoundary
from backend.persistence.ports import StaleStateError
from backend.skill_system import SkillExecutor, SkillRegistry
from backend.skill_system.runtime import register_fake_skills
from backend.workflow_engine.services import WorkflowExecutionCoordinator


class SequentialIds:
    def __init__(self) -> None:
        self._counts: defaultdict[str, int] = defaultdict(int)

    def __call__(self, prefix: str) -> str:
        self._counts[prefix] += 1
        return f"{prefix}-persistence-{self._counts[prefix]}"


def _clock() -> datetime:
    return datetime(2026, 7, 20, 16, 0, tzinfo=UTC)


def _workflow(*, max_attempts: int = 1) -> Workflow:
    return Workflow(
        id="persisted-search",
        version="1.0.0",
        name="Persisted search",
        input_schema={"topic": {"type": "string"}},
        steps=(
            WorkflowStep(
                id="search",
                kind=WorkflowStepKind.SKILL,
                uses="mock_paper_search@1.0.0",
                input_mapping={"query": "${inputs.topic}"},
                max_attempts=max_attempts,
            ),
        ),
        outputs={"papers": "${nodes.search.outputs.papers}"},
    )


def _execution(domain: ExecutionCoordinator, workflow: Workflow | None = None):
    return domain.create_workflow_run(
        workflow=workflow or _workflow(),
        project_id="project-persistence",
        actor_user_id="user-persistence",
        idempotency_key="request-persistence",
        inputs={"topic": "persistent runtimes"},
        agent_profile_ref="agent@1.0.0",
    )


def _save_all_checkpoints(uow: InMemoryUnitOfWork, execution) -> None:
    for checkpoint in execution.checkpoints:
        uow.checkpoints.save(
            checkpoint,
            boundary=CheckpointBoundary.DOMAIN_TRANSITION,
        )


def _runtime(
    database: InMemoryDatabase,
    ids: SequentialIds,
) -> AgentRuntime:
    registry = SkillRegistry()
    register_fake_skills(registry)
    domain = ExecutionCoordinator(clock=_clock, id_factory=ids)
    return AgentRuntime(
        workflow_coordinator=WorkflowExecutionCoordinator(
            domain_coordinator=domain
        ),
        skill_executor=SkillExecutor(registry),
        unit_of_work=InMemoryUnitOfWork(database),
    )


def test_save_and_restore_workflow_execution() -> None:
    database = InMemoryDatabase()
    ids = SequentialIds()
    domain = ExecutionCoordinator(clock=_clock, id_factory=ids)
    execution = _execution(domain)
    domain.start_execution(execution)
    domain.mark_step_ready(
        execution,
        step_id="search",
        inputs={"query": "persistent runtimes"},
    )

    writer = InMemoryUnitOfWork(database)
    version = writer.workflows.save(execution, expected_version=None)
    _save_all_checkpoints(writer, execution)
    writer.commit()

    reader = InMemoryUnitOfWork(database)
    restored = reader.workflows.get(execution.workflow_run.id)
    assert restored is not None
    restored.checkpoints.extend(reader.checkpoints.list(execution.workflow_run.id))

    assert version == 1
    assert reader.workflows.get_version(execution.workflow_run.id) == 1
    assert restored is not execution
    assert restored.workflow_run.status is WorkflowRunStatus.RUNNING
    assert restored.latest_step_run("search").status is StepRunStatus.READY
    assert restored.latest_checkpoint.id == execution.latest_checkpoint.id
    assert restored.latest_checkpoint.restore_state() == execution.latest_checkpoint.restore_state()


def test_checkpoint_recovery_after_simulated_restart() -> None:
    database = InMemoryDatabase()
    ids = SequentialIds()
    first_domain = ExecutionCoordinator(clock=_clock, id_factory=ids)
    execution = _execution(first_domain, _workflow(max_attempts=2))
    first_domain.start_execution(execution)
    first_domain.mark_step_ready(execution, step_id="search", inputs={"query": "x"})
    first_domain.update_step_state(
        execution,
        step_id="search",
        target_status=StepRunStatus.RUNNING,
    )
    retry_checkpoint = first_domain.update_step_state(
        execution,
        step_id="search",
        target_status=StepRunStatus.FAILED,
        error_code="TRANSIENT",
        retryable=True,
    )
    assert retry_checkpoint is not None

    writer = InMemoryUnitOfWork(database)
    writer.workflows.save(execution, expected_version=None)
    _save_all_checkpoints(writer, execution)
    writer.commit()

    restarted_uow = InMemoryUnitOfWork(database)
    restored = restarted_uow.workflows.get(execution.workflow_run.id)
    assert restored is not None
    restored.checkpoints.extend(restarted_uow.checkpoints.list(execution.workflow_run.id))
    recovered = ExecutionCoordinator(
        clock=_clock,
        id_factory=ids,
    ).resume_from_checkpoint(restored, restored.latest_checkpoint)

    assert recovered is not None
    assert recovered.attempt == 2
    assert recovered.status is StepRunStatus.READY
    assert restored.workflow_run.status is WorkflowRunStatus.RUNNING


def test_runtime_resume_is_idempotent_after_adapter_restart() -> None:
    database = InMemoryDatabase()
    ids = SequentialIds()
    first_runtime = _runtime(database, ids)
    execution = _execution(first_runtime.workflow.domain)
    first = asyncio.run(first_runtime.run(execution))
    first_version = first_runtime.uow.workflows.get_version(execution.workflow_run.id)
    checkpoint_count = len(first_runtime.checkpoints.list(execution.workflow_run.id))
    memory_count = len(
        first_runtime.memory.history("project-persistence", execution.workflow_run.id)
    )

    restarted_runtime = _runtime(database, ids)
    repeated = asyncio.run(restarted_runtime.run(execution.workflow_run.id))

    assert repeated == first
    assert restarted_runtime.uow.workflows.get_version(execution.workflow_run.id) == first_version
    assert len(restarted_runtime.checkpoints.list(execution.workflow_run.id)) == checkpoint_count
    assert len(
        restarted_runtime.memory.history(
            "project-persistence",
            execution.workflow_run.id,
        )
    ) == memory_count


def test_optimistic_concurrency_rejects_stale_unit_of_work() -> None:
    database = InMemoryDatabase()
    ids = SequentialIds()
    domain = ExecutionCoordinator(clock=_clock, id_factory=ids)
    execution = _execution(domain)
    initial = InMemoryUnitOfWork(database)
    initial.workflows.save(execution, expected_version=None)
    _save_all_checkpoints(initial, execution)
    initial.commit()

    first = InMemoryUnitOfWork(database)
    second = InMemoryUnitOfWork(database)
    first_execution = first.workflows.get(execution.workflow_run.id)
    second_execution = second.workflows.get(execution.workflow_run.id)
    assert first_execution is not None and second_execution is not None
    first_execution.checkpoints.extend(first.checkpoints.list(execution.workflow_run.id))
    second_execution.checkpoints.extend(second.checkpoints.list(execution.workflow_run.id))
    first_domain = ExecutionCoordinator(clock=_clock, id_factory=ids)
    second_domain = ExecutionCoordinator(clock=_clock, id_factory=ids)
    first_domain.start_execution(first_execution)
    second_domain.start_execution(second_execution)

    first.workflows.update_state(first_execution, expected_version=1)
    _save_all_checkpoints(first, first_execution)
    first.commit()

    second.workflows.update_state(second_execution, expected_version=1)
    _save_all_checkpoints(second, second_execution)
    with pytest.raises(StaleStateError):
        second.commit()

    second.rollback()
    assert second.workflows.get_version(execution.workflow_run.id) == 2


def test_unit_of_work_rollback_discards_all_repository_changes() -> None:
    database = InMemoryDatabase()
    ids = SequentialIds()
    domain = ExecutionCoordinator(clock=_clock, id_factory=ids)
    execution = _execution(domain)
    artifact = ArtifactMetadata(
        id="artifact-1",
        project_id="project-persistence",
        logical_artifact_id="report",
        logical_name="report.md",
        version=1,
        kind="report",
        storage_ref="memory://report-1",
        checksum="sha256:test",
        media_type="text/markdown",
        size=12,
        producer_run_id=execution.workflow_run.id,
        created_at=_clock(),
    )
    approval = ApprovalRequest(
        id="approval-rollback",
        project_id="project-persistence",
        workflow_run_id=execution.workflow_run.id,
        step_run_id="step-run-rollback",
        policy_key="project_reviewer",
        request_fingerprint="sha256:rollback",
        prompt="Approve this rollback test action?",
        requested_action={"capability": "test"},
        requested_by="test",
        permitted_approver_role="reviewer",
        requested_at=_clock(),
    )
    event = ExecutionEvent(
        id="event-rollback",
        project_id="project-persistence",
        workflow_run_id=execution.workflow_run.id,
        sequence=1,
        event_type=ExecutionEventType.APPROVAL_REQUESTED,
        payload=EventPayload(data={"approval_request_id": approval.id}),
        request_id="request-rollback",
        occurred_at=_clock(),
    )

    uow = InMemoryUnitOfWork(database)
    uow.workflows.save(execution, expected_version=None)
    _save_all_checkpoints(uow, execution)
    uow.memory.initialize_context(
        project_id="project-persistence",
        workflow_run_id=execution.workflow_run.id,
        context={"goal": "rollback"},
        producer="test",
    )
    uow.artifacts.save(artifact)
    uow.approvals.save(approval, expected_version=None)
    uow.events.append(event, expected_sequence=0)
    uow.rollback()

    observer = InMemoryUnitOfWork(database)
    assert observer.workflows.get(execution.workflow_run.id) is None
    assert observer.checkpoints.list(execution.workflow_run.id) == ()
    assert observer.memory.history("project-persistence", execution.workflow_run.id) == ()
    assert observer.artifacts.get(artifact.id) is None
    assert observer.approvals.get(approval.id) is None
    assert observer.events.list_for_run(
        event.project_id,
        event.workflow_run_id,
    ) == ()
