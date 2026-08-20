"""Local project and Package product use cases without research execution."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from backend.application.errors import (
    ApplicationCodedNotFoundError,
    ApplicationNotFoundError,
    ApplicationUnavailableError,
    ApplicationValidationError,
)
from backend.workflow_packages import build_literature_search_package
from backend.workflow_packages.production_workflows import (
    LITERATURE_SEARCH_CAPSULE_VERSION as PRODUCTION_CAPSULE_VERSION,
    LITERATURE_SEARCH_WORKFLOW_VERSION as PRODUCTION_WORKFLOW_VERSION,
    LITERATURE_SEARCH_V0_5_WORKFLOW_VERSION,
    LITERATURE_SEARCH_V0_7_CAPSULE_VERSION,
    LITERATURE_SEARCH_V0_6_WORKFLOW_VERSION,
    LITERATURE_SEARCH_V0_8_CAPSULE_VERSION,
    build_literature_search_v0_6_package,
    build_literature_search_v0_7_package,
    build_literature_search_v0_8_package,
    literature_search_workflow_document as production_workflow_document,
    literature_search_v0_5_workflow_document,
    literature_search_v0_6_workflow_document,
)
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
        project_setup_initializer: Callable[
            [LocalProject, str, tuple[str, ...]], None
        ] | None = None,
        package_pin_resolver: Callable[[str], tuple[str, str, str] | None]
        | None = None,
        package_artifact_registrar: Callable[
            [LocalProject, str], None
        ] | None = None,
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
        self._project_setup_initializer = project_setup_initializer
        self._package_pin_resolver = package_pin_resolver
        self._package_artifact_registrar = package_artifact_registrar
        self._rollback = rollback_callback

    def create(
        self,
        *,
        name: str,
        research_topic: str,
        selected_workflow: str,
        workflow_setup: str = "literature-only",
        custom_workflow_definition_ids: list[str] | tuple[str, ...] = (),
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
            if self._project_setup_initializer is not None:
                self._project_setup_initializer(
                    project,
                    workflow_setup,
                    tuple(custom_workflow_definition_ids),
                )
            elif self._workspace_initializer is not None:
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
            raise ApplicationCodedNotFoundError(
                "Project not found", code="PROJECT_NOT_FOUND"
            )
        return project

    def generate_package(self, project_id: str) -> LocalProject:
        project = self.get(project_id)
        if project.selected_workflow != LITERATURE_SEARCH_WORKFLOW:
            raise ApplicationValidationError("Project Workflow is not supported")
        storage_root = self._resolved_storage_root()
        pin = (
            self._package_pin_resolver(project.project_id)
            if self._package_pin_resolver is not None
            else None
        )
        production_v0_6 = pin is not None and pin[1:] == (
            PRODUCTION_WORKFLOW_VERSION,
            PRODUCTION_CAPSULE_VERSION,
        )
        production_v0_7 = pin is not None and pin[1:] == (
            LITERATURE_SEARCH_V0_5_WORKFLOW_VERSION,
            LITERATURE_SEARCH_V0_7_CAPSULE_VERSION,
        )
        production_v0_8 = pin is not None and pin[1:] == (
            LITERATURE_SEARCH_V0_6_WORKFLOW_VERSION,
            LITERATURE_SEARCH_V0_8_CAPSULE_VERSION,
        )
        if (
            pin is not None
            and not production_v0_6
            and not production_v0_7
            and not production_v0_8
            and pin[1:] != ("0.3.0", "0.5.0")
        ):
            raise ApplicationValidationError(
                "Project Literature Search pin has no reviewed standalone Package compiler"
            )
        # Keep the accepted 0.5.0 Package path and bytes unchanged. New B7
        # Projects receive a separately pinned, instance-bound 0.6.0 Package.
        output = storage_root / project.project_id / (
            "literature-search-v0.8"
            if production_v0_8
            else "literature-search-v0.7"
            if production_v0_7
            else "literature-search-v0.6"
            if production_v0_6
            else "literature-search-v0.5"
        )
        try:
            if production_v0_8:
                assert pin is not None
                built = build_literature_search_v0_8_package(
                    project_id=project.project_id,
                    project_name=project.name,
                    research_topic=project.research_topic,
                    output_root=output,
                    package_id=(
                        f"literature-search-{project.project_id}-{pin[0]}-v0.8"
                    ),
                )
                workflow_version = LITERATURE_SEARCH_V0_6_WORKFLOW_VERSION
                workflow_checksum = canonical_hash(
                    literature_search_v0_6_workflow_document()
                )
            elif production_v0_7:
                assert pin is not None
                built = build_literature_search_v0_7_package(
                    project_id=project.project_id,
                    project_name=project.name,
                    research_topic=project.research_topic,
                    output_root=output,
                    package_id=(
                        f"literature-search-{project.project_id}-{pin[0]}-v0.7"
                    ),
                )
                workflow_version = LITERATURE_SEARCH_V0_5_WORKFLOW_VERSION
                workflow_checksum = canonical_hash(
                    literature_search_v0_5_workflow_document()
                )
            elif production_v0_6:
                assert pin is not None
                built = build_literature_search_v0_6_package(
                    project_id=project.project_id,
                    project_name=project.name,
                    research_topic=project.research_topic,
                    output_root=output,
                    package_id=(
                        f"literature-search-{project.project_id}-{pin[0]}-v0.6"
                    ),
                )
                workflow_version = PRODUCTION_WORKFLOW_VERSION
                workflow_checksum = canonical_hash(production_workflow_document())
            else:
                built = build_literature_search_package(
                    project_id=project.project_id,
                    project_name=project.name,
                    research_topic=project.research_topic,
                    output_root=output,
                    allow_absolute_output_root=True,
                )
                workflow_version = WORKFLOW_VERSION
                workflow_checksum = canonical_hash(workflow_document())
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
            workflow_version=workflow_version,
            workflow_checksum=workflow_checksum,
            archive_storage_key=archive_key,
            file_count=built.file_count,
            package_size_bytes=built.package_size_bytes,
            generated_at=generated_at,
        )
        updated = project.with_package(package, updated_at=generated_at)
        self._repository.save(updated)
        if pin is not None and self._package_artifact_registrar is not None:
            self._package_artifact_registrar(updated, pin[0])
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
