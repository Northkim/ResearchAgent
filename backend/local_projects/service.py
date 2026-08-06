"""Local project and Package product use cases without research execution."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from backend.application.errors import (
    ApplicationNotFoundError,
    ApplicationUnavailableError,
    ApplicationValidationError,
)
from backend.workflow_packages import build_literature_search_package
from backend.workflow_packages.serialization import canonical_hash
from backend.workflow_packages.template import WORKFLOW_ID, WORKFLOW_VERSION, workflow_document

from .contracts import (
    LITERATURE_SEARCH_WORKFLOW,
    LocalPackageMetadata,
    LocalProject,
)
from .ports import LocalProjectRepository


class LocalProjectService:
    """Manage cloud project metadata and deterministic local Package delivery."""

    def __init__(
        self,
        *,
        repository: LocalProjectRepository,
        commit_callback: Callable[[], None],
        package_root: str | Path,
        clock: Callable[[], datetime] | None = None,
        project_id_factory: Callable[[], str] | None = None,
        workspace_initializer: Callable[[LocalProject], None] | None = None,
        rollback_callback: Callable[[], None] | None = None,
    ) -> None:
        self._repository = repository
        self._commit = commit_callback
        self._package_root = Path(package_root)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._project_id_factory = project_id_factory or (
            lambda: f"project-{uuid.uuid4().hex}"
        )
        self._workspace_initializer = workspace_initializer
        self._rollback = rollback_callback

    def create(
        self,
        *,
        name: str,
        research_topic: str,
        selected_workflow: str,
    ) -> LocalProject:
        timestamp = self._timestamp(self._clock())
        try:
            project = LocalProject(
                project_id=self._project_id_factory(),
                name=name,
                research_topic=research_topic,
                selected_workflow=selected_workflow,
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValueError as error:
            raise ApplicationValidationError(str(error)) from error
        self._repository.add(project)
        try:
            if self._workspace_initializer is not None:
                self._workspace_initializer(project)
            self._commit()
        except Exception:
            if self._rollback is not None:
                self._rollback()
            raise
        return project

    def list_projects(self) -> tuple[LocalProject, ...]:
        return self._repository.list_all()

    def get(self, project_id: str) -> LocalProject:
        project = self._repository.get(project_id)
        if project is None:
            raise ApplicationNotFoundError("Local project not found")
        return project

    def generate_package(self, project_id: str) -> LocalProject:
        project = self.get(project_id)
        if project.selected_workflow != LITERATURE_SEARCH_WORKFLOW:
            raise ApplicationValidationError("Project Workflow is not supported")
        storage_root = self._resolved_storage_root()
        # Keep older immutable Package generations readable while allowing the
        # current template identity to produce a new deterministic artifact.
        output = storage_root / project.project_id / "literature-search-v0.5"
        try:
            built = build_literature_search_package(
                project_id=project.project_id,
                project_name=project.name,
                research_topic=project.research_topic,
                output_root=output,
                allow_absolute_output_root=True,
            )
        except (FileExistsError, OSError, ValueError) as error:
            raise ApplicationUnavailableError(
                "Local Workflow Package generation failed closed"
            ) from error
        if not built.validation.valid or not built.archive_validation.valid:
            raise ApplicationUnavailableError(
                "Local Workflow Package validation failed closed"
            )
        archive_key = built.archive_path.relative_to(storage_root).as_posix()
        generated_at = self._timestamp(self._clock())
        package = LocalPackageMetadata(
            package_id=built.package_id,
            package_schema_version=built.package_schema_version,
            package_checksum=built.package_checksum,
            manifest_checksum=built.manifest_checksum,
            zip_checksum=built.zip_checksum,
            workflow_id=WORKFLOW_ID,
            workflow_version=WORKFLOW_VERSION,
            workflow_checksum=canonical_hash(workflow_document()),
            archive_storage_key=archive_key,
            file_count=built.file_count,
            package_size_bytes=built.package_size_bytes,
            generated_at=generated_at,
        )
        updated = project.with_package(package, updated_at=generated_at)
        self._repository.save(updated)
        self._commit()
        return updated

    def latest_package(self, project_id: str) -> LocalPackageMetadata:
        project = self.get(project_id)
        if project.current_package is None:
            raise ApplicationNotFoundError("Workflow Package has not been generated")
        return project.current_package

    def read_package_archive(self, project_id: str, package_id: str) -> tuple[bytes, str]:
        package = self.latest_package(project_id)
        if package.package_id != package_id:
            raise ApplicationNotFoundError("Workflow Package not found")
        storage_root = self._resolved_storage_root()
        archive = (storage_root / package.archive_storage_key).resolve()
        project_root = (storage_root / project_id).resolve()
        try:
            archive.relative_to(project_root)
        except ValueError:
            raise ApplicationUnavailableError("Workflow Package storage identity is invalid")
        if not archive.is_file() or archive.is_symlink():
            raise ApplicationUnavailableError("Workflow Package archive is unavailable")
        content = archive.read_bytes()
        from backend.workflow_packages.serialization import sha256_bytes

        if sha256_bytes(content) != package.zip_checksum:
            raise ApplicationUnavailableError("Workflow Package archive failed integrity verification")
        return content, f"{package.package_id}.zip"

    def _resolved_storage_root(self) -> Path:
        root = self._package_root.expanduser().resolve()
        if root.is_symlink():
            raise ApplicationUnavailableError("Local Package root must not be a symbolic link")
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _timestamp(value: datetime) -> str:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("local product clock must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
