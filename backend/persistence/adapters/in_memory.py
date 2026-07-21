"""Transactional deterministic in-memory implementations of all repositories."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from backend.domain.enums import ApprovalRequestStatus, WorkflowRunStatus
from backend.domain.models import ApprovalRequest, ArtifactMetadata, Checkpoint, Workflow
from backend.domain.services import ExecutionState
from backend.execution_events import ExecutionEvent, ExecutionEventStore
from backend.persistence.models import (
    ApprovalRecord,
    CheckpointBoundary,
    CheckpointRecord,
    MemoryRevision,
    WorkflowExecutionRecord,
)
from backend.persistence.models._immutability import freeze_json, thaw_json
from backend.persistence.ports import (
    ApprovalRepository,
    ArtifactRepository,
    CheckpointRepository,
    DuplicateEntityError,
    MemoryRepository,
    StaleStateError,
    UnitOfWork,
    WorkflowRepository,
)


@dataclass(slots=True)
class InMemoryDatabase:
    """Shared committed state used to simulate a database across UoW instances."""

    executions: dict[str, WorkflowExecutionRecord] = field(default_factory=dict)
    checkpoint_records: dict[str, tuple[CheckpointRecord, ...]] = field(
        default_factory=dict
    )
    memory_revisions: dict[tuple[str, str], tuple[MemoryRevision, ...]] = field(
        default_factory=dict
    )
    artifacts: dict[str, ArtifactMetadata] = field(default_factory=dict)
    approvals: dict[str, ApprovalRecord] = field(default_factory=dict)
    execution_events: dict[
        tuple[str, str], tuple[ExecutionEvent, ...]
    ] = field(default_factory=dict)


class InMemoryWorkflowRepository(WorkflowRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def save(
        self,
        execution: ExecutionState,
        *,
        expected_version: int | None,
    ) -> int:
        run_id = execution.workflow_run.id
        current = self._uow._executions.get(run_id)
        if expected_version is None:
            if current is not None:
                raise StaleStateError(
                    f"WorkflowRun {run_id} already exists at persistence version "
                    f"{current.persistence_version}"
                )
            conflicting_run = next(
                (
                    record.workflow_run.id
                    for record in self._uow._executions.values()
                    if record.workflow_run.project_id
                    == execution.workflow_run.project_id
                    and record.workflow_run.idempotency_key
                    == execution.workflow_run.idempotency_key
                    and record.workflow_run.id != run_id
                ),
                None,
            )
            if conflicting_run is not None:
                raise DuplicateEntityError(
                    "Workflow execution idempotency key is already owned by "
                    f"WorkflowRun {conflicting_run}"
                )
            next_version = 1
        else:
            if current is None:
                raise StaleStateError(f"WorkflowRun {run_id} does not exist")
            if current.persistence_version != expected_version:
                raise StaleStateError(
                    f"WorkflowRun {run_id} expected persistence version "
                    f"{expected_version}; found {current.persistence_version}"
                )
            next_version = expected_version + 1

        self._uow._workflow_expected.setdefault(run_id, expected_version)
        self._uow._executions[run_id] = WorkflowExecutionRecord.from_execution(
            execution,
            persistence_version=next_version,
        )
        self._uow._dirty_workflows.add(run_id)
        return next_version

    def get(self, workflow_run_id: str) -> ExecutionState | None:
        record = self._uow._executions.get(workflow_run_id)
        return record.to_execution() if record is not None else None

    def get_version(self, workflow_run_id: str) -> int | None:
        record = self._uow._executions.get(workflow_run_id)
        return record.persistence_version if record is not None else None

    def get_by_idempotency_key(
        self,
        project_id: str,
        idempotency_key: str,
    ) -> ExecutionState | None:
        matches = [
            record
            for record in self._uow._executions.values()
            if record.workflow_run.project_id == project_id
            and record.workflow_run.idempotency_key == idempotency_key
        ]
        if not matches:
            return None
        record = min(matches, key=lambda item: item.workflow_run.id)
        return record.to_execution()

    def list_runs(
        self,
        *,
        status: WorkflowRunStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[ExecutionState, ...]:
        records = [
            record
            for record in self._uow._executions.values()
            if status is None or record.workflow_run.status is status
        ]
        records.sort(
            key=lambda record: (
                record.workflow_run.created_at,
                record.workflow_run.id,
            ),
            reverse=True,
        )
        return tuple(
            record.to_execution() for record in records[offset : offset + limit]
        )

    def count_runs(self, *, status: WorkflowRunStatus | None = None) -> int:
        return sum(
            1
            for record in self._uow._executions.values()
            if status is None or record.workflow_run.status is status
        )

    def list_definitions(self) -> tuple[Workflow, ...]:
        definitions = {
            (record.workflow.id, record.workflow.version): record.workflow
            for record in self._uow._executions.values()
        }
        return tuple(definitions[key] for key in sorted(definitions))


class InMemoryCheckpointRepository(CheckpointRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def save(
        self,
        checkpoint: Checkpoint,
        *,
        boundary: CheckpointBoundary,
        step_id: str | None = None,
        attempt: int | None = None,
    ) -> CheckpointRecord:
        checkpoint.verify_integrity()
        run_id = checkpoint.workflow_run_id
        records = list(self._uow._checkpoint_records.get(run_id, ()))
        key = (boundary, checkpoint.id, step_id, attempt)
        for record in records:
            if record.checkpoint.id == checkpoint.id and record.checkpoint != checkpoint:
                raise DuplicateEntityError(
                    f"Checkpoint ID {checkpoint.id} has conflicting immutable content"
                )
            if (
                record.boundary,
                record.checkpoint.id,
                record.step_id,
                record.attempt,
            ) == key:
                return record

        record = CheckpointRecord(
            record_sequence=len(records) + 1,
            boundary=boundary,
            checkpoint=checkpoint,
            step_id=step_id,
            attempt=attempt,
        )
        records.append(record)
        self._uow._checkpoint_records[run_id] = tuple(records)
        self._uow._dirty_checkpoint_runs.add(run_id)
        return record

    def get_latest(self, workflow_run_id: str) -> Checkpoint | None:
        checkpoints = self.list(workflow_run_id)
        return checkpoints[-1] if checkpoints else None

    def list(self, workflow_run_id: str) -> tuple[Checkpoint, ...]:
        by_id: dict[str, Checkpoint] = {}
        for record in self.list_records(workflow_run_id):
            by_id.setdefault(record.checkpoint.id, record.checkpoint)
        return tuple(sorted(by_id.values(), key=lambda item: (item.sequence, item.id)))

    def list_records(self, workflow_run_id: str) -> tuple[CheckpointRecord, ...]:
        return self._uow._checkpoint_records.get(workflow_run_id, ())


class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def initialize_context(
        self,
        *,
        project_id: str,
        workflow_run_id: str,
        context: Mapping[str, Any],
        producer: str,
        source_references: tuple[str, ...] = (),
    ) -> MemoryRevision:
        existing = self.history(project_id, workflow_run_id)
        if existing:
            return existing[-1]
        return self.update_context(
            project_id=project_id,
            workflow_run_id=workflow_run_id,
            updates=context,
            producer=producer,
            source_references=source_references,
        )

    def read_context(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> Mapping[str, Any]:
        revisions = self.history(project_id, workflow_run_id)
        return revisions[-1].context if revisions else freeze_json({}, path="context")

    def update_context(
        self,
        *,
        project_id: str,
        workflow_run_id: str,
        updates: Mapping[str, Any],
        producer: str,
        source_references: tuple[str, ...] = (),
    ) -> MemoryRevision:
        key = (project_id, workflow_run_id)
        revisions = list(self._uow._memory_revisions.get(key, ()))
        merged = thaw_json(revisions[-1].context) if revisions else {}
        merged.update(thaw_json(freeze_json(updates, path="updates")))
        revision = MemoryRevision(
            project_id=project_id,
            workflow_run_id=workflow_run_id,
            revision=len(revisions) + 1,
            context=merged,
            producer=producer,
            source_references=source_references,
        )
        revisions.append(revision)
        self._uow._memory_revisions[key] = tuple(revisions)
        self._uow._dirty_memory_scopes.add(key)
        return revision

    def history(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[MemoryRevision, ...]:
        return self._uow._memory_revisions.get((project_id, workflow_run_id), ())


class InMemoryArtifactRepository(ArtifactRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def save(self, artifact: ArtifactMetadata) -> None:
        existing = self._uow._artifacts.get(artifact.id)
        if existing is not None and existing != artifact:
            raise DuplicateEntityError(
                f"Artifact ID {artifact.id} has conflicting immutable metadata"
            )
        if existing is None:
            self._uow._artifacts[artifact.id] = artifact
            self._uow._dirty_artifacts.add(artifact.id)

    def get(self, artifact_id: str) -> ArtifactMetadata | None:
        return self._uow._artifacts.get(artifact_id)

    def list_for_project(self, project_id: str) -> tuple[ArtifactMetadata, ...]:
        return tuple(
            sorted(
                (
                    artifact
                    for artifact in self._uow._artifacts.values()
                    if artifact.project_id == project_id
                ),
                key=lambda item: (
                    item.logical_artifact_id,
                    item.version,
                    item.id,
                ),
            )
        )


class InMemoryApprovalRepository(ApprovalRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def save(
        self,
        approval: ApprovalRequest,
        *,
        expected_version: int | None,
    ) -> int:
        current = self._uow._approvals.get(approval.id)
        if expected_version is None:
            if current is not None:
                raise StaleStateError(
                    f"ApprovalRequest {approval.id} already exists at persistence "
                    f"version {current.persistence_version}"
                )
            next_version = 1
        else:
            if current is None:
                raise StaleStateError(
                    f"ApprovalRequest {approval.id} does not exist"
                )
            if current.persistence_version != expected_version:
                raise StaleStateError(
                    f"ApprovalRequest {approval.id} expected persistence version "
                    f"{expected_version}; found {current.persistence_version}"
                )
            next_version = expected_version + 1

        self._uow._approval_expected.setdefault(approval.id, expected_version)
        self._uow._approvals[approval.id] = ApprovalRecord.from_approval(
            approval,
            persistence_version=next_version,
        )
        self._uow._dirty_approvals.add(approval.id)
        return next_version

    def get(self, approval_id: str) -> ApprovalRequest | None:
        record = self._uow._approvals.get(approval_id)
        return record.to_approval() if record is not None else None

    def get_version(self, approval_id: str) -> int | None:
        record = self._uow._approvals.get(approval_id)
        return record.persistence_version if record is not None else None

    def get_by_fingerprint(
        self,
        project_id: str,
        workflow_run_id: str,
        request_fingerprint: str,
    ) -> ApprovalRequest | None:
        records = [
            record
            for record in self._uow._approvals.values()
            if record.project_id == project_id
            and record.workflow_run_id == workflow_run_id
            and record.request_fingerprint == request_fingerprint
        ]
        if not records:
            return None
        return max(
            records,
            key=lambda record: (record.requested_at, record.id),
        ).to_approval()

    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ApprovalRequest, ...]:
        records = sorted(
            (
                record
                for record in self._uow._approvals.values()
                if record.project_id == project_id
                and record.workflow_run_id == workflow_run_id
            ),
            key=lambda record: (record.requested_at, record.id),
        )
        return tuple(record.to_approval() for record in records)

    def list_pending_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ApprovalRequest, ...]:
        return tuple(
            approval
            for approval in self.list_for_run(project_id, workflow_run_id)
            if approval.status is ApprovalRequestStatus.PENDING
        )

    def list_requests(
        self,
        *,
        status: ApprovalRequestStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[ApprovalRequest, ...]:
        records = [
            record
            for record in self._uow._approvals.values()
            if status is None or record.status is status
        ]
        records.sort(
            key=lambda record: (record.requested_at, record.id),
            reverse=True,
        )
        return tuple(
            record.to_approval() for record in records[offset : offset + limit]
        )

    def count_requests(
        self,
        *,
        status: ApprovalRequestStatus | None = None,
    ) -> int:
        return sum(
            1
            for record in self._uow._approvals.values()
            if status is None or record.status is status
        )

class InMemoryExecutionEventStore(ExecutionEventStore):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def append(
        self,
        event: ExecutionEvent,
        *,
        expected_sequence: int,
    ) -> ExecutionEvent:
        existing = self.get(event.id)
        if existing is not None:
            if existing != event:
                raise DuplicateEntityError(
                    f"ExecutionEvent ID {event.id} has conflicting immutable content"
                )
            return existing

        scope = (event.project_id, event.workflow_run_id)
        events = list(self._uow._execution_events.get(scope, ()))
        current_sequence = len(events)
        if expected_sequence != current_sequence:
            raise StaleStateError(
                f"Execution event stream {scope} expected sequence "
                f"{expected_sequence}; found {current_sequence}"
            )
        if event.sequence != current_sequence + 1:
            raise StaleStateError(
                f"ExecutionEvent {event.id} must use sequence "
                f"{current_sequence + 1}; received {event.sequence}"
            )

        events.append(event)
        self._uow._execution_events[scope] = tuple(events)
        self._uow._dirty_event_streams.add(scope)
        return event

    def get(self, event_id: str) -> ExecutionEvent | None:
        for events in self._uow._execution_events.values():
            for event in events:
                if event.id == event_id:
                    return event
        return None

    def latest_sequence(self, project_id: str, workflow_run_id: str) -> int:
        return len(self._uow._execution_events.get((project_id, workflow_run_id), ()))

    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ExecutionEvent, ...]:
        return self._uow._execution_events.get((project_id, workflow_run_id), ())


class InMemoryUnitOfWork(UnitOfWork):
    """Reusable transactional view over a shared InMemoryDatabase."""

    def __init__(self, database: InMemoryDatabase | None = None) -> None:
        self.database = database or InMemoryDatabase()
        self._workflow_repository = InMemoryWorkflowRepository(self)
        self._checkpoint_repository = InMemoryCheckpointRepository(self)
        self._memory_repository = InMemoryMemoryRepository(self)
        self._artifact_repository = InMemoryArtifactRepository(self)
        self._approval_repository = InMemoryApprovalRepository(self)
        self._event_store = InMemoryExecutionEventStore(self)
        self._refresh()

    @property
    def workflows(self) -> WorkflowRepository:
        return self._workflow_repository

    @property
    def checkpoints(self) -> CheckpointRepository:
        return self._checkpoint_repository

    @property
    def memory(self) -> MemoryRepository:
        return self._memory_repository

    @property
    def artifacts(self) -> ArtifactRepository:
        return self._artifact_repository

    @property
    def approvals(self) -> ApprovalRepository:
        return self._approval_repository

    @property
    def events(self) -> ExecutionEventStore:
        return self._event_store

    def commit(self) -> None:
        self._validate_concurrency()
        for run_id in self._dirty_workflows:
            self.database.executions[run_id] = self._executions[run_id]
        for run_id in self._dirty_checkpoint_runs:
            self.database.checkpoint_records[run_id] = self._checkpoint_records[run_id]
        for scope in self._dirty_memory_scopes:
            self.database.memory_revisions[scope] = self._memory_revisions[scope]
        for artifact_id in self._dirty_artifacts:
            self.database.artifacts[artifact_id] = self._artifacts[artifact_id]
        for approval_id in self._dirty_approvals:
            self.database.approvals[approval_id] = self._approvals[approval_id]
        for scope in self._dirty_event_streams:
            self.database.execution_events[scope] = self._execution_events[scope]
        self._refresh()

    def rollback(self) -> None:
        self._refresh()

    def _validate_concurrency(self) -> None:
        for run_id in self._dirty_workflows:
            expected = self._workflow_expected[run_id]
            current = self.database.executions.get(run_id)
            current_version = current.persistence_version if current is not None else None
            if current_version != expected:
                raise StaleStateError(
                    f"WorkflowRun {run_id} expected committed persistence version "
                    f"{expected}; found {current_version}"
                )
            candidate = self._executions[run_id]
            conflicting_run = next(
                (
                    record.workflow_run.id
                    for record in self.database.executions.values()
                    if record.workflow_run.project_id
                    == candidate.workflow_run.project_id
                    and record.workflow_run.idempotency_key
                    == candidate.workflow_run.idempotency_key
                    and record.workflow_run.id != run_id
                ),
                None,
            )
            if conflicting_run is not None:
                raise DuplicateEntityError(
                    "Workflow execution idempotency key was concurrently claimed by "
                    f"WorkflowRun {conflicting_run}"
                )

        for run_id in self._dirty_checkpoint_runs:
            current_count = len(self.database.checkpoint_records.get(run_id, ()))
            expected_count = self._base_checkpoint_counts.get(run_id, 0)
            if current_count != expected_count:
                raise StaleStateError(
                    f"Checkpoint stream {run_id} expected {expected_count} records; "
                    f"found {current_count}"
                )

        for scope in self._dirty_memory_scopes:
            current_count = len(self.database.memory_revisions.get(scope, ()))
            expected_count = self._base_memory_counts.get(scope, 0)
            if current_count != expected_count:
                raise StaleStateError(
                    f"Memory scope {scope} expected revision {expected_count}; "
                    f"found {current_count}"
                )

        for artifact_id in self._dirty_artifacts:
            current = self.database.artifacts.get(artifact_id)
            if current is not None and current != self._artifacts[artifact_id]:
                raise DuplicateEntityError(
                    f"Artifact ID {artifact_id} was concurrently reused"
                )

        for approval_id in self._dirty_approvals:
            expected = self._approval_expected[approval_id]
            current = self.database.approvals.get(approval_id)
            current_version = current.persistence_version if current is not None else None
            if current_version != expected:
                raise StaleStateError(
                    f"ApprovalRequest {approval_id} expected committed persistence "
                    f"version {expected}; found {current_version}"
                )
        committed_event_ids = {
            event.id
            for events in self.database.execution_events.values()
            for event in events
        }
        for scope in self._dirty_event_streams:
            current_count = len(self.database.execution_events.get(scope, ()))
            expected_count = self._base_event_counts.get(scope, 0)
            if current_count != expected_count:
                raise StaleStateError(
                    f"Execution event stream {scope} expected sequence "
                    f"{expected_count}; found {current_count}"
                )
            for event in self._execution_events[scope][expected_count:]:
                if event.id in committed_event_ids:
                    raise DuplicateEntityError(
                        f"ExecutionEvent ID {event.id} was concurrently reused"
                    )
                committed_event_ids.add(event.id)

    def _refresh(self) -> None:
        self._executions = dict(self.database.executions)
        self._checkpoint_records = dict(self.database.checkpoint_records)
        self._memory_revisions = dict(self.database.memory_revisions)
        self._artifacts = dict(self.database.artifacts)
        self._approvals = dict(self.database.approvals)
        self._execution_events = dict(self.database.execution_events)
        self._base_checkpoint_counts = {
            run_id: len(records)
            for run_id, records in self.database.checkpoint_records.items()
        }
        self._base_memory_counts = {
            scope: len(revisions)
            for scope, revisions in self.database.memory_revisions.items()
        }
        self._base_event_counts = {
            scope: len(events)
            for scope, events in self.database.execution_events.items()
        }
        self._workflow_expected: dict[str, int | None] = {}
        self._approval_expected: dict[str, int | None] = {}
        self._dirty_workflows: set[str] = set()
        self._dirty_checkpoint_runs: set[str] = set()
        self._dirty_memory_scopes: set[tuple[str, str]] = set()
        self._dirty_artifacts: set[str] = set()
        self._dirty_approvals: set[str] = set()
        self._dirty_event_streams: set[tuple[str, str]] = set()
