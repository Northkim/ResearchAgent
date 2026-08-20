from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.user_skills import VerifiedSkillSource


def _create(client: TestClient, name: str) -> str:
    response = client.post("/projects", json={
        "name": name,
        "research_topic": "Controlled Project deletion topic",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "full-research",
        "custom_workflow_definition_ids": [],
    })
    assert response.status_code == 201
    return response.json()["project_id"]


def test_project_delete_removes_only_exact_cloud_graph_and_preserves_global_skill(
    tmp_path,
) -> None:
    database = InMemoryDatabase()
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "cloud-packages"),
        user_skill_source_resolver=lambda *_: VerifiedSkillSource(
            "a" * 40, "sha256:" + "b" * 64
        ),
    )
    with TestClient(create_app(container)) as client:
        deleted_project = _create(client, "Delete this Project")
        retained_project = _create(client, "Keep this Project")
        created_skill = client.post("/user-skills", json={
            "name": "Reusable research notes",
            "description": "Keep research notes concise.",
            "source_locator": "https://github.com/example/research-notes",
        })
        assert created_skill.status_code == 201
        skill_id = created_skill.json()["skill_id"]
        assert client.post(
            f"/projects/{deleted_project}/user-skills", json={"skill_id": skill_id}
        ).status_code == 200

        assert len([
            item for item in database.project_workflow_instances.values()
            if item.project_id == deleted_project
        ]) == 5
        global_definition_count = len(database.workflow_definitions)

        response = client.delete(f"/projects/{deleted_project}")
        assert response.status_code == 204
        missing = client.get(f"/projects/{deleted_project}")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "PROJECT_NOT_FOUND"
        assert client.get(f"/projects/{retained_project}").status_code == 200

        assert deleted_project not in database.local_projects
        assert deleted_project not in database.projects
        assert not any(
            item.project_id == deleted_project
            for item in database.project_workflow_instances.values()
        )
        assert not any(key[0] == deleted_project for key in database.desired_manifests)
        assert not any(
            item.project_id == deleted_project
            for item in database.manifest_entries.values()
        )
        assert not any(key[0] == deleted_project for key in database.project_user_skills)
        assert database.user_skills[skill_id].skill_id == skill_id
        assert client.get(f"/user-skills/{skill_id}").json()["usage_count"] == 0
        assert len(database.workflow_definitions) == global_definition_count

        replay = client.delete(f"/projects/{deleted_project}")
        assert replay.status_code == 404
        assert replay.json()["error"]["code"] == "PROJECT_NOT_FOUND"
