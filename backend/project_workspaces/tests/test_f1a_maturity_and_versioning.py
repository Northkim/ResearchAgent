from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces.contracts import (
    CoreCapabilityMaturity,
    WorkflowDefinitionLifecycle,
    WorkflowDefinitionVersion,
    WorkflowReviewStatus,
)


def _client(tmp_path) -> tuple[TestClient, InMemoryDatabase]:
    database = InMemoryDatabase()
    return TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "packages"),
    ))), database


def test_catalog_exposes_reviewed_maturity_and_recommends_new_idea_version(
    tmp_path,
) -> None:
    client, database = _client(tmp_path)
    created = client.post("/projects", json={
        "name": "F1A catalog fixture",
        "research_topic": "Synthetic research",
        "selected_workflow": "LITERATURE_SEARCH",
    })
    assert created.status_code == 201
    detail = client.get(
        "/workflow-definitions/idea-discovery-local-experimental"
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["recommended_version"]["version"] == "0.2.0"
    assert body["recommended_version"]["core_capability_maturity"] == "REVIEWED_CORE"
    assert body["recommended_capsule"]["capsule_version"] == "0.3.0"
    assert [(item["version"], item["core_capability_maturity"]) for item in body["versions"]] == [
        ("0.1.0", "REVIEWED_CORE"), ("0.2.0", "REVIEWED_CORE")
    ]
    assert set(database.workflow_definitions) == {
        "literature-search-local-experimental",
        "idea-discovery-local-experimental",
        "writing-local-experimental",
        "review-local-experimental",
        "reproduction-experiment-local-experimental",
    }


def test_existing_idea_instance_remains_pinned_when_new_version_is_seeded(
    tmp_path,
) -> None:
    client, _ = _client(tmp_path)
    project = client.post("/projects", json={
        "name": "F1A pin fixture",
        "research_topic": "Synthetic research",
        "selected_workflow": "LITERATURE_SEARCH",
    }).json()
    project_id = project["project_id"]
    old = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": "idea-discovery-local-experimental",
        "workflow_version": "0.1.0",
        "capsule_id": "capsule-f07330db6f0d87f3fd482b698223ea75",
        "capsule_version": "0.1.0",
        "base_revision": 1,
    })
    assert old.status_code == 201, old.text
    catalog = client.get(
        "/workflow-definitions/idea-discovery-local-experimental"
    ).json()
    assert catalog["recommended_version"]["version"] == "0.2.0"
    instances = client.get(f"/projects/{project_id}/workflow-instances").json()
    old_instance = next(
        item for item in instances["items"]
        if item["workflow_definition_id"] == "idea-discovery-local-experimental"
    )
    assert (old_instance["workflow_version"], old_instance["capsule_version"]) == (
        "0.1.0", "0.1.0"
    )


def test_existing_idea_0_2_capsule_is_not_silently_upgraded(tmp_path) -> None:
    client, _ = _client(tmp_path)
    project = client.post("/projects", json={
        "name": "F1F immutable pin fixture",
        "research_topic": "Synthetic research",
        "selected_workflow": "LITERATURE_SEARCH",
    }).json()
    project_id = project["project_id"]
    created = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": "idea-discovery-local-experimental",
        "workflow_version": "0.2.0",
        "capsule_id": "capsule-6b66289a38895ce0eba2f76cd7725176",
        "capsule_version": "0.2.0",
        "base_revision": 1,
    })
    assert created.status_code == 201, created.text
    instance = created.json()
    assert (instance["workflow_version"], instance["capsule_version"]) == (
        "0.2.0", "0.2.0"
    )
    catalog = client.get(
        "/workflow-definitions/idea-discovery-local-experimental"
    ).json()
    assert catalog["recommended_capsule"]["capsule_version"] == "0.3.0"


def test_existing_experiment_0_3_capsule_is_not_silently_upgraded(tmp_path) -> None:
    client, _ = _client(tmp_path)
    project = client.post("/projects", json={
        "name": "Experiment immutable pin fixture",
        "research_topic": "Synthetic research",
        "selected_workflow": "LITERATURE_SEARCH",
    }).json()
    project_id = project["project_id"]
    created = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": "reproduction-experiment-local-experimental",
        "workflow_version": "0.3.0",
        "capsule_id": "capsule-4aa162608aafec3c67db316957f57349",
        "capsule_version": "0.3.0",
        "base_revision": 1,
    })
    assert created.status_code == 201, created.text
    instance = created.json()
    assert (instance["workflow_version"], instance["capsule_version"]) == (
        "0.3.0", "0.3.0"
    )
    catalog = client.get(
        "/workflow-definitions/reproduction-experiment-local-experimental"
    ).json()
    assert catalog["recommended_version"]["version"] == "0.3.0"
    assert catalog["recommended_capsule"]["capsule_version"] == "0.4.0"


def test_maturity_is_canonical_and_independent_from_lifecycle() -> None:
    now = datetime(2026, 8, 7, tzinfo=UTC)
    reviewed = WorkflowDefinitionVersion(
        workflow_definition_id="test-reviewed-workflow",
        version="1.0.0",
        contract_checksum="sha256:" + "1" * 64,
        input_schema_id="input/v1",
        output_schema_id="output/v1",
        compatibility={"lifecycle": WorkflowDefinitionLifecycle.PLANNED.value},
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.SCAFFOLD_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )
    assert reviewed.core_capability_maturity is CoreCapabilityMaturity.SCAFFOLD_CORE
    assert reviewed.compatibility["lifecycle"] == "PLANNED"
    with pytest.raises(ValueError, match="canonical enum"):
        WorkflowDefinitionVersion(
            workflow_definition_id="test-invalid-workflow",
            version="1.0.0",
            contract_checksum="sha256:" + "2" * 64,
            input_schema_id="input/v1",
            output_schema_id="output/v1",
            compatibility={},
            review_status=WorkflowReviewStatus.REVIEWED,
            core_capability_maturity="REVIEWED_CORE",  # type: ignore[arg-type]
            published_at=now,
            created_at=now,
            updated_at=now,
        )
