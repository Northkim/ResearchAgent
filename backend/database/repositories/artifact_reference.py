"""PostgreSQL adapter for local-product Artifact References."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.artifact_references.contracts import (
    ArtifactDependencyBinding,
    ArtifactReference,
    ArtifactState,
    CompatibilityMode,
    DependencyBindingState,
    MaterializationMode,
    WorkflowArtifactRequirement,
)
from backend.artifact_references.errors import ArtifactReferenceConflictError
from backend.artifact_references.ports import ArtifactReferenceRepository
from backend.database.orm import (
    ArtifactDependencyBindingORM,
    LocalArtifactReferenceORM,
    WorkflowArtifactRequirementORM,
)

from ._helpers import pending_by_composite_key, pending_instances


class SQLAlchemyArtifactReferenceRepository(ArtifactReferenceRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_artifact(self, artifact: ArtifactReference) -> None:
        existing = self.get_artifact(artifact.artifact_id)
        if existing is not None:
            if existing.immutable_identity() != artifact.immutable_identity():
                raise ArtifactReferenceConflictError(
                    "Artifact immutable identity already exists with different content"
                )
            return
        by_progress = next(
            (
                value
                for value in self.list_for_progress(artifact.producer_progress_receipt_id)
                if value.relative_path == artifact.relative_path
            ),
            None,
        )
        if by_progress is not None:
            if by_progress.immutable_identity() != artifact.immutable_identity():
                raise ArtifactReferenceConflictError(
                    "Progress output path is already bound to another Artifact"
                )
            return
        self.session.add(LocalArtifactReferenceORM(
            artifact_id=artifact.artifact_id,
            project_id=artifact.project_id,
            producer_workflow_instance_id=artifact.producer_workflow_instance_id,
            producer_progress_receipt_id=artifact.producer_progress_receipt_id,
            producer_progress_report_id=artifact.producer_progress_report_id,
            producer_execution_round=artifact.producer_execution_round,
            producer_capsule_id=artifact.producer_capsule_id,
            producer_capsule_version=artifact.producer_capsule_version,
            artifact_type=artifact.artifact_type,
            artifact_schema_version=artifact.artifact_schema_version,
            media_type=artifact.media_type,
            state=artifact.state.value,
            relative_path=artifact.relative_path,
            content_checksum=artifact.content_checksum,
            size_bytes=artifact.size_bytes,
            cloud_metadata_available=artifact.cloud_metadata_available,
            produced_at=artifact.produced_at,
            retired_at=artifact.retired_at,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        ))

    def get_artifact(self, artifact_id: str) -> ArtifactReference | None:
        row = next(
            (
                item
                for item in pending_instances(self.session, LocalArtifactReferenceORM)
                if item.artifact_id == artifact_id
            ),
            None,
        ) or self.session.get(LocalArtifactReferenceORM, artifact_id)
        return None if row is None else _artifact(row)

    def list_artifacts(
        self,
        *,
        project_id: str,
        producer_workflow_instance_id: str | None = None,
        artifact_type: str | None = None,
        state: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ArtifactReference, ...]:
        statement = select(LocalArtifactReferenceORM).where(
            LocalArtifactReferenceORM.project_id == project_id
        )
        statement = _artifact_filters(
            statement,
            producer_workflow_instance_id=producer_workflow_instance_id,
            artifact_type=artifact_type,
            state=state,
        ).order_by(
            LocalArtifactReferenceORM.produced_at.desc(),
            LocalArtifactReferenceORM.artifact_id,
        )
        rows = list(self.session.scalars(statement))
        rows.extend(
            row
            for row in pending_instances(self.session, LocalArtifactReferenceORM)
            if row not in rows
            and row.project_id == project_id
            and (producer_workflow_instance_id is None or row.producer_workflow_instance_id == producer_workflow_instance_id)
            and (artifact_type is None or row.artifact_type == artifact_type)
            and (state is None or row.state == state)
        )
        rows.sort(key=lambda row: (-row.produced_at.timestamp(), row.artifact_id))
        return tuple(_artifact(row) for row in rows[offset:offset + limit])

    def count_artifacts(
        self,
        *,
        project_id: str,
        producer_workflow_instance_id: str | None = None,
        artifact_type: str | None = None,
        state: str | None = None,
    ) -> int:
        statement = select(func.count()).select_from(LocalArtifactReferenceORM).where(
            LocalArtifactReferenceORM.project_id == project_id
        )
        statement = _artifact_filters(
            statement,
            producer_workflow_instance_id=producer_workflow_instance_id,
            artifact_type=artifact_type,
            state=state,
        )
        return int(self.session.scalar(statement) or 0) + sum(
            1
            for row in pending_instances(self.session, LocalArtifactReferenceORM)
            if row.project_id == project_id
            and (producer_workflow_instance_id is None or row.producer_workflow_instance_id == producer_workflow_instance_id)
            and (artifact_type is None or row.artifact_type == artifact_type)
            and (state is None or row.state == state)
        )

    def list_for_progress(self, receipt_id: str) -> tuple[ArtifactReference, ...]:
        rows = list(self.session.scalars(
            select(LocalArtifactReferenceORM).where(
                LocalArtifactReferenceORM.producer_progress_receipt_id == receipt_id
            )
        ))
        rows.extend(
            row
            for row in pending_instances(self.session, LocalArtifactReferenceORM)
            if row.producer_progress_receipt_id == receipt_id and row not in rows
        )
        rows.sort(key=lambda row: (row.relative_path, row.artifact_id))
        return tuple(_artifact(row) for row in rows)

    def add_requirement(self, requirement: WorkflowArtifactRequirement) -> None:
        existing = self.get_requirement(
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
        )
        if existing is not None:
            if existing != requirement:
                raise ArtifactReferenceConflictError(
                    "Workflow Artifact Requirement immutable-content conflict"
                )
            return
        self.session.add(WorkflowArtifactRequirementORM(
            workflow_definition_id=requirement.workflow_definition_id,
            workflow_version=requirement.workflow_version,
            requirement_key=requirement.requirement_key,
            artifact_type=requirement.artifact_type,
            compatibility_mode=requirement.compatibility_mode.value,
            schema_constraint=requirement.schema_constraint,
            cardinality_min=requirement.cardinality_min,
            cardinality_max=requirement.cardinality_max,
            required=requirement.required,
            materialization_mode=requirement.materialization_mode.value,
            target_relative_path=requirement.target_relative_path,
            created_at=requirement.created_at,
            updated_at=requirement.updated_at,
        ))

    def get_requirement(
        self, workflow_definition_id: str, workflow_version: str, requirement_key: str
    ) -> WorkflowArtifactRequirement | None:
        key = (workflow_definition_id, workflow_version, requirement_key)
        row = pending_by_composite_key(
            self.session,
            WorkflowArtifactRequirementORM,
            key,
            ("workflow_definition_id", "workflow_version", "requirement_key"),
        ) or self.session.get(WorkflowArtifactRequirementORM, key)
        return None if row is None else _requirement(row)

    def add_binding(self, binding: ArtifactDependencyBinding) -> None:
        existing = self.get_binding(binding.binding_id)
        if existing is not None:
            if existing != binding:
                raise ArtifactReferenceConflictError(
                    "Artifact dependency binding immutable-content conflict"
                )
            return
        self.session.add(ArtifactDependencyBindingORM(
            binding_id=binding.binding_id,
            project_id=binding.project_id,
            consumer_workflow_instance_id=binding.consumer_workflow_instance_id,
            consumer_workflow_definition_id=binding.consumer_workflow_definition_id,
            consumer_workflow_version=binding.consumer_workflow_version,
            requirement_key=binding.requirement_key,
            artifact_id=binding.artifact_id,
            expected_checksum=binding.expected_checksum,
            state=binding.state.value,
            idempotency_key=binding.idempotency_key,
            created_at=binding.created_at,
            updated_at=binding.updated_at,
            retired_at=binding.retired_at,
        ))

    def save_binding(self, binding: ArtifactDependencyBinding) -> None:
        row = next(
            (
                item
                for item in pending_instances(self.session, ArtifactDependencyBindingORM)
                if item.binding_id == binding.binding_id
            ),
            None,
        ) or self.session.get(ArtifactDependencyBindingORM, binding.binding_id)
        if row is None:
            raise ValueError("Artifact dependency binding does not exist")
        existing = _binding(row)
        if (
            existing.binding_id,
            existing.project_id,
            existing.consumer_workflow_instance_id,
            existing.consumer_workflow_definition_id,
            existing.consumer_workflow_version,
            existing.requirement_key,
            existing.artifact_id,
            existing.expected_checksum,
            existing.idempotency_key,
            existing.created_at,
        ) != (
            binding.binding_id,
            binding.project_id,
            binding.consumer_workflow_instance_id,
            binding.consumer_workflow_definition_id,
            binding.consumer_workflow_version,
            binding.requirement_key,
            binding.artifact_id,
            binding.expected_checksum,
            binding.idempotency_key,
            binding.created_at,
        ):
            raise ArtifactReferenceConflictError(
                "Artifact dependency binding immutable-content conflict"
            )
        row.state = binding.state.value
        row.updated_at = binding.updated_at
        row.retired_at = binding.retired_at

    def get_binding(self, binding_id: str) -> ArtifactDependencyBinding | None:
        row = next(
            (
                item
                for item in pending_instances(self.session, ArtifactDependencyBindingORM)
                if item.binding_id == binding_id
            ),
            None,
        ) or self.session.get(ArtifactDependencyBindingORM, binding_id)
        return None if row is None else _binding(row)

    def get_binding_by_idempotency(
        self, project_id: str, consumer_workflow_instance_id: str, idempotency_key: str
    ) -> ArtifactDependencyBinding | None:
        rows = list(self.session.scalars(
            select(ArtifactDependencyBindingORM).where(
                ArtifactDependencyBindingORM.project_id == project_id,
                ArtifactDependencyBindingORM.consumer_workflow_instance_id
                == consumer_workflow_instance_id,
                ArtifactDependencyBindingORM.idempotency_key == idempotency_key,
            )
        ))
        rows.extend(
            row
            for row in pending_instances(self.session, ArtifactDependencyBindingORM)
            if row.project_id == project_id
            and row.consumer_workflow_instance_id == consumer_workflow_instance_id
            and row.idempotency_key == idempotency_key
            and row not in rows
        )
        return None if not rows else _binding(rows[0])

    def list_bindings(
        self, project_id: str, consumer_workflow_instance_id: str, *,
        offset: int = 0, limit: int = 100,
    ) -> tuple[ArtifactDependencyBinding, ...]:
        rows = list(self.session.scalars(
            select(ArtifactDependencyBindingORM).where(
                ArtifactDependencyBindingORM.project_id == project_id,
                ArtifactDependencyBindingORM.consumer_workflow_instance_id
                == consumer_workflow_instance_id,
            )
        ))
        rows.extend(
            row
            for row in pending_instances(self.session, ArtifactDependencyBindingORM)
            if row.project_id == project_id
            and row.consumer_workflow_instance_id == consumer_workflow_instance_id
            and row not in rows
        )
        rows.sort(key=lambda row: (row.requirement_key, row.created_at, row.binding_id))
        return tuple(_binding(row) for row in rows[offset:offset + limit])

    def list_project_bindings(
        self, project_id: str
    ) -> tuple[ArtifactDependencyBinding, ...]:
        rows = list(self.session.scalars(
            select(ArtifactDependencyBindingORM).where(
                ArtifactDependencyBindingORM.project_id == project_id
            )
        ))
        rows.extend(
            row
            for row in pending_instances(self.session, ArtifactDependencyBindingORM)
            if row.project_id == project_id and row not in rows
        )
        rows.sort(key=lambda row: (
            row.consumer_workflow_instance_id,
            row.requirement_key,
            row.created_at,
            row.binding_id,
        ))
        return tuple(_binding(row) for row in rows)

    def count_bindings(
        self, project_id: str, consumer_workflow_instance_id: str
    ) -> int:
        statement = select(func.count()).select_from(ArtifactDependencyBindingORM).where(
            ArtifactDependencyBindingORM.project_id == project_id,
            ArtifactDependencyBindingORM.consumer_workflow_instance_id
            == consumer_workflow_instance_id,
        )
        return int(self.session.scalar(statement) or 0) + sum(
            row.project_id == project_id
            and row.consumer_workflow_instance_id == consumer_workflow_instance_id
            for row in pending_instances(self.session, ArtifactDependencyBindingORM)
        )


def _artifact_filters(statement, *, producer_workflow_instance_id, artifact_type, state):
    if producer_workflow_instance_id is not None:
        statement = statement.where(
            LocalArtifactReferenceORM.producer_workflow_instance_id
            == producer_workflow_instance_id
        )
    if artifact_type is not None:
        statement = statement.where(LocalArtifactReferenceORM.artifact_type == artifact_type)
    if state is not None:
        statement = statement.where(LocalArtifactReferenceORM.state == state)
    return statement


def _artifact(row: LocalArtifactReferenceORM) -> ArtifactReference:
    return ArtifactReference(
        artifact_id=row.artifact_id,
        project_id=row.project_id,
        producer_workflow_instance_id=row.producer_workflow_instance_id,
        producer_progress_receipt_id=row.producer_progress_receipt_id,
        producer_progress_report_id=row.producer_progress_report_id,
        producer_execution_round=row.producer_execution_round,
        producer_capsule_id=row.producer_capsule_id,
        producer_capsule_version=row.producer_capsule_version,
        artifact_type=row.artifact_type,
        artifact_schema_version=row.artifact_schema_version,
        media_type=row.media_type,
        state=ArtifactState(row.state),
        relative_path=row.relative_path,
        content_checksum=row.content_checksum,
        size_bytes=row.size_bytes,
        cloud_metadata_available=row.cloud_metadata_available,
        produced_at=row.produced_at,
        retired_at=row.retired_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _requirement(row: WorkflowArtifactRequirementORM) -> WorkflowArtifactRequirement:
    return WorkflowArtifactRequirement(
        workflow_definition_id=row.workflow_definition_id,
        workflow_version=row.workflow_version,
        requirement_key=row.requirement_key,
        artifact_type=row.artifact_type,
        compatibility_mode=CompatibilityMode(row.compatibility_mode),
        schema_constraint=row.schema_constraint,
        cardinality_min=row.cardinality_min,
        cardinality_max=row.cardinality_max,
        required=row.required,
        materialization_mode=MaterializationMode(row.materialization_mode),
        target_relative_path=row.target_relative_path,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _binding(row: ArtifactDependencyBindingORM) -> ArtifactDependencyBinding:
    return ArtifactDependencyBinding(
        binding_id=row.binding_id,
        project_id=row.project_id,
        consumer_workflow_instance_id=row.consumer_workflow_instance_id,
        consumer_workflow_definition_id=row.consumer_workflow_definition_id,
        consumer_workflow_version=row.consumer_workflow_version,
        requirement_key=row.requirement_key,
        artifact_id=row.artifact_id,
        expected_checksum=row.expected_checksum,
        state=DependencyBindingState(row.state),
        idempotency_key=row.idempotency_key,
        created_at=row.created_at,
        updated_at=row.updated_at,
        retired_at=row.retired_at,
    )
