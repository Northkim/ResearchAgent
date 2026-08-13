from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import (
    _seed_upstream,
)
from backend.project_workspaces.tests.test_owner_real_research_gate import (
    _loopback_server,
)
from backend.workflow_packages.production_workflows import (
    IDEA_DISCOVERY_WORKFLOW_ID,
    LITERATURE_SEARCH_WORKFLOW_ID,
    REVIEW_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
)


def _copy_executable(source: Path, target: Path) -> Path:
    shutil.copyfile(source, target)
    target.chmod(0o700)
    return target


def _instances(client: httpx.Client, project_id: str) -> list[dict]:
    response = client.get(f"/projects/{project_id}/workflow-instances")
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _roots(workspace: Path) -> dict[str, Path]:
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    return {
        item["workflow_instance_id"]: workspace / item["relative_path"]
        for item in lock["installed_capsules"]
    }


def _bind(
    client: httpx.Client, project_id: str, consumer: dict, key: str,
    artifact: dict, number: int,
) -> None:
    response = client.post(
        f"/projects/{project_id}/workflow-instances/"
        f"{consumer['workflow_instance_id']}/artifact-dependencies",
        json={
            "requirement_key": key,
            "artifact_id": artifact["artifact_id"],
            "idempotency_key": f"00000000-0000-4000-8000-{number:012d}",
        },
    )
    assert response.status_code == 201, response.text


def _artifact(
    client: httpx.Client, project_id: str, workflow_instance_id: str,
    artifact_type: str,
) -> dict:
    response = client.get(
        f"/projects/{project_id}/artifacts",
        params={
            "workflow_instance_id": workflow_instance_id,
            "artifact_type": artifact_type,
        },
    )
    assert response.status_code == 200, response.text
    values = response.json()["artifacts"]
    assert len(values) == 1
    return values[0]


def _run_pty(
    *, repository: Path, workspace: Path, capsule: Path, workflow: str,
    base_url: str, fake: Path, marker: str,
    workflow_instance_id: str | None = None,
) -> str:
    command = [
        sys.executable,
        str(repository / "backend/workflow_packages/tests/interactive_e2e_driver.py"),
        "--workspace-root", str(workspace),
        "--capsule-root", str(capsule),
        "--workflow", workflow,
        "--base-url", base_url,
        "--expect-marker", marker,
    ]
    if workflow_instance_id:
        command.extend(["--workflow-instance", workflow_instance_id])
    driven = subprocess.run(
        command,
        cwd=repository,
        env=dict(os.environ) | {
            "REAGENT_CODEX_EXECUTABLE": str(fake),
            "REAGENT_LOCAL_BASE_URL": base_url,
            "REAGENT_OPENALEX_API_KEY": "secret-must-not-cross-writing-review",
            "REAGENT_DATABASE_URL": "secret-must-not-cross-writing-review",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )
    assert driven.returncode == 0, driven.stdout + driven.stderr
    assert marker in driven.stdout
    assert "secret-must-not-cross-writing-review" not in driven.stdout + driven.stderr
    return driven.stdout


def test_workspace_root_interactive_writing_review_revision_chain(
    tmp_path: Path,
) -> None:
    database = InMemoryDatabase()
    uow_factory = lambda: InMemoryUnitOfWork(database)
    app = create_app(ApplicationContainer(
        unit_of_work_factory=uow_factory,
        local_package_root=str(tmp_path / "cloud-packages"),
    ))
    repository = Path(__file__).resolve().parents[3]
    fake = _copy_executable(
        repository / "backend/workflow_packages/tests/fake_writing_review_codex_cli.py",
        tmp_path / "codex-writing-review-fixture",
    )

    with _loopback_server(app) as base_url, httpx.Client(
        base_url=base_url, timeout=30
    ) as client:
        created = client.post("/projects", json={
            "name": "Interactive Writing Review chain",
            "research_topic": "Synthetic immutable revision qualification",
            "selected_workflow": "LITERATURE_SEARCH",
            "workflow_setup": "full-research",
        })
        assert created.status_code == 201, created.text
        project_id = created.json()["project_id"]
        instances = {
            item["workflow_definition_id"]: item
            for item in _instances(client, project_id)
        }
        writing_a = instances[WRITING_WORKFLOW_ID]
        review_a = instances[REVIEW_WORKFLOW_ID]
        assert (writing_a["workflow_version"], writing_a["capsule_version"]) == (
            "0.2.0", "0.3.0",
        )
        assert (review_a["workflow_version"], review_a["capsule_version"]) == (
            "0.2.0", "0.3.0",
        )

        descriptor = client.get(
            f"/projects/{project_id}/workspace-bootstrap"
        ).json()
        workspace = tmp_path / "Writing Review Workspace 空格"
        workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
        transport = workspace_cli.HTTPWorkspaceSyncTransport(base_url)
        assert workspace_cli.sync_workspace(
            workspace_root=workspace, transport=transport
        ).status == "SYNCED"
        roots = _roots(workspace)
        now = datetime(2026, 8, 13, tzinfo=UTC)

        literature = instances[LITERATURE_SEARCH_WORKFLOW_ID]
        library = _seed_upstream(
            uow_factory=uow_factory, project_id=project_id, instance=literature,
            root=roots[literature["workflow_instance_id"]],
            artifact_type="selected-paper-library/v1",
            content={"schema": "selected-paper-library/v1", "papers": []},
            character="a",
        )
        idea = instances[IDEA_DISCOVERY_WORKFLOW_ID]
        selected_idea = _seed_upstream(
            uow_factory=uow_factory, project_id=project_id, instance=idea,
            root=roots[idea["workflow_instance_id"]],
            artifact_type="selected-research-idea/v1",
            content={
                "schema": "selected-research-idea/v1",
                "selected_idea": {
                    "title": "Synthetic immutable revision direction",
                    "research_question": "How can bootstrap continuity be qualified?",
                },
            },
            character="b",
        )
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=transport, now=now
        )
        _bind(client, project_id, writing_a, "research_idea", selected_idea, 1)
        _bind(client, project_id, writing_a, "literature_library", library, 2)
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=writing_a["workflow_instance_id"],
            transport=transport, now=now,
        )
        writing_output = _run_pty(
            repository=repository, workspace=workspace,
            capsule=roots[writing_a["workflow_instance_id"]],
            workflow=WRITING_WORKFLOW_ID, base_url=base_url, fake=fake,
            marker="REAGENT WRITING — INPUT_REVIEW",
        )
        assert "Revision round: no" in writing_output
        draft_a = _artifact(
            client, project_id, writing_a["workflow_instance_id"],
            "manuscript-draft/v1",
        )
        draft_a_path = roots[writing_a["workflow_instance_id"]] / draft_a["relative_path"]
        draft_a_bytes = draft_a_path.read_bytes()

        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=transport, now=now
        )
        _bind(client, project_id, review_a, "manuscript", draft_a, 3)
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=review_a["workflow_instance_id"],
            transport=transport, now=now,
        )
        _run_pty(
            repository=repository, workspace=workspace,
            capsule=roots[review_a["workflow_instance_id"]],
            workflow=REVIEW_WORKFLOW_ID, base_url=base_url, fake=fake,
            marker="REAGENT REVIEW — INPUT_REVIEW",
        )
        review_report = _artifact(
            client, project_id, review_a["workflow_instance_id"],
            "review-report/v1",
        )
        review_path = roots[review_a["workflow_instance_id"]] / review_report["relative_path"]
        review_bytes = review_path.read_bytes()
        assert json.loads(review_bytes)["recommendation"] == "INSUFFICIENT_EVIDENCE"

        detail = client.get(f"/workflow-definitions/{WRITING_WORKFLOW_ID}").json()
        added = client.post(
            f"/projects/{project_id}/workflow-instances",
            json={
                "workflow_definition_id": WRITING_WORKFLOW_ID,
                "workflow_version": detail["recommended_version"]["version"],
                "capsule_id": detail["recommended_capsule"]["capsule_id"],
                "capsule_version": detail["recommended_capsule"]["capsule_version"],
                "base_revision": 1,
            },
        )
        assert added.status_code == 201, added.text
        writing_b = added.json()
        assert (writing_b["workflow_version"], writing_b["capsule_version"]) == (
            "0.2.0", "0.3.0",
        )
        assert workspace_cli.sync_workspace(
            workspace_root=workspace, transport=transport
        ).status == "SYNCED"
        roots = _roots(workspace)
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=transport, now=now
        )
        for number, (key, artifact) in enumerate((
            ("research_idea", selected_idea),
            ("literature_library", library),
            ("prior_manuscript", draft_a),
            ("review_feedback", review_report),
        ), start=4):
            _bind(client, project_id, writing_b, key, artifact, number)
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=writing_b["workflow_instance_id"],
            transport=transport, now=now,
        )
        revision_output = _run_pty(
            repository=repository, workspace=workspace,
            capsule=roots[writing_b["workflow_instance_id"]],
            workflow=WRITING_WORKFLOW_ID,
            workflow_instance_id=writing_b["workflow_instance_id"],
            base_url=base_url, fake=fake,
            marker="REAGENT WRITING — INPUT_REVIEW",
        )
        assert "Revision round: yes" in revision_output
        draft_b = _artifact(
            client, project_id, writing_b["workflow_instance_id"],
            "manuscript-draft/v1",
        )
        draft_b_value = json.loads(
            (roots[writing_b["workflow_instance_id"]] / draft_b["relative_path"]).read_text()
        )
        assert draft_b_value["source_artifacts"]["prior_manuscript"]["artifact_id"] == draft_a["artifact_id"]
        assert draft_b_value["source_artifacts"]["review_feedback"]["artifact_id"] == review_report["artifact_id"]
        assert draft_a_path.read_bytes() == draft_a_bytes
        assert review_path.read_bytes() == review_bytes

        for instance in (writing_a, review_a, writing_b):
            progress = client.get(
                f"/projects/{project_id}/workflow-instances/"
                f"{instance['workflow_instance_id']}/progress"
            ).json()
            assert progress["history_total"] == 1
            assert progress["projection"]["latest_execution_round"] == 1
            assert progress["projection"]["research_status"] == "COMPLETED"
