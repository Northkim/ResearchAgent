from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from backend.artifact_references.research_flow_contracts import (
    validate_experiment_record,
    validate_manuscript_draft,
    validate_review_report,
)
from backend.project_workspaces.contracts import CoreCapabilityMaturity
from backend.workflow_packages import scaffold_runtime
from backend.workflow_packages.production_workflows import (
    EXPERIMENT_WORKFLOW_ID,
    REVIEW_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
    build_experiment_scaffold_package,
    build_review_scaffold_package,
    build_writing_scaffold_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes

PROJECT_ID = "project-" + "1" * 32
INSTANCE_ID = "wfi-" + "2" * 32


def _build(tmp_path: Path, workflow_id: str, suffix: str):
    builder = {
        WRITING_WORKFLOW_ID: build_writing_scaffold_package,
        REVIEW_WORKFLOW_ID: build_review_scaffold_package,
        EXPERIMENT_WORKFLOW_ID: build_experiment_scaffold_package,
    }[workflow_id]
    return builder(
        project_id=PROJECT_ID,
        project_name="F1B synthetic scaffold",
        research_topic="Synthetic bounded topic",
        output_root=tmp_path / suffix,
        package_id=f"f1b-{workflow_id}-fixture",
    )


def _ref(kind: str, character: str) -> dict[str, str]:
    return {
        "artifact_id": "artifact-" + character * 32,
        "artifact_type": kind,
        "sha256": "sha256:" + character * 64,
    }


def _write_provenance(root: Path, records: dict[str, dict[str, str]]) -> None:
    payload = {
        "schema_version": "reagent.scaffold-input-provenance/v0.1",
        "workflow_instance_id": INSTANCE_ID,
        "artifacts": {
            key: {**value, "relative_path": f"inputs/{key}.json"}
            for key, value in records.items()
        },
    }
    (root / "memory/input-provenance.json").write_text(
        canonical_json(payload) + "\n", encoding="utf-8"
    )


@pytest.mark.parametrize("workflow_id", [
    WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID,
])
def test_scaffold_capsules_are_deterministic_immutable_and_visibly_safe(
    tmp_path: Path, workflow_id: str,
) -> None:
    first = _build(tmp_path, workflow_id, "first")
    second = _build(tmp_path, workflow_id, "second")
    assert first.package_checksum == second.package_checksum
    assert first.zip_checksum == second.zip_checksum
    assert first.validation.valid and first.archive_validation.valid
    root = first.package_root
    manifest = json.loads((root / "package-manifest.json").read_text())
    config = json.loads((root / "workflow/scaffold.json").read_text())
    assert manifest["workflow_version"] == "0.1.0"
    assert config["core_capability_maturity"] == "SCAFFOLD_CORE"
    assert "Product flow is functional" in (root / "AGENT.md").read_text()
    assert "Never invent citations" in (root / "AGENT.md").read_text()
    assert runpy.run_path(str(root / "validate_package.py"))["validate"](
        root, pristine=True
    )["valid"]


def test_scaffold_artifacts_pass_frozen_f1a_contracts_and_reject_fake_results(
    tmp_path: Path,
) -> None:
    writing = _build(tmp_path, WRITING_WORKFLOW_ID, "writing").package_root
    idea_ref = _ref("selected-research-idea/v1", "a")
    library_ref = _ref("selected-paper-library/v1", "b")
    _write_provenance(writing, {"research_idea": idea_ref, "literature_library": library_ref})
    (writing / "inputs/selected-research-idea.json").write_text(canonical_json({
        "schema": "selected-research-idea/v1",
        "selected_idea": {"title": "Bounded title", "research_question": "What is bounded?"},
    }))
    artifact, human = scaffold_runtime._scaffold_payload(
        json.loads((writing / "workflow/scaffold.json").read_text()),
        json.loads((writing / "memory/input-provenance.json").read_text())["artifacts"],
        writing,
    )
    assert b"SCAFFOLD PLACEHOLDER" in human
    validate_manuscript_draft(
        artifact, producer_maturity=CoreCapabilityMaturity.SCAFFOLD_CORE
    )

    review = _build(tmp_path, REVIEW_WORKFLOW_ID, "review").package_root
    _write_provenance(review, {"manuscript": _ref("manuscript-draft/v1", "c")})
    report, human = scaffold_runtime._scaffold_payload(
        json.loads((review / "workflow/scaffold.json").read_text()),
        json.loads((review / "memory/input-provenance.json").read_text())["artifacts"],
        review,
    )
    assert b"SCAFFOLD REVIEW PLACEHOLDER" in human
    assert report["recommendation"] == "INSUFFICIENT_EVIDENCE"
    validate_review_report(report, producer_maturity=CoreCapabilityMaturity.SCAFFOLD_CORE)

    experiment = _build(tmp_path, EXPERIMENT_WORKFLOW_ID, "experiment").package_root
    _write_provenance(experiment, {"research_idea": idea_ref})
    (experiment / "inputs/selected-research-idea.json").write_text(canonical_json({
        "schema": "selected-research-idea/v1",
        "selected_idea": {"title": "Bounded title", "research_question": "What is bounded?"},
    }))
    record, human = scaffold_runtime._scaffold_payload(
        json.loads((experiment / "workflow/scaffold.json").read_text()),
        json.loads((experiment / "memory/input-provenance.json").read_text())["artifacts"],
        experiment,
    )
    assert b"SCAFFOLD EXPERIMENT PLACEHOLDER" in human
    assert record["execution_status"] == "PLACEHOLDER_NOT_EXECUTED"
    assert record["actual_results"] is None
    validate_experiment_record(record, producer_maturity=CoreCapabilityMaturity.SCAFFOLD_CORE)
    forged = {**record, "execution_status": "COMPLETED", "actual_results": {
        "summary": "fake", "metrics": [], "observations": []
    }}
    validator = runpy.run_path(str(experiment / "validate_package.py"))
    with pytest.raises(Exception, match="cannot claim execution"):
        validator["validate_scaffold_artifact"](forged)


def test_scaffold_preflight_requires_exact_materialized_checksums(tmp_path: Path) -> None:
    root = _build(tmp_path, EXPERIMENT_WORKFLOW_ID, "preflight").package_root
    idea = {"schema": "selected-research-idea/v1", "selected_idea": {
        "title": "Bounded", "research_question": "What is bounded?"
    }}
    content = (canonical_json(idea) + "\n").encode()
    target = root / "inputs/selected-research-idea.json"
    target.write_bytes(content)
    ref = _ref("selected-research-idea/v1", "a")
    ref["sha256"] = sha256_bytes(content)
    _write_provenance(root, {"research_idea": ref})
    provenance = json.loads((root / "memory/input-provenance.json").read_text())
    provenance["artifacts"]["research_idea"]["relative_path"] = (
        "inputs/selected-research-idea.json"
    )
    (root / "memory/input-provenance.json").write_text(canonical_json(provenance) + "\n")
    assert scaffold_runtime.preflight(root)["ready"] is True
    target.write_text(canonical_json({**idea, "drift": True}) + "\n")
    with pytest.raises(scaffold_runtime.ScaffoldRuntimeError, match="checksum drift"):
        scaffold_runtime.preflight(root)
