from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.api import ApplicationContainer, create_app
from backend.database.orm.models import Base, UserManagedSkillORM
from backend.user_skills import VerifiedSkillSource


def _create(client: TestClient, name: str) -> str:
    response = client.post("/projects", json={
        "name": name,
        "research_topic": "Marked disposable Project lifecycle qualification",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "full-research",
        "custom_workflow_definition_ids": [],
    })
    assert response.status_code == 201
    return response.json()["project_id"]


def test_project_delete_is_transactional_project_scoped_and_preserves_global_records(
    sql_uow_factory,
    tmp_path,
) -> None:
    container = ApplicationContainer(
        unit_of_work_factory=sql_uow_factory,
        local_package_root=str(tmp_path / "cloud-packages"),
        user_skill_source_resolver=lambda *_: VerifiedSkillSource(
            "a" * 40, "sha256:" + "b" * 64
        ),
    )
    with TestClient(create_app(container)) as client:
        deleted_project = _create(client, "Delete PostgreSQL Project")
        retained_project = _create(client, "Retain PostgreSQL Project")
        skill = client.post("/user-skills", json={
            "name": "Shared SQL Skill",
            "description": "Controlled reusable instructions.",
            "source_locator": "https://github.com/example/shared-sql-skill",
        }).json()
        assert client.post(
            f"/projects/{deleted_project}/user-skills",
            json={"skill_id": skill["skill_id"]},
        ).status_code == 200
        assert client.post(
            f"/projects/{retained_project}/user-skills",
            json={"skill_id": skill["skill_id"]},
        ).status_code == 200

        with sql_uow_factory() as uow:
            assert len(uow.workflow_foundation.list_workflow_instances(deleted_project)) == 5
            uow.delete_project_cloud_state(deleted_project)
            uow.rollback()
        assert client.get(f"/projects/{deleted_project}").status_code == 200

        assert client.delete(f"/projects/{deleted_project}").status_code == 204

        with sql_uow_factory() as uow:
            for table in Base.metadata.sorted_tables:
                if "project_id" not in table.c:
                    continue
                count = uow.session.scalar(
                    select(func.count()).select_from(table).where(
                        table.c.project_id == deleted_project
                    )
                )
                assert count == 0, table.name
            assert uow.session.scalar(
                select(func.count()).select_from(UserManagedSkillORM).where(
                    UserManagedSkillORM.skill_id == skill["skill_id"]
                )
            ) == 1
            assert len(
                uow.workflow_foundation.list_workflow_instances(retained_project)
            ) == 5

        detail = client.get(f"/user-skills/{skill['skill_id']}").json()
        assert detail["usage_count"] == 1
        assert [item["project_id"] for item in detail["projects"]] == [
            retained_project
        ]
