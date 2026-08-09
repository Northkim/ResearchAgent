from __future__ import annotations

from datetime import UTC, datetime
import json

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.local_projects import LocalProject
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces.contracts import (
    SkillDefinition,
    SkillLifecycle,
    SkillReviewStatus,
    SkillSourceClass,
    SkillTrustTier,
    SkillVersion,
)
from backend.project_workspaces.production_workflows import SCAFFOLD_WORKFLOWS
from backend.project_workspaces.service import ensure_production_workflow_foundation
from backend.project_workspaces.skills import PRODUCTION_SKILLS
from backend.project_workspaces.errors import WorkflowFoundationConflictError
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_f1c_project_presets import _Transport


NOW = datetime(2026, 8, 9, tzinfo=UTC)


def _client(tmp_path):
    database = InMemoryDatabase()
    return TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "packages"),
    ))), database


def test_skill_catalog_is_read_only_stable_and_projects_exact_pins(tmp_path) -> None:
    client, _ = _client(tmp_path)
    assert client.post("/projects", json={
        "name": "F1D registry",
        "research_topic": "Synthetic",
        "selected_workflow": "LITERATURE_SEARCH",
    }).status_code == 201
    page = client.get("/skills?offset=0&limit=1")
    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert len(page.json()["items"]) == 1
    all_items = client.get("/skills").json()["items"]
    assert [item["skill_id"] for item in all_items] == sorted(
        asset.skill_id for asset in PRODUCTION_SKILLS
    )
    for item in all_items:
        assert item["trust"] == "BUILT_IN_REVIEWED"
        assert item["current_version"]["version"] == "0.1.0"
        detail = client.get(f"/skills/{item['skill_id']}").json()
        assert len(detail["workflow_usages"]) == 4
        assert {use["workflow_version"] for use in detail["workflow_usages"]} == {"0.2.0", "0.3.0"}
    assert client.post("/skills", json={}).status_code == 405
    writing = client.get("/workflow-definitions/writing-local-experimental").json()
    skills = writing["recommended_version"]["skills"]
    assert [(item["skill_id"], item["version"]) for item in skills] == [
        (asset.skill_id, "0.1.0") for asset in PRODUCTION_SKILLS
    ]


def test_old_scaffold_versions_remain_and_existing_instance_does_not_upgrade() -> None:
    database = InMemoryDatabase()
    uow = InMemoryUnitOfWork(database)
    ensure_production_workflow_foundation(uow, now=NOW)
    service = ProjectWorkspaceApplicationService(unit_of_work=uow, clock=lambda: NOW)
    project = LocalProject(
        project_id="project-" + "1" * 32,
        name="Existing F1B project",
        research_topic="Synthetic",
        selected_workflow="LITERATURE_SEARCH",
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
    )
    versions = uow.workflow_foundation.list_definition_versions(
        "writing-local-experimental"
    )
    assert {item.version for item in versions} == {"0.1.0", "0.2.0"}
    old_capsules = [
        item for item in uow.workflow_foundation.list_capsule_versions(
            "writing-local-experimental"
        ) if item.capsule_version == "0.1.0"
    ]
    assert len(old_capsules) == 1
    service.initialize_new_project(project)
    uow.commit()
    next_uow = InMemoryUnitOfWork(database)
    next_service = ProjectWorkspaceApplicationService(
        unit_of_work=next_uow, clock=lambda: NOW
    )
    existing = next_service.create_instance(
        project_id=project.project_id,
        workflow_definition_id="writing-local-experimental",
        workflow_version="0.1.0",
        capsule_id=old_capsules[0].capsule_id,
        capsule_version="0.1.0",
        display_name="Writing legacy",
        base_revision=1,
    )
    final_uow = InMemoryUnitOfWork(database)
    ensure_production_workflow_foundation(final_uow, now=NOW)
    final_service = ProjectWorkspaceApplicationService(
        unit_of_work=final_uow, clock=lambda: NOW
    )
    unchanged = final_service.get_instance(
        project.project_id, existing.workflow_instance_id
    )
    assert unchanged.workflow_version == "0.1.0"
    assert unchanged.capsule_version == "0.1.0"


def test_full_preset_resolves_skill_backed_scaffold_versions(tmp_path) -> None:
    client, _ = _client(tmp_path)
    created = client.post("/projects", json={
        "name": "F1D full project",
        "research_topic": "Synthetic",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "full-research",
    })
    instances = client.get(
        f"/projects/{created.json()['project_id']}/workflow-instances"
    ).json()["items"]
    by_id = {item["workflow_definition_id"]: item for item in instances}
    for workflow_id in SCAFFOLD_WORKFLOWS:
        expected = (
            "0.3.0"
            if workflow_id == "reproduction-experiment-local-experimental"
            else "0.2.0"
        )
        assert by_id[workflow_id]["workflow_version"] == expected
        assert by_id[workflow_id]["capsule_version"] == expected
        assert [item["skill_id"] for item in by_id[workflow_id]["skills"]] == [
            asset.skill_id for asset in PRODUCTION_SKILLS
        ]
    assert by_id["literature-search-local-experimental"]["skills"] == []
    assert by_id["idea-discovery-local-experimental"]["skills"] == []


def test_skill_version_pins_do_not_float_when_a_new_version_exists() -> None:
    database = InMemoryDatabase()
    uow = InMemoryUnitOfWork(database)
    ensure_production_workflow_foundation(uow, now=NOW)
    asset = PRODUCTION_SKILLS[0]
    newer = SkillVersion(
        skill_id=asset.skill_id,
        skill_version="0.2.0",
        content_checksum="sha256:" + "a" * 64,
        manifest_schema_version="local-skill/v0.1",
        content_manifest={"schema_version": "local-skill/v0.1", "files": []},
        trust_tier=SkillTrustTier.BUILT_IN_REVIEWED,
        review_status=SkillReviewStatus.REVIEWED,
        content_source_identity="test-only-new-version",
        published_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    uow.workflow_foundation.add_skill_version(newer)
    old_pins = uow.workflow_foundation.list_workflow_skill_pins(
        "writing-local-experimental", "0.2.0"
    )
    assert old_pins[0].skill_version == "0.1.0"
    assert old_pins[0].skill_checksum == asset.content_checksum
    assert uow.workflow_foundation.get_skill_version(
        asset.skill_id, old_pins[0].skill_version
    ).content_checksum == asset.content_checksum

    conflicting = SkillVersion(
        skill_id=asset.skill_id,
        skill_version="0.1.0",
        content_checksum="sha256:" + "b" * 64,
        manifest_schema_version="local-skill/v0.1",
        content_manifest={"schema_version": "local-skill/v0.1", "files": []},
        trust_tier=SkillTrustTier.BUILT_IN_REVIEWED,
        review_status=SkillReviewStatus.REVIEWED,
        content_source_identity="conflicting-fixture",
        published_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    with pytest.raises(WorkflowFoundationConflictError, match="immutable-content"):
        uow.workflow_foundation.add_skill_version(conflicting)


def test_skill_projection_queries_are_bounded_for_large_catalog(monkeypatch) -> None:
    database = InMemoryDatabase()
    uow = InMemoryUnitOfWork(database)
    ensure_production_workflow_foundation(uow, now=NOW)
    for index in range(100):
        skill_id = f"fixture-skill-{index:03d}"
        uow.workflow_foundation.add_skill_definition(SkillDefinition(
            skill_id=skill_id,
            display_name=f"Fixture Skill {index}",
            description="Bounded query fixture",
            lifecycle=SkillLifecycle.AVAILABLE,
            source_class=SkillSourceClass.PLATFORM_BUILT_IN,
            trust_tier=SkillTrustTier.BUILT_IN_REVIEWED,
            created_at=NOW,
            updated_at=NOW,
        ))
        uow.workflow_foundation.add_skill_version(SkillVersion(
            skill_id=skill_id,
            skill_version="0.1.0",
            content_checksum="sha256:" + f"{index + 1:064x}",
            manifest_schema_version="local-skill/v0.1",
            content_manifest={"schema_version": "local-skill/v0.1", "files": []},
            trust_tier=SkillTrustTier.BUILT_IN_REVIEWED,
            review_status=SkillReviewStatus.REVIEWED,
            content_source_identity=f"fixture-source-{index}",
            published_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        ))
    calls = {"definitions": 0, "versions": 0, "pins": 0}
    repository = uow.workflow_foundation
    originals = {
        "definitions": repository.list_skill_definitions,
        "versions": repository.list_all_skill_versions,
        "pins": repository.list_all_workflow_skill_pins,
    }
    for key, method_name in (
        ("definitions", "list_skill_definitions"),
        ("versions", "list_all_skill_versions"),
        ("pins", "list_all_workflow_skill_pins"),
    ):
        original = originals[key]
        def counted(original=original, key=key):
            calls[key] += 1
            return original()
        monkeypatch.setattr(repository, method_name, counted)
    service = ProjectWorkspaceApplicationService(unit_of_work=uow, clock=lambda: NOW)
    definitions, total = service.list_skills(offset=0, limit=100)
    assert total == 102 and len(definitions) == 100
    for definition in definitions:
        service.skill_versions_for(definition.skill_id)
    for _ in range(20):
        service.skill_projections_for("writing-local-experimental", "0.2.0")
    assert calls == {"definitions": 2, "versions": 1, "pins": 1}


def test_local_preflight_reports_tampered_bundled_skill(tmp_path) -> None:
    client, _ = _client(tmp_path)
    created = client.post("/projects", json={
        "name": "F1D local tamper",
        "research_topic": "Synthetic",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "full-research",
    }).json()
    project_id = created["project_id"]
    descriptor = client.get(
        f"/projects/{project_id}/workspace-bootstrap"
    ).json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
    transport = _Transport(client)
    workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    writing = next(
        item for item in lock["installed_capsules"]
        if item["workflow_definition_id"] == "writing-local-experimental"
    )
    skill = (
        workspace / writing["relative_path"] / "workflow/skills"
        / PRODUCTION_SKILLS[0].skill_id / "SKILL.md"
    )
    skill.write_text(skill.read_text() + "\nlocal drift\n")
    with pytest.raises(
        workspace_cli.WorkspaceCLIError,
        match="required built-in Skill is missing or changed",
    ) as error:
        workspace_cli.run_workflow(
            workspace_root=workspace,
            workflow_instance_id=writing["workflow_instance_id"],
            transport=transport,
            api_url="http://127.0.0.1:8000",
            preflight_only=True,
        )
    assert error.value.code == "LOCAL_CAPSULE_DRIFT"
