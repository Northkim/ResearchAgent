"""PostgreSQL persistence and reload tests for the local V0.1 product."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, text

from backend.database import SQLAlchemyUnitOfWork
from backend.local_projects import LITERATURE_SEARCH_WORKFLOW
from backend.local_projects.service import LocalProjectService


def _service(
    factory: Callable[[], SQLAlchemyUnitOfWork],
    package_root: Path,
) -> tuple[LocalProjectService, SQLAlchemyUnitOfWork]:
    uow = factory()
    return LocalProjectService(
        repository=uow.local_projects,
        commit_callback=uow.commit,
        package_root=package_root,
        clock=lambda: datetime(2026, 8, 5, 12, 0, tzinfo=UTC),
        project_id_factory=lambda: "project-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    ), uow


def test_local_project_and_package_reload_from_postgresql(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
    tmp_path: Path,
) -> None:
    writer, writer_uow = _service(sql_uow_factory, tmp_path / "packages")
    project = writer.create(
        name="Fictional PostgreSQL project",
        research_topic="A fictional public topic for PostgreSQL reload",
        selected_workflow=LITERATURE_SEARCH_WORKFLOW,
    )
    packaged = writer.generate_package(project.project_id)
    writer_uow.close()

    reader, reader_uow = _service(sql_uow_factory, tmp_path / "packages")
    reloaded = reader.get(project.project_id)
    assert reloaded == packaged
    assert reader.list_projects() == (packaged,)
    assert reloaded.current_package is not None
    archive, filename = reader.read_package_archive(
        project.project_id,
        reloaded.current_package.package_id,
    )
    assert archive.startswith(b"PK")
    assert filename.endswith(".zip")
    reader_uow.close()


def test_local_project_actions_create_no_hosted_state(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
    postgres_engine: Engine,
    tmp_path: Path,
) -> None:
    service, uow = _service(sql_uow_factory, tmp_path / "packages")
    project = service.create(
        name="Boundary canary",
        research_topic="A fictional public boundary-canary topic",
        selected_workflow=LITERATURE_SEARCH_WORKFLOW,
    )
    service.generate_package(project.project_id)
    uow.close()
    with postgres_engine.connect() as connection:
        for table in (
            "workflow_runs",
            "workflow_step_runs",
            "agent_sessions",
            "execution_events",
            "provider_operations",
        ):
            assert connection.scalar(text(f'SELECT count(*) FROM "{table}"')) == 0
        assert connection.scalar(text("SELECT count(*) FROM local_projects")) == 1
