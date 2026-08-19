"""Local exact-byte qualification for the forward Idea precondition."""

from __future__ import annotations

import json

import pytest

from backend.project_workspaces import workspace_cli
from backend.workflow_packages.serialization import canonical_hash


ARTIFACT_ID = "artifact-36363636363636363636363636363636"
ARTIFACT_HASH = "sha256:" + "a" * 64


def _artifact() -> dict[str, str]:
    return {
        "artifact_id": ARTIFACT_ID,
        "artifact_type": "selected-paper-library/v1",
        "content_checksum": ARTIFACT_HASH,
    }


def _library(count: int) -> bytes:
    return json.dumps({
        "schema": "selected-paper-library/v1",
        "source_schemas": ["reagent.paper-candidate/v0.1"],
        "source_checksums": ["sha256:" + "b" * 64],
        "papers": [
            {
                "candidate_id": f"candidate-{index}",
                "paper": {"title": f"Controlled paper {index}"},
                "selection": {"decision": "SELECTED"},
            }
            for index in range(count)
        ],
    }, sort_keys=True).encode("utf-8")


@pytest.mark.parametrize("count", (0, 1, 3))
def test_exact_local_bytes_project_bounded_selected_count(count: int) -> None:
    result = workspace_cli._project_artifact_content_qualification(
        artifact=_artifact(), content=_library(count)
    )
    assert result is not None
    payload = {
        "schema": "reagent.artifact-qualification.selected-paper-library/v0.1",
        "artifact_id": ARTIFACT_ID,
        "artifact_checksum": ARTIFACT_HASH,
        "selected_count": count,
    }
    assert result == {
        **payload,
        "qualification_checksum": canonical_hash(payload),
    }


def test_non_literature_artifact_has_no_content_qualification() -> None:
    assert workspace_cli._project_artifact_content_qualification(
        artifact={**_artifact(), "artifact_type": "selected-research-idea/v1"},
        content=b"{}",
    ) is None


def test_exact_local_qualification_uses_existing_reporting_path(tmp_path) -> None:
    source = tmp_path / "selected-paper-library.json"
    source.write_bytes(_library(1))

    class Transport:
        def __init__(self) -> None:
            self.reported: list[tuple[str, str, dict[str, object]]] = []

        def report_artifact_content_qualification(
            self, project_id: str, artifact_id: str, payload: dict[str, object]
        ) -> None:
            self.reported.append((project_id, artifact_id, payload))

    transport = Transport()
    reported, warnings = workspace_cli._report_artifact_content_qualifications(
        descriptor={"project_id": "project-" + "3" * 32},
        cloud_artifacts=[_artifact()],
        verified_sources={ARTIFACT_ID: source},
        transport=transport,
    )
    assert reported == 1
    assert warnings == ()
    assert transport.reported[0][0:2] == (
        "project-" + "3" * 32,
        ARTIFACT_ID,
    )
    assert transport.reported[0][2]["selected_count"] == 1
