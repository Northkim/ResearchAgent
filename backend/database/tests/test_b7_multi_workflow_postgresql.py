from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.project_workspaces.tests.test_b7_multi_workflow import (
    qualify_real_multi_workflow_artifact_handoff,
)


def test_b7_complete_chain_persists_across_fresh_postgresql_sessions(
    sql_uow_factory,
    tmp_path: Path,
) -> None:
    container = ApplicationContainer(
        unit_of_work_factory=sql_uow_factory,
        local_package_root=str(tmp_path / "cloud-packages"),
    )
    project_id = qualify_real_multi_workflow_artifact_handoff(
        TestClient(create_app(container)),
        tmp_path,
    )

    # A new app/client creates fresh SQLAlchemy sessions. The complete Workflow,
    # Progress, Artifact provenance, dependency, Manifest, and acknowledgement
    # state must reload rather than relying on in-process objects.
    restarted = TestClient(create_app(container))
    instances = restarted.get(
        f"/projects/{project_id}/workflow-instances"
    ).json()["items"]
    progress = restarted.get(f"/projects/{project_id}/progress").json()
    artifacts = restarted.get(f"/projects/{project_id}/artifacts").json()
    idea = next(
        item for item in instances
        if item["workflow_definition_id"] == "idea-discovery-local-experimental"
    )
    dependencies = restarted.get(
        f"/projects/{project_id}/workflow-instances/"
        f"{idea['workflow_instance_id']}/artifact-dependencies"
    ).json()

    assert len(instances) == 2
    assert progress["total_progress_report_count"] == 2
    assert artifacts["total"] == 1
    assert dependencies["total"] == 1
