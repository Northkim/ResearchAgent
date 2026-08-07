"""Trusted Package-to-Workflow-Instance identity resolution."""

from __future__ import annotations

from backend.application.errors import ApplicationCodedValidationError
from backend.persistence.ports import UnitOfWork
from backend.project_workspaces.legacy import legacy_workflow_instance_id

from .contracts import NormalizedProgressRecord, ProgressReportUploadEnvelope


class ProgressWorkflowIdentityResolver:
    """Resolve only canonical legacy Packages or exact B4 Capsule artifacts."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    def resolve(
        self,
        envelope: ProgressReportUploadEnvelope,
        normalized: NormalizedProgressRecord | None,
        requested_workflow_instance_id: str | None,
    ) -> str:
        project = self._uow.project_manifests.get_project(envelope.project_id)
        local_project = self._uow.local_projects.get(envelope.project_id)
        if project is None or local_project is None:
            raise _identity_error("Progress Project is not registered")

        artifacts = tuple(
            item
            for item in self._uow.workspace_sync.list_capsule_artifacts(
                envelope.project_id
            )
            if item.package_id == envelope.package_id
            and item.package_checksum == envelope.package_checksum
        )
        legacy_id = legacy_workflow_instance_id(envelope.project_id)
        package = local_project.current_package
        legacy_package_matches = (
            package is not None
            and package.package_id == envelope.package_id
            and package.package_checksum == envelope.package_checksum
        )

        if requested_workflow_instance_id is not None:
            instance_id = requested_workflow_instance_id
            artifact_matches = tuple(
                item for item in artifacts if item.workflow_instance_id == instance_id
            )
            if not artifact_matches and not (
                legacy_package_matches and instance_id == legacy_id
            ):
                raise _identity_error(
                    "Progress Package is not bound to the requested Workflow Instance"
                )
        elif len(artifacts) == 1:
            instance_id = artifacts[0].workflow_instance_id
        elif len(artifacts) > 1:
            raise _identity_error("Progress Package identity is ambiguous")
        elif legacy_package_matches:
            instance_id = legacy_id
        else:
            raise _identity_error(
                "Progress upload requires an exact Capsule artifact or supported "
                "legacy Package binding"
            )

        instance = self._uow.workflow_foundation.get_workflow_instance(instance_id)
        if instance is None:
            raise _identity_error("Workflow Instance does not exist")
        if instance.project_id != envelope.project_id:
            raise _identity_error("Workflow Instance belongs to another Project")
        if normalized is not None and (
            normalized.project_id != envelope.project_id
            or normalized.workflow_id != instance.workflow_definition_id
            or normalized.workflow_version != instance.workflow_version
        ):
            raise _identity_error(
                "Progress Report Workflow identity does not match the Workflow Instance"
            )
        return instance.workflow_instance_id


def _identity_error(message: str) -> ApplicationCodedValidationError:
    return ApplicationCodedValidationError(
        message,
        code="PROGRESS_WORKFLOW_IDENTITY_MISMATCH",
    )
