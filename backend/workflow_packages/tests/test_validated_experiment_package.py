from __future__ import annotations

import pytest

from backend.workflow_packages.experiment_preparation_contracts import (
    BuilderFamily, BuilderIdentity, ExactArtifactReference,
    ExperimentPreparationContractError, HarnessIdentity, PackageOrigin,
    PreparedPackageReceipt, RuntimeIdentity, WorkflowCapsuleIdentity,
)
from backend.workflow_packages.validated_experiment_package import (
    NamedChecksum, PackageSafetyEvidence, ValidatedExperimentPackage,
    VALIDATED_PACKAGE_SCHEMA,
)

SHA = ["sha256:" + char * 64 for char in "abcdef"]


def _receipt() -> PreparedPackageReceipt:
    return PreparedPackageReceipt.create(
        origin_type=PackageOrigin.REAGENT_PREPARED,
        selected_idea=ExactArtifactReference("artifact-" + "a" * 32, "selected-research-idea/v1", SHA[0]),
        workflow_capsule=WorkflowCapsuleIdentity(
            "reproduction-experiment-local-experimental", "0.5.0", SHA[1],
            "capsule-" + "c" * 32, "0.8.0", SHA[2],
        ),
        harness=HarnessIdentity("CODEX", "1", "session-1"),
        builder=BuilderIdentity(BuilderFamily.SKLEARN_TABULAR_CLASSIFICATION_V1, "1", SHA[3]),
        git=None, package_tree_checksum=SHA[0], manifest_checksum=SHA[1],
        entrypoint_checksum=SHA[2], dependency_checksum=SHA[3],
        runtime=RuntimeIdentity("PYTHON", "3.12", SHA[4]),
        prepared_at="2026-08-17T00:00:00Z",
    )


def _safety(**overrides: bool) -> PackageSafetyEvidence:
    values = {field: True for field in PackageSafetyEvidence.__dataclass_fields__}
    values.update(overrides)
    return PackageSafetyEvidence(**values)


def _validated(**overrides) -> ValidatedExperimentPackage:
    receipt = _receipt()
    values = {
        "schema": VALIDATED_PACKAGE_SCHEMA,
        "package_tree_checksum": receipt.package_tree_checksum,
        "manifest_checksum": receipt.manifest_checksum,
        "entrypoint_relative_path": "src/run.py",
        "entrypoint_checksum": receipt.entrypoint_checksum,
        "dependency_relative_path": "requirements.lock",
        "dependency_checksum": receipt.dependency_checksum,
        "runtime": receipt.runtime,
        "configuration_identities": (NamedChecksum("configuration", SHA[5]),),
        "input_identities": (NamedChecksum("selected_research_idea", receipt.selected_idea.sha256),),
        "prepared_package_receipt": receipt,
        "prepared_package_receipt_checksum": receipt.receipt_checksum,
        "selected_idea": receipt.selected_idea,
        "workflow_capsule": receipt.workflow_capsule,
        "harness": receipt.harness,
        "safety": _safety(), "validation_status": "VALIDATED",
        "validated_at": "2026-08-17T00:01:00Z",
    }
    values.update(overrides)
    return ValidatedExperimentPackage(**values)


def test_both_preparation_paths_converge_on_one_validated_package_contract() -> None:
    package = _validated()
    assert package.prepared_package_receipt.origin_type is PackageOrigin.REAGENT_PREPARED
    source = package.prepared_package_receipt
    local_receipt = PreparedPackageReceipt.create(
        origin_type=PackageOrigin.LOCAL_PROJECT, selected_idea=source.selected_idea,
        workflow_capsule=source.workflow_capsule, harness=source.harness,
        builder=None, git=None, package_tree_checksum=source.package_tree_checksum,
        manifest_checksum=source.manifest_checksum,
        entrypoint_checksum=source.entrypoint_checksum,
        dependency_checksum=source.dependency_checksum, runtime=source.runtime,
        prepared_at=source.prepared_at,
    )
    local = _validated(
        prepared_package_receipt=local_receipt,
        prepared_package_receipt_checksum=local_receipt.receipt_checksum,
    )
    assert local.prepared_package_receipt.origin_type is PackageOrigin.LOCAL_PROJECT
    assert type(local) is type(package)


@pytest.mark.parametrize("path", ["/Users/alice/run.py", "../run.py", "src\\run.py"])
def test_validated_package_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(ExperimentPreparationContractError):
        _validated(entrypoint_relative_path=path)


def test_validated_package_requires_all_safety_and_exact_receipt_lineage() -> None:
    with pytest.raises(ExperimentPreparationContractError, match="every safety"):
        _safety(symlinks_rejected=False)
    with pytest.raises(ExperimentPreparationContractError, match="does not match"):
        _validated(entrypoint_checksum=SHA[5])
    with pytest.raises(ExperimentPreparationContractError, match="selected Idea bytes"):
        _validated(input_identities=(NamedChecksum("other_input", SHA[0]),))
