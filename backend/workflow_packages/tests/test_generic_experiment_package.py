from __future__ import annotations

import pytest

from backend.workflow_packages.generic_experiment_contracts import (
    ContractRef,
    ExactIdentity,
    ImplementationSpecificationRef,
    NamedChecksum,
    ResearchObjectiveRef,
    RuntimeRequirement,
)
from backend.workflow_packages.generic_experiment_package import (
    DependencyDeclaration,
    ExperimentPackageManifest,
    GenericExperimentPackageError,
    LaunchTarget,
    PackageOrigin,
    PackageSafetyEvidence,
    PreparedExperimentPackageReceipt,
    ValidatedExperimentPackage,
)

SHA = ["sha256:" + char * 64 for char in "abcdef0123456789"]


def package(dependencies: tuple[DependencyDeclaration, ...] = ()) -> ValidatedExperimentPackage:
    capability = ExactIdentity("textual-observation-capability", "0.1.0", SHA[0])
    objective = ResearchObjectiveRef(
        "selected-research-idea/v1", "artifact-" + "a" * 32, SHA[1],
        "Review a bounded set of archival descriptions.",
    )
    specification = ImplementationSpecificationRef(
        capability.checksum, "reagent.fixture.textual-spec/v0.1", SHA[2], SHA[3],
        ContractRef("reagent.spec-validation/v0.1", SHA[4]),
    )
    runtime = RuntimeRequirement(
        "REVIEWED_LOCAL_PROCESS", ">=1,<2", (),
        tuple(ContractRef("reagent.dependency-declaration/v0.1", item.checksum) for item in dependencies),
        ContractRef("reagent.launch-contract/local-process/v0.1", SHA[5]),
        "DISABLED", (("wall_time_seconds", "60"),),
    )
    manifest = ExperimentPackageManifest(
        capability.checksum, specification,
        LaunchTarget("bin/reviewed-process", SHA[6], runtime.launch_contract),
        dependencies, (NamedChecksum("coding-rubric", SHA[7]),),
        (NamedChecksum("research-objective", objective.source_artifact_checksum),),
        (), runtime.requirement_checksum,
        (NamedChecksum("categorical-observations", SHA[8]),),
    )
    receipt = PreparedExperimentPackageReceipt(
        PackageOrigin.REAGENT_PREPARED, objective, SHA[2], capability, specification,
        SHA[9], manifest.manifest_checksum, manifest.launch_target.checksum,
        tuple(item.checksum for item in dependencies), runtime, (),
        ExactIdentity("reproduction-experiment-local-experimental", "0.6.0", SHA[10]),
        ExactIdentity("generic-experiment-capsule", "0.9.0", SHA[11]),
        ExactIdentity("codex-harness", "1.0.0", SHA[12]), None,
        "2026-08-17T03:00:00Z",
    )
    safety = PackageSafetyEvidence(True, True, True, True, True, True, True)
    return ValidatedExperimentPackage(
        manifest, receipt, receipt.package_tree_checksum, runtime.requirement_checksum,
        (), safety, "VALIDATED", "2026-08-17T03:01:00Z",
    )


@pytest.mark.parametrize("count", (0, 1, 3))
def test_package_v02_supports_zero_one_or_multiple_dependency_declarations(count: int) -> None:
    dependencies = tuple(
        DependencyDeclaration("LOCK_OR_CAPABILITY_DECLARATION", f"deps/dependency-{index}.lock", SHA[index])
        for index in range(count)
    )
    result = package(dependencies)
    assert len(result.manifest.dependency_declarations) == count
    assert result.prepared_receipt.origin is PackageOrigin.REAGENT_PREPARED
    assert "python" not in result.canonical_json().lower()


@pytest.mark.parametrize("path", ("../escape", "/tmp/launch", "bin\\launch"))
def test_package_v02_rejects_unsafe_launch_and_dependency_paths(path: str) -> None:
    with pytest.raises(ValueError):
        LaunchTarget(path, SHA[0], ContractRef("reagent.launch-contract/local-process/v0.1", SHA[1]))


def test_package_v02_requires_independent_safety_and_exact_lineage() -> None:
    with pytest.raises(GenericExperimentPackageError, match="every package safety"):
        PackageSafetyEvidence(True, True, False, True, True, True, True)
    current = package()
    with pytest.raises(GenericExperimentPackageError, match="lineage mismatch"):
        ValidatedExperimentPackage(
            current.manifest, current.prepared_receipt, current.package_tree_checksum,
            SHA[13], (), current.safety, "VALIDATED", current.validated_at,
        )


def test_path_a_and_future_path_b_share_the_same_validated_contract() -> None:
    current = package()
    receipt = current.prepared_receipt
    local = PreparedExperimentPackageReceipt(
        PackageOrigin.LOCAL_PROJECT, receipt.research_objective, receipt.methodology_checksum,
        receipt.capability, receipt.implementation_specification,
        receipt.package_tree_checksum, receipt.manifest_checksum,
        receipt.launch_target_checksum, receipt.dependency_declaration_checksums,
        receipt.runtime_requirement, receipt.resource_identity_checksums,
        receipt.workflow, receipt.capsule, receipt.harness,
        ContractRef("reagent.local-project-origin/v0.1", SHA[14]), receipt.prepared_at,
    )
    converged = ValidatedExperimentPackage(
        current.manifest, local, current.package_tree_checksum,
        current.runtime_requirement_checksum, (), current.safety,
        "VALIDATED", current.validated_at,
    )
    assert type(converged) is type(current)
    assert converged.prepared_receipt.origin is PackageOrigin.LOCAL_PROJECT
