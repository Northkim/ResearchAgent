"""Runtime-owned context assembled for one deterministic step attempt."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from backend.agent_runtime._immutability import freeze_json
from backend.domain.services import ExecutionState
from backend.persistence.ports import MemoryRepository
from backend.workflow_engine.models import StepReady


@dataclass(frozen=True, slots=True, kw_only=True)
class AgentExecutionContext:
    """Bounded runtime context; never includes developer `.agent_read` memory."""

    project_id: str
    workflow_run_id: str
    agent_session_id: str
    workflow_id: str
    workflow_version: str
    step_id: str
    step_run_id: str
    attempt: int
    workflow_inputs: Mapping[str, Any]
    resolved_inputs: Mapping[str, Any]
    working_memory: Mapping[str, Any]
    memory_revision: int
    checkpoint_id: str
    source_references: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "workflow_inputs",
            freeze_json(self.workflow_inputs, path="workflow_inputs"),
        )
        object.__setattr__(
            self,
            "resolved_inputs",
            freeze_json(self.resolved_inputs, path="resolved_inputs"),
        )
        object.__setattr__(
            self,
            "working_memory",
            freeze_json(self.working_memory, path="working_memory"),
        )
        object.__setattr__(self, "source_references", tuple(self.source_references))


class ExecutionContextBuilder:
    """Build a project/run-scoped context from committed in-memory state."""

    def build(
        self,
        execution: ExecutionState,
        decision: StepReady,
        memory_store: MemoryRepository,
    ) -> AgentExecutionContext:
        checkpoint = execution.latest_checkpoint
        checkpoint.verify_integrity()
        if decision.workflow_run_id != execution.workflow_run.id:
            raise ValueError("StepReady belongs to another WorkflowRun")
        if decision.step_run_id != execution.latest_step_run(decision.step_id).id:
            raise ValueError("StepReady belongs to a stale StepRun attempt")

        memory_revision = memory_store.latest_revision_number(
            execution.workflow_run.project_id,
            execution.workflow_run.id,
        )
        return AgentExecutionContext(
            project_id=execution.workflow_run.project_id,
            workflow_run_id=execution.workflow_run.id,
            agent_session_id=execution.agent_session.id,
            workflow_id=execution.workflow.id,
            workflow_version=execution.workflow.version,
            step_id=decision.step_id,
            step_run_id=decision.step_run_id,
            attempt=decision.attempt,
            workflow_inputs=execution.workflow_run.inputs,
            resolved_inputs=decision.resolved_inputs,
            working_memory=memory_store.read_context(
                execution.workflow_run.project_id,
                execution.workflow_run.id,
            ),
            memory_revision=memory_revision,
            checkpoint_id=checkpoint.id,
            source_references=(
                f"workflow:{execution.workflow.id}@{execution.workflow.version}",
                f"checkpoint:{checkpoint.id}",
                f"step_run:{decision.step_run_id}",
            ),
        )
