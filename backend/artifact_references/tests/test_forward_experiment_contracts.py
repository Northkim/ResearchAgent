from __future__ import annotations

from copy import deepcopy

import pytest

from backend.artifact_references.presentation_contracts import (
    ArtifactPresentationContractError,
    EXPERIMENT_RECORD_PRESENTATION_SCHEMA,
    validate_experiment_record_presentation,
)
from backend.artifact_references.research_flow_contracts import (
    ARTIFACT_CONTRACTS, FORWARD_ARTIFACT_CONTRACTS, FORWARD_WORKFLOW_CONTRACTS,
    FUTURE_WORKFLOW_CONTRACTS,
    ResearchFlowContractError, validate_experiment_record_v2,
    validate_experiment_record_v3,
)
from backend.workflow_packages.experiment_preparation_contracts import (
    DesignApproval, ExperimentMethodology, PackageOrigin, RunApprovalFoundation,
)
from backend.workflow_packages.sklearn_tabular_builder import (
    SklearnTabularClassificationSpec,
)
from backend.workflow_packages.serialization import canonical_hash
from backend.workflow_packages.tests.test_experiment_preparation_contracts import (
    bounds, methodology, receipt, runtime,
)


def _record(origin: PackageOrigin = PackageOrigin.REAGENT_PREPARED) -> dict:
    initial = methodology()
    method = ExperimentMethodology.create(
        selected_idea=initial.selected_idea,
        frozen_scientific_requirements=initial.frozen_scientific_requirements,
        implementation_decisions=initial.implementation_decisions,
        unresolved_methodological_decisions=(), dataset=initial.dataset,
        experiment_conditions=initial.experiment_conditions,
        evaluation_protocol=initial.evaluation_protocol, metrics=initial.metrics,
        robustness_analysis=initial.robustness_analysis,
        leakage_controls=initial.leakage_controls, seeds=initial.seeds,
        repetitions=initial.repetitions,
        compute_runtime_bounds=initial.compute_runtime_bounds,
        network_policy=initial.network_policy, assumptions=initial.assumptions,
        claim_boundaries=initial.claim_boundaries,
        expected_scientific_outputs=initial.expected_scientific_outputs,
    )
    design = DesignApproval.create(method, approved_at="2026-08-17T00:01:00Z")
    package = receipt(origin)
    plan_value = {
        "package_receipt_checksum": package.receipt_checksum,
        "command": ["python", "src/run.py"], "runtime": runtime().to_dict(),
        "metrics": ["accuracy", "macro-F1"], "run_seed_scope": [11, 29],
        "execution_limits": bounds().to_dict(), "network_policy": "DISABLED",
        "expected_outputs": ["metrics.json"],
    }
    plan = {"sha256": canonical_hash(plan_value), "value": plan_value}
    approval = RunApprovalFoundation.create(
        prepared_package_receipt_checksum=package.receipt_checksum,
        execution_plan_checksum=plan["sha256"], command=tuple(plan_value["command"]),
        runtime=runtime(), metrics=tuple(plan_value["metrics"]),
        run_seed_scope=tuple(plan_value["run_seed_scope"]), execution_limits=bounds(),
        expected_outputs=tuple(plan_value["expected_outputs"]),
        approved_at="2026-08-17T00:02:00Z",
    )
    execution = {
        "process_outcome": "SUCCEEDED", "execution_plan_checksum": plan["sha256"],
        "run_approval_checksum": approval.approval_checksum,
        "started_at": "2026-08-17T00:03:00Z", "completed_at": "2026-08-17T00:04:00Z",
        "exit_code": 0, "network_policy": "DISABLED",
        "stdout_checksum": "sha256:" + "1" * 64,
        "stderr_checksum": "sha256:" + "2" * 64,
    }
    evaluation = {
        "validity": "VALID", "scientific_evidence_status": "LIMITED",
        "metrics": [{"name": "accuracy", "value": 0.81, "unit": None}],
        "comparisons": ["Standardized KNN exceeded the unscaled condition."],
        "robustness_summary": "The bounded neighbor grid retained the direction.",
        "summary": "The controlled Wine evaluation completed.",
    }
    limitations = ["The evidence is Wine-specific."]
    reviewed = canonical_hash({
        "execution": execution, "evaluation": evaluation,
        "result_status": "SUCCEEDED", "limitations": limitations,
    })
    review_payload = {
        "decision": "FINALIZE", "reviewed_at": "2026-08-17T00:05:00Z",
        "reviewed_subject_checksum": reviewed,
    }
    specification = SklearnTabularClassificationSpec.create(
        methodology_checksum=method.methodology_checksum,
        dataset="SKLEARN_WINE", estimator="KNEIGHBORS_CLASSIFIER",
        conditions=("RAW", "STANDARD_SCALER", "MINMAX_SCALER"), n_neighbors=5,
        cv_splits=3, cv_repeats=method.repetitions, cv_seed=method.seeds[0],
        metrics=("accuracy", "macro_f1"), robustness_neighbors=(3, 5, 7),
        result_schema="reagent.experiment-result/v0.2",
    )
    package_value = package.to_dict()
    if origin is PackageOrigin.REAGENT_PREPARED:
        package_value["implementation_specification_checksum"] = specification.specification_checksum
        payload = dict(package_value); payload.pop("receipt_checksum")
        package_value["receipt_checksum"] = canonical_hash(payload)
        from backend.workflow_packages.experiment_preparation_contracts import PreparedPackageReceipt
        package = PreparedPackageReceipt.from_mapping(package_value)
        plan_value["package_receipt_checksum"] = package.receipt_checksum
        plan = {"sha256": canonical_hash(plan_value), "value": plan_value}
        approval = RunApprovalFoundation.create(
            prepared_package_receipt_checksum=package.receipt_checksum,
            execution_plan_checksum=plan["sha256"], command=tuple(plan_value["command"]),
            runtime=runtime(), metrics=tuple(plan_value["metrics"]),
            run_seed_scope=tuple(plan_value["run_seed_scope"]), execution_limits=bounds(),
            expected_outputs=tuple(plan_value["expected_outputs"]),
            approved_at="2026-08-17T00:02:00Z",
        )
        execution["execution_plan_checksum"] = plan["sha256"]
        execution["run_approval_checksum"] = approval.approval_checksum
        reviewed = canonical_hash({"execution": execution, "evaluation": evaluation, "result_status": "SUCCEEDED", "limitations": limitations})
        review_payload["reviewed_subject_checksum"] = reviewed
    return {
        "schema": "experiment-record/v3", "core_capability_maturity": "REVIEWED_CORE",
        "mode": origin.value, "source_artifacts": [method.selected_idea.to_dict()],
        "methodology_contract": method.to_dict(), "design_approval": design.to_dict(),
        "prepared_package": package.to_dict(), "approved_execution_plan": plan,
        "implementation_specification": ({
            "sha256": canonical_hash(specification.to_dict()),
            "value": specification.to_dict(),
        } if origin is PackageOrigin.REAGENT_PREPARED else None),
        "run_approval": approval.to_dict(), "execution": execution,
        "evaluation": evaluation, "result_status": "SUCCEEDED",
        "owner_review": {**review_payload, "review_checksum": canonical_hash(review_payload)},
        "presentation_summary": {
            "title": "Wine KNN scaling experiment", "summary": "A bounded local comparison.",
            "key_findings": ["Scaling changed the bounded Wine result."],
        }, "limitations": limitations,
    }


@pytest.mark.parametrize("origin", list(PackageOrigin))
def test_experiment_record_v3_is_provider_neutral_and_git_optional(origin: PackageOrigin) -> None:
    value = _record(origin)
    validated = validate_experiment_record_v3(value)
    assert validated["mode"] == origin.value
    assert validated["prepared_package"]["git"] is None
    assert validated["execution"]["process_outcome"] == "SUCCEEDED"
    assert validated["evaluation"]["validity"] == "VALID"
    assert validated["evaluation"]["scientific_evidence_status"] == "LIMITED"


def test_v3_rejects_checksum_drift_and_remains_isolated_from_v2() -> None:
    value = _record()
    value["prepared_package"]["package_tree_checksum"] = "sha256:" + "9" * 64
    with pytest.raises(ResearchFlowContractError, match="receipt checksum mismatch"):
        validate_experiment_record_v3(value)
    with pytest.raises(ResearchFlowContractError, match="experiment record v2"):
        validate_experiment_record_v2(_record())
    assert ARTIFACT_CONTRACTS["experiment-record/v3"].production_producer_available is True
    assert FORWARD_ARTIFACT_CONTRACTS["experiment-record/v3"].production_producer_available is True


def test_v3_keeps_process_evaluation_evidence_and_limitations_distinct() -> None:
    value = _record()
    value["evaluation"]["scientific_evidence_status"] = "UNAVAILABLE"
    with pytest.raises(ResearchFlowContractError, match="unavailable scientific evidence"):
        validate_experiment_record_v3(value)
    value = _record()
    value["execution"]["process_outcome"] = "FAILED"
    with pytest.raises(ResearchFlowContractError, match="successful v3 result"):
        validate_experiment_record_v3(value)


def _presentation() -> dict:
    value = {
        "schema": EXPERIMENT_RECORD_PRESENTATION_SCHEMA,
        "artifact": {"artifact_id": "artifact-" + "b" * 32, "artifact_type": "experiment-record/v3", "sha256": "sha256:" + "b" * 64},
        "selected_idea_summary": {
            "title": "Wine scaling", "research_question": "Does scaling improve KNN?",
            "dataset": "Wine classification dataset", "claim_boundary": "Wine-specific only",
        },
        "experiment_source_mode": "REAGENT_PREPARED",
        "methodology_summary": {
            "conditions": ["Unscaled", "StandardScaler", "MinMaxScaler"],
            "evaluation_protocol": ["Repeated stratified cross-validation"],
            "metrics": ["accuracy", "macro-F1"], "robustness_analysis": ["Neighbor sensitivity"],
            "leakage_controls": ["Scaling inside folds"], "reproducibility_controls": ["Controlled seeds"],
            "claim_boundaries": ["Wine-specific only"],
        },
        "preparation_status": "VALIDATED", "design_approval_status": "APPROVED",
        "run_approval_status": "CONSUMED", "provenance_status": "VALIDATED",
        "execution_outcome": "SUCCEEDED",
        "primary_metrics": [{"name": "accuracy", "value": 0.81, "unit": None}],
        "comparisons": ["StandardScaler exceeded unscaled KNN."],
        "robustness_summary": "The bounded result persisted across neighbors.",
        "scientific_evidence_status": "LIMITED", "limitations": ["One dataset."],
    }
    return {**value, "presentation_checksum": canonical_hash(value)}


def test_presentation_is_exact_artifact_bound_and_bounded() -> None:
    value = _presentation()
    assert validate_experiment_record_presentation(value)["artifact"]["artifact_type"] == "experiment-record/v3"
    for forbidden in ("/Users/alice/project", "```python", "Traceback (most recent call last)"):
        changed = deepcopy(value)
        changed["limitations"] = [forbidden]
        payload = dict(changed)
        payload.pop("presentation_checksum")
        changed["presentation_checksum"] = canonical_hash(payload)
        with pytest.raises(ArtifactPresentationContractError, match="source, logs, credentials, or local paths"):
            validate_experiment_record_presentation(changed)
    extra = {**value, "source_code": "print('no')"}
    with pytest.raises(ArtifactPresentationContractError, match="fields mismatch"):
        validate_experiment_record_presentation(extra)


def test_forward_chain_is_reserved_exact_and_historical_consumers_stay_v2_only() -> None:
    assert [(key, item.workflow_version, item.capsule_version, item.output_artifact_type, item.published) for key, item in FORWARD_WORKFLOW_CONTRACTS.items()] == [
        ("initial-writing", "0.5.0", "0.7.0", "manuscript-draft/v4", False),
        ("review", "0.4.0", "0.6.0", "review-report/v3", False),
        ("writing-revision", "0.6.0", "0.8.0", "manuscript-draft/v5", False),
    ]
    assert FORWARD_WORKFLOW_CONTRACTS["initial-writing"].inputs[-1].artifact_type == "experiment-record/v3"
    assert all(dependency.artifact_type != "experiment-record/v3" for dependency in FUTURE_WORKFLOW_CONTRACTS["writing"].inputs)
