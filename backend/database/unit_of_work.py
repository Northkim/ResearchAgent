"""SQLAlchemy transaction boundary implementing the frozen UnitOfWork port."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import case, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from backend.database.orm import (
    AgentSessionORM,
    ApprovalRequestORM,
    ArtifactORM,
    ArtifactDependencyBindingORM,
    CheckpointORM,
    CheckpointRecordORM,
    ExecutionEventORM,
    MemoryRevisionORM,
    LocalProjectORM,
    LocalArtifactReferenceORM,
    LocalBuiltInSkillDefinitionORM,
    LocalSkillVersionORM,
    LocalWorkflowCapsuleVersionORM,
    LocalWorkflowDefinitionORM,
    LocalWorkflowDefinitionVersionORM,
    ProviderOperationORM,
    ProxyCapabilityTokenORM,
    ProxyOperationORM,
    ProjectProgressProjectionORM,
    ProjectDesiredManifestORM,
    ProjectManifestEntryORM,
    ProjectORM,
    ProjectWorkflowInstanceORM,
    ProjectResourceReferenceORM,
    WorkflowCapsuleArtifactORM,
    WorkflowArtifactRequirementORM,
    WorkspaceInstallationAcknowledgementORM,
    StepRunORM,
    UploadedProgressReportORM,
    WorkflowDefinitionORM,
    WorkflowInputSetupDecisionORM,
    WorkflowDefinitionVersionSkillPinORM,
    WorkflowResourceBindingORM,
    WorkflowResourceRequirementORM,
    WorkflowRunORM,
)
from backend.database.orm.models import (
    ControlledLocalRunApprovalORM,
    ProjectUserSkillORM,
    UserManagedSkillORM,
)
from backend.controlled_local_run_approvals import (
    ControlledLocalApprovalStatus,
    ControlledLocalRunApproval,
    ControlledLocalRunSummary,
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
from backend.local_projects.ports import LocalProjectRepository
from backend.project_workspaces.ports import (
    ProjectManifestRepository,
    WorkflowFoundationRepository,
    WorkspaceSyncRepository,
)
from backend.user_skills import SQLAlchemyUserSkillRepository

from .repositories import (
    SQLAlchemyApprovalRepository,
    SQLAlchemyArtifactRepository,
    SQLAlchemyArtifactReferenceRepository,
    SQLAlchemyCheckpointRepository,
    SQLAlchemyExecutionEventStore,
    SQLAlchemyMemoryRepository,
    SQLAlchemyLocalProjectRepository,
    SQLAlchemyProviderOperationRepository,
    SQLAlchemyProgressReportRepository,
    SQLAlchemyWorkflowRepository,
    SQLAlchemyWorkflowFoundationRepository,
    SQLAlchemyProjectManifestRepository,
    SQLAlchemyResourceReferenceRepository,
    SQLAlchemyWorkspaceSyncRepository,
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


class SQLAlchemyControlledLocalRunApprovalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(
        self, request_id: str, *, for_update: bool = False
    ) -> ControlledLocalRunApproval | None:
        statement = select(ControlledLocalRunApprovalORM).where(
            ControlledLocalRunApprovalORM.request_id == request_id
        )
        if for_update:
            statement = statement.with_for_update()
        row = self.session.scalar(statement)
        return None if row is None else self._contract(row)

    def get_current(
        self, project_id: str, workflow_instance_id: str, *, for_update: bool = False
    ) -> ControlledLocalRunApproval | None:
        statement = (
            select(ControlledLocalRunApprovalORM)
            .where(
                ControlledLocalRunApprovalORM.project_id == project_id,
                ControlledLocalRunApprovalORM.workflow_instance_id
                == workflow_instance_id,
            )
            .order_by(
                case(
                    (
                        ControlledLocalRunApprovalORM.status.in_(
                            ("REQUESTED", "APPROVED")
                        ),
                        2,
                    ),
                    (ControlledLocalRunApprovalORM.status == "SUPERSEDED", 0),
                    else_=1,
                ).desc(),
                ControlledLocalRunApprovalORM.created_at.desc(),
                ControlledLocalRunApprovalORM.request_id.desc(),
            )
            .limit(1)
        )
        if for_update:
            statement = statement.with_for_update()
        row = self.session.scalar(statement)
        return None if row is None else self._contract(row)

    def add(self, request: ControlledLocalRunApproval) -> None:
        self.session.add(self._row(request))

    def save(self, request: ControlledLocalRunApproval) -> None:
        row = self.session.get(ControlledLocalRunApprovalORM, request.request_id)
        if row is None:
            raise DuplicateEntityError("Controlled-local Run Approval does not exist")
        self._apply(row, request)

    @staticmethod
    def _row(value: ControlledLocalRunApproval) -> ControlledLocalRunApprovalORM:
        row = ControlledLocalRunApprovalORM(request_id=value.request_id)
        SQLAlchemyControlledLocalRunApprovalRepository._apply(row, value)
        return row

    @staticmethod
    def _apply(row: ControlledLocalRunApprovalORM, value: ControlledLocalRunApproval) -> None:
        row.project_id = value.project_id
        row.workflow_instance_id = value.workflow_instance_id
        row.schema = value.schema
        row.research_objective_checksum = value.research_objective_checksum
        row.execution_plan_checksum = value.execution_plan_checksum
        row.validated_package_checksum = value.validated_package_checksum
        row.runtime_compatibility_checksum = value.runtime_compatibility_checksum
        row.capability_checksum = value.capability_checksum
        row.summary_json = value.summary.to_dict()
        row.summary_checksum = value.summary.summary_checksum
        row.request_checksum = value.request_checksum
        row.created_at = value.created_at
        row.status = value.status.value
        row.owner_actor = value.owner_actor
        row.decision_reason = value.decision_reason
        row.decision_idempotency_key = value.decision_idempotency_key
        row.decided_at = value.decided_at
        row.approval_checksum = value.approval_checksum
        row.consumed_attempt_id = value.consumed_attempt_id
        row.consumed_at = value.consumed_at
        row.consumption_checksum = value.consumption_checksum

    @staticmethod
    def _contract(row: ControlledLocalRunApprovalORM) -> ControlledLocalRunApproval:
        return ControlledLocalRunApproval(
            request_id=row.request_id, project_id=row.project_id,
            workflow_instance_id=row.workflow_instance_id,
            research_objective_checksum=row.research_objective_checksum,
            execution_plan_checksum=row.execution_plan_checksum,
            validated_package_checksum=row.validated_package_checksum,
            runtime_compatibility_checksum=row.runtime_compatibility_checksum,
            capability_checksum=row.capability_checksum,
            summary=ControlledLocalRunSummary.from_mapping(row.summary_json),
            created_at=row.created_at, request_checksum=row.request_checksum,
            status=ControlledLocalApprovalStatus(row.status),
            owner_actor=row.owner_actor, decision_reason=row.decision_reason,
            decision_idempotency_key=row.decision_idempotency_key,
            decided_at=row.decided_at, approval_checksum=row.approval_checksum,
            consumed_attempt_id=row.consumed_attempt_id,
            consumed_at=row.consumed_at,
            consumption_checksum=row.consumption_checksum,
            schema=row.schema,
        )


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
        self._local_projects = SQLAlchemyLocalProjectRepository(self.session)
        self._workflow_foundation = SQLAlchemyWorkflowFoundationRepository(self.session)
        self._project_manifests = SQLAlchemyProjectManifestRepository(self.session)
        self._workspace_sync = SQLAlchemyWorkspaceSyncRepository(self.session)
        self._artifact_references = SQLAlchemyArtifactReferenceRepository(self.session)
        self._resource_references = SQLAlchemyResourceReferenceRepository(self.session)
        self.user_skills = SQLAlchemyUserSkillRepository(self.session)
        self.controlled_local_run_approvals = (
            SQLAlchemyControlledLocalRunApprovalRepository(self.session)
        )

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

    @property
    def local_projects(self) -> LocalProjectRepository:
        return self._local_projects

    @property
    def workflow_foundation(self) -> WorkflowFoundationRepository:
        return self._workflow_foundation

    @property
    def project_manifests(self) -> ProjectManifestRepository:
        return self._project_manifests

    @property
    def workspace_sync(self) -> WorkspaceSyncRepository:
        return self._workspace_sync

    @property
    def artifact_references(self):
        return self._artifact_references

    @property
    def resource_references(self):
        return self._resource_references

    def delete_project_cloud_state(self, project_id: str) -> None:
        """Delete one Project-owned graph in FK-safe order in this transaction."""

        project_rows = (
            ArtifactDependencyBindingORM,
            LocalArtifactReferenceORM,
            UploadedProgressReportORM,
            WorkflowInputSetupDecisionORM,
            ControlledLocalRunApprovalORM,
            WorkflowResourceBindingORM,
            ProjectResourceReferenceORM,
            WorkspaceInstallationAcknowledgementORM,
            ProjectManifestEntryORM,
            WorkflowCapsuleArtifactORM,
            ProjectUserSkillORM,
            ProjectProgressProjectionORM,
        )
        self.session.execute(
            delete(ProxyOperationORM).where(ProxyOperationORM.project_id == project_id)
        )
        self.session.execute(
            delete(ProxyCapabilityTokenORM).where(
                ProxyCapabilityTokenORM.project_id == project_id
            )
        )
        # Hosted compatibility rows are scoped by Workflow Run, not canonical
        # Project FKs. Artifacts lack an ON DELETE action and must go first;
        # the remaining run-owned graph cascades from WorkflowRunORM.
        self.session.execute(
            delete(ArtifactORM).where(ArtifactORM.project_id == project_id)
        )
        self.session.execute(
            delete(WorkflowRunORM).where(WorkflowRunORM.project_id == project_id)
        )
        for model in project_rows:
            self.session.execute(delete(model).where(model.project_id == project_id))
        self.session.execute(
            delete(ProjectWorkflowInstanceORM).where(
                ProjectWorkflowInstanceORM.project_id == project_id
            )
        )
        self.session.execute(
            delete(ProjectDesiredManifestORM).where(
                ProjectDesiredManifestORM.project_id == project_id
            )
        )
        self.session.execute(
            delete(ProjectORM).where(ProjectORM.project_id == project_id)
        )
        self.session.execute(
            delete(LocalProjectORM).where(LocalProjectORM.project_id == project_id)
        )

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
        self._flush_type(LocalProjectORM)
        self._flush_type(ProjectORM)
        self._flush_type(UserManagedSkillORM)
        self._flush_type(LocalWorkflowDefinitionORM)
        self._flush_type(LocalWorkflowDefinitionVersionORM)
        self._flush_type(LocalBuiltInSkillDefinitionORM)
        self._flush_type(LocalSkillVersionORM)
        self._flush_type(WorkflowDefinitionVersionSkillPinORM)
        self._flush_type(LocalWorkflowCapsuleVersionORM)
        self._flush_type(ProjectWorkflowInstanceORM)
        self._flush_type(ProjectUserSkillORM)
        self._flush_type(ControlledLocalRunApprovalORM)
        self._flush_type(ProjectResourceReferenceORM)
        self._flush_type(ProjectDesiredManifestORM)
        self._flush_type(ProjectManifestEntryORM)
        self._flush_type(WorkflowCapsuleArtifactORM)
        self._flush_type(WorkspaceInstallationAcknowledgementORM)
        self._flush_type(WorkflowRunORM)
        self._flush_type(AgentSessionORM)
        self._flush_type(StepRunORM)
        self._flush_type(ProviderOperationORM)
        self._flush_type(UploadedProgressReportORM)
        self._flush_type(LocalArtifactReferenceORM)
        self._flush_type(WorkflowArtifactRequirementORM)
        self._flush_type(ArtifactDependencyBindingORM)
        self._flush_type(WorkflowInputSetupDecisionORM)
        self._flush_type(WorkflowResourceRequirementORM)
        self._flush_type(WorkflowResourceBindingORM)
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
