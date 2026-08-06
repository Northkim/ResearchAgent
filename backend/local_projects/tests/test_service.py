from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.application.errors import ApplicationValidationError
from backend.local_projects import LITERATURE_SEARCH_WORKFLOW
from backend.local_projects.service import LocalProjectService
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.workflow_packages import validate_package


def _service(tmp_path: Path, database: InMemoryDatabase | None = None):
    state = database or InMemoryDatabase()
    uow = InMemoryUnitOfWork(state)
    service = LocalProjectService(
        repository=uow.local_projects,
        commit_callback=uow.commit,
        package_root=tmp_path / "packages",
        clock=lambda: datetime(2026, 8, 5, 10, 0, tzinfo=UTC),
        project_id_factory=lambda: "project-0123456789abcdef0123456789abcdef",
    )
    return service, state


def test_create_list_and_reload_local_project(tmp_path: Path) -> None:
    service, database = _service(tmp_path)
    created = service.create(
        name="Fictional continuity review",
        research_topic="A public fictional topic about portable task state",
        selected_workflow=LITERATURE_SEARCH_WORKFLOW,
    )
    assert service.list_projects() == (created,)

    reloaded, _ = _service(tmp_path, database)
    assert reloaded.get(created.project_id) == created


def test_only_literature_search_is_accepted(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    with pytest.raises(ApplicationValidationError, match="only selectable"):
        service.create(
            name="Unsupported project",
            research_topic="A fictional topic",
            selected_workflow="SYSTEMATIC_REVIEW",
        )


def test_package_generation_binds_topic_and_is_deterministic(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    project = service.create(
        name="Fictional package project",
        research_topic="A fictional public topic about local research folders",
        selected_workflow=LITERATURE_SEARCH_WORKFLOW,
    )
    first = service.generate_package(project.project_id)
    second = service.generate_package(project.project_id)
    assert first.current_package == second.current_package
    assert first.current_package is not None

    package_root = (
        tmp_path
        / "packages"
        / project.project_id
        / "literature-search-v0.5"
        / "package"
    )
    assert validate_package(package_root, pristine=True).valid
    import json

    request = json.loads((package_root / "inputs/research_request.json").read_text())
    project_input = json.loads((package_root / "inputs/project.json").read_text())
    assert request["topic"] == project.research_topic
    assert project_input == {
        "schema_version": "local-project-input/v0.1",
        "project_id": project.project_id,
        "project_name": project.name,
        "selected_workflow": LITERATURE_SEARCH_WORKFLOW,
    }


def test_missing_or_tampered_archive_fails_closed(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    project = service.create(
        name="Archive integrity",
        research_topic="A fictional public archive-integrity topic",
        selected_workflow=LITERATURE_SEARCH_WORKFLOW,
    )
    generated = service.generate_package(project.project_id)
    assert generated.current_package is not None
    archive = (
        tmp_path
        / "packages"
        / generated.current_package.archive_storage_key
    )
    archive.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="integrity"):
        service.read_package_archive(
            project.project_id,
            generated.current_package.package_id,
        )
