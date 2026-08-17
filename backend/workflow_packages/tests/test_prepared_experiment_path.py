from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from backend.artifact_references.research_flow_contracts import validate_experiment_record_v3
from backend.workflow_packages import prepared_experiment_runtime as runtime
from backend.workflow_packages.experiment_preparation_contracts import (
    ComputeRuntimeBounds, ExactArtifactReference, ExperimentMethodology,
    ImplementationDecision,
)
from backend.workflow_packages.production_workflows import (
    PREPARED_EXPERIMENT_CAPSULE_CHECKSUM, PREPARED_EXPERIMENT_CAPSULE_ID,
    PREPARED_EXPERIMENT_CONTRACT_CHECKSUM, build_prepared_experiment_v0_8_package,
)
from backend.workflow_packages.sklearn_tabular_builder import (
    AutomaticPreparationUnsupported, SklearnTabularClassificationSpec,
    package_tree, render_candidate,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes
from backend.project_workspaces.workspace_cli import SUPPORTED_CAPSULE_PINS


def _methodology() -> ExperimentMethodology:
    return ExperimentMethodology.create(
        selected_idea=ExactArtifactReference("artifact-" + "a" * 32, "selected-research-idea/v1", "sha256:" + "b" * 64),
        frozen_scientific_requirements=("Compare raw, StandardScaler, and MinMaxScaler KNN on Wine.",),
        implementation_decisions=(ImplementationDecision("Use sklearn Pipelines inside each fold.", "This enforces leakage-safe preprocessing.", True),),
        unresolved_methodological_decisions=(), dataset="scikit-learn Wine classification dataset",
        experiment_conditions=("Raw KNN", "StandardScaler plus KNN", "MinMaxScaler plus KNN"),
        evaluation_protocol=("Leakage-safe repeated stratified cross-validation inside each fold",),
        metrics=("accuracy", "macro-F1"), robustness_analysis=("Bounded neighbor-count sensitivity",),
        leakage_controls=("Fit scaling only inside each training fold",), seeds=(11,), repetitions=2,
        compute_runtime_bounds=ComputeRuntimeBounds(20, 120, 2, 1_000_000),
        network_policy="DISABLED", assumptions=("The bundled sklearn dataset is authoritative.",),
        claim_boundaries=("Wine-specific conclusions; no global novelty claim.",),
        expected_scientific_outputs=("Condition metrics", "Neighbor robustness summary"),
    )


def _spec(methodology: ExperimentMethodology) -> SklearnTabularClassificationSpec:
    return SklearnTabularClassificationSpec.create(
        methodology_checksum=methodology.methodology_checksum,
        dataset="SKLEARN_WINE", estimator="KNEIGHBORS_CLASSIFIER",
        conditions=("RAW", "STANDARD_SCALER", "MINMAX_SCALER"), n_neighbors=5,
        cv_splits=3, cv_repeats=2, cv_seed=11,
        metrics=("accuracy", "macro_f1"), robustness_neighbors=(3, 5, 7),
        result_schema="reagent.experiment-result/v0.2",
    )


def _proposal() -> dict:
    methodology = _methodology()
    return {
        "frozen_scientific_requirements": list(methodology.frozen_scientific_requirements),
        "implementation_decisions": [item.to_dict() for item in methodology.implementation_decisions],
        "unresolved_methodological_decisions": [], "dataset": methodology.dataset,
        "experiment_conditions": list(methodology.experiment_conditions),
        "evaluation_protocol": list(methodology.evaluation_protocol), "metrics": list(methodology.metrics),
        "robustness_analysis": list(methodology.robustness_analysis), "leakage_controls": list(methodology.leakage_controls),
        "seeds": list(methodology.seeds), "repetitions": methodology.repetitions,
        "compute_runtime_bounds": methodology.compute_runtime_bounds.to_dict(), "network_policy": "DISABLED",
        "assumptions": list(methodology.assumptions), "claim_boundaries": list(methodology.claim_boundaries),
        "expected_scientific_outputs": list(methodology.expected_scientific_outputs),
        "implementation_specification": {"n_neighbors": 5, "cv_splits": 3, "cv_repeats": 2, "cv_seed": 11, "robustness_neighbors": [3, 5, 7]},
    }


def _capsule(tmp_path: Path) -> Path:
    return build_prepared_experiment_v0_8_package(
        project_id="project-" + "a" * 32, project_name="Wine",
        research_topic="KNN scaling", output_root=tmp_path,
        package_id="package-" + "b" * 32,
    ).package_root


def _input(root: Path) -> None:
    idea = {"schema": "selected-research-idea/v1", "selected_idea": {"title": "Wine scaling", "research_question": "Does feature scaling improve KNN on Wine?"}}
    content = (canonical_json(idea) + "\n").encode()
    (root / "inputs/selected-research-idea.json").write_bytes(content)
    reference = {"artifact_id": "artifact-" + "a" * 32, "artifact_type": "selected-research-idea/v1", "sha256": sha256_bytes(content)}
    (root / "memory/input-provenance.json").write_text(canonical_json({"schema_version": "reagent.real-experiment-input-provenance/v0.1", "workflow_instance_id": "wfi-" + "c" * 32, "artifacts": {"research_idea": reference}}) + "\n")


def test_builder_is_deterministic_leakage_safe_and_rejects_unreviewed_vocabulary(tmp_path: Path) -> None:
    methodology = _methodology()
    spec = _spec(methodology)
    spec.validate_methodology(methodology)
    first, second = tmp_path / "first", tmp_path / "second"
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    render_candidate(first, spec, version)
    render_candidate(second, spec, version)
    assert package_tree(first)[0] == package_tree(second)[0]
    source = (first / "run_experiment.py").read_text()
    assert "Pipeline" in source and "RepeatedStratifiedKFold" in source
    assert "eval(" not in source and "exec(" not in source and "subprocess" not in source
    if importlib.util.find_spec("sklearn") is not None:
        completed = subprocess.run([sys.executable, "run_experiment.py", "experiment-config.json"], cwd=first, text=True, capture_output=True, check=True)
        result = json.loads(completed.stdout)
        assert [item["condition"] for item in result["conditions"]] == ["RAW", "STANDARD_SCALER", "MINMAX_SCALER"]
        assert len(result["robustness"]) == 9
    changed = spec.to_dict(); changed["dataset"] = "ARBITRARY_DATASET"
    with pytest.raises(AutomaticPreparationUnsupported):
        SklearnTabularClassificationSpec.from_mapping(changed)
    with pytest.raises(AutomaticPreparationUnsupported):
        SklearnTabularClassificationSpec.from_mapping({**spec.to_dict(), "python": "print('unsafe')"})


def test_publication_package_is_exact_and_contains_no_resource_or_git_requirement(tmp_path: Path) -> None:
    root = _capsule(tmp_path)
    workflow = json.loads((root / "workflow/workflow.json").read_text())
    contract = json.loads((root / "workflow/prepared-experiment.json").read_text())
    assert workflow["workflow_version"] == "0.5.0"
    assert workflow["resource_requirements"] == []
    assert workflow["artifact_outputs"][0]["artifact_type"] == "experiment-record/v3"
    assert contract["workflow_capsule"] == {
        "workflow_definition_id": "reproduction-experiment-local-experimental",
        "workflow_version": "0.5.0", "workflow_checksum": PREPARED_EXPERIMENT_CONTRACT_CHECKSUM,
        "capsule_id": PREPARED_EXPERIMENT_CAPSULE_ID, "capsule_version": "0.8.0",
        "capsule_checksum": PREPARED_EXPERIMENT_CAPSULE_CHECKSUM,
    }
    assert (root / "bounded_runner.py").read_bytes() == Path(runtime.__file__).with_name("real_experiment_runtime.py").read_bytes()
    assert SUPPORTED_CAPSULE_PINS[("reproduction-experiment-local-experimental", "0.5.0", "0.8.0")][1] is False


def test_controlled_path_a_is_resumable_checksum_approved_and_finalizes_v3(tmp_path: Path, monkeypatch) -> None:
    root = _capsule(tmp_path)
    _input(root)

    def fake_harness(capsule: Path, _executable: str) -> None:
        runtime._atomic_json(capsule / "memory/methodology-proposal.json", _proposal())

    executions = 0

    def fake_execute(capsule: Path, plan: dict, approval, attempt: str) -> dict:
        nonlocal executions
        executions += 1
        spec = runtime.SklearnTabularClassificationSpec.from_mapping(runtime._object(capsule / "memory/implementation-specification.json", "spec"))
        result = {
            "schema_version": "reagent.experiment-result/v0.2",
            "conditions": [{"condition": name, "n_neighbors": spec.n_neighbors, "metrics": {"accuracy": 0.7 + index / 10, "macro_f1": 0.69 + index / 10}} for index, name in enumerate(spec.conditions)],
            "robustness": [{"condition": name, "n_neighbors": neighbor, "metrics": {"accuracy": 0.75, "macro_f1": 0.74}} for neighbor in spec.robustness_neighbors for name in spec.conditions],
        }
        (capsule / "memory/execution").mkdir(parents=True, exist_ok=True)
        runtime._atomic_json(capsule / "memory/execution/stdout.json", result)
        runtime._atomic_bytes(capsule / "memory/execution/stderr.log", b"")
        return {"process_outcome": "SUCCEEDED", "execution_plan_checksum": plan["sha256"], "run_approval_checksum": approval.approval_checksum, "started_at": "2026-08-17T00:00:00Z", "completed_at": "2026-08-17T00:00:01Z", "exit_code": 0, "network_policy": "DISABLED", "stdout_checksum": sha256_bytes((capsule / "memory/execution/stdout.json").read_bytes()), "stderr_checksum": sha256_bytes(b"")}

    monkeypatch.setattr(runtime, "_run_harness", fake_harness)
    monkeypatch.setattr(runtime, "_codex_executable", lambda _value: "fake-codex")
    monkeypatch.setattr(runtime, "_execute", fake_execute)
    monkeypatch.setattr(runtime, "_dependencies_available", lambda: True)
    answer = lambda prompt: prompt.split("`")[1]
    with pytest.raises(runtime.PreparedExperimentError, match="did not finalize"):
        runtime.run(root, "wfi-" + "c" * 32, design_input=answer, run_input=answer, review_input=lambda _prompt: "pause")
    result = runtime.run(root, "wfi-" + "c" * 32, design_input=answer, run_input=answer, review_input=answer)
    artifact = json.loads((root / result["artifact"]["relative_path"]).read_text())
    validated = validate_experiment_record_v3(artifact)
    assert validated["mode"] == "REAGENT_PREPARED"
    assert validated["evaluation"]["validity"] == "VALID"
    assert validated["evaluation"]["scientific_evidence_status"] == "LIMITED"
    assert validated["prepared_package"]["git"] is None
    assert (root / "memory/design-approval.json").is_file()
    assert (root / "memory/prepared-package-receipt.json").is_file()
    assert (root / "memory/run-approval-consumption.json").is_file()
    assert executions == 1
    with pytest.raises(runtime.PreparedExperimentError, match="terminal Progress"):
        runtime.run(root, "wfi-" + "c" * 32)


def test_unresolved_methodology_stops_before_design_or_package(tmp_path: Path) -> None:
    root = _capsule(tmp_path)
    _input(root)
    proposal = _proposal()
    proposal["unresolved_methodological_decisions"] = [{"question": "How many folds?", "material_effects": ["EVALUATION", "REPRODUCIBILITY"]}]
    runtime._atomic_json(root / "memory/methodology-proposal.json", proposal)
    reference, _ = runtime._input(root)
    with pytest.raises(runtime.PreparedExperimentError, match="Owner decision checkpoint"):
        runtime._methodology_from_proposal(root, reference)
    assert not (root / "memory/design-approval.json").exists()
    assert not (root / "memory/preparation").exists()
