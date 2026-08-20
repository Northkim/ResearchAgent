from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.project_workspaces.tests.test_f1f_complete_product_width import (
    qualify_complete_product_width,
)


def test_complete_product_width_survives_fresh_postgresql_sessions(
    sql_uow_factory, tmp_path: Path,
) -> None:
    container = ApplicationContainer(
        unit_of_work_factory=sql_uow_factory,
        local_package_root=str(tmp_path / "cloud-packages"),
        clock=lambda: datetime(
            2026, 8, 20, 10, tzinfo=timezone(timedelta(hours=8))
        ),
    )
    result = qualify_complete_product_width(TestClient(create_app(container)), tmp_path)

    # A new app/client forces fresh SQLAlchemy sessions and qualifies the Cloud
    # half of restart recovery without relying on in-process repository state.
    restarted = TestClient(create_app(container))
    project_id = result["project_id"]
    instances = restarted.get(
        f"/projects/{project_id}/workflow-instances"
    ).json()
    progress = restarted.get(f"/projects/{project_id}/progress").json()
    artifacts = restarted.get(f"/projects/{project_id}/artifacts").json()
    resources = restarted.get(f"/projects/{project_id}/resources").json()
    manifest = restarted.get(f"/projects/{project_id}/manifest").json()

    assert instances["total"] == 6
    assert instances["manifest_revision"] == 6
    assert progress["total_progress_report_count"] == 6
    assert artifacts["total"] == 6
    assert resources["total"] == 3
    assert manifest["manifest_revision"] == 6
    assert len(result["artifact_ids"]) == 6
