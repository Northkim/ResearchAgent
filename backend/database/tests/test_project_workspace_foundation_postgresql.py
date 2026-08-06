from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from backend.local_projects import LocalPackageMetadata, LocalProject
from backend.project_workspaces import (
    LITERATURE_SEARCH_CAPSULE_ID,
    LITERATURE_SEARCH_DEFINITION_ID,
    LITERATURE_SEARCH_STABLE_KEY,
    ProjectWorkflowInstance,
    WorkflowFoundationConflictError,
    WorkflowInstanceDesiredState,
    legacy_workflow_instance_id,
    reconcile_legacy_workflow_foundation,
)

NOW = datetime(2026, 8, 6, tzinfo=timezone.utc)


def _package(package_id: str) -> LocalPackageMetadata:
    return LocalPackageMetadata(
        package_id=package_id,
        package_schema_version="workflow-package/v0.1",
        package_checksum="sha256:" + "1" * 64,
        manifest_checksum="sha256:" + "2" * 64,
        zip_checksum="sha256:" + "3" * 64,
        workflow_id="literature-search-local-experimental",
        workflow_version="0.3.0",
        workflow_checksum="sha256:efd338d84b33665da25118c7dce6927f62b231ff3bc73527f4132c7bcb410e7f",
        archive_storage_key=f"local-package-archives/{package_id}.zip",
        file_count=10,
        package_size_bytes=1000,
        generated_at="2026-08-06T01:00:00Z",
    )


def _project(project_id: str, *, package=None) -> LocalProject:
    return LocalProject(
        project_id=project_id,
        name="Unicode 项目",
        research_topic="Topic α",
        selected_workflow="LITERATURE_SEARCH",
        created_at="2026-08-06T00:00:00Z",
        updated_at="2026-08-06T01:00:00Z",
        current_package=package,
    )


def test_seed_lookup_persistence_and_reload(sql_uow_factory) -> None:
    project = _project("project-11111111111111111111111111111111")
    with sql_uow_factory() as uow:
        uow.local_projects.add(project)
        reconcile_legacy_workflow_foundation(uow, now=NOW)
        assert uow.workflow_foundation.get_definition("missing") is None
        assert uow.workflow_foundation.get_definition_by_stable_key("missing") is None
        uow.commit()

    with sql_uow_factory() as uow:
        definition = uow.workflow_foundation.get_definition(LITERATURE_SEARCH_DEFINITION_ID)
        assert definition is not None
        assert definition.allows_multiple_instances is True
        assert uow.workflow_foundation.get_definition_by_stable_key(
            LITERATURE_SEARCH_STABLE_KEY
        ) == definition
        assert len(uow.workflow_foundation.list_definitions()) == 1
        version = uow.workflow_foundation.get_definition_version(
            LITERATURE_SEARCH_DEFINITION_ID, "0.3.0"
        )
        assert version is not None and version.contract_checksum.startswith("sha256:")
        capsule = uow.workflow_foundation.get_capsule_version(
            LITERATURE_SEARCH_CAPSULE_ID, "0.5.0"
        )
        assert capsule is not None
        assert capsule.compatibility["trust_classification"] == "TRUSTED_BUILT_IN_UNSIGNED"
        instances = uow.workflow_foundation.list_workflow_instances(project.project_id)
        assert [item.workflow_instance_id for item in instances] == [
            legacy_workflow_instance_id(project.project_id)
        ]
        assert uow.workflow_foundation.get_workflow_instance("wfi-" + "0" * 32) is None
        assert uow.workflow_foundation.get_workflow_instance(
            instances[0].workflow_instance_id
        ) == instances[0]
        for table in (
            "workflow_runs",
            "workflow_step_runs",
            "artifacts",
            "uploaded_progress_reports",
            "proxy_capability_tokens",
        ):
            assert uow.session.execute(
                text(f'SELECT count(*) FROM "{table}"')
            ).scalar_one() == 0


def test_repeated_backfill_is_idempotent_and_package_independent(sql_uow_factory) -> None:
    project = _project(
        "project-22222222222222222222222222222222",
        package=_package("literature-search-project-22222222222222222222222222222222-v0.5"),
    )
    with sql_uow_factory() as uow:
        uow.local_projects.add(project)
        reconcile_legacy_workflow_foundation(uow, now=NOW)
        reconcile_legacy_workflow_foundation(uow, now=NOW)
        uow.commit()
    with sql_uow_factory() as uow:
        instances = uow.workflow_foundation.list_workflow_instances(project.project_id)
        assert len(instances) == 1
        assert instances[0].capsule_id == LITERATURE_SEARCH_CAPSULE_ID
        original_identity = instances[0].workflow_instance_id
        changed = project.with_package(
            _package("literature-search-project-22222222222222222222222222222222-v0.5-r2"),
            updated_at="2026-08-06T02:00:00Z",
        )
        uow.local_projects.save(changed)
        reconcile_legacy_workflow_foundation(uow, now=NOW)
        uow.commit()
    with sql_uow_factory() as uow:
        instance = uow.workflow_foundation.list_workflow_instances(project.project_id)[0]
        assert instance.workflow_instance_id == original_identity
        assert instance.legacy_package_id == project.current_package.package_id


def test_multiple_same_definition_instances_are_supported(sql_uow_factory) -> None:
    project = _project("project-33333333333333333333333333333333")
    with sql_uow_factory() as uow:
        uow.local_projects.add(project)
        reconcile_legacy_workflow_foundation(uow, now=NOW)
        second = ProjectWorkflowInstance(
            workflow_instance_id="wfi-44444444444444444444444444444444",
            project_id=project.project_id,
            workflow_definition_id=LITERATURE_SEARCH_DEFINITION_ID,
            workflow_version="0.3.0",
            capsule_id=LITERATURE_SEARCH_CAPSULE_ID,
            capsule_version="0.5.0",
            desired_state=WorkflowInstanceDesiredState.ACTIVE,
            display_name="Literature Search 2",
            created_manifest_revision=1,
            retired_manifest_revision=None,
            legacy_package_id=None,
            created_at=NOW,
            updated_at=NOW,
        )
        uow.workflow_foundation.add_workflow_instance(second)
        uow.commit()
    with sql_uow_factory() as uow:
        assert len(uow.workflow_foundation.list_workflow_instances(project.project_id)) == 2


def test_immutable_version_and_capsule_conflicts_fail_closed(sql_uow_factory) -> None:
    with sql_uow_factory() as uow:
        reconcile_legacy_workflow_foundation(uow, now=NOW)
        version = uow.workflow_foundation.get_definition_version(
            LITERATURE_SEARCH_DEFINITION_ID, "0.3.0"
        )
        capsule = uow.workflow_foundation.get_capsule_version(
            LITERATURE_SEARCH_CAPSULE_ID, "0.5.0"
        )
        assert version is not None and capsule is not None
        with pytest.raises(WorkflowFoundationConflictError):
            uow.workflow_foundation.add_definition_version(
                replace(version, contract_checksum="sha256:" + "1" * 64)
            )
        with pytest.raises(WorkflowFoundationConflictError):
            uow.workflow_foundation.add_capsule_version(
                replace(capsule, definition_checksum="sha256:" + "2" * 64)
            )


def test_repository_and_uow_rollback_leave_no_partial_state(sql_uow_factory) -> None:
    project = _project("project-55555555555555555555555555555555")
    with sql_uow_factory() as uow:
        uow.local_projects.add(project)
        reconcile_legacy_workflow_foundation(uow, now=NOW)
        uow.rollback()
    with sql_uow_factory() as uow:
        assert uow.local_projects.get(project.project_id) is None
        assert uow.workflow_foundation.get_definition(LITERATURE_SEARCH_DEFINITION_ID) is None
        assert uow.workflow_foundation.list_workflow_instances(project.project_id) == ()
