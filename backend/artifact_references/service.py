"""Cloud Artifact metadata, dependency binding, and plan orchestration."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import re
from typing import Any
from uuid import UUID, uuid5

from backend.application.errors import (
    ApplicationCodedConflictError,
    ApplicationCodedNotFoundError,
    ApplicationCodedValidationError,
)
from backend.persistence.ports import UnitOfWork
from backend.progress_reports.contracts import NormalizedProgressRecord, UploadedProgressReport
from backend.workflow_packages.serialization import canonical_hash
from backend.workflow_packages.serialization import canonical_json, to_json_value
from backend.artifact_references.generic_experiment_contracts import (
    GenericExperimentArtifactError,
    GenericExperimentPresentation,
    PresentationBlock,
    PresentationKind,
)

from .contracts import (
    ARTIFACT_PAGE_SCHEMA,
    MATERIALIZATION_PLAN_SCHEMA,
    PAPER_LIBRARY_NONEMPTY_PRECONDITION_SCHEMA,
    PAPER_LIBRARY_QUALIFICATION_SCHEMA,
    ArtifactContentQualification,
    ArtifactDeclaration,
    ArtifactDependencyBinding,
    ArtifactPresentation,
    ArtifactMaterializationPlan,
    ArtifactReference,
    ArtifactState,
    CompatibilityMode,
    DependencyBindingState,
    MaterializationMode,
    WorkflowInputSetupDecision,
)
from .errors import ArtifactReferenceConflictError
from .upstream_presentations import (
    MANUSCRIPT_PRESENTATION_SCHEMA,
    PAPER_LIBRARY_PRESENTATION_SCHEMA,
    REVIEW_PRESENTATION_SCHEMA,
    REVIEW_PRESENTATION_SCHEMA_V2,
    RESEARCH_IDEA_PRESENTATION_SCHEMA,
    UpstreamPresentationError,
    validate_manuscript_presentation,
    validate_paper_library_presentation,
    validate_review_presentation,
    validate_review_presentation_v2,
    validate_research_idea_presentation,
)

_NAMESPACE = UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")


class ArtifactReferenceService:
    """Persist bounded metadata only; Artifact bytes always remain local."""

    def __init__(self, *, unit_of_work: UnitOfWork, clock) -> None:
        self._uow = unit_of_work
        self._clock = clock

    def derive_reviewed_progress_declarations(
        self,
        *,
        workflow_instance_id: str,
        normalized: NormalizedProgressRecord,
    ) -> tuple[ArtifactDeclaration, ...]:
        """Recover declarations from an exact reviewed Capsule/Progress contract.

        Literature Search 0.6.0 final reports contain the authoritative path,
        checksum, size, and Artifact kind, but its published runner did not
        forward the redundant declaration list through the local-session
        adapter. Derivation remains fail-closed: only a COMPLETED report and an
        exact producer Capsule output contract can produce declarations.
        """

        if normalized.status.value != "COMPLETED":
            return ()
        instance = self._uow.workflow_foundation.get_workflow_instance(
            workflow_instance_id
        )
        if (
            instance is None
            or instance.workflow_definition_id != normalized.workflow_id
            or instance.workflow_version != normalized.workflow_version
            or instance.capsule_id is None
            or instance.capsule_version is None
        ):
            raise ApplicationCodedConflictError(
                "Progress producer does not match its exact Workflow Instance",
                code="ARTIFACT_PRODUCER_MISMATCH",
            )
        capsule = self._uow.workflow_foundation.get_capsule_version(
            instance.capsule_id, instance.capsule_version
        )
        if capsule is None:
            raise ApplicationCodedValidationError(
                "Artifact producer Capsule contract is unavailable",
                code="ARTIFACT_CONTRACT_VIOLATION",
            )
        contracts = _output_contracts(capsule.compatibility)
        if not contracts:
            return ()
        produced_at = datetime.fromisoformat(
            normalized.completed_at.replace("Z", "+00:00")
        )
        declarations: list[ArtifactDeclaration] = []
        for output in sorted(
            normalized.output_artifacts,
            key=lambda item: (item.relative_path, item.artifact_kind),
        ):
            for artifact_type, contract in contracts.items():
                if contract.get("progress_artifact_kind") != output.artifact_kind:
                    continue
                if output.size is None:
                    raise ApplicationCodedValidationError(
                        "Reviewed Artifact Progress metadata has no byte size",
                        code="ARTIFACT_CONTRACT_VIOLATION",
                    )
                identifier = uuid5(
                    _NAMESPACE,
                    "production-artifact/v1|package="
                    + normalized.package_id
                    + "|report="
                    + normalized.report_id
                    + "|path="
                    + output.relative_path
                    + "|checksum="
                    + output.checksum,
                )
                declaration = ArtifactDeclaration(
                    artifact_id="artifact-" + identifier.hex,
                    artifact_type=artifact_type,
                    artifact_schema_version=contract["artifact_schema_version"],
                    media_type=output.media_type,
                    relative_path=output.relative_path,
                    content_checksum=output.checksum,
                    size_bytes=output.size,
                    produced_at=produced_at,
                )
                if not _matches_output_contract(
                    contract=contract,
                    declaration=declaration,
                    progress_artifact_kind=output.artifact_kind,
                ):
                    raise ApplicationCodedValidationError(
                        "Progress Artifact violates the exact reviewed Capsule contract",
                        code="ARTIFACT_CONTRACT_VIOLATION",
                    )
                declarations.append(declaration)
        return tuple(declarations)

    def promote_progress_artifacts(
        self,
        *,
        report: UploadedProgressReport,
        normalized: NormalizedProgressRecord,
        declarations: tuple[ArtifactDeclaration, ...],
    ) -> tuple[ArtifactReference, ...]:
        existing = self._uow.artifact_references.list_for_progress(report.receipt_id)
        if existing:
            self._require_replay_equivalent(existing, declarations)
            return existing
        if not declarations:
            return ()
        if not report.accepted_for_projection:
            raise ApplicationCodedValidationError(
                "Rejected Progress cannot produce canonical Artifacts",
                code="ARTIFACT_CONTRACT_VIOLATION",
            )
        instance = self._uow.workflow_foundation.get_workflow_instance(
            report.workflow_instance_id
        )
        if instance is None or instance.project_id != report.project_id:
            raise ApplicationCodedConflictError(
                "Artifact producer Workflow Instance mismatch",
                code="ARTIFACT_PRODUCER_MISMATCH",
            )
        if instance.capsule_id is None or instance.capsule_version is None:
            raise ApplicationCodedValidationError(
                "Artifact producer has no exact Capsule pin",
                code="ARTIFACT_CONTRACT_VIOLATION",
            )
        capsule = self._uow.workflow_foundation.get_capsule_version(
            instance.capsule_id, instance.capsule_version
        )
        if capsule is None:
            raise ApplicationCodedValidationError(
                "Artifact producer Capsule contract is unavailable",
                code="ARTIFACT_CONTRACT_VIOLATION",
            )
        output_contracts = _output_contracts(capsule.compatibility)
        if not output_contracts:
            raise ApplicationCodedValidationError(
                "Producer Capsule has no reviewed canonical Artifact output types",
                code="ARTIFACT_TYPE_UNKNOWN",
            )
        report_outputs = {item.relative_path: item for item in normalized.output_artifacts}
        if len(declarations) > 100:
            raise ApplicationCodedValidationError(
                "Artifact declaration list exceeds the reviewed bound",
                code="ARTIFACT_CONTRACT_VIOLATION",
            )
        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        now = _aware(self._clock())
        produced: list[ArtifactReference] = []
        for declaration in sorted(declarations, key=lambda item: (item.relative_path, item.artifact_id)):
            if declaration.artifact_id in seen_ids or declaration.relative_path in seen_paths:
                raise ApplicationCodedValidationError(
                    "Artifact declarations contain a duplicate identity or path",
                    code="ARTIFACT_CONTRACT_VIOLATION",
                )
            seen_ids.add(declaration.artifact_id)
            seen_paths.add(declaration.relative_path)
            progress_output = report_outputs.get(declaration.relative_path)
            if progress_output is None or (
                progress_output.checksum != declaration.content_checksum
                or progress_output.media_type != declaration.media_type
                or progress_output.size != declaration.size_bytes
            ):
                raise ApplicationCodedConflictError(
                    "Artifact declaration differs from immutable Progress metadata",
                    code="ARTIFACT_CONTRACT_VIOLATION",
                )
            contract = output_contracts.get(declaration.artifact_type)
            if contract is None:
                raise ApplicationCodedValidationError(
                    "Artifact type is not declared by the exact producer Capsule",
                    code="ARTIFACT_TYPE_UNKNOWN",
                )
            if not _matches_output_contract(
                contract=contract,
                declaration=declaration,
                progress_artifact_kind=progress_output.artifact_kind,
            ):
                raise ApplicationCodedValidationError(
                    "Artifact declaration violates the reviewed producer contract",
                    code="ARTIFACT_CONTRACT_VIOLATION",
                )
            artifact = ArtifactReference(
                artifact_id=declaration.artifact_id,
                project_id=report.project_id,
                producer_workflow_instance_id=report.workflow_instance_id,
                producer_progress_receipt_id=report.receipt_id,
                producer_progress_report_id=report.report_id,
                producer_execution_round=normalized.execution_round,
                producer_capsule_id=instance.capsule_id,
                producer_capsule_version=instance.capsule_version,
                artifact_type=declaration.artifact_type,
                artifact_schema_version=declaration.artifact_schema_version,
                media_type=declaration.media_type,
                state=ArtifactState.LOCAL_AVAILABLE,
                relative_path=declaration.relative_path,
                content_checksum=declaration.content_checksum,
                size_bytes=declaration.size_bytes,
                cloud_metadata_available=True,
                produced_at=declaration.produced_at,
                retired_at=None,
                created_at=now,
                updated_at=now,
            )
            try:
                self._uow.artifact_references.add_artifact(artifact)
            except ArtifactReferenceConflictError as error:
                raise ApplicationCodedConflictError(
                    str(error), code="ARTIFACT_REFERENCE_CONFLICT"
                ) from error
            produced.append(artifact)
        return tuple(produced)

    def assert_progress_replay(
        self, receipt_id: str, declarations: tuple[ArtifactDeclaration, ...]
    ) -> None:
        existing = self._uow.artifact_references.list_for_progress(receipt_id)
        self._require_replay_equivalent(existing, declarations)

    def list_artifacts(
        self,
        *,
        project_id: str,
        producer_workflow_instance_id: str | None,
        artifact_type: str | None,
        state: str | None,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        project = self._uow.project_manifests.get_project(project_id)
        if project is None:
            raise ApplicationCodedNotFoundError(
                "Project not found", code="PROJECT_NOT_FOUND"
            )
        if producer_workflow_instance_id is not None:
            maturities = self._uow.workflow_foundation.get_instance_maturities(
                project_id, (producer_workflow_instance_id,)
            )
            if producer_workflow_instance_id not in maturities:
                raise ApplicationCodedNotFoundError(
                    "Producer Workflow Instance not found",
                    code="WORKFLOW_INSTANCE_NOT_FOUND",
                )
        if state is not None:
            try:
                ArtifactState(state)
            except ValueError as error:
                raise ApplicationCodedValidationError(
                    "Artifact state filter is invalid", code="INVALID_REQUEST"
                ) from error
        values = self._uow.artifact_references.list_artifacts(
            project_id=project_id,
            producer_workflow_instance_id=producer_workflow_instance_id,
            artifact_type=artifact_type,
            state=state,
            offset=offset,
            limit=limit,
        )
        total = self._uow.artifact_references.count_artifacts(
            project_id=project_id,
            producer_workflow_instance_id=producer_workflow_instance_id,
            artifact_type=artifact_type,
            state=state,
        )
        producer_ids = tuple(sorted({item.producer_workflow_instance_id for item in values}))
        if producer_workflow_instance_id is None:
            maturities = self._uow.workflow_foundation.get_instance_maturities(
                project_id, producer_ids
            )
        if set(producer_ids) - set(maturities):
            raise ApplicationCodedValidationError(
                "Artifact producer Workflow Version is unavailable",
                code="ARTIFACT_PRODUCER_MISMATCH",
            )
        return {
            "schema_version": ARTIFACT_PAGE_SCHEMA,
            "project_id": project_id,
            "artifacts": [
                _artifact_document(
                    item,
                    maturities[item.producer_workflow_instance_id],
                    self._uow.artifact_references.get_presentation(item.artifact_id),
                    self._uow.artifact_references.get_content_qualification(
                        item.artifact_id
                    ),
                )
                for item in values
            ],
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + len(values) < total,
        }

    def report_presentation(
        self, *, project_id: str, artifact_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Accept one immutable, exact-bound, bounded presentation companion."""

        project = self._uow.project_manifests.get_project(project_id)
        if project is None:
            raise ApplicationCodedNotFoundError(
                "Project not found", code="PROJECT_NOT_FOUND"
            )
        artifact = self._uow.artifact_references.get_artifact(artifact_id)
        if artifact is None or artifact.project_id != project_id:
            raise ApplicationCodedNotFoundError(
                "Artifact not found", code="ARTIFACT_NOT_FOUND"
            )
        normalized = _validate_registered_presentation(artifact=artifact, value=payload)
        if (
            normalized["artifact_id"] != artifact.artifact_id
            or normalized["artifact_checksum"] != artifact.content_checksum
        ):
            raise ApplicationCodedConflictError(
                "Presentation does not bind the exact current Artifact",
                code="ARTIFACT_PRESENTATION_ARTIFACT_MISMATCH",
            )
        existing = self._uow.artifact_references.get_presentation(artifact_id)
        if existing is not None:
            if (
                existing.artifact_checksum != artifact.content_checksum
                or existing.schema_identity != normalized["schema"]
                or existing.presentation_checksum != normalized["presentation_checksum"]
                or to_json_value(existing.payload) != normalized
            ):
                raise ApplicationCodedConflictError(
                    "Artifact presentation is immutable and already differs",
                    code="ARTIFACT_PRESENTATION_CONFLICT",
                )
            return _presentation_document(existing)
        presentation = ArtifactPresentation(
            artifact_id=artifact.artifact_id,
            artifact_checksum=artifact.content_checksum,
            schema_identity=normalized["schema"],
            presentation_checksum=normalized["presentation_checksum"],
            payload=normalized,
            reported_at=_aware(self._clock()),
        )
        try:
            self._uow.artifact_references.add_presentation(presentation)
        except ArtifactReferenceConflictError as error:
            raise ApplicationCodedConflictError(
                str(error), code="ARTIFACT_PRESENTATION_CONFLICT"
            ) from error
        self._uow.commit()
        return _presentation_document(presentation)

    def report_content_qualification(
        self, *, project_id: str, artifact_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Accept one immutable bounded fact derived from exact Local bytes."""

        project = self._uow.project_manifests.get_project(project_id)
        if project is None:
            raise ApplicationCodedNotFoundError(
                "Project not found", code="PROJECT_NOT_FOUND"
            )
        artifact = self._uow.artifact_references.get_artifact(artifact_id)
        if artifact is None or artifact.project_id != project_id:
            raise ApplicationCodedNotFoundError(
                "Artifact not found", code="ARTIFACT_NOT_FOUND"
            )
        normalized = _validate_content_qualification(artifact, payload)
        existing = self._uow.artifact_references.get_content_qualification(artifact_id)
        if existing is not None:
            if (
                existing.artifact_checksum != artifact.content_checksum
                or existing.schema_identity != normalized["schema"]
                or existing.qualification_checksum
                != normalized["qualification_checksum"]
                or to_json_value(existing.payload) != normalized
            ):
                raise ApplicationCodedConflictError(
                    "Artifact content qualification is immutable and already differs",
                    code="ARTIFACT_QUALIFICATION_CONFLICT",
                )
            return _qualification_document(existing)
        qualification = ArtifactContentQualification(
            artifact_id=artifact.artifact_id,
            artifact_checksum=artifact.content_checksum,
            schema_identity=normalized["schema"],
            qualification_checksum=normalized["qualification_checksum"],
            payload=normalized,
            reported_at=_aware(self._clock()),
        )
        try:
            self._uow.artifact_references.add_content_qualification(qualification)
        except ArtifactReferenceConflictError as error:
            raise ApplicationCodedConflictError(
                str(error), code="ARTIFACT_QUALIFICATION_CONFLICT"
            ) from error
        self._uow.commit()
        return _qualification_document(qualification)

    def list_compatible_artifacts(
        self,
        *,
        project_id: str,
        consumer_workflow_instance_id: str,
        requirement_key: str,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        consumer = self._uow.workflow_foundation.get_workflow_instance(
            consumer_workflow_instance_id
        )
        if consumer is None or consumer.project_id != project_id:
            raise ApplicationCodedNotFoundError(
                "Consumer Workflow Instance not found",
                code="WORKFLOW_INSTANCE_NOT_FOUND",
            )
        requirement = self._uow.artifact_references.get_requirement(
            consumer.workflow_definition_id,
            consumer.workflow_version,
            requirement_key,
        )
        if requirement is None:
            raise ApplicationCodedNotFoundError(
                "Consumer Artifact requirement not found",
                code="DEPENDENCY_NOT_FOUND",
            )
        candidates = tuple(
            item
            for item in self._uow.artifact_references.list_artifacts(
                project_id=project_id,
                artifact_type=requirement.artifact_type,
                limit=1_000,
            )
            if is_compatible_artifact(
                requirement,
                item,
                self._uow.artifact_references.get_content_qualification(
                    item.artifact_id
                ),
            )
        )
        page = candidates[offset:offset + limit]
        maturities = self._uow.workflow_foundation.get_instance_maturities(
            project_id,
            tuple(sorted({item.producer_workflow_instance_id for item in page})),
        )
        return {
            "schema_version": ARTIFACT_PAGE_SCHEMA,
            "project_id": project_id,
            "artifacts": [
                _artifact_document(
                    item,
                    maturities[item.producer_workflow_instance_id],
                    self._uow.artifact_references.get_presentation(item.artifact_id),
                    self._uow.artifact_references.get_content_qualification(
                        item.artifact_id
                    ),
                )
                for item in page
            ],
            "offset": offset,
            "limit": limit,
            "total": len(candidates),
            "has_more": offset + len(page) < len(candidates),
        }

    def bind_dependency(
        self,
        *,
        project_id: str,
        consumer_workflow_instance_id: str,
        requirement_key: str,
        artifact_id: str,
        idempotency_key: str,
        replace_binding_id: str | None = None,
    ) -> ArtifactDependencyBinding:
        _canonical_uuid(idempotency_key)
        consumer = self._uow.workflow_foundation.get_workflow_instance(
            consumer_workflow_instance_id
        )
        if consumer is None or consumer.project_id != project_id:
            raise ApplicationCodedNotFoundError(
                "Consumer Workflow Instance not found",
                code="WORKFLOW_INSTANCE_NOT_FOUND",
            )
        if consumer.desired_state.value != "ACTIVE":
            raise ApplicationCodedConflictError(
                "Retired consumer cannot accept a new dependency binding",
                code="DEPENDENCY_BINDING_CONFLICT",
            )
        requirement = self._uow.artifact_references.get_requirement(
            consumer.workflow_definition_id, consumer.workflow_version, requirement_key
        )
        if requirement is None:
            raise ApplicationCodedNotFoundError(
                "Consumer Artifact requirement not found", code="DEPENDENCY_NOT_FOUND"
            )
        artifact = self._uow.artifact_references.get_artifact(artifact_id)
        if artifact is None or artifact.project_id != project_id:
            raise ApplicationCodedNotFoundError(
                "Artifact Reference not found", code="ARTIFACT_REFERENCE_NOT_FOUND"
            )
        _require_compatible(
            requirement,
            artifact,
            self._uow.artifact_references.get_content_qualification(artifact_id),
        )
        existing_replay = self._uow.artifact_references.get_binding_by_idempotency(
            project_id, consumer_workflow_instance_id, idempotency_key
        )
        candidate_identity = (requirement_key, artifact_id, artifact.content_checksum)
        if existing_replay is not None:
            if (
                existing_replay.requirement_key,
                existing_replay.artifact_id,
                existing_replay.expected_checksum,
            ) != candidate_identity:
                raise ApplicationCodedConflictError(
                    "Dependency idempotency key was reused with different content",
                    code="IDEMPOTENCY_CONFLICT",
                )
            return existing_replay
        active = next(
            (
                item
                for item in self._uow.artifact_references.list_bindings(
                    project_id, consumer_workflow_instance_id, limit=1_000
                )
                if item.requirement_key == requirement_key
                and item.state is DependencyBindingState.ACTIVE
            ),
            None,
        )
        now = _aware(self._clock())
        if active is not None:
            if replace_binding_id != active.binding_id:
                raise ApplicationCodedConflictError(
                    "Dependency already has a different active Artifact binding",
                    code="DEPENDENCY_BINDING_CONFLICT",
                )
            self._uow.artifact_references.save_binding(
                replace(
                    active,
                    state=DependencyBindingState.RETIRED,
                    updated_at=now,
                    retired_at=now,
                )
            )
        elif replace_binding_id is not None:
            raise ApplicationCodedConflictError(
                "Dependency replacement target is not the active binding",
                code="DEPENDENCY_BINDING_CONFLICT",
            )
        identifier = uuid5(
            UUID(idempotency_key),
            "artifact-binding/v1|"
            f"project={project_id}|consumer={consumer_workflow_instance_id}|"
            f"requirement={requirement_key}|artifact={artifact_id}",
        )
        binding = ArtifactDependencyBinding(
            binding_id="artifact-binding-" + identifier.hex,
            project_id=project_id,
            consumer_workflow_instance_id=consumer_workflow_instance_id,
            consumer_workflow_definition_id=consumer.workflow_definition_id,
            consumer_workflow_version=consumer.workflow_version,
            requirement_key=requirement_key,
            artifact_id=artifact_id,
            expected_checksum=artifact.content_checksum,
            state=DependencyBindingState.ACTIVE,
            idempotency_key=idempotency_key,
            created_at=now,
            updated_at=now,
            retired_at=None,
        )
        self._uow.artifact_references.add_binding(binding)
        self._uow.commit()
        return binding

    def list_dependencies(
        self, *, project_id: str, consumer_workflow_instance_id: str,
        offset: int = 0, limit: int = 100,
    ) -> dict[str, Any]:
        consumer = self._uow.workflow_foundation.get_workflow_instance(
            consumer_workflow_instance_id
        )
        if consumer is None or consumer.project_id != project_id:
            raise ApplicationCodedNotFoundError(
                "Consumer Workflow Instance not found",
                code="WORKFLOW_INSTANCE_NOT_FOUND",
            )
        values = self._uow.artifact_references.list_bindings(
            project_id, consumer_workflow_instance_id, offset=offset, limit=limit
        )
        total = self._uow.artifact_references.count_bindings(
            project_id, consumer_workflow_instance_id
        )
        return {
            "schema_version": "reagent.artifact-dependency-page/v0.1",
            "project_id": project_id,
            "consumer_workflow_instance_id": consumer_workflow_instance_id,
            "dependencies": [binding_document(item) for item in values],
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + len(values) < total,
        }

    def input_setup_state(
        self, *, project_id: str, consumer_workflow_instance_id: str
    ) -> dict[str, Any]:
        consumer, requirements, bindings = self._input_setup_authority(
            project_id=project_id,
            consumer_workflow_instance_id=consumer_workflow_instance_id,
        )
        state = evaluate_input_setup(
            requirements=requirements,
            bindings=bindings,
            decisions=self._uow.artifact_references.list_input_setup_decisions(
                project_id, consumer_workflow_instance_id
            ),
        )
        return input_setup_state_document(consumer, state)

    def confirm_input_setup(
        self,
        *,
        project_id: str,
        consumer_workflow_instance_id: str,
        omitted_optional_requirement_keys: tuple[str, ...],
        idempotency_key: str,
    ) -> WorkflowInputSetupDecision:
        _canonical_uuid(idempotency_key)
        consumer, requirements, bindings = self._input_setup_authority(
            project_id=project_id,
            consumer_workflow_instance_id=consumer_workflow_instance_id,
        )
        state = evaluate_input_setup(
            requirements=requirements,
            bindings=bindings,
            decisions=(),
        )
        if state["missing_required_requirement_keys"]:
            raise ApplicationCodedValidationError(
                "Required Artifact inputs must be selected before input setup can be confirmed",
                code="DEPENDENCY_UNRESOLVED",
            )
        omitted = tuple(sorted(set(omitted_optional_requirement_keys)))
        if omitted != tuple(omitted_optional_requirement_keys):
            raise ApplicationCodedValidationError(
                "Omitted optional requirement keys must be unique and sorted",
                code="INVALID_REQUEST",
            )
        if omitted != state["omitted_optional_requirement_keys"]:
            raise ApplicationCodedConflictError(
                "Input setup omissions differ from the current exact bindings",
                code="INPUT_SETUP_CHANGED",
            )
        if not omitted:
            raise ApplicationCodedValidationError(
                "No unresolved optional evidence requires an omission decision",
                code="INVALID_REQUEST",
            )
        existing = self._uow.artifact_references.get_input_setup_decision_by_idempotency(
            project_id, consumer_workflow_instance_id, idempotency_key
        )
        now = _aware(self._clock())
        payload = {
            "schema_version": "reagent.workflow-input-setup-decision/v0.1",
            "project_id": project_id,
            "consumer_workflow_instance_id": consumer_workflow_instance_id,
            "consumer_workflow_definition_id": consumer.workflow_definition_id,
            "consumer_workflow_version": consumer.workflow_version,
            "binding_set_checksum": state["binding_set_checksum"],
            "omitted_optional_requirement_keys": list(omitted),
            "decision": "CONTINUE_WITHOUT_OPTIONAL_EVIDENCE",
            "idempotency_key": idempotency_key,
            "decided_at": _utc_text(now),
        }
        decision = WorkflowInputSetupDecision(
            decision_id="input-decision-" + uuid5(
                UUID(idempotency_key), canonical_json(payload)
            ).hex,
            project_id=project_id,
            consumer_workflow_instance_id=consumer_workflow_instance_id,
            consumer_workflow_definition_id=consumer.workflow_definition_id,
            consumer_workflow_version=consumer.workflow_version,
            binding_set_checksum=state["binding_set_checksum"],
            omitted_optional_requirement_keys=omitted,
            decision="CONTINUE_WITHOUT_OPTIONAL_EVIDENCE",
            idempotency_key=idempotency_key,
            decision_checksum=canonical_hash(payload),
            decided_at=now,
        )
        if existing is not None:
            if not valid_input_setup_decision(existing):
                raise ApplicationCodedConflictError(
                    "Stored input setup decision integrity is invalid",
                    code="INPUT_SETUP_CHANGED",
                )
            if (
                existing.binding_set_checksum,
                existing.omitted_optional_requirement_keys,
                existing.decision,
            ) != (
                decision.binding_set_checksum,
                decision.omitted_optional_requirement_keys,
                decision.decision,
            ):
                raise ApplicationCodedConflictError(
                    "Input setup idempotency key was reused after inputs changed",
                    code="IDEMPOTENCY_CONFLICT",
                )
            return existing
        self._uow.artifact_references.add_input_setup_decision(decision)
        self._uow.commit()
        return decision

    def _input_setup_authority(
        self, *, project_id: str, consumer_workflow_instance_id: str
    ):
        consumer = self._uow.workflow_foundation.get_workflow_instance(
            consumer_workflow_instance_id
        )
        if consumer is None or consumer.project_id != project_id:
            raise ApplicationCodedNotFoundError(
                "Consumer Workflow Instance not found",
                code="WORKFLOW_INSTANCE_NOT_FOUND",
            )
        requirements = tuple(
            item
            for item in self._uow.artifact_references.list_requirements()
            if item.workflow_definition_id == consumer.workflow_definition_id
            and item.workflow_version == consumer.workflow_version
        )
        bindings = tuple(
            item
            for item in self._uow.artifact_references.list_bindings(
                project_id, consumer_workflow_instance_id, limit=1_000
            )
            if item.state is DependencyBindingState.ACTIVE
        )
        return consumer, requirements, bindings

    def materialization_plan(
        self, *, project_id: str, consumer_workflow_instance_id: str
    ) -> dict[str, Any]:
        project = self._uow.project_manifests.get_project(project_id)
        consumer = self._uow.workflow_foundation.get_workflow_instance(
            consumer_workflow_instance_id
        )
        if project is None or consumer is None or consumer.project_id != project_id:
            raise ApplicationCodedNotFoundError(
                "Consumer Workflow Instance not found",
                code="WORKFLOW_INSTANCE_NOT_FOUND",
            )
        if consumer.capsule_id is None or consumer.capsule_version is None:
            raise ApplicationCodedValidationError(
                "Consumer Capsule pin is unavailable", code="DEPENDENCY_UNRESOLVED"
            )
        requirements = tuple(
            item
            for item in self._uow.artifact_references.list_requirements()
            if item.workflow_definition_id == consumer.workflow_definition_id
            and item.workflow_version == consumer.workflow_version
        )
        plans: list[dict[str, Any]] = []
        bindings = tuple(
            binding
            for binding in self._uow.artifact_references.list_bindings(
                project_id, consumer_workflow_instance_id, limit=1_000
            )
            if binding.state is DependencyBindingState.ACTIVE
        )
        setup = evaluate_input_setup(
            requirements=requirements,
            bindings=bindings,
            decisions=self._uow.artifact_references.list_input_setup_decisions(
                project_id, consumer_workflow_instance_id
            ),
        )
        if setup["missing_required_requirement_keys"]:
            raise ApplicationCodedValidationError(
                "Required Artifact inputs are not selected",
                code="DEPENDENCY_UNRESOLVED",
            )
        if setup["decision_required"] and setup["current_decision"] is None:
            raise ApplicationCodedValidationError(
                "Resolve optional evidence or explicitly continue without it before materialization",
                code="INPUT_SETUP_DECISION_REQUIRED",
            )
        created_at = max(
            (binding.updated_at for binding in bindings),
            default=project.updated_at,
        )
        for binding in bindings:
            artifact = self._uow.artifact_references.get_artifact(binding.artifact_id)
            requirement = self._uow.artifact_references.get_requirement(
                binding.consumer_workflow_definition_id,
                binding.consumer_workflow_version,
                binding.requirement_key,
            )
            producer = (
                None
                if artifact is None
                else self._uow.workflow_foundation.get_workflow_instance(
                    artifact.producer_workflow_instance_id
                )
            )
            if artifact is None or requirement is None or producer is None:
                raise ApplicationCodedValidationError(
                    "Artifact dependency provenance is incomplete",
                    code="DEPENDENCY_UNRESOLVED",
                )
            if producer.project_id != project_id or producer.capsule_version is None:
                raise ApplicationCodedConflictError(
                    "Artifact producer Project identity mismatch",
                    code="ARTIFACT_PROJECT_MISMATCH",
                )
            _require_compatible(
                requirement,
                artifact,
                self._uow.artifact_references.get_content_qualification(
                    artifact.artifact_id
                ),
            )
            if binding.expected_checksum != artifact.content_checksum:
                raise ApplicationCodedConflictError(
                    "Artifact binding checksum drift detected",
                    code="ARTIFACT_CHECKSUM_MISMATCH",
                )
            item = {
                "binding_id": binding.binding_id,
                "requirement_key": binding.requirement_key,
                "consumer_workflow_instance_id": consumer_workflow_instance_id,
                "producer_workflow_instance_id": artifact.producer_workflow_instance_id,
                "artifact_id": artifact.artifact_id,
                "artifact_type": artifact.artifact_type,
                "artifact_schema_version": artifact.artifact_schema_version,
                "expected_checksum": artifact.content_checksum,
                "expected_size_bytes": artifact.size_bytes,
                "source_capsule_relative_path": _capsule_path(producer),
                "source_relative_path": artifact.relative_path,
                "target_capsule_relative_path": _capsule_path(consumer),
                "target_relative_path": requirement.target_relative_path,
                "materialization_mode": requirement.materialization_mode.value,
            }
            plans.append(item)
        plans.sort(key=lambda item: (item["requirement_key"], item["artifact_id"]))
        payload = {
            "schema_version": MATERIALIZATION_PLAN_SCHEMA,
            "project_id": project_id,
            "workspace_id": project.workspace_id,
            "consumer_workflow_instance_id": consumer_workflow_instance_id,
            "artifacts": plans,
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
        }
        return {**payload, "plan_checksum": canonical_hash(payload)}

    @staticmethod
    def _require_replay_equivalent(
        existing: tuple[ArtifactReference, ...],
        declarations: tuple[ArtifactDeclaration, ...],
    ) -> None:
        existing_payload = [
            {
                "artifact_id": item.artifact_id,
                "artifact_type": item.artifact_type,
                "artifact_schema_version": item.artifact_schema_version,
                "media_type": item.media_type,
                "relative_path": item.relative_path,
                "content_checksum": item.content_checksum,
                "size_bytes": item.size_bytes,
                "produced_at": item.produced_at.astimezone(timezone.utc).isoformat().replace(
                    "+00:00", "Z"
                ),
            }
            for item in sorted(existing, key=lambda value: (value.relative_path, value.artifact_id))
        ]
        incoming = [
            item.canonical_payload()
            for item in sorted(declarations, key=lambda value: (value.relative_path, value.artifact_id))
        ]
        if existing_payload != incoming:
            raise ApplicationCodedConflictError(
                "Progress retry changed canonical Artifact declarations",
                code="PROGRESS_IDEMPOTENCY_CONFLICT",
            )


def _require_compatible(
    requirement,
    artifact: ArtifactReference,
    qualification: ArtifactContentQualification | None = None,
) -> None:
    if artifact.state not in {ArtifactState.LOCAL_AVAILABLE, ArtifactState.RETIRED}:
        raise ApplicationCodedValidationError(
            "Artifact lifecycle is not eligible for local materialization",
            code="DEPENDENCY_UNRESOLVED",
        )
    if requirement.artifact_type != artifact.artifact_type:
        raise ApplicationCodedValidationError(
            "Artifact type does not satisfy the consumer requirement",
            code="DEPENDENCY_TYPE_MISMATCH",
        )
    if requirement.compatibility_mode is not CompatibilityMode.EXACT:
        raise ApplicationCodedValidationError(
            "Only reviewed exact Artifact schema compatibility is executable in B6",
            code="DEPENDENCY_TYPE_MISMATCH",
        )
    if requirement.schema_constraint != artifact.artifact_schema_version:
        raise ApplicationCodedValidationError(
            "Artifact schema does not satisfy the exact consumer requirement",
            code="DEPENDENCY_TYPE_MISMATCH",
        )
    if requirement.materialization_mode is not MaterializationMode.VERIFIED_COPY:
        raise ApplicationCodedValidationError(
            "Dependency is not approved for local verified-copy materialization",
            code="DEPENDENCY_UNRESOLVED",
        )
    precondition = requirement.content_precondition
    if precondition is None:
        return
    if (
        precondition.get("schema") != PAPER_LIBRARY_NONEMPTY_PRECONDITION_SCHEMA
        or precondition.get("qualification_schema")
        != PAPER_LIBRARY_QUALIFICATION_SCHEMA
        or precondition.get("minimum_selected_count") != 1
    ):
        raise ApplicationCodedValidationError(
            "Artifact content precondition is unsupported",
            code="DEPENDENCY_TYPE_MISMATCH",
        )
    if (
        qualification is None
        or qualification.artifact_id != artifact.artifact_id
        or qualification.artifact_checksum != artifact.content_checksum
        or qualification.schema_identity != PAPER_LIBRARY_QUALIFICATION_SCHEMA
        or qualification.payload.get("selected_count", 0) < 1
    ):
        raise ApplicationCodedValidationError(
            "Idea Discovery requires a paper library with at least one selected paper",
            code="ARTIFACT_CONTENT_PRECONDITION_UNSATISFIED",
        )


def is_compatible_artifact(requirement, artifact, qualification=None) -> bool:
    try:
        _require_compatible(requirement, artifact, qualification)
    except ApplicationCodedValidationError:
        return False
    return True


def exact_binding_set_checksum(bindings) -> str:
    return canonical_hash([
        {
            "requirement_key": item.requirement_key,
            "binding_id": item.binding_id,
            "artifact_id": item.artifact_id,
            "expected_checksum": item.expected_checksum,
        }
        for item in sorted(
            (
                item for item in bindings
                if item.state is DependencyBindingState.ACTIVE
            ),
            key=lambda item: (item.requirement_key, item.binding_id),
        )
    ])


def evaluate_input_setup(*, requirements, bindings, decisions) -> dict[str, Any]:
    active = {
        item.requirement_key: item
        for item in bindings
        if item.state is DependencyBindingState.ACTIVE
    }
    missing_required = tuple(sorted(
        item.requirement_key
        for item in requirements
        if item.required and item.requirement_key not in active
    ))
    omitted_optional = tuple(sorted(
        item.requirement_key
        for item in requirements
        if not item.required and item.requirement_key not in active
    ))
    binding_set_checksum = exact_binding_set_checksum(bindings)
    current = max(
        (
            item
            for item in decisions
            if valid_input_setup_decision(item)
            and item.binding_set_checksum == binding_set_checksum
            and item.omitted_optional_requirement_keys == omitted_optional
            and item.decision == "CONTINUE_WITHOUT_OPTIONAL_EVIDENCE"
        ),
        key=lambda item: (item.decided_at, item.decision_id),
        default=None,
    )
    return {
        "binding_set_checksum": binding_set_checksum,
        "missing_required_requirement_keys": missing_required,
        "omitted_optional_requirement_keys": omitted_optional,
        "decision_required": not missing_required and bool(omitted_optional),
        "current_decision": current,
    }


def valid_input_setup_decision(decision: WorkflowInputSetupDecision) -> bool:
    payload = {
        "schema_version": "reagent.workflow-input-setup-decision/v0.1",
        "project_id": decision.project_id,
        "consumer_workflow_instance_id": decision.consumer_workflow_instance_id,
        "consumer_workflow_definition_id": decision.consumer_workflow_definition_id,
        "consumer_workflow_version": decision.consumer_workflow_version,
        "binding_set_checksum": decision.binding_set_checksum,
        "omitted_optional_requirement_keys": list(
            decision.omitted_optional_requirement_keys
        ),
        "decision": decision.decision,
        "idempotency_key": decision.idempotency_key,
        "decided_at": _utc_text(decision.decided_at),
    }
    expected_id = "input-decision-" + uuid5(
        UUID(decision.idempotency_key), canonical_json(payload)
    ).hex
    return (
        decision.decision_id == expected_id
        and decision.decision_checksum == canonical_hash(payload)
    )


def input_setup_decision_document(
    decision: WorkflowInputSetupDecision,
) -> dict[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "project_id": decision.project_id,
        "consumer_workflow_instance_id": decision.consumer_workflow_instance_id,
        "consumer_workflow_definition_id": decision.consumer_workflow_definition_id,
        "consumer_workflow_version": decision.consumer_workflow_version,
        "binding_set_checksum": decision.binding_set_checksum,
        "omitted_optional_requirement_keys": list(
            decision.omitted_optional_requirement_keys
        ),
        "decision": decision.decision,
        "idempotency_key": decision.idempotency_key,
        "decision_checksum": decision.decision_checksum,
        "decided_at": _utc_text(decision.decided_at),
    }


def input_setup_state_document(consumer, state: dict[str, Any]) -> dict[str, Any]:
    current = state["current_decision"]
    return {
        "schema_version": "reagent.workflow-input-setup-state/v0.1",
        "project_id": consumer.project_id,
        "consumer_workflow_instance_id": consumer.workflow_instance_id,
        "binding_set_checksum": state["binding_set_checksum"],
        "missing_required_requirement_keys": list(
            state["missing_required_requirement_keys"]
        ),
        "omitted_optional_requirement_keys": list(
            state["omitted_optional_requirement_keys"]
        ),
        "decision_required": state["decision_required"],
        "current_decision": (
            None if current is None else input_setup_decision_document(current)
        ),
    }


def _output_contracts(compatibility) -> dict[str, dict[str, str]]:
    raw = compatibility.get("artifact_outputs") if hasattr(compatibility, "get") else None
    if not isinstance(raw, (list, tuple)):
        return {}
    result: dict[str, dict[str, str]] = {}
    common = {
        "artifact_type",
        "artifact_schema_version",
        "media_type",
        "progress_artifact_kind",
    }
    for item in raw:
        fields = set(item) if hasattr(item, "items") else set()
        exact = fields == common | {"relative_path"}
        addressed = fields == common | {
            "relative_path_prefix",
            "content_addressed_filename",
        }
        if not exact and not addressed:
            raise ApplicationCodedValidationError(
                "Producer Capsule Artifact output contract is invalid",
                code="ARTIFACT_CONTRACT_VIOLATION",
            )
        value = {str(key): str(content) for key, content in item.items()}
        if value["artifact_type"] in result:
            raise ApplicationCodedValidationError(
                "Producer Capsule declares a duplicate Artifact type",
                code="ARTIFACT_CONTRACT_VIOLATION",
            )
        result[value["artifact_type"]] = value
    return result


def _matches_output_contract(
    *, contract: dict[str, str], declaration: ArtifactDeclaration, progress_artifact_kind: str
) -> bool:
    if (
        contract.get("artifact_schema_version") != declaration.artifact_schema_version
        or contract.get("media_type") != declaration.media_type
        or contract.get("progress_artifact_kind") != progress_artifact_kind
    ):
        return False
    if "relative_path" in contract:
        return contract["relative_path"] == declaration.relative_path
    prefix = contract.get("relative_path_prefix")
    filename = contract.get("content_addressed_filename")
    if prefix is None or filename != "sha256-<content-sha256>.json":
        return False
    expected = prefix.rstrip("/") + "/sha256-" + declaration.content_checksum[7:] + ".json"
    return declaration.relative_path == expected


def _artifact_document(
    item: ArtifactReference,
    producer_core_capability_maturity: str,
    presentation: ArtifactPresentation | None = None,
    qualification: ArtifactContentQualification | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "reagent.artifact-reference/v0.1",
        "artifact_id": item.artifact_id,
        "project_id": item.project_id,
        "producer_workflow_instance_id": item.producer_workflow_instance_id,
        "producer_progress_receipt_id": item.producer_progress_receipt_id,
        "producer_progress_report_id": item.producer_progress_report_id,
        "producer_execution_round": item.producer_execution_round,
        "producer_capsule_id": item.producer_capsule_id,
        "producer_capsule_version": item.producer_capsule_version,
        "producer_core_capability_maturity": producer_core_capability_maturity,
        "artifact_type": item.artifact_type,
        "artifact_schema_version": item.artifact_schema_version,
        "media_type": item.media_type,
        "state": item.state.value,
        "relative_path": item.relative_path,
        "content_checksum": item.content_checksum,
        "size_bytes": item.size_bytes,
        "cloud_metadata_available": item.cloud_metadata_available,
        "produced_at": _utc_text(item.produced_at),
        "retired_at": None if item.retired_at is None else _utc_text(item.retired_at),
        "created_at": _utc_text(item.created_at),
        "updated_at": _utc_text(item.updated_at),
        "presentation": (
            None if presentation is None else _presentation_document(presentation)
        ),
        "content_qualification": (
            None if qualification is None else _qualification_document(qualification)
        ),
    }


def _presentation_document(presentation: ArtifactPresentation) -> dict[str, Any]:
    return {
        "schema_identity": presentation.schema_identity,
        "artifact_id": presentation.artifact_id,
        "artifact_checksum": presentation.artifact_checksum,
        "presentation_checksum": presentation.presentation_checksum,
        "payload": to_json_value(presentation.payload),
        "reported_at": _utc_text(presentation.reported_at),
    }


def _qualification_document(
    qualification: ArtifactContentQualification,
) -> dict[str, Any]:
    return {
        "schema_identity": qualification.schema_identity,
        "artifact_id": qualification.artifact_id,
        "artifact_checksum": qualification.artifact_checksum,
        "qualification_checksum": qualification.qualification_checksum,
        "payload": to_json_value(qualification.payload),
        "reported_at": _utc_text(qualification.reported_at),
    }


def _validate_content_qualification(
    artifact: ArtifactReference, value: dict[str, Any]
) -> dict[str, Any]:
    fields = {
        "schema", "artifact_id", "artifact_checksum", "selected_count",
        "qualification_checksum",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ApplicationCodedValidationError(
            "Artifact content qualification fields mismatch",
            code="ARTIFACT_QUALIFICATION_INVALID",
        )
    payload = dict(value)
    checksum = payload.pop("qualification_checksum")
    selected_count = payload.get("selected_count")
    if (
        payload.get("schema") != PAPER_LIBRARY_QUALIFICATION_SCHEMA
        or artifact.artifact_type != "selected-paper-library/v1"
        or artifact.artifact_schema_version != "selected-paper-library/v1"
        or payload.get("artifact_id") != artifact.artifact_id
        or payload.get("artifact_checksum") != artifact.content_checksum
        or isinstance(selected_count, bool)
        or not isinstance(selected_count, int)
        or not 0 <= selected_count <= 10_000
        or checksum != canonical_hash(payload)
    ):
        raise ApplicationCodedValidationError(
            "Artifact content qualification is invalid",
            code="ARTIFACT_QUALIFICATION_INVALID",
        )
    return value


_PRESENTATION_SECRET = re.compile(
    r"(?i)(?:api[_ -]?key|access[_ -]?token|password|secret|bearer)\s*[:=]"
)
_PRESENTATION_LOG = re.compile(r"(?i)\b(?:stdout|stderr)\s*:")
_PRESENTATION_LOCAL_PATH = re.compile(
    r"(?:^|[\s\"'])(?:/[A-Za-z0-9._-]+){2,}(?:[\s\"',.;:]|$)"
)


def _validate_generic_experiment_presentation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schema", "artifact_id", "artifact_checksum", "blocks",
        "presentation_checksum",
    }:
        raise ApplicationCodedValidationError(
            "Experiment presentation shape is invalid",
            code="ARTIFACT_PRESENTATION_INVALID",
        )
    blocks = value.get("blocks")
    if not isinstance(blocks, list):
        raise ApplicationCodedValidationError(
            "Experiment presentation blocks are invalid",
            code="ARTIFACT_PRESENTATION_INVALID",
        )
    try:
        candidate = GenericExperimentPresentation(
            artifact_id=value["artifact_id"],
            artifact_checksum=value["artifact_checksum"],
            blocks=tuple(
                PresentationBlock(
                    kind=PresentationKind(item["kind"]),
                    label=item["label"],
                    value=item["value"],
                )
                for item in blocks
                if isinstance(item, dict) and set(item) == {"kind", "label", "value"}
            ),
        )
    except (KeyError, TypeError, ValueError, GenericExperimentArtifactError) as error:
        raise ApplicationCodedValidationError(
            "Experiment presentation content is invalid",
            code="ARTIFACT_PRESENTATION_INVALID",
        ) from error
    if len(candidate.blocks) != len(blocks):
        raise ApplicationCodedValidationError(
            "Experiment presentation block shape is invalid",
            code="ARTIFACT_PRESENTATION_INVALID",
        )
    normalized = to_json_value(candidate)
    if value["schema"] != normalized["schema"] or value["presentation_checksum"] != normalized["presentation_checksum"]:
        raise ApplicationCodedValidationError(
            "Experiment presentation checksum or schema is invalid",
            code="ARTIFACT_PRESENTATION_INVALID",
        )
    serialized = canonical_json(normalized)
    if len(serialized.encode("utf-8")) > 65_536:
        raise ApplicationCodedValidationError(
            "Experiment presentation exceeds its size bound",
            code="ARTIFACT_PRESENTATION_INVALID",
        )
    if (
        _PRESENTATION_SECRET.search(serialized)
        or _PRESENTATION_LOG.search(serialized)
        or _PRESENTATION_LOCAL_PATH.search(serialized)
    ):
        raise ApplicationCodedValidationError(
            "Experiment presentation contains local paths, credentials, or raw logs",
            code="ARTIFACT_PRESENTATION_INVALID",
        )
    return normalized


_PRESENTATION_VALIDATORS = {
    (
        "experiment-record/v4",
        "reagent.artifact-presentation.experiment-record/v0.2",
    ): _validate_generic_experiment_presentation,
    (
        "experiment-record/v5",
        "reagent.artifact-presentation.experiment-record/v0.2",
    ): _validate_generic_experiment_presentation,
    (
        "selected-paper-library/v1",
        PAPER_LIBRARY_PRESENTATION_SCHEMA,
    ): validate_paper_library_presentation,
    (
        "selected-research-idea/v1",
        RESEARCH_IDEA_PRESENTATION_SCHEMA,
    ): validate_research_idea_presentation,
    ("manuscript-draft/v4", MANUSCRIPT_PRESENTATION_SCHEMA): validate_manuscript_presentation,
    ("manuscript-draft/v5", MANUSCRIPT_PRESENTATION_SCHEMA): validate_manuscript_presentation,
    ("review-report/v3", REVIEW_PRESENTATION_SCHEMA): validate_review_presentation,
    ("review-report/v3", REVIEW_PRESENTATION_SCHEMA_V2): validate_review_presentation_v2,
}


def _validate_registered_presentation(*, artifact, value: Any) -> dict[str, Any]:
    """Fail closed unless an exact Artifact/schema pair has a fixed validator."""

    if artifact.artifact_schema_version != artifact.artifact_type:
        raise ApplicationCodedValidationError(
            "Artifact type and schema do not support a presentation companion",
            code="ARTIFACT_PRESENTATION_INVALID",
        )
    schema = value.get("schema") if isinstance(value, dict) else None
    validator = _PRESENTATION_VALIDATORS.get((artifact.artifact_type, schema))
    if validator is None:
        raise ApplicationCodedValidationError(
            "Artifact type and presentation schema are not an accepted pair",
            code="ARTIFACT_PRESENTATION_INVALID",
        )
    try:
        return validator(value)
    except UpstreamPresentationError as error:
        raise ApplicationCodedValidationError(
            "Artifact presentation content is invalid",
            code="ARTIFACT_PRESENTATION_INVALID",
        ) from error


def require_compatible_artifact(requirement, artifact, qualification=None) -> None:
    """Expose the exact binding compatibility guard to product orchestrators."""

    _require_compatible(requirement, artifact, qualification)


def binding_document(binding: ArtifactDependencyBinding) -> dict[str, Any]:
    return {
        "binding_id": binding.binding_id,
        "project_id": binding.project_id,
        "consumer_workflow_instance_id": binding.consumer_workflow_instance_id,
        "consumer_workflow_definition_id": binding.consumer_workflow_definition_id,
        "consumer_workflow_version": binding.consumer_workflow_version,
        "requirement_key": binding.requirement_key,
        "artifact_id": binding.artifact_id,
        "expected_checksum": binding.expected_checksum,
        "state": binding.state.value,
        "idempotency_key": binding.idempotency_key,
        "created_at": binding.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": binding.updated_at.isoformat().replace("+00:00", "Z"),
        "retired_at": None if binding.retired_at is None else binding.retired_at.isoformat().replace("+00:00", "Z"),
    }


def _capsule_path(instance) -> str:
    return (
        f"capsules/{instance.workflow_definition_id}/"
        f"{instance.workflow_instance_id}/{instance.capsule_version}"
    )


def _canonical_uuid(value: str) -> None:
    try:
        if str(UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError) as error:
        raise ApplicationCodedValidationError(
            "idempotency_key must use canonical UUID text", code="INVALID_REQUEST"
        ) from error


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Artifact service clock must be timezone-aware")
    return value.astimezone(timezone.utc)


def _utc_text(value: datetime) -> str:
    return _aware(value).isoformat().replace("+00:00", "Z")
