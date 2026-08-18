from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi.testclient import TestClient
import pytest

import backend.user_skills as user_skills
from backend.api import ApplicationContainer, create_app
from backend.database.orm.models import ProjectORM
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.user_skills import (
    ProjectUserSkill,
    SQLAlchemyUserSkillRepository,
    UserSkill,
    VerifiedSkillSource,
    parse_github_skill_locator,
    resolve_github_skill_source,
)
from backend.workflow_packages.serialization import canonical_hash

NOW = datetime(2026, 8, 18, tzinfo=UTC)
REVISION = "a" * 40
SOURCE = "https://github.com/example/sample-research-skill"
SKILL_ID = "skill-" + "1" * 32


def _source_checksum(files: dict[str, bytes]) -> str:
    entries = [{
        "path": path,
        "size": len(content),
        "blob": hashlib.sha1(
            f"blob {len(content)}\0".encode("ascii") + content
        ).hexdigest(),
    } for path, content in sorted(files.items())]
    return canonical_hash({"files": entries})


FILES = {"SKILL.md": b"# Sample research skill\n\nKeep claims grounded.\n"}
CHECKSUM = _source_checksum(FILES)


def _resolver(locator: str, revision: str | None) -> VerifiedSkillSource:
    assert parse_github_skill_locator(locator).repository == "sample-research-skill"
    assert revision in {None, "main"}
    return VerifiedSkillSource(REVISION, CHECKSUM)


def test_github_source_contract_is_exact_bounded_and_credential_free(monkeypatch) -> None:
    for locator in (
        "https://token@github.com/example/skill",
        "https://github.com/example/skill?token=secret",
        "file:///private/skill",
        "https://github.com/example/skill/tree/main/../unsafe",
    ):
        with pytest.raises(ValueError):
            parse_github_skill_locator(locator)

    blob = hashlib.sha1(
        f"blob {len(FILES['SKILL.md'])}\0".encode("ascii") + FILES["SKILL.md"]
    ).hexdigest()

    def github_json(url: str):
        if "/commits/" in url:
            return {"sha": REVISION}
        return [{
            "type": "file", "path": "SKILL.md",
            "size": len(FILES["SKILL.md"]), "sha": blob,
        }]

    monkeypatch.setattr(user_skills, "_github_json", github_json)
    assert resolve_github_skill_source(SOURCE) == VerifiedSkillSource(REVISION, CHECKSUM)

    monkeypatch.setattr(user_skills, "_github_json", lambda url: (
        {"sha": REVISION} if "/commits/" in url else []
    ))
    with pytest.raises(Exception) as missing:
        resolve_github_skill_source(SOURCE)
    assert getattr(missing.value, "code", None) == "USER_SKILL_DOCUMENT_MISSING"


def test_user_skill_api_is_separate_idempotent_and_project_scoped() -> None:
    database = InMemoryDatabase()
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        clock=lambda: NOW,
        user_skill_source_resolver=_resolver,
    )
    with TestClient(create_app(container)) as client:
        projects = []
        for suffix in ("one", "two"):
            response = client.post("/projects", json={
                "name": f"Skill project {suffix}",
                "research_topic": "Controlled public topic",
                "selected_workflow": "LITERATURE_SEARCH",
                "workflow_setup": "literature-only",
                "custom_workflow_definition_ids": [],
            })
            assert response.status_code == 201
            projects.append(response.json()["project_id"])

        reviewed_before = len(database.skill_definitions)
        invalid = client.post("/user-skills", json={
            "name": "Unsafe", "description": "Invalid source",
            "source_locator": "https://example.com/skill",
        })
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "USER_SKILL_SOURCE_INVALID"

        created = client.post("/user-skills", json={
            "name": "Academic Literature Review",
            "description": "Review papers and extract grounded evidence.",
            "source_locator": SOURCE,
        })
        assert created.status_code == 201
        skill = created.json()
        assert skill["source_revision"] == REVISION
        assert skill["source_checksum"] == CHECKSUM
        assert skill["usage_count"] == 0
        assert len(database.skill_definitions) == reviewed_before

        for project_id in projects:
            first = client.post(
                f"/projects/{project_id}/user-skills", json={"skill_id": skill["skill_id"]}
            )
            replay = client.post(
                f"/projects/{project_id}/user-skills", json={"skill_id": skill["skill_id"]}
            )
            assert first.status_code == replay.status_code == 200
            assert first.json()["local_status"] == "Needs sync"
        assert client.get("/user-skills").json()["items"][0]["usage_count"] == 2

        blocked = client.delete(f"/user-skills/{skill['skill_id']}")
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "USER_SKILL_IN_USE"

        wrong = client.post(
            f"/projects/{projects[0]}/user-skills/sync-ack",
            json={"installed_skills": []},
        )
        assert wrong.status_code == 409
        extra = client.post(
            f"/projects/{projects[0]}/user-skills/sync-ack",
            json={"installed_skills": [{
                "skill_id": skill["skill_id"], "source_checksum": CHECKSUM,
                "unexpected": "value",
            }]},
        )
        assert extra.status_code == 409
        ready = client.post(
            f"/projects/{projects[0]}/user-skills/sync-ack",
            json={"installed_skills": [{
                "skill_id": skill["skill_id"], "source_checksum": CHECKSUM,
            }]},
        )
        assert ready.status_code == 200
        assert client.get(f"/projects/{projects[0]}/user-skills").json()["items"][0]["local_status"] == "Ready"

        for _ in range(2):
            assert client.delete(
                f"/projects/{projects[0]}/user-skills/{skill['skill_id']}"
            ).status_code == 200
        assert client.get(f"/projects/{projects[1]}/user-skills").json()["total"] == 1


def test_user_skill_sql_round_trip_and_existing_project_default(sql_uow_factory) -> None:
    project_id = "project-" + "2" * 32
    skill = UserSkill(
        SKILL_ID, "Scientific Writing", "scientific-writing",
        "Help structure academic writing.", SOURCE, REVISION, CHECKSUM, NOW, NOW,
    )
    with sql_uow_factory() as uow:
        uow.session.add(ProjectORM(
            project_id=project_id, workspace_id="workspace-" + "2" * 32,
            name="Disposable Skill Project", research_topic="Controlled topic",
            status="ACTIVE", current_manifest_revision=0,
            legacy_local_project_id=None, created_at=NOW, updated_at=NOW,
        ))
        uow.user_skills.add_skill(skill)
        uow.session.flush()
        assert uow.user_skills.list_project_skills(project_id) == ()
        uow.user_skills.add_project_skill(ProjectUserSkill(
            project_id, SKILL_ID, None, NOW, None,
        ))
        uow.commit()
    with sql_uow_factory() as uow:
        assert uow.user_skills.get_skill(SKILL_ID) == skill
        assert uow.user_skills.list_project_skills(project_id) == (
            ProjectUserSkill(project_id, SKILL_ID, None, NOW, None),
        )
        assert isinstance(uow.user_skills, SQLAlchemyUserSkillRepository)
