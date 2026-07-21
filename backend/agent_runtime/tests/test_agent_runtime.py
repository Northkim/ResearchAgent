"""Deterministic end-to-end tests across Domain, Engine, Skills, and Runtime."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime

from backend.agent_runtime import AgentRuntime, CheckpointBoundary
from backend.domain.enums import (
    ApprovalRequestStatus,
    StepRunStatus,
    WorkflowRunStatus,
    WorkflowStepKind,
)
from backend.domain.models import Workflow, WorkflowStep
from backend.domain.services import ExecutionCoordinator
from backend.execution_events import ExecutionEventType
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.skill_system import (
    FieldSchema,
    SkillDefinition,
    SkillExecutionContext,
    SkillExecutionFailure,
    SkillExecutor,
    SkillMetadata,
    SkillRegistry,
    SkillSchema,
)
from backend.skill_system.runtime import register_fake_skills
from backend.workflow_engine.models import ApprovalOutcome
from backend.workflow_engine.services import WorkflowExecutionCoordinator


class SequentialIds:
    def __init__(self) -> None:
        self._counts: defaultdict[str, int] = defaultdict(int)

    def __call__(self, prefix: str) -> str:
        self._counts[prefix] += 1
        return f"{prefix}-{self._counts[prefix]}"


def _clock() -> datetime:
    return datetime(2026, 7, 20, 12, 0, tzinfo=UTC)


def _runtime(
    registry: SkillRegistry,
    *,
    database: InMemoryDatabase | None = None,
    ids: SequentialIds | None = None,
) -> tuple[AgentRuntime, ExecutionCoordinator, InMemoryDatabase]:
    database = database or InMemoryDatabase()
    ids = ids or SequentialIds()
    domain = ExecutionCoordinator(clock=_clock, id_factory=ids)
    integration = WorkflowExecutionCoordinator(domain_coordinator=domain)
    return (
        AgentRuntime(
            workflow_coordinator=integration,
            skill_executor=SkillExecutor(registry),
            unit_of_work=InMemoryUnitOfWork(database),
            clock=_clock,
            id_factory=ids,
        ),
        domain,
        database,
    )


def _execution(
    domain: ExecutionCoordinator,
    workflow: Workflow,
    inputs: dict[str, object],
):
    return domain.create_workflow_run(
        workflow=workflow,
        project_id="project-1",
        actor_user_id="user-1",
        idempotency_key=f"start:{workflow.id}",
        inputs=inputs,
        agent_profile_ref="deterministic-agent@1.0.0",
    )


def _linear_workflow() -> Workflow:
    return Workflow(
        id="mock-literature-review",
        version="1.0.0",
        name="Mock literature review",
        input_schema={"topic": {"type": "string"}},
        steps=(
            WorkflowStep(
                id="search",
                kind=WorkflowStepKind.SKILL,
                uses="mock_paper_search@1.0.0",
                input_mapping={"query": "${inputs.topic}"},
            ),
            WorkflowStep(
                id="summary",
                kind=WorkflowStepKind.SKILL,
                uses="mock_summary@1.0.0",
                needs=("search",),
                input_mapping={"papers": "${nodes.search.outputs.papers}"},
            ),
        ),
        outputs={"summary": "${nodes.summary.outputs.summary}"},
    )


def test_end_to_end_linear_workflow_completes() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    runtime, domain, _ = _runtime(registry)
    execution = _execution(
        domain,
        _linear_workflow(),
        {"topic": "persistent research agents"},
    )

    result = asyncio.run(runtime.run(execution))

    assert result.status is WorkflowRunStatus.COMPLETED
    assert result.completed_steps == ("search", "summary")
    assert result.outputs["summary"].startswith("Mock summary:")
    assert execution.latest_step_run("search").status is StepRunStatus.COMPLETED
    assert execution.latest_step_run("summary").status is StepRunStatus.COMPLETED
    boundaries = runtime.checkpoints.boundaries_for(execution.workflow_run.id)
    assert boundaries.count(CheckpointBoundary.BEFORE_SKILL) == 2
    assert boundaries.count(CheckpointBoundary.AFTER_SKILL) == 2
    assert CheckpointBoundary.BEFORE_TERMINAL in boundaries
    memory = runtime.memory.read_context("project-1", execution.workflow_run.id)
    assert tuple(memory["step_outputs"]) == ("search", "summary")


def test_skill_failure_is_applied_as_terminal_domain_failure() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    runtime, domain, _ = _runtime(registry)
    workflow = Workflow(
        id="empty-summary",
        version="1.0.0",
        name="Empty summary",
        input_schema={"papers": {"type": "array"}},
        steps=(
            WorkflowStep(
                id="summary",
                kind=WorkflowStepKind.SKILL,
                uses="mock_summary@1.0.0",
                input_mapping={"papers": "${inputs.papers}"},
            ),
        ),
    )
    execution = _execution(domain, workflow, {"papers": []})

    result = asyncio.run(runtime.run(execution))

    assert result.status is WorkflowRunStatus.FAILED
    assert result.error_code == "EMPTY_PAPERS"
    assert execution.latest_step_run("summary").status is StepRunStatus.FAILED
    boundaries = runtime.checkpoints.boundaries_for(execution.workflow_run.id)
    assert CheckpointBoundary.BEFORE_TERMINAL in boundaries
    assert CheckpointBoundary.AFTER_SKILL in boundaries
    assert boundaries.index(CheckpointBoundary.BEFORE_TERMINAL) < boundaries.index(
        CheckpointBoundary.TERMINAL
    )


def test_workflow_start_emits_durable_start_event() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    runtime, domain, _ = _runtime(registry)
    execution = _execution(domain, _linear_workflow(), {"topic": "events"})

    asyncio.run(runtime.run(execution))

    events = runtime.uow.events.list_for_run("project-1", execution.workflow_run.id)
    assert events[0].event_type is ExecutionEventType.WORKFLOW_STARTED
    assert events[0].payload.data["workflow_id"] == execution.workflow.id


def test_skill_execution_emits_one_event_per_skill_result() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    runtime, domain, _ = _runtime(registry)
    execution = _execution(domain, _linear_workflow(), {"topic": "events"})

    asyncio.run(runtime.run(execution))

    events = runtime.uow.events.list_for_run("project-1", execution.workflow_run.id)
    skill_events = [
        event
        for event in events
        if event.event_type is ExecutionEventType.SKILL_EXECUTED
    ]
    assert [event.payload.data["step_id"] for event in skill_events] == [
        "search",
        "summary",
    ]
    assert all(event.payload.data["success"] is True for event in skill_events)


def test_workflow_completion_emits_terminal_completion_event() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    runtime, domain, _ = _runtime(registry)
    execution = _execution(domain, _linear_workflow(), {"topic": "events"})

    asyncio.run(runtime.run(execution))

    events = runtime.uow.events.list_for_run("project-1", execution.workflow_run.id)
    assert events[-1].event_type is ExecutionEventType.WORKFLOW_COMPLETED
    assert events[-1].payload.data["status"] == "COMPLETED"


def test_workflow_failure_emits_terminal_failure_event() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    runtime, domain, _ = _runtime(registry)
    workflow = Workflow(
        id="event-failure",
        version="1.0.0",
        name="Event failure",
        input_schema={"papers": {"type": "array"}},
        steps=(
            WorkflowStep(
                id="summary",
                kind=WorkflowStepKind.SKILL,
                uses="mock_summary@1.0.0",
                input_mapping={"papers": "${inputs.papers}"},
            ),
        ),
    )
    execution = _execution(domain, workflow, {"papers": []})

    asyncio.run(runtime.run(execution))

    events = runtime.uow.events.list_for_run("project-1", execution.workflow_run.id)
    assert events[-1].event_type is ExecutionEventType.WORKFLOW_FAILED
    assert events[-1].payload.data["error_code"] == "EMPTY_PAPERS"


def test_retry_checkpoint_recovery_creates_a_new_attempt() -> None:
    registry = SkillRegistry()
    transient_definition = SkillDefinition(
        name="transient_mock",
        version="1.0.0",
        description="Fail once and then recover deterministically.",
        input_schema=SkillSchema(fields={}),
        output_schema=SkillSchema(
            fields={"value": FieldSchema(kind="string")},
        ),
        metadata=SkillMetadata(
            side_effect="none",
            retry_safe=True,
            implementation_entrypoint="test:transient_mock",
        ),
    )

    async def transient_mock(
        inputs: dict[str, object],
        context: SkillExecutionContext,
    ):
        del inputs
        if context.attempt == 1:
            raise SkillExecutionFailure(
                "TRANSIENT_MOCK_FAILURE",
                "first attempt fails",
                retryable=True,
            )
        return {"value": "recovered"}

    registry.register(transient_definition, transient_mock)
    ids = SequentialIds()
    runtime, domain, database = _runtime(registry, ids=ids)
    workflow = Workflow(
        id="retry-recovery",
        version="1.0.0",
        name="Retry recovery",
        steps=(
            WorkflowStep(
                id="work",
                kind=WorkflowStepKind.SKILL,
                uses="transient_mock@1.0.0",
                max_attempts=2,
            ),
        ),
        outputs={"value": "${nodes.work.outputs.value}"},
    )
    execution = _execution(domain, workflow, {})

    waiting = asyncio.run(runtime.run(execution))
    assert waiting.status is WorkflowRunStatus.RETRY_SCHEDULED
    retry_checkpoint_id = execution.latest_checkpoint.id

    restarted_runtime, _, _ = _runtime(registry, database=database, ids=ids)
    completed = asyncio.run(restarted_runtime.run(execution.workflow_run.id))
    restored = restarted_runtime.load_execution(execution.workflow_run.id)

    assert completed.status is WorkflowRunStatus.COMPLETED
    assert completed.outputs == {"value": "recovered"}
    assert len([step for step in restored.step_runs if step.step_id == "work"]) == 2
    assert restored.latest_step_run("work").attempt == 2
    assert retry_checkpoint_id != restored.latest_checkpoint.id
    assert CheckpointBoundary.RECOVERED in restarted_runtime.checkpoints.boundaries_for(
        execution.workflow_run.id
    )


def test_approval_pause_and_resume() -> None:
    registry = SkillRegistry()
    runtime, domain, _ = _runtime(registry)
    workflow = Workflow(
        id="approval-only",
        version="1.0.0",
        name="Approval only",
        steps=(
            WorkflowStep(
                id="approve",
                kind=WorkflowStepKind.APPROVAL,
                approval_policy="project_reviewer",
            ),
        ),
    )
    execution = _execution(domain, workflow, {})

    waiting = asyncio.run(runtime.run(execution))
    assert waiting.status is WorkflowRunStatus.WAITING_FOR_APPROVAL
    checkpoint_count = len(execution.checkpoints)
    pending = runtime.uow.approvals.list_pending_for_run(
        "project-1",
        execution.workflow_run.id,
    )
    assert len(pending) == 1
    assert pending[0].status is ApprovalRequestStatus.PENDING
    assert pending[0].step_run_id == execution.latest_step_run("approve").id
    event_types = tuple(
        event.event_type
        for event in runtime.uow.events.list_for_run(
            "project-1",
            execution.workflow_run.id,
        )
    )
    assert ExecutionEventType.APPROVAL_REQUESTED in event_types

    still_waiting = asyncio.run(runtime.run(execution))
    assert still_waiting.status is WorkflowRunStatus.WAITING_FOR_APPROVAL
    assert len(execution.checkpoints) == checkpoint_count

    completed = asyncio.run(
        runtime.run(execution, approval_outcome=ApprovalOutcome.APPROVED)
    )
    restored = runtime.load_execution(execution.workflow_run.id)
    assert completed.status is WorkflowRunStatus.COMPLETED
    assert restored.latest_step_run("approve").status is StepRunStatus.COMPLETED


def test_completed_resume_is_idempotent() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    runtime, domain, database = _runtime(registry)
    execution = _execution(domain, _linear_workflow(), {"topic": "memory"})
    first = asyncio.run(runtime.run(execution))
    checkpoint_count = len(execution.checkpoints)
    memory_revisions = len(runtime.memory.history("project-1", execution.workflow_run.id))

    restarted_runtime, _, _ = _runtime(registry, database=database)
    repeated = asyncio.run(restarted_runtime.run(execution.workflow_run.id))

    assert repeated == first
    assert len(execution.checkpoints) == checkpoint_count
    assert len(
        restarted_runtime.memory.history("project-1", execution.workflow_run.id)
    ) == memory_revisions


def test_rejected_approval_handles_cancelled_decision() -> None:
    registry = SkillRegistry()
    runtime, domain, _ = _runtime(registry)
    workflow = Workflow(
        id="approval-rejection",
        version="1.0.0",
        name="Approval rejection",
        steps=(
            WorkflowStep(
                id="approve",
                kind=WorkflowStepKind.APPROVAL,
                approval_policy="project_reviewer",
            ),
        ),
    )
    execution = _execution(domain, workflow, {})
    asyncio.run(runtime.run(execution))

    cancelled = asyncio.run(
        runtime.run(execution, approval_outcome=ApprovalOutcome.REJECTED)
    )

    assert cancelled.status is WorkflowRunStatus.CANCELLED
    boundaries = runtime.checkpoints.boundaries_for(execution.workflow_run.id)
    assert CheckpointBoundary.BEFORE_TERMINAL in boundaries
    assert CheckpointBoundary.TERMINAL in boundaries
