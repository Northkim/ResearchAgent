from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from backend.local_projects.service import LocalProjectService
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.resource_references.service import ResourceReferenceService


def test_postgresql_resource_reference_and_exact_binding_reload(
    sql_uow_factory, tmp_path,
) -> None:
    uow = sql_uow_factory()
    workspace = ProjectWorkspaceApplicationService(
        unit_of_work=uow, clock=lambda: datetime(2026, 8, 9, tzinfo=UTC)
    )
    project = LocalProjectService(
        repository=uow.local_projects,
        commit_callback=uow.commit,
        rollback_callback=uow.rollback,
        project_setup_initializer=workspace.initialize_project_setup,
        package_root=tmp_path / "packages",
        clock=lambda: datetime(2026, 8, 9, tzinfo=UTC),
        project_id_factory=lambda: "project-" + "e" * 32,
    ).create(
        name="F1E PostgreSQL",
        research_topic="Synthetic Resource persistence",
        selected_workflow="LITERATURE_SEARCH",
        workflow_setup="full-research",
    )
    experiment = next(
        item for item in workspace.list_instances(project.project_id)
        if item.workflow_definition_id == "reproduction-experiment-local-experimental"
    )
    service = ResourceReferenceService(
        unit_of_work=uow, clock=lambda: datetime(2026, 8, 9, 1, tzinfo=UTC)
    )
    resource = service.create_resource(
        project_id=project.project_id,
        resource_kind="DATASET",
        provider="LOCAL_TEST",
        locator="fixture/postgresql",
        exact_revision="fixture-revision-postgresql",
        expected_content_checksum="sha256:" + "f" * 64,
        display_name="PostgreSQL fixture",
        metadata={"qualification": True},
    )
    binding = service.bind_resource(
        project_id=project.project_id,
        workflow_instance_id=experiment.workflow_instance_id,
        requirement_key="dataset",
        resource_id=resource.resource_id,
        idempotency_key=str(uuid4()),
    )
    uow.close()

    reloaded = sql_uow_factory()
    assert reloaded.resource_references.get_resource(resource.resource_id) == resource
    assert reloaded.resource_references.get_binding(binding.binding_id) == binding
    actual_requirements = {
        (
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
            requirement.resource_kind.value,
            requirement.cardinality_min,
            requirement.cardinality_max,
            requirement.required,
            frozenset(provider.value for provider in requirement.allowed_providers),
        )
        for requirement in reloaded.resource_references.list_requirements()
    }
    expected_requirements = {
        (
            "reproduction-experiment-local-experimental",
            "0.3.0",
            "source_repository",
            "SOURCE_REPOSITORY",
            0,
            1,
            False,
            frozenset({"GITHUB", "LOCAL_TEST"}),
        ),
        (
            "reproduction-experiment-local-experimental",
            "0.3.0",
            "dataset",
            "DATASET",
            0,
            1,
            False,
            frozenset({"HUGGING_FACE", "LOCAL_TEST"}),
        ),
        (
            "reproduction-experiment-local-experimental",
            "0.3.0",
            "model",
            "MODEL",
            0,
            1,
            False,
            frozenset({"HUGGING_FACE", "LOCAL_TEST"}),
        ),
        (
            "reproduction-experiment-local-experimental",
            "0.3.0",
            "checkpoint",
            "CHECKPOINT",
            0,
            1,
            False,
            frozenset({"HUGGING_FACE", "LOCAL_TEST"}),
        ),
        (
            "reproduction-experiment-local-experimental",
            "0.4.0",
            "source_repository",
            "SOURCE_REPOSITORY",
            1,
            1,
            True,
            frozenset({"GITHUB"}),
        ),
    }
    assert actual_requirements == expected_requirements
    reloaded.close()
