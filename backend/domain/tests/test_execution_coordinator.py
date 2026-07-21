"""End-to-end domain lifecycle tests with no infrastructure dependencies."""

from __future__ import annotations

import unittest
from dataclasses import replace

from backend.domain.enums import (
    AgentSessionStatus,
    StepRunStatus,
    WorkflowRunStatus,
    WorkflowStepKind,
)
from backend.domain.exceptions import CheckpointIntegrityError, InvalidStateTransition
from backend.domain.models import Workflow, WorkflowStep
from backend.domain.services import ExecutionCoordinator, ExecutionState


def make_research_workflow(*, max_attempts: int = 1) -> Workflow:
    return Workflow(
        id="literature-search",
        version="1.0.0",
        name="Literature search",
        input_schema={"topic": {"type": "string"}},
        steps=(
            WorkflowStep(
                id="search",
                kind=WorkflowStepKind.SKILL,
                uses="paper-search@1.0.0",
                max_attempts=max_attempts,
            ),
            WorkflowStep(
                id="synthesize",
                kind=WorkflowStepKind.SKILL,
                uses="literature-synthesis@1.0.0",
                needs=("search",),
            ),
        ),
        outputs={"report": "${nodes.synthesize.outputs.report}"},
    )


def make_execution(
    coordinator: ExecutionCoordinator, workflow: Workflow
) -> ExecutionState:
    return coordinator.create_workflow_run(
        workflow=workflow,
        project_id="project-1",
        actor_user_id="user-1",
        idempotency_key="request-1",
        inputs={"topic": "persistent research agents"},
        agent_profile_ref="research-agent@1.0.0",
    )


class ExecutionCoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.coordinator = ExecutionCoordinator()

    def test_normal_workflow_lifecycle(self) -> None:
        execution = make_execution(self.coordinator, make_research_workflow())

        self.assertEqual(execution.workflow_run.status, WorkflowRunStatus.CREATED)
        self.coordinator.start_execution(execution)
        self.assertEqual(execution.workflow_run.status, WorkflowRunStatus.RUNNING)
        self.assertEqual(
            execution.latest_step_run("search").status, StepRunStatus.CREATED
        )
        self.coordinator.mark_step_ready(
            execution, step_id="search", inputs={"query": "persistent research agents"}
        )
        self.assertEqual(execution.latest_step_run("search").status, StepRunStatus.READY)

        self.coordinator.update_step_state(
            execution, step_id="search", target_status=StepRunStatus.RUNNING
        )
        self.coordinator.update_step_state(
            execution,
            step_id="search",
            target_status=StepRunStatus.COMPLETED,
            outputs={"papers": ["paper-1"]},
        )
        self.assertEqual(
            execution.latest_step_run("synthesize").status, StepRunStatus.CREATED
        )
        self.coordinator.mark_step_ready(
            execution, step_id="synthesize", inputs={"papers": ["paper-1"]}
        )

        self.coordinator.update_step_state(
            execution, step_id="synthesize", target_status=StepRunStatus.RUNNING
        )
        self.coordinator.update_step_state(
            execution,
            step_id="synthesize",
            target_status=StepRunStatus.COMPLETED,
            outputs={"report": "artifact-1"},
        )
        self.coordinator.complete_workflow(
            execution, outputs={"report": "artifact-1"}
        )

        self.assertEqual(execution.workflow_run.status, WorkflowRunStatus.COMPLETED)
        self.assertEqual(
            execution.agent_session.status, AgentSessionStatus.COMPLETED
        )
        self.assertEqual(execution.workflow_run.outputs, {"report": "artifact-1"})

    def test_invalid_state_transition_raises_domain_exception(self) -> None:
        execution = make_execution(self.coordinator, make_research_workflow())

        with self.assertRaises(InvalidStateTransition):
            execution.workflow_run.transition_to(WorkflowRunStatus.COMPLETED)

        with self.assertRaises(InvalidStateTransition):
            execution.agent_session.transition_to(AgentSessionStatus.COMPLETED)

        with self.assertRaises(InvalidStateTransition):
            execution.latest_step_run("search").transition_to(
                StepRunStatus.COMPLETED
            )

        with self.assertRaises(InvalidStateTransition):
            self.coordinator.update_step_state(
                execution,
                step_id="search",
                target_status=StepRunStatus.COMPLETED,
            )

    def test_retryable_failure_recovers_as_new_attempt(self) -> None:
        execution = make_execution(
            self.coordinator, make_research_workflow(max_attempts=2)
        )
        self.coordinator.start_execution(execution)
        self.coordinator.mark_step_ready(execution, step_id="search")
        self.coordinator.update_step_state(
            execution, step_id="search", target_status=StepRunStatus.RUNNING
        )
        retry_checkpoint = self.coordinator.update_step_state(
            execution,
            step_id="search",
            target_status=StepRunStatus.FAILED,
            error_code="TRANSIENT_PROVIDER_ERROR",
            retryable=True,
        )

        self.assertIsNotNone(retry_checkpoint)
        self.assertEqual(
            execution.workflow_run.status, WorkflowRunStatus.RETRY_SCHEDULED
        )
        retry_attempt = self.coordinator.resume_from_checkpoint(
            execution, retry_checkpoint  # type: ignore[arg-type]
        )

        self.assertIsNotNone(retry_attempt)
        self.assertEqual(retry_attempt.attempt, 2)  # type: ignore[union-attr]
        self.assertEqual(retry_attempt.status, StepRunStatus.READY)  # type: ignore[union-attr]
        self.assertEqual(execution.workflow_run.status, WorkflowRunStatus.RUNNING)
        self.assertEqual(len(execution.step_runs), 3)

        self.coordinator.update_step_state(
            execution, step_id="search", target_status=StepRunStatus.RUNNING
        )
        self.coordinator.update_step_state(
            execution,
            step_id="search",
            target_status=StepRunStatus.COMPLETED,
            outputs={"papers": ["paper-1"]},
        )
        self.coordinator.mark_step_ready(execution, step_id="synthesize")
        self.coordinator.update_step_state(
            execution, step_id="synthesize", target_status=StepRunStatus.RUNNING
        )
        self.coordinator.update_step_state(
            execution,
            step_id="synthesize",
            target_status=StepRunStatus.COMPLETED,
            outputs={"report": "artifact-1"},
        )
        self.coordinator.complete_workflow(
            execution, outputs={"report": "artifact-1"}
        )
        self.assertEqual(execution.workflow_run.status, WorkflowRunStatus.COMPLETED)

    def test_approval_pause_and_resume(self) -> None:
        workflow = Workflow(
            id="review",
            version="1.0.0",
            name="Review gate",
            input_schema={"topic": {"type": "string"}},
            steps=(
                WorkflowStep(
                    id="approve",
                    kind=WorkflowStepKind.APPROVAL,
                    approval_policy="project_reviewer",
                ),
            ),
        )
        execution = make_execution(self.coordinator, workflow)
        self.coordinator.start_execution(execution)
        self.coordinator.mark_step_ready(execution, step_id="approve")
        self.coordinator.update_step_state(
            execution, step_id="approve", target_status=StepRunStatus.RUNNING
        )
        approval_checkpoint = self.coordinator.update_step_state(
            execution,
            step_id="approve",
            target_status=StepRunStatus.WAITING_APPROVAL,
        )

        self.assertEqual(
            execution.workflow_run.status, WorkflowRunStatus.WAITING_APPROVAL
        )
        self.assertEqual(execution.agent_session.status, AgentSessionStatus.WAITING)
        resumed_step = self.coordinator.resume_from_checkpoint(
            execution, approval_checkpoint  # type: ignore[arg-type]
        )
        self.assertEqual(resumed_step.status, StepRunStatus.RUNNING)  # type: ignore[union-attr]
        self.assertEqual(execution.workflow_run.status, WorkflowRunStatus.RUNNING)

        self.coordinator.update_step_state(
            execution, step_id="approve", target_status=StepRunStatus.COMPLETED
        )
        self.coordinator.complete_workflow(execution, outputs={})
        self.assertEqual(execution.workflow_run.status, WorkflowRunStatus.COMPLETED)

    def test_checkpoint_creation_is_ordered_and_integrity_protected(self) -> None:
        execution = make_execution(self.coordinator, make_research_workflow())
        initial_checkpoint = execution.latest_checkpoint
        started_checkpoint = self.coordinator.start_execution(execution)
        explicit_checkpoint = self.coordinator.create_checkpoint(execution)

        self.assertEqual(initial_checkpoint.sequence, 1)
        self.assertEqual(started_checkpoint.sequence, 2)
        self.assertEqual(explicit_checkpoint.sequence, 3)
        self.assertEqual(explicit_checkpoint.parent_id, started_checkpoint.id)
        explicit_checkpoint.verify_integrity()
        restored = explicit_checkpoint.restore_state()
        self.assertEqual(restored["workflow_run"]["status"], "RUNNING")
        self.assertEqual(restored["workflow"]["version"], "1.0.0")

        tampered_checkpoint = replace(explicit_checkpoint, state_hash="0" * 64)
        with self.assertRaises(CheckpointIntegrityError):
            tampered_checkpoint.verify_integrity()


if __name__ == "__main__":
    unittest.main()
