"""SQLAlchemy transaction boundary implementing the frozen UnitOfWork port."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from backend.database.orm import (
    AgentSessionORM,
    ApprovalRequestORM,
    ArtifactORM,
    CheckpointORM,
    CheckpointRecordORM,
    ExecutionEventORM,
    MemoryRevisionORM,
    ProviderOperationORM,
    ProjectProgressProjectionORM,
    StepRunORM,
    UploadedProgressReportORM,
    WorkflowDefinitionORM,
    WorkflowRunORM,
)
from backend.execution_events.ports import ExecutionEventStore
from backend.persistence.ports import (
    ApprovalRepository,
    ArtifactRepository,
    CheckpointRepository,
    DuplicateEntityError,
    MemoryRepository,
    ProviderOperationRepository,
    StaleStateError,
    UnitOfWork,
    WorkflowRepository,
)
from backend.progress_reports.ports import ProgressReportRepository

from .repositories import (
    SQLAlchemyApprovalRepository,
    SQLAlchemyArtifactRepository,
    SQLAlchemyCheckpointRepository,
    SQLAlchemyExecutionEventStore,
    SQLAlchemyMemoryRepository,
    SQLAlchemyProviderOperationRepository,
    SQLAlchemyProgressReportRepository,
    SQLAlchemyWorkflowRepository,
)


_STALE_CONSTRAINTS = {
    "pk_approval_requests",
    "pk_checkpoint_records",
    "pk_memory_revisions",
    "pk_workflow_runs",
    "uq_checkpoint_records_boundary_identity",
    "uq_checkpoints_run_sequence",
    "uq_execution_events_run_sequence",
    "pk_provider_operations",
}


class SQLAlchemyUnitOfWork(UnitOfWork):
    """One SQLAlchemy Session and transaction shared by every repository."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session = session_factory()
        self.session.begin()
        self._workflows = SQLAlchemyWorkflowRepository(self.session)
        self._checkpoints = SQLAlchemyCheckpointRepository(self.session)
        self._memory = SQLAlchemyMemoryRepository(self.session)
        self._artifacts = SQLAlchemyArtifactRepository(self.session)
        self._approvals = SQLAlchemyApprovalRepository(self.session)
        self._events = SQLAlchemyExecutionEventStore(self.session)
        self._provider_operations = SQLAlchemyProviderOperationRepository(self.session)
        self._progress_reports = SQLAlchemyProgressReportRepository(self.session)

    @property
    def workflows(self) -> WorkflowRepository:
        return self._workflows

    @property
    def checkpoints(self) -> CheckpointRepository:
        return self._checkpoints

    @property
    def memory(self) -> MemoryRepository:
        return self._memory

    @property
    def artifacts(self) -> ArtifactRepository:
        return self._artifacts

    @property
    def approvals(self) -> ApprovalRepository:
        return self._approvals

    @property
    def events(self) -> ExecutionEventStore:
        return self._events

    @property
    def provider_operations(self) -> ProviderOperationRepository:
        return self._provider_operations

    @property
    def progress_reports(self) -> ProgressReportRepository:
        return self._progress_reports

    def commit(self) -> None:
        try:
            self._flush_in_dependency_order()
            self.session.commit()
        except StaleDataError as error:
            self.session.rollback()
            raise StaleStateError(
                "SQLAlchemy optimistic version check rejected stale state"
            ) from error
        except IntegrityError as error:
            constraint = _constraint_name(error)
            self.session.rollback()
            if constraint in _STALE_CONSTRAINTS:
                raise StaleStateError(
                    f"PostgreSQL concurrency constraint {constraint} rejected the write"
                ) from error
            raise DuplicateEntityError(
                "PostgreSQL rejected a duplicate or inconsistent persistent identity"
                + (f" ({constraint})" if constraint else "")
            ) from error

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        if self.session.in_transaction():
            self.session.rollback()
        self.session.close()

    def __enter__(self) -> SQLAlchemyUnitOfWork:
        if not self.session.in_transaction():
            self.session.begin()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None:
            self.rollback()
        self.close()

    def _flush_in_dependency_order(self) -> None:
        """Flush staged rows in FK order without exposing ORM relationships."""

        self._flush_type(WorkflowDefinitionORM)
        self._flush_type(WorkflowRunORM)
        self._flush_type(AgentSessionORM)
        self._flush_type(StepRunORM)
        self._flush_type(ProviderOperationORM)
        self._flush_type(UploadedProgressReportORM)
        self._flush_type(ProjectProgressProjectionORM)

        checkpoints = sorted(
            self._pending_or_dirty(CheckpointORM),
            key=lambda row: row.sequence,
        )
        for checkpoint in checkpoints:
            self.session.flush(objects=[checkpoint])

        self._flush_type(CheckpointRecordORM)
        self._flush_type(MemoryRevisionORM)
        self._flush_type(ArtifactORM)
        self._flush_type(ApprovalRequestORM)

        events = sorted(
            self._pending_or_dirty(ExecutionEventORM),
            key=lambda row: row.sequence,
        )
        for event in events:
            self.session.flush(objects=[event])

    def _flush_type(self, model_type: type[object]) -> None:
        objects = self._pending_or_dirty(model_type)
        if objects:
            self.session.flush(objects=objects)

    def _pending_or_dirty(self, model_type: type[object]) -> list[object]:
        return [
            instance
            for instance in (*tuple(self.session.new), *tuple(self.session.dirty))
            if isinstance(instance, model_type)
        ]


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(error.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None)
