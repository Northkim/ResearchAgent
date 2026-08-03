from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.research.adapters import LocalFilesystemArtifactStorage

from .factories import native_report, upload_envelope, with_same_id_and_changed_content


@pytest.fixture
def progress_client(tmp_path) -> Iterator[tuple[TestClient, InMemoryDatabase]]:
    class ForbiddenProvider:
        def __getattr__(self, name):
            raise AssertionError(f"progress upload touched provider capability {name}")

    database = InMemoryDatabase()
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        artifact_storage=LocalFilesystemArtifactStorage(tmp_path / "artifacts"),
        paper_search_provider=ForbiddenProvider(),  # type: ignore[arg-type]
        structured_generation_provider=ForbiddenProvider(),  # type: ignore[arg-type]
        grounded_paper_search_provider=ForbiddenProvider(),  # type: ignore[arg-type]
    )
    container.source_content_provider = ForbiddenProvider()  # type: ignore[assignment]
    container.llm_provider = ForbiddenProvider()  # type: ignore[assignment]
    with TestClient(create_app(container)) as client:
        yield client, database


def test_upload_list_read_original_and_projection(progress_client) -> None:
    client, database = progress_client
    report = native_report()
    envelope = upload_envelope(report)

    uploaded = client.post(
        f"/projects/{report.project_id}/progress-reports",
        json=envelope.to_dict(),
    )
    listed = client.get(f"/projects/{report.project_id}/progress-reports")
    fetched = client.get(
        f"/projects/{report.project_id}/progress-reports/{report.report_id}"
    )
    original = client.get(
        f"/projects/{report.project_id}/progress-reports/{report.report_id}/original"
    )
    projection = client.get(f"/projects/{report.project_id}/progress")

    assert uploaded.status_code == 201
    assert listed.status_code == fetched.status_code == original.status_code == 200
    assert projection.status_code == 200
    assert listed.json()[0]["normalized_record"]["report_id"] == report.report_id
    assert original.content == envelope.original_report_bytes()
    assert projection.json()["latest_execution_round"] == 1
    assert database.executions == {}
    assert database.execution_events == {}
    assert database.provider_operations == {}


def test_api_replay_returns_200_and_conflict_returns_409(progress_client) -> None:
    client, _ = progress_client
    report = native_report()
    envelope = upload_envelope(report)
    path = f"/projects/{report.project_id}/progress-reports"
    first = client.post(path, json=envelope.to_dict())
    replay = client.post(path, json=envelope.to_dict())
    conflict = client.post(
        path,
        json=upload_envelope(with_same_id_and_changed_content(report)).to_dict(),
    )

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert conflict.status_code == 409
    history = client.get(f"/projects/{report.project_id}/progress-reports").json()
    conflict_row = next(item for item in history if not item["accepted_for_projection"])
    audited = client.get(
        f"/projects/{report.project_id}/progress-reports/{report.report_id}",
        params={"receipt_id": conflict_row["receipt_id"]},
    )
    assert audited.status_code == 200
    assert audited.json()["receipt_id"] == conflict_row["receipt_id"]


def test_api_rejects_path_project_mismatch_and_oversized_declared_size(
    progress_client,
) -> None:
    client, _ = progress_client
    report = native_report()
    payload = upload_envelope(report).to_dict()

    mismatch = client.post("/projects/another-project/progress-reports", json=payload)
    payload["original_report_size"] = 256 * 1024 + 1
    oversized = client.post(
        f"/projects/{report.project_id}/progress-reports",
        json=payload,
    )

    assert mismatch.status_code == 422
    assert oversized.status_code == 422


def test_invalid_upload_never_creates_execution_state(progress_client) -> None:
    client, database = progress_client
    report = native_report()
    payload = upload_envelope(report).to_dict()
    payload["report_schema_version"] = "progress-report/v9"

    response = client.post(
        f"/projects/{report.project_id}/progress-reports",
        json=payload,
    )

    assert response.status_code == 422
    assert database.executions == {}
    assert database.checkpoint_records == {}
    assert database.memory_revisions == {}
    assert database.execution_events == {}
    assert database.provider_operations == {}


def test_secret_like_upload_is_rejected_before_cloud_history(progress_client) -> None:
    client, database = progress_client
    report = native_report()
    unsafe = upload_envelope(
        report,
        content=report.canonical_json().replace(
            "Fictional catalog screening is recorded.",
            "sk-proj-fictionalsecret123",
        ).encode(),
    )

    response = client.post(
        f"/projects/{report.project_id}/progress-reports",
        json=unsafe.to_dict(),
    )

    assert response.status_code == 422
    assert database.progress_reports == {}
