from __future__ import annotations

import json
import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from backend.artifact_references import (
    PRODUCTION_ARTIFACT_CONTRACTS, validate_experiment_record_v4,
)
from backend.artifact_references.tests.test_generic_experiment_record_v4 import record
from backend.workflow_packages.generic_experiment_publication import (
    GENERIC_EXPERIMENT_ARTIFACT_TYPE, GENERIC_EXPERIMENT_CAPSULE_CHECKSUM,
    GENERIC_EXPERIMENT_CAPSULE_ID, GENERIC_EXPERIMENT_CAPSULE_VERSION,
    GENERIC_EXPERIMENT_CONTRACT_CHECKSUM, GENERIC_EXPERIMENT_WORKFLOW_VERSION,
    REFERENCE_CAPABILITY_SKILL, build_generic_experiment_v0_9_package,
    generic_experiment_workflow_document,
)
from backend.workflow_packages.production_workflows import (
    PREPARED_EXPERIMENT_CAPSULE_CHECKSUM, PREPARED_EXPERIMENT_CONTRACT_CHECKSUM,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes


def _package(tmp_path: Path, name: str = "generic"):
    return build_generic_experiment_v0_9_package(
        project_id="project-" + "a" * 32,
        project_name="GEN-C qualification",
        research_topic="Domain-neutral local computation",
        output_root=tmp_path / name,
        package_id=name,
    )


def _materialize(root: Path, *, question: str, proposal: dict) -> None:
    idea = {
        "schema": "selected-research-idea/v1",
        "selected_idea": {"title": "Controlled objective", "research_question": question},
    }
    content = (canonical_json(idea) + "\n").encode()
    (root / "inputs/selected-research-idea.json").write_bytes(content)
    (root / "memory/input-provenance.json").write_text(canonical_json({
        "schema_version": "reagent.generic-experiment-input-provenance/v0.1",
        "workflow_instance_id": "wfi-" + "b" * 32,
        "artifacts": {"research_idea": {
            "artifact_id": "artifact-" + "c" * 32,
            "artifact_type": "selected-research-idea/v1",
            "sha256": sha256_bytes(content),
        }},
    }) + "\n")
    (root / "memory/methodology-proposal.json").write_text(
        canonical_json(proposal) + "\n"
    )


def _proposal(*, supported: bool, unresolved=()) -> dict:
    values = {
        key: ["Bounded generic declaration."]
        for key in (
            "questions_or_hypotheses", "inputs_or_materials", "protocol",
            "observations_or_outputs", "evaluation_criteria",
            "reproducibility_controls", "resource_constraints",
            "compute_constraints", "assumptions", "claim_boundaries",
        )
    }
    if supported:
        values.update({
            "questions_or_hypotheses": ["Wine nearest classification accuracy?"],
            "inputs_or_materials": ["Wine classification material."],
            "protocol": ["Nearest neighbor with stratified assessment."],
            "evaluation_criteria": ["Accuracy is reviewed."],
        })
    values["network_policy"] = "DISABLED"
    values["unresolved_material_decisions"] = list(unresolved)
    return values


def test_exact_publication_build_registry_and_historical_freeze(tmp_path: Path) -> None:
    workflow = generic_experiment_workflow_document()
    assert workflow["workflow_version"] == "0.6.0"
    assert workflow["input_requirements"][0]["artifact_type"] == "selected-research-idea/v1"
    assert workflow["artifact_outputs"][0]["artifact_type"] == "experiment-record/v4"
    serialized = canonical_json(workflow).lower()
    for forbidden in ("sklearn", "python", "knn", "wine", "metrics", "cross-validation"):
        assert forbidden not in serialized
    assert GENERIC_EXPERIMENT_WORKFLOW_VERSION == "0.6.0"
    assert GENERIC_EXPERIMENT_CAPSULE_VERSION == "0.9.0"
    assert GENERIC_EXPERIMENT_ARTIFACT_TYPE == "experiment-record/v4"
    assert GENERIC_EXPERIMENT_CAPSULE_ID == "capsule-" + GENERIC_EXPERIMENT_CAPSULE_CHECKSUM[7:39]
    assert GENERIC_EXPERIMENT_CONTRACT_CHECKSUM == "sha256:5e91401ee48979ff1e61453c8e304565c9c35ab317d511fdb458b82347dff517"
    assert PREPARED_EXPERIMENT_CONTRACT_CHECKSUM == "sha256:23b6e3cae5746c8589927d2380595df61d01c6fb3f487cf47e09753f3ef8b600"
    assert PREPARED_EXPERIMENT_CAPSULE_CHECKSUM == "sha256:5e02c832357355b6036b7e21cfbae3061306b16268d04ee75c764c56c759bd98"
    assert REFERENCE_CAPABILITY_SKILL.skill_id == "sklearn-tabular-classification-preparation-local-builtin"
    built = _package(tmp_path)
    assert built.validation.valid and built.archive_validation.valid
    manifest = json.loads((built.package_root / "package-manifest.json").read_text())
    assert manifest["skill_pins"][0]["checksum"] == REFERENCE_CAPABILITY_SKILL.content_checksum
    capabilities = json.loads((built.package_root / "workflow/capabilities.json").read_text())
    assert len(capabilities["capabilities"]) == 1
    assert capabilities["capabilities"][0]["classification"] == "REFERENCE_EXPERIMENT_CAPABILITY"
    assert "synthetic" not in canonical_json(capabilities).lower()
    value = record()
    assert PRODUCTION_ARTIFACT_CONTRACTS["experiment-record/v4"].validator(value)["schema"] == "experiment-record/v4"
    with pytest.raises(TypeError):
        validate_experiment_record_v4(value.to_dict())


def test_public_checkpoint_supported_unsupported_unresolved_and_resume(tmp_path: Path) -> None:
    supported = _package(tmp_path, "supported").package_root
    _materialize(
        supported,
        question="Does nearest classification retain accuracy on Wine?",
        proposal=_proposal(supported=True),
    )
    runtime = runpy.run_path(str(supported / "reagent_local.py"))
    first = runtime["run"](supported, "wfi-" + "b" * 32)
    assert first["status"] == "DESIGN_APPROVAL_REQUIRED"
    assert first["selected_capability"]["skill"]["identity"] == REFERENCE_CAPABILITY_SKILL.skill_id
    assert not (supported / "memory/preparation").exists()
    assert runtime["run"](supported, "wfi-" + "b" * 32) == first
    assert runtime["validate"](supported, pristine=False)["valid"]

    unsupported = _package(tmp_path, "unsupported").package_root
    _materialize(
        unsupported,
        question="How do tidal narratives change across archival editions?",
        proposal=_proposal(supported=False),
    )
    result = runpy.run_path(str(unsupported / "reagent_local.py"))["run"](
        unsupported, "wfi-" + "b" * 32,
    )
    assert result["status"] == "AUTOMATIC_PREPARATION_UNSUPPORTED"
    assert "sklearn" not in result["summary"].lower()
    assert not (unsupported / "memory/preparation").exists()

    unresolved = _package(tmp_path, "unresolved").package_root
    _materialize(
        unresolved,
        question="Which categorical interpretation should govern the comparison?",
        proposal=_proposal(supported=False, unresolved=("Owner must choose the interpretation rule.",)),
    )
    stopped = runpy.run_path(str(unresolved / "reagent_local.py"))["run"](
        unresolved, "wfi-" + "b" * 32,
    )
    assert stopped["status"] == "METHODOLOGY_DECISION_REQUIRED"
    assert stopped["continuation"]["stage"] == "METHODOLOGY_UNRESOLVED"


def test_generic_capsule_dependency_direction_and_runtime_is_late_bound(tmp_path: Path) -> None:
    generic_source = Path(
        "backend/workflow_packages/generic_experiment_coordinator.py"
    ).read_text()
    for forbidden in (
        "sklearn_reference_capability", "sklearn_tabular_builder",
        "prepared_experiment_runtime", "SklearnTabularClassificationSpec",
    ):
        assert forbidden not in generic_source
    built = _package(tmp_path, "isolation")
    runner = (built.package_root / "reagent_local.py").read_text()
    assert "import numpy" not in runner and "import sklearn" not in runner
    assert "install" in (built.package_root / "AGENT.md").read_text().lower()


@pytest.mark.skipif(
    os.environ.get("REAGENT_REAL_CODEX_QUALIFICATION") != "1",
    reason="explicit E7 real Codex qualification only",
)
def test_real_codex_reaches_generic_owner_methodology_checkpoint(tmp_path: Path) -> None:
    executable = shutil.which("codex")
    assert executable is not None, "installed Codex CLI is required for E7"
    adapter = tmp_path / "codex-exec-adapter"
    adapter.write_text(
        f"#!{sys.executable}\n"
        "import os, subprocess, sys\n"
        f"actual={executable!r}\n"
        "raise SystemExit(subprocess.call([actual,'exec','--ephemeral',"
        "'--skip-git-repo-check','--sandbox','workspace-write','-C',os.getcwd(),sys.argv[-1]]))\n",
        encoding="utf-8",
    )
    adapter.chmod(adapter.stat().st_mode | 0o100)
    root = _package(tmp_path, "real-codex").package_root
    proposal = _proposal(supported=False)
    del proposal  # real Codex, rather than a fixture writer, owns this evidence
    idea = {
        "schema": "selected-research-idea/v1",
        "selected_idea": {
            "title": "Unresolved archival interpretation comparison",
            "research_question": (
                "Should the experiment classify ambiguous passages using the literal "
                "rubric or the contextual rubric? The Owner has not chosen which "
                "interpretation governs the scientific comparison."
            ),
            "proposed_direction": (
                "Compare the two interpretations only after the Owner selects the "
                "scientifically authoritative rubric."
            ),
        },
    }
    content = (canonical_json(idea) + "\n").encode()
    (root / "inputs/selected-research-idea.json").write_bytes(content)
    (root / "memory/input-provenance.json").write_text(canonical_json({
        "schema_version": "reagent.generic-experiment-input-provenance/v0.1",
        "workflow_instance_id": "wfi-" + "e" * 32,
        "artifacts": {"research_idea": {
            "artifact_id": "artifact-" + "f" * 32,
            "artifact_type": "selected-research-idea/v1",
            "sha256": sha256_bytes(content),
        }},
    }) + "\n")
    completed = subprocess.run(
        [
            sys.executable, "reagent_local.py", "run", ".",
            "--workflow-instance", "wfi-" + "e" * 32,
            "--codex-executable", str(adapter),
        ],
        cwd=root, check=False, text=True, capture_output=True, timeout=240,
    )
    assert completed.returncode == 0, completed.stderr
    checkpoint = json.loads((root / "memory/generic-checkpoint.json").read_text())
    assert checkpoint["status"] == "METHODOLOGY_DECISION_REQUIRED"
    assert checkpoint["methodology"]["unresolved_material_decisions"]
    assert not (root / "memory/preparation").exists()
