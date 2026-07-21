"""Deterministic, single-active-node v1 scheduler."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.enums import StepRunStatus

from ..exceptions import WorkflowStateError
from ..models import (
    ExecutionSnapshot,
    StepDefinition,
    StepRunSnapshot,
    WorkflowDefinition,
)


@dataclass(frozen=True, slots=True)
class ScheduledNode:
    definition: StepDefinition
    step_run: StepRunSnapshot
    requires_ready_transition: bool


class DeterministicScheduler:
    """Select one eligible node by definition order and stable ID."""

    SUCCESS_STATES = frozenset({StepRunStatus.COMPLETED, StepRunStatus.SKIPPED})
    ACTIVE_STATES = frozenset(
        {StepRunStatus.RUNNING, StepRunStatus.WAITING_APPROVAL}
    )

    def select(
        self,
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
    ) -> ScheduledNode | None:
        latest = self._latest_for_definition(definition, snapshot)
        active = [
            step_run
            for step_run in latest.values()
            if step_run.status in self.ACTIVE_STATES
        ]
        if len(active) > 1:
            raise WorkflowStateError("V1 permits at most one active workflow step")
        if active:
            return None

        candidates: list[tuple[int, str, StepDefinition, StepRunSnapshot, bool]] = []
        for index, step in enumerate(definition.steps):
            step_run = latest[step.id]
            dependencies_complete = all(
                latest[dependency].status in self.SUCCESS_STATES
                for dependency in step.needs
            )
            if step_run.status is StepRunStatus.READY:
                if not dependencies_complete:
                    raise WorkflowStateError(
                        f"Step {step.id} is READY before its dependencies completed"
                    )
                candidates.append((index, step.id, step, step_run, False))
            elif step_run.status is StepRunStatus.CREATED and dependencies_complete:
                candidates.append((index, step.id, step, step_run, True))

        if not candidates:
            return None
        _, _, step, step_run, requires_ready = min(
            candidates, key=lambda candidate: (candidate[0], candidate[1])
        )
        return ScheduledNode(step, step_run, requires_ready)

    def all_successful(
        self,
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
    ) -> bool:
        return all(
            step_run.status in self.SUCCESS_STATES
            for step_run in self._latest_for_definition(
                definition, snapshot
            ).values()
        )

    def has_active_step(
        self,
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
    ) -> bool:
        active = [
            step_run
            for step_run in self._latest_for_definition(
                definition, snapshot
            ).values()
            if step_run.status in self.ACTIVE_STATES
        ]
        if len(active) > 1:
            raise WorkflowStateError("V1 permits at most one active workflow step")
        return bool(active)

    @staticmethod
    def _latest_for_definition(
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
    ) -> dict[str, StepRunSnapshot]:
        latest = dict(snapshot.latest_attempts())
        definition_ids = {step.id for step in definition.steps}
        state_ids = set(latest)
        if definition_ids != state_ids:
            missing = definition_ids - state_ids
            unknown = state_ids - definition_ids
            raise WorkflowStateError(
                "Execution step state does not match definition; "
                f"missing={sorted(missing)}, unknown={sorted(unknown)}"
            )
        return latest
