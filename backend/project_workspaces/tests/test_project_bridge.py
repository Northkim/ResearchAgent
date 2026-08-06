from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.local_projects.service import LocalProjectService
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces.application import ProjectWorkspaceApplicationService


@pytest.mark.parametrize(
    ("repository_name", "method_name"),
    (
        ("workflow_foundation", "add_workflow_instance"),
        ("project_manifests", "add_manifest"),
        ("project_manifests", "add_manifest_entries"),
    ),
)
def test_project_creation_rolls_back_for_each_bridge_failure(
    tmp_path,
    monkeypatch,
    repository_name: str,
    method_name: str,
) -> None:
    database = InMemoryDatabase()
    uow = InMemoryUnitOfWork(database)
    workspace = ProjectWorkspaceApplicationService(
        unit_of_work=uow,
        clock=lambda: datetime(2026, 8, 6, tzinfo=UTC),
    )
    repository = getattr(uow, repository_name)

    def fail(*_args, **_kwargs):
        raise RuntimeError(f"injected {method_name} failure")

    monkeypatch.setattr(repository, method_name, fail)
    local = LocalProjectService(
        repository=uow.local_projects,
        commit_callback=uow.commit,
        rollback_callback=uow.rollback,
        workspace_initializer=workspace.initialize_project,
        package_root=tmp_path / "packages",
        clock=lambda: datetime(2026, 8, 6, tzinfo=UTC),
        project_id_factory=lambda: "project-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    with pytest.raises(RuntimeError, match="injected"):
        local.create(
            name="Atomic bridge",
            research_topic="Public fictional topic",
            selected_workflow="LITERATURE_SEARCH",
        )

    assert database.local_projects == {}
    assert database.projects == {}
    assert database.project_workflow_instances == {}
    assert database.desired_manifests == {}
    assert database.manifest_entries == {}
