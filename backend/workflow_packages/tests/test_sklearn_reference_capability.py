from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from backend.workflow_packages.generic_experiment_contracts import (
    ContractRef, GenericMethodology, NamedChecksum, ProcessOutcome,
    ResearchObjectiveRef, SupportStatus,
)
from backend.workflow_packages.generic_experiment_coordinator import ExecutionOutput
from backend.workflow_packages.experiment_capability_runtime import CapabilityPreparationContext
from backend.workflow_packages.serialization import sha256_bytes
from backend.workflow_packages.sklearn_reference_capability import (
    REFERENCE_CAPABILITY, REFERENCE_DESCRIPTOR, SklearnReferenceCapability,
)
from backend.workflow_packages.sklearn_tabular_builder import SklearnTabularClassificationSpec

SHA = ["sha256:" + char * 64 for char in "abcdef0123456789"]


def method() -> GenericMethodology:
    objective = ResearchObjectiveRef(
        "selected-research-idea/v1", "artifact-" + "a" * 32, SHA[0],
        "Compare nearest-neighbor classification conditions on Wine.",
    )
    return GenericMethodology(
        objective, ("How does nearest-neighbor classification behave?",),
        ("The reviewed Wine reference corpus",),
        ("Use stratified folds and compare raw, standard, and minmax conditions.",),
        ("Accuracy and categorical condition results",),
        ("Report accuracy and macro F1 for every neighbor condition.",),
        ("Use repeated stratified evaluation and a bounded neighbor check.",),
        ("No external research Resource.",), ("Bounded local execution.",),
        "DISABLED", ("The reviewed corpus is fixed.",),
        ("Claims remain bounded to the reference design.",),
    )


def test_reference_capability_owns_support_spec_runtime_and_evaluation_without_execution(tmp_path):
    implementation = SklearnReferenceCapability()
    current = method()
    assert REFERENCE_DESCRIPTOR.classification == "REFERENCE_EXPERIMENT_CAPABILITY"
    assert REFERENCE_CAPABILITY.interface_version == "0.1.0"
    assert implementation.assess_support(current.research_objective, current).status is SupportStatus.SUPPORTED
    spec = SklearnTabularClassificationSpec.create(
        methodology_checksum=current.methodology_checksum, dataset="SKLEARN_WINE",
        estimator="KNEIGHBORS_CLASSIFIER",
        conditions=("RAW", "STANDARD_SCALER", "MINMAX_SCALER"), n_neighbors=5,
        cv_splits=5, cv_repeats=2, cv_seed=17,
        metrics=("accuracy", "macro_f1"), robustness_neighbors=(3, 5, 7),
        result_schema="reagent.experiment-result/v0.2",
    )
    validated = implementation.validate_specification(current, spec.to_dict())
    requirements = implementation.declare_requirements(current, validated)
    assert requirements.runtime_requirement.runtime_family == "PYTHON"
    assert requirements.runtime_requirement.required_capabilities == ("NUMPY", "SCIKIT_LEARN")
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()
    candidate = implementation.prepare(candidate_root, CapabilityPreparationContext(
        current.research_objective, current, validated, requirements, (),
        "2026-08-17T08:59:00Z",
    ))
    assert candidate.manifest.launch_target.relative_path == "run_experiment.py"
    assert (candidate_root / "requirements.lock").read_text() == "numpy\nscikit-learn\n"
    content = b'{"schema_version":"reagent.experiment-result/v0.2","conditions":[{"condition":"RAW","metrics":{"accuracy":0.8}}],"robustness":[]}'
    output = NamedChecksum("experiment-result", sha256_bytes(content))
    plan = SimpleNamespace(
        plan_checksum=SHA[1], capability_output_contract=ContractRef("reagent.sklearn-output/v0.1", SHA[2]),
    )
    evidence = SimpleNamespace(outputs=(output,), completed_at="2026-08-17T09:00:00Z", process_outcome=ProcessOutcome.SUCCEEDED)
    evaluated = implementation.evaluate({
        "objective": current.research_objective, "methodology": current,
        "specification": validated, "plan": plan, "execution_evidence": evidence,
        "outputs": (ExecutionOutput("experiment-result", content),),
    })
    assert evaluated.receipt.validity.value == "VALID"
    assert evaluated.scientific_evidence_status == "LIMITED"


def test_generic_coordinator_dependency_scan_and_historical_reference_bytes_are_immutable():
    root = Path(__file__).resolve().parents[3]
    coordinator = root / "backend/workflow_packages/generic_experiment_coordinator.py"
    source = coordinator.read_text(encoding="utf-8")
    imported = {
        alias.name for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names
    }
    assert not any(term in source.casefold() for term in ("sklearn", "knn", "wine", "numpy", "cross-validation", '"metrics"'))
    assert not any(
        forbidden in name for name in imported
        for forbidden in (
            "sklearn", "numpy", "sklearn_tabular_builder",
            "prepared_experiment_runtime", "SklearnTabularClassificationSpec",
        )
    )
    assert sha256_bytes((root / "backend/workflow_packages/prepared_experiment_runtime.py").read_bytes()) == "sha256:024b818c18ff3a77d66e3162f549b05b8db70057a3c87480a9171b8ee3144d3c"
    assert sha256_bytes((root / "backend/workflow_packages/sklearn_tabular_builder.py").read_bytes()) == "sha256:8c7af9ec83ec9fea6aeb707d2a735b9c2f16056655ece8982df0621edcb65b6b"
    assert REFERENCE_CAPABILITY.implementation_entrypoint_checksum == sha256_bytes(
        (root / REFERENCE_CAPABILITY.implementation_entrypoint).read_bytes()
    )
