from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_sync import _ClientTransport
from backend.project_workspaces.workspace_cli import WorkspaceCLIError
from backend.database.tests.test_user_managed_skills import CHECKSUM, FILES, REVISION, SOURCE


class _SkillTransport:
    def __init__(self, delegate, items):
        self.delegate = delegate
        self.items = items
        self.reports = []

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def list_project_skills(self, project_id):
        del project_id
        return {"items": self.items, "total": len(self.items)}

    def acknowledge_project_skills(self, project_id, installed_skills):
        self.reports.append((project_id, installed_skills))


def _item() -> dict:
    return {
        "skill_id": "skill-" + "1" * 32,
        "name": "Academic Literature Review",
        "slug": "academic-literature-review",
        "description": "Review papers and extract grounded evidence.",
        "source_locator": SOURCE,
        "source_revision": REVISION,
        "source_checksum": CHECKSUM,
        "usage_count": 1,
        "local_status": "Needs sync",
    }


def _resolve(locator: str, revision: str) -> dict[str, bytes]:
    assert locator == SOURCE
    assert revision == REVISION
    return FILES


@contextmanager
def _synced_workspace(tmp_path: Path):
    database = InMemoryDatabase()
    with TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "cloud-packages"),
    ))) as client:
        created = client.post("/projects", json={
            "name": "Disposable Skill Workspace",
            "research_topic": "Controlled Skill fixture",
            "selected_workflow": "LITERATURE_SEARCH",
            "workflow_setup": "literature-only",
        })
        assert created.status_code == 201, created.text
        project_id = created.json()["project_id"]
        descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
        workspace = tmp_path / "workspace"
        workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
        transport = _ClientTransport(client)
        assert workspace_cli.sync_workspace(
            workspace_root=workspace, transport=transport
        ).status == "SYNCED"
        yield workspace, transport


def test_normal_sync_installs_and_detaches_only_managed_agent_skill(tmp_path: Path) -> None:
    with _synced_workspace(tmp_path) as (workspace, base_transport):
        manual = workspace / ".agents/skills/manual-skill/SKILL.md"
        manual.parent.mkdir(parents=True)
        manual.write_text("# Owner Skill\n", encoding="utf-8")
        transport = _SkillTransport(base_transport, [_item()])

        first = workspace_cli.sync_workspace(
            workspace_root=workspace,
            transport=transport,
            skill_source_resolver=_resolve,
        )
        installed = workspace / ".agents/skills/academic-literature-review"
        assert first.status == "SYNCED"
        assert (installed / "SKILL.md").read_bytes() == FILES["SKILL.md"]
        lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
        assert lock["installed_skills"][0]["source_checksum"] == CHECKSUM
        assert transport.reports[-1][1] == [{
            "skill_id": _item()["skill_id"], "source_checksum": CHECKSUM,
        }]

        second = workspace_cli.sync_workspace(
            workspace_root=workspace,
            transport=transport,
            skill_source_resolver=_resolve,
        )
        assert second.status == "NO_CHANGE"

        transport.items = []
        detached = workspace_cli.sync_workspace(
            workspace_root=workspace,
            transport=transport,
            skill_source_resolver=_resolve,
        )
        assert detached.status == "SYNCED"
        assert not installed.exists()
        assert manual.read_text(encoding="utf-8") == "# Owner Skill\n"
        assert workspace_cli.sync_workspace(
            workspace_root=workspace,
            transport=transport,
            skill_source_resolver=_resolve,
        ).status == "NO_CHANGE"


def test_normal_sync_refuses_managed_skill_drift(tmp_path: Path) -> None:
    with _synced_workspace(tmp_path) as (workspace, base_transport):
        transport = _SkillTransport(base_transport, [_item()])
        workspace_cli.sync_workspace(
            workspace_root=workspace,
            transport=transport,
            skill_source_resolver=_resolve,
        )
        document = workspace / ".agents/skills/academic-literature-review/SKILL.md"
        document.write_text("# Locally changed\n", encoding="utf-8")

        with pytest.raises(WorkspaceCLIError) as raised:
            workspace_cli.sync_workspace(
                workspace_root=workspace,
                transport=transport,
                skill_source_resolver=_resolve,
            )
        assert raised.value.code == "USER_SKILL_LOCAL_DRIFT"
        assert document.read_text(encoding="utf-8") == "# Locally changed\n"


def test_normal_sync_refuses_verified_source_drift(tmp_path: Path) -> None:
    with _synced_workspace(tmp_path) as (workspace, base_transport):
        transport = _SkillTransport(base_transport, [_item()])

        with pytest.raises(WorkspaceCLIError) as raised:
            workspace_cli.sync_workspace(
                workspace_root=workspace,
                transport=transport,
                skill_source_resolver=lambda locator, revision: {
                    "SKILL.md": b"# Changed upstream\n"
                },
            )
        assert raised.value.code == "USER_SKILL_SOURCE_DRIFT"
        assert not (workspace / ".agents/skills/academic-literature-review").exists()
