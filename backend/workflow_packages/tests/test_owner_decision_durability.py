from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from backend.workflow_packages.production_workflows import (
    build_idea_discovery_v0_5_package,
    build_literature_search_v0_7_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes


PROJECT_ID = "project-" + "d" * 32


def _write(path: Path, value: object) -> bytes:
    content = (canonical_json(value) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content


def test_literature_owner_disposition_survives_resume_and_rejects_drift(
    tmp_path: Path,
) -> None:
    package = build_literature_search_v0_7_package(
        project_id=PROJECT_ID,
        project_name="Durable Literature",
        research_topic="Controlled",
        output_root=tmp_path,
        package_id="durable-literature",
    ).package_root
    validator = runpy.run_path(str(package / "validate_package.py"))
    assert validator["validate"](package, pristine=False)["valid"] is True

    candidates = {
        "schema_version": "candidate-papers/v0.2",
        "mode": "NORMAL",
        "candidates": [
            {"candidate_id": "candidate-" + "a" * 16},
            {"candidate_id": "candidate-" + "b" * 16},
        ],
    }
    candidate_bytes = _write(package / "outputs/candidate_papers.json", candidates)
    snapshot = {
        "schema_version": "reagent.owner-decision-snapshot.literature/v0.1",
        "candidate_set_checksum": sha256_bytes(candidate_bytes),
        "decision_revision": 2,
        "decisions": [
            {
                "candidate_id": "candidate-" + "a" * 16,
                "disposition": "SELECTED",
                "reason": "Direct evidence for the bounded question.",
            },
            {
                "candidate_id": "candidate-" + "b" * 16,
                "disposition": "UNCERTAIN",
                "reason": "Useful context with incomplete support.",
            },
        ],
    }
    _write(package / "memory/owner-decisions.json", snapshot)
    validator["_validate_owner_decisions"](package)
    assert json.loads((package / "memory/owner-decisions.json").read_text()) == snapshot

    candidates["candidates"].reverse()
    _write(package / "outputs/candidate_papers.json", candidates)
    with pytest.raises(Exception, match="candidate set drifted"):
        validator["_validate_owner_decisions"](package)


def test_idea_owner_selection_survives_resume_and_rejects_candidate_drift(
    tmp_path: Path,
) -> None:
    package = build_idea_discovery_v0_5_package(
        project_id=PROJECT_ID,
        project_name="Durable Idea",
        research_topic="Controlled",
        output_root=tmp_path,
        package_id="durable-idea",
    ).package_root
    validator = runpy.run_path(str(package / "validate_package.py"))
    assert validator["validate"](package, pristine=False)["valid"] is True

    candidates = {
        "schema": "candidate-ideas/v0.1",
        "source_artifact": {
            "artifact_id": "artifact-" + "a" * 32,
            "artifact_type": "selected-paper-library/v1",
            "sha256": "sha256:" + "b" * 64,
        },
        "ideas": [
            {"idea_id": "idea-001", "status": "candidate"},
            {"idea_id": "idea-002", "status": "selected"},
        ],
    }
    candidate_bytes = _write(package / "outputs/candidate_ideas.json", candidates)
    snapshot = {
        "schema_version": "reagent.owner-decision-snapshot.idea/v0.1",
        "candidate_set_checksum": sha256_bytes(candidate_bytes),
        "decision_revision": 1,
        "selected_idea_id": "idea-002",
        "decision": "SELECTED",
    }
    _write(package / "memory/owner-decisions.json", snapshot)
    validator["_validate_owner_decisions"](package)
    assert json.loads((package / "memory/owner-decisions.json").read_text()) == snapshot

    candidates["ideas"][1]["status"] = "candidate"
    _write(package / "outputs/candidate_ideas.json", candidates)
    with pytest.raises(Exception, match="candidate set drifted"):
        validator["_validate_owner_decisions"](package)
