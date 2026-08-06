from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

from sqlalchemy import Engine, text

from backend.application.errors import ApplicationCodedConflictError
from backend.database import SQLAlchemyUnitOfWork
from backend.local_projects.service import LocalProjectService
from backend.project_workspaces import (
    LITERATURE_SEARCH_CAPSULE_ID,
    LITERATURE_SEARCH_DEFINITION_ID,
)
from backend.project_workspaces.application import ProjectWorkspaceApplicationService


def _create_project(factory, tmp_path) -> str:
    uow = factory()
    workspace = ProjectWorkspaceApplicationService(
        unit_of_work=uow,
        clock=lambda: datetime(2026, 8, 6, 1, tzinfo=UTC),
    )
    service = LocalProjectService(
        repository=uow.local_projects,
        commit_callback=uow.commit,
        rollback_callback=uow.rollback,
        workspace_initializer=workspace.initialize_project,
        package_root=tmp_path / "packages",
        clock=lambda: datetime(2026, 8, 6, tzinfo=UTC),
        project_id_factory=lambda: "project-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    project = service.create(
        name="Concurrent Project",
        research_topic="Public fictional concurrency topic",
        selected_workflow="LITERATURE_SEARCH",
    )
    uow.close()
    return project.project_id


def test_project_bridge_persists_and_postgresql_cas_allows_one_winner(
    sql_uow_factory,
    postgres_engine: Engine,
    tmp_path,
) -> None:
    project_id = _create_project(sql_uow_factory, tmp_path)
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT current_manifest_revision FROM projects WHERE project_id=:id"
        ), {"id": project_id}) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM project_workflow_instances WHERE project_id=:id"
        ), {"id": project_id}) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM project_manifest_entries WHERE project_id=:id"
        ), {"id": project_id}) == 1

    barrier = Barrier(2)

    def mutate(suffix: str) -> str:
        uow = sql_uow_factory()
        service = ProjectWorkspaceApplicationService(
            unit_of_work=uow,
            clock=lambda: datetime(2026, 8, 6, 2, tzinfo=UTC),
            instance_id_factory=lambda: f"wfi-{suffix * 32}",
        )
        barrier.wait()
        try:
            service.create_instance(
                project_id=project_id,
                workflow_definition_id=LITERATURE_SEARCH_DEFINITION_ID,
                workflow_version="0.3.0",
                capsule_id=LITERATURE_SEARCH_CAPSULE_ID,
                capsule_version="0.5.0",
                display_name=None,
                base_revision=1,
            )
            return "success"
        except ApplicationCodedConflictError as error:
            assert error.code == "MANIFEST_REVISION_CONFLICT"
            return "conflict"
        finally:
            uow.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(mutate, ("b", "c")))
    assert sorted(outcomes) == ["conflict", "success"]
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT current_manifest_revision FROM projects WHERE project_id=:id"
        ), {"id": project_id}) == 2
        assert connection.scalar(text(
            "SELECT count(*) FROM project_workflow_instances WHERE project_id=:id"
        ), {"id": project_id}) == 2
        assert connection.scalar(text(
            "SELECT count(*) FROM project_desired_manifests WHERE project_id=:id"
        ), {"id": project_id}) == 2
        assert connection.scalar(text(
            "SELECT count(*) FROM project_manifest_entries WHERE project_id=:id "
            "AND manifest_revision=2"
        ), {"id": project_id}) == 2
