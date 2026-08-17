from __future__ import annotations

import math

import pytest

from backend.artifact_references.generic_experiment_contracts import (
    ExperimentRecordV4,
    GenericExperimentArtifactError,
    GenericExperimentPresentation,
    PresentationBlock,
    PresentationKind,
)
from backend.artifact_references.research_flow_contracts import (
    ResearchFlowContractError,
    validate_experiment_record_v3,
)
from backend.workflow_packages.generic_experiment_contracts import (
    CapabilityAssessment,
    CapabilityEvaluationReceipt,
    CapabilityOperation,
    CapabilitySelection,
    CompatibilityStatus,
    ContractRef,
    DesignApproval,
    EvaluationValidity,
    ExactIdentity,
    ExperimentCapability,
    GenericMethodology,
    ImplementationSpecificationRef,
    NamedChecksum,
    NormalizedExperimentResult,
    ProcessOutcome,
    ResearchObjectiveRef,
    RuntimeCompatibility,
    RuntimeRequirement,
    ScientificEvidenceStatus,
    SelectionMateriality,
    SupportStatus,
)
from backend.workflow_packages.generic_experiment_package import (
    ExperimentPackageManifest,
    LaunchTarget,
    PackageOrigin,
    PackageSafetyEvidence,
    PreparedExperimentPackageReceipt,
    ValidatedExperimentPackage,
)

SHA = ["sha256:" + char * 64 for char in "abcdef0123456789"]


def record() -> ExperimentRecordV4:
    objective = ResearchObjectiveRef(
        "selected-research-idea/v1", "artifact-" + "a" * 32, SHA[0],
        "Assess whether a bounded archival transfer preserves categorical provenance statements.",
    )
    methodology = GenericMethodology(
        objective, ("Which provenance statements remain preserved?",),
        ("A reviewed set of source and transferred descriptions",),
        ("Apply a bounded textual concordance rubric.",),
        ("Categorical preserved, changed, or absent observations",),
        ("Every material statement receives exactly one reviewed category.",),
        ("Apply the same rubric and record identity order.",),
        ("No external research Resources are required.",),
        ("One bounded local process lasting under one minute.",), "DISABLED",
        ("Descriptions are authoritative for this bounded check.",),
        ("No claim beyond the reviewed descriptions.",),
    )
    design = DesignApproval.approve(methodology, "2026-08-17T04:00:00Z")
    capability = ExperimentCapability(
        "0.1.0", ExactIdentity("textual-observation-skill", "0.1.0", SHA[1]),
        ExactIdentity("textual-observation-capsule", "0.1.0", SHA[2]),
        "capability/textual_observation", SHA[3],
        tuple(CapabilityOperation), "reagent.fixture.textual-spec/v0.1",
        "reagent.fixture.textual-evaluation/v0.1", "reagent.fixture.textual-presentation/v0.1",
    )
    assessment = CapabilityAssessment(
        capability.capability_checksum, objective.objective_ref_checksum,
        methodology.methodology_checksum, SupportStatus.SUPPORTED,
        ("The reviewed textual capability supports this bounded methodology.",),
    )
    selection = CapabilitySelection(
        methodology.methodology_checksum, (assessment,), SelectionMateriality.NOT_APPLICABLE,
        capability.capability_checksum, "The only supported reviewed capability was selected.", None,
    )
    specification = ImplementationSpecificationRef(
        capability.capability_checksum, capability.implementation_spec_schema or "",
        methodology.methodology_checksum, SHA[4],
        ContractRef("reagent.spec-validation/v0.1", SHA[5]),
        (("Evidence form", "Categorical textual observations."),),
    )
    runtime = RuntimeRequirement(
        "REVIEWED_TEXT_PROCESS", ">=1,<2", ("UTF8_TEXT",), (),
        ContractRef("reagent.launch-contract/local-process/v0.1", SHA[6]),
        "DISABLED", (("wall_time_seconds", "60"),),
    )
    manifest = ExperimentPackageManifest(
        capability.capability_checksum, specification,
        LaunchTarget("bin/textual-review", SHA[7], runtime.launch_contract), (), (),
        (NamedChecksum("objective", objective.source_artifact_checksum),), (),
        runtime.requirement_checksum,
        (NamedChecksum("categorical-observations", SHA[8]),),
    )
    prepared = PreparedExperimentPackageReceipt(
        PackageOrigin.REAGENT_PREPARED, objective, methodology.methodology_checksum,
        ExactIdentity("textual-observation-capability", "0.1.0", capability.capability_checksum),
        specification, SHA[9], manifest.manifest_checksum, manifest.launch_target.checksum,
        (), runtime, (),
        ExactIdentity("reproduction-experiment-local-experimental", "0.6.0", SHA[10]),
        ExactIdentity("generic-experiment-capsule", "0.9.0", SHA[11]), None, None,
        "2026-08-17T04:01:00Z",
    )
    validated = ValidatedExperimentPackage(
        manifest, prepared, prepared.package_tree_checksum, runtime.requirement_checksum,
        (), PackageSafetyEvidence(True, True, True, True, True, True, True),
        "VALIDATED", "2026-08-17T04:02:00Z",
    )
    compatibility = RuntimeCompatibility(
        runtime.requirement_checksum, SHA[12], SHA[13], CompatibilityStatus.COMPATIBLE,
        ("A reviewed local text-process runtime is compatible.",), "2026-08-17T04:03:00Z",
    )
    plan = ContractRef("reagent.experiment-execution-plan/v0.2", SHA[14])
    evaluation = CapabilityEvaluationReceipt(
        capability.capability_checksum, objective.objective_ref_checksum,
        methodology.methodology_checksum, specification.specification_checksum,
        plan.checksum, (NamedChecksum("categorical-observations", SHA[8]),), SHA[15],
        capability.evaluation_schema or "", SHA[6], EvaluationValidity.VALID,
        ("The evidence covers only the reviewed descriptions.",), "2026-08-17T04:04:00Z",
    )
    return ExperimentRecordV4(
        objective, methodology, design, selection, capability, specification, (),
        validated, runtime, compatibility, plan,
        ContractRef("reagent.experiment-run-approval/v0.2", SHA[5]), evaluation,
        NormalizedExperimentResult(
            ProcessOutcome.SUCCEEDED, EvaluationValidity.VALID,
            ScientificEvidenceStatus.LIMITED, ("Bounded source set.",),
        ),
        ContractRef("reagent.experiment-owner-result-review/v0.1", SHA[4]),
        ContractRef("reagent.artifact-presentation.experiment-record/v0.2", SHA[3]),
        ("No claim beyond the reviewed descriptions.",),
    )


def test_non_ml_v4_proves_generic_core_has_no_metric_cv_or_python_requirement() -> None:
    value = record()
    serialized = value.canonical_json().lower()
    for forbidden in ("sklearn", "knn", "cross-validation", '"metrics"', "python"):
        assert forbidden not in serialized
    assert value.schema == "experiment-record/v4"
    assert value.record_checksum == record().record_checksum
    with pytest.raises(ResearchFlowContractError):
        validate_experiment_record_v3(value.to_dict())


def test_safe_presentation_supports_all_generic_primitives_and_non_metric_evidence() -> None:
    blocks = (
        PresentationBlock(PresentationKind.PROSE, "Finding", "Two statements were preserved and one changed."),
        PresentationBlock(PresentationKind.SCALAR, "Review complete", True),
        PresentationBlock(PresentationKind.TABLE, "Categorical observations", {
            "columns": ("Statement", "Status"),
            "rows": (("Creator", "preserved"), ("Custody", "changed")),
        }),
        PresentationBlock(PresentationKind.SERIES, "Review order", (
            {"x": "first", "y": "preserved"}, {"x": "second", "y": "changed"},
        )),
        PresentationBlock(PresentationKind.FIGURE_REFERENCE, "Rendered concordance", {
            "output_id": "output-concordance-figure", "checksum": SHA[0],
        }),
        PresentationBlock(PresentationKind.OUTPUT_REFERENCE, "Complete observations", {
            "output_id": "output-categorical-observations", "checksum": SHA[1],
        }),
    )
    presentation = GenericExperimentPresentation(
        "artifact-" + "b" * 32, SHA[2], blocks,
    )
    assert presentation.presentation_checksum


@pytest.mark.parametrize("value", ("/Users/alice/private", "```python", "Traceback secret"))
def test_presentation_rejects_private_paths_code_and_logs(value: str) -> None:
    with pytest.raises(GenericExperimentArtifactError):
        PresentationBlock(PresentationKind.PROSE, "Unsafe", value)


def test_presentation_rejects_nan_and_unbounded_shapes() -> None:
    with pytest.raises(GenericExperimentArtifactError, match="scalar"):
        PresentationBlock(PresentationKind.SCALAR, "Invalid", math.nan)
    with pytest.raises(GenericExperimentArtifactError, match="row bound"):
        PresentationBlock(PresentationKind.TABLE, "Too many", {
            "columns": ("Value",), "rows": tuple((index,) for index in range(101)),
        })
