from __future__ import annotations

import pytest

from backend.workflow_packages.experiment_preparation_contracts import (
    BuilderFamily,
    BuilderIdentity,
    ComputeRuntimeBounds,
    DesignApproval,
    ExactArtifactReference,
    ExperimentMethodology,
    ExperimentPreparationContractError,
    FORWARD_EXPERIMENT_ARTIFACT_TYPE,
    FORWARD_EXPERIMENT_CAPSULE_VERSION,
    FORWARD_EXPERIMENT_DEFINITION_VERSION,
    HarnessIdentity,
    ImplementationDecision,
    MethodologicalEffect,
    PackageOrigin,
    PreparedPackageReceipt,
    RunApprovalFoundation,
    RuntimeIdentity,
    SanitizedGitProvenance,
    UnresolvedMethodologicalDecision,
    WorkflowCapsuleIdentity,
)
from backend.workflow_packages.serialization import canonical_hash

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64


def idea() -> ExactArtifactReference:
    return ExactArtifactReference("artifact-" + "a" * 32, "selected-research-idea/v1", SHA_A)


def workflow() -> WorkflowCapsuleIdentity:
    return WorkflowCapsuleIdentity(
        "reproduction-experiment-local-experimental", "0.5.0", SHA_A,
        "capsule-" + "b" * 32, "0.8.0", SHA_B,
    )


def runtime() -> RuntimeIdentity:
    return RuntimeIdentity("PYTHON", "3.12", SHA_C)


def bounds() -> ComputeRuntimeBounds:
    return ComputeRuntimeBounds(30, 120, 2, 1_000_000)


def methodology(*, dataset: str = "scikit-learn Wine") -> ExperimentMethodology:
    return ExperimentMethodology.create(
        selected_idea=idea(),
        frozen_scientific_requirements=("Compare unscaled, StandardScaler, and MinMaxScaler KNN.",),
        implementation_decisions=(ImplementationDecision("Use sklearn Pipelines.", "Prevents leakage.", True),),
        unresolved_methodological_decisions=(UnresolvedMethodologicalDecision(
            "Choose the bounded neighbor grid.", (MethodologicalEffect.EVALUATION,),
        ),),
        dataset=dataset,
        experiment_conditions=("Unscaled KNN", "StandardScaler plus KNN", "MinMaxScaler plus KNN"),
        evaluation_protocol=("Repeated stratified cross-validation",),
        metrics=("accuracy", "macro-F1"),
        robustness_analysis=("Bounded neighbor-count sensitivity",),
        leakage_controls=("Fit scaling inside each training fold",),
        seeds=(11, 29), repetitions=2, compute_runtime_bounds=bounds(),
        network_policy="DISABLED", assumptions=("Bundled dataset is sufficient.",),
        claim_boundaries=("Wine-specific conclusions only.",),
        expected_scientific_outputs=("Condition metrics", "Robustness summary"),
    )


def receipt(origin: PackageOrigin, *, git=None) -> PreparedPackageReceipt:
    builder = None
    if origin is PackageOrigin.REAGENT_PREPARED:
        builder = BuilderIdentity(BuilderFamily.SKLEARN_TABULAR_CLASSIFICATION_V1, "1", SHA_D)
    return PreparedPackageReceipt.create(
        origin_type=origin, selected_idea=idea(), workflow_capsule=workflow(),
        harness=HarnessIdentity("CODEX", "1", "session-bounded"), builder=builder, git=git,
        implementation_specification_checksum=(SHA_D if builder is not None else None),
        package_tree_checksum=SHA_A, manifest_checksum=SHA_B,
        entrypoint_checksum=SHA_C, dependency_checksum=SHA_D, runtime=runtime(),
        prepared_at="2026-08-17T00:00:00Z",
    )


def test_methodology_is_versioned_deterministic_and_design_approval_drift_sensitive() -> None:
    first = methodology()
    assert first.schema == "reagent.experiment-methodology/v0.1"
    assert ExperimentMethodology.from_mapping(first.to_dict()) == first
    assert methodology().methodology_checksum == first.methodology_checksum
    approval = DesignApproval.create(first, approved_at="2026-08-17T00:01:00Z")
    approval.validate_methodology(first)
    changed = methodology(dataset="A different dataset")
    assert changed.methodology_checksum != first.methodology_checksum
    with pytest.raises(ExperimentPreparationContractError, match="drift"):
        approval.validate_methodology(changed)
    assert approval.authorization_scope == "IMPLEMENTATION_PREPARATION_ONLY"
    assert (FORWARD_EXPERIMENT_DEFINITION_VERSION, FORWARD_EXPERIMENT_CAPSULE_VERSION, FORWARD_EXPERIMENT_ARTIFACT_TYPE) == (
        "0.5.0", "0.8.0", "experiment-record/v3",
    )


def test_methodology_rejects_missing_and_unjustified_implementation_decisions() -> None:
    value = methodology().to_dict()
    value.pop("dataset")
    with pytest.raises(ExperimentPreparationContractError, match="fields mismatch"):
        ExperimentMethodology.from_mapping(value)
    with pytest.raises(ExperimentPreparationContractError, match="scientific meaning"):
        ImplementationDecision("Change dataset.", "Convenience.", False)


@pytest.mark.parametrize("origin", list(PackageOrigin))
def test_prepared_receipt_supports_each_provider_neutral_origin(origin: PackageOrigin) -> None:
    git = SanitizedGitProvenance(origin is PackageOrigin.LOCAL_PROJECT, "a" * 40, None) if origin is not PackageOrigin.REAGENT_PREPARED else None
    current = receipt(origin, git=git)
    assert current.schema == "reagent.prepared-experiment-package/v0.1"
    assert PreparedPackageReceipt.from_mapping(current.to_dict()) == current
    assert receipt(origin, git=git).receipt_checksum == current.receipt_checksum
    assert current.package_tree_checksum == SHA_A


def test_git_is_optional_truthful_and_credential_free() -> None:
    non_git = receipt(PackageOrigin.LOCAL_PROJECT)
    assert non_git.git is None
    dirty = receipt(PackageOrigin.LOCAL_PROJECT, git=SanitizedGitProvenance(True, "b" * 40, "github.com/owner/repo"))
    assert dirty.git and dirty.git.dirty and dirty.package_tree_checksum == SHA_A
    clean_no_remote = receipt(PackageOrigin.LOCAL_PROJECT, git=SanitizedGitProvenance(False, "c" * 40, None))
    assert clean_no_remote.git and clean_no_remote.git.remote_identity is None
    with pytest.raises(ExperimentPreparationContractError, match="credential-free"):
        SanitizedGitProvenance(False, "d" * 40, "https://user:secret@example.com/repo")


def test_receipt_rejects_absolute_path_fields_and_checksum_tamper() -> None:
    current = receipt(PackageOrigin.LOCAL_PROJECT).to_dict()
    current["git"] = {"dirty": False, "head_revision": "a" * 40, "remote_identity": "/Users/alice/project"}
    with pytest.raises(ExperimentPreparationContractError):
        PreparedPackageReceipt.from_mapping(current)
    current = receipt(PackageOrigin.LOCAL_PROJECT).to_dict()
    current["harness"]["session_id"] = "/Users/alice/private"
    with pytest.raises(ExperimentPreparationContractError, match="machine-specific"):
        PreparedPackageReceipt.from_mapping(current)
    current = receipt(PackageOrigin.LOCAL_PROJECT).to_dict()
    current["package_tree_checksum"] = SHA_D
    with pytest.raises(ExperimentPreparationContractError, match="receipt checksum mismatch"):
        PreparedPackageReceipt.from_mapping(current)


def test_run_approval_is_one_use_scoped_and_drift_sensitive() -> None:
    package = receipt(PackageOrigin.REAGENT_PREPARED)
    plan = {"command": ["python", "run.py"], "metrics": ["accuracy"]}
    approval = RunApprovalFoundation.create(
        prepared_package_receipt_checksum=package.receipt_checksum,
        execution_plan_checksum=canonical_hash(plan), command=("python", "run.py"),
        runtime=runtime(), metrics=("accuracy",), run_seed_scope=(11,),
        execution_limits=bounds(), expected_outputs=("metrics.json",),
        approved_at="2026-08-17T00:02:00Z",
    )
    approval.validate_execution_plan(plan, package)
    assert approval.scope == "ONE_EXECUTION"
    with pytest.raises(ExperimentPreparationContractError, match="drift"):
        approval.validate_execution_plan({"command": ["python", "other.py"]}, package)
    assert RunApprovalFoundation.from_mapping(approval.to_dict()) == approval
