from __future__ import annotations

import pytest

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
    GenericExperimentContractError,
    GenericMethodology,
    ImplementationSpecificationRef,
    LocalRuntimeCandidate,
    NamedChecksum,
    NormalizedExperimentResult,
    ProcessOutcome,
    ResearchObjectiveRef,
    RuntimeCompatibility,
    RuntimeRequirement,
    ScientificEvidenceStatus,
    SelectionMateriality,
    SelectionOutcome,
    SupportStatus,
)

SHA = ["sha256:" + char * 64 for char in "abcdef0123456789"]


def objective(*, artifact_type: str = "selected-research-idea/v1") -> ResearchObjectiveRef:
    return ResearchObjectiveRef(
        artifact_type, "artifact-" + "a" * 32, SHA[0],
        "Determine whether archival descriptions preserve the stated provenance.",
    )


def methodology(*, protocol: str = "Compare the source and preserved descriptions.", unresolved=()) -> GenericMethodology:
    return GenericMethodology(
        objective(), ("Are essential provenance statements preserved?",),
        ("A bounded set of archival descriptions",), (protocol,),
        ("A categorical concordance record",),
        ("Every material statement is classified as preserved, changed, or absent.",),
        ("Use the same reviewed coding rubric for every record.",),
        ("No external Resources are required.",), ("Complete within one local minute.",),
        "DISABLED", ("The supplied descriptions are authoritative for this check.",),
        ("Findings apply only to the reviewed records.",), unresolved,
    )


def capability(char: str = "1") -> ExperimentCapability:
    return ExperimentCapability(
        "0.1.0",
        ExactIdentity(f"textual-observation-skill-{char}", "0.1.0", "sha256:" + char * 64),
        ExactIdentity(f"textual-observation-capsule-{char}", "0.1.0", "sha256:" + char * 64),
        "capability/prepare", "sha256:" + char * 64,
        (
            CapabilityOperation.ASSESS_SUPPORT, CapabilityOperation.PREPARE,
            CapabilityOperation.DECLARE_REQUIREMENTS, CapabilityOperation.EVALUATE,
            CapabilityOperation.PRESENT,
        ),
        "reagent.fixture.textual-spec/v0.1",
        "reagent.fixture.textual-evaluation/v0.1",
        "reagent.fixture.textual-presentation/v0.1",
    )


def assessment(current: ExperimentCapability, status: SupportStatus, order: int = 0) -> CapabilityAssessment:
    return CapabilityAssessment(
        current.capability_checksum, objective().objective_ref_checksum,
        methodology().methodology_checksum, status, ("Bounded reviewed support assessment.",), order,
    )


def test_objective_and_methodology_are_generic_deterministic_and_drift_sensitive() -> None:
    assert objective().objective_ref_checksum == objective().objective_ref_checksum
    assert methodology().methodology_checksum == methodology().methodology_checksum
    changed = methodology(protocol="Use a second reviewed comparison protocol.")
    assert changed.methodology_checksum != methodology().methodology_checksum
    assert not hasattr(methodology(), "dataset")
    with pytest.raises(GenericExperimentContractError, match="unsupported"):
        objective(artifact_type="future-reproduction-objective/v1")

    approval = DesignApproval.approve(methodology(), "2026-08-17T02:00:00Z")
    approval.validate(methodology())
    with pytest.raises(GenericExperimentContractError, match="drift"):
        approval.validate(changed)
    with pytest.raises(GenericExperimentContractError, match="unresolved"):
        DesignApproval.approve(methodology(unresolved=("Choose the material coding rule.",)), "2026-08-17T02:00:00Z")


def test_capability_is_exact_reviewed_identity_without_closed_scientific_enum() -> None:
    current = capability()
    assert current.capability_checksum == capability().capability_checksum
    assert current.skill.identity.startswith("textual-observation")
    assert current.implementation_spec_schema == "reagent.fixture.textual-spec/v0.1"
    with pytest.raises(ValueError):
        ExperimentCapability(
            "0.1.0", current.skill, current.capsule, "../escape", SHA[1],
            (CapabilityOperation.PREPARE,),
        )


def test_capability_selection_preserves_material_owner_decisions() -> None:
    one = capability("1")
    none_available = CapabilitySelection(
        methodology().methodology_checksum, (), SelectionMateriality.NOT_APPLICABLE,
        None, "No reviewed Capability is pinned for assessment.", None,
    )
    assert none_available.outcome is SelectionOutcome.AUTOMATIC_PREPARATION_UNSUPPORTED
    unsupported = CapabilitySelection(
        methodology().methodology_checksum,
        (assessment(one, SupportStatus.UNSUPPORTED),),
        SelectionMateriality.NOT_APPLICABLE, None, "No reviewed capability supports this methodology.", None,
    )
    assert unsupported.outcome is SelectionOutcome.AUTOMATIC_PREPARATION_UNSUPPORTED
    awaiting = CapabilitySelection(
        methodology().methodology_checksum,
        (assessment(one, SupportStatus.NEEDS_OWNER_DECISION),),
        SelectionMateriality.NOT_APPLICABLE, None,
        "A material methodology decision must be resolved before support can be assessed.", None,
    )
    assert awaiting.outcome is SelectionOutcome.CAPABILITY_ASSESSMENT_OWNER_DECISION_REQUIRED

    automatic = CapabilitySelection(
        methodology().methodology_checksum,
        (assessment(one, SupportStatus.SUPPORTED),),
        SelectionMateriality.NOT_APPLICABLE, one.capability_checksum,
        "The only supported reviewed capability was selected.", None,
    )
    assert automatic.outcome is SelectionOutcome.AUTO_SELECTED

    two = capability("2")
    material = CapabilitySelection(
        methodology().methodology_checksum,
        (assessment(one, SupportStatus.SUPPORTED), assessment(two, SupportStatus.SUPPORTED)),
        SelectionMateriality.MATERIAL_DIFFERENCE, None,
        "The supported capabilities make materially different choices.", None,
    )
    assert material.outcome is SelectionOutcome.PREPARATION_CAPABILITY_SELECTION_REQUIRED
    with pytest.raises(GenericExperimentContractError, match="Owner confirmation"):
        CapabilitySelection(
            methodology().methodology_checksum,
            material.assessments, SelectionMateriality.MATERIAL_DIFFERENCE,
            one.capability_checksum, "Priority cannot decide a material choice.", None,
        )

    fallback = CapabilitySelection(
        methodology().methodology_checksum,
        (assessment(one, SupportStatus.SUPPORTED, 5), assessment(two, SupportStatus.SUPPORTED, 1)),
        SelectionMateriality.NON_MATERIAL_FALLBACK_EQUIVALENT, two.capability_checksum,
        "The reviewed alternatives are explicitly fallback-equivalent.", None,
    )
    assert fallback.outcome is SelectionOutcome.AUTO_SELECTED
    assert fallback.selection_checksum == CapabilitySelection(
        fallback.methodology_checksum, fallback.assessments, fallback.materiality,
        fallback.selected_capability_checksum, fallback.rationale, None,
    ).selection_checksum


def test_specification_reference_is_checksum_only_and_rejects_executable_summary() -> None:
    current = capability()
    reference = ImplementationSpecificationRef(
        current.capability_checksum, current.implementation_spec_schema or "",
        methodology().methodology_checksum, SHA[3], ContractRef("reagent.spec-validation/v0.1", SHA[4]),
        (("Coding scheme", "Preserved, changed, or absent."),),
    )
    assert reference.specification_checksum == SHA[3]
    assert "scientific_fields" not in reference.to_dict()
    with pytest.raises(GenericExperimentContractError, match="non-executable"):
        ImplementationSpecificationRef(
            current.capability_checksum, current.implementation_spec_schema or "",
            methodology().methodology_checksum, SHA[3], ContractRef("reagent.spec-validation/v0.1", SHA[4]),
            (("Implementation", "```python\nprint('no')\n```"),),
        )


def test_runtime_contracts_are_language_neutral_and_local_path_stays_local() -> None:
    requirement = RuntimeRequirement(
        "REVIEWED_LOCAL_PROCESS", ">=1,<2", ("UTF8_TEXT",), (),
        ContractRef("reagent.launch-contract/local-process/v0.1", SHA[5]),
        "DISABLED", (("wall_time_seconds", "60"),),
    )
    candidate = LocalRuntimeCandidate(
        "local-runtime-1", "REVIEWED_LOCAL_PROCESS", "1.2",
        "/opt/reagent/bin/reviewed-process", ("UTF8_TEXT",), SHA[6], (), True,
    )
    assert "local_launcher_path" not in candidate.portable_identity()
    compatible = RuntimeCompatibility(
        requirement.requirement_checksum, candidate.portable_identity_checksum,
        candidate.environment_checksum, CompatibilityStatus.COMPATIBLE,
        ("The reviewed local runtime satisfies the declared launch contract.",),
        "2026-08-17T02:01:00Z",
    )
    assert compatible.compatibility_checksum
    assert "python" not in requirement.canonical_json().lower()


def test_evaluation_and_normalized_status_do_not_equate_process_and_evidence() -> None:
    current = capability()
    receipt = CapabilityEvaluationReceipt(
        current.capability_checksum, objective().objective_ref_checksum,
        methodology().methodology_checksum, SHA[3], SHA[4],
        (NamedChecksum("categorical-observations", SHA[5]),), SHA[6],
        current.evaluation_schema or "", SHA[7], EvaluationValidity.VALID,
        ("The reviewed sample is bounded.",), "2026-08-17T02:02:00Z",
    )
    assert receipt.evaluation_checksum
    result = NormalizedExperimentResult(
        ProcessOutcome.SUCCEEDED, EvaluationValidity.VALID,
        ScientificEvidenceStatus.LIMITED, ("Only reviewed records are covered.",),
    )
    assert result.scientific_evidence_status is ScientificEvidenceStatus.LIMITED
    with pytest.raises(GenericExperimentContractError, match="non-successful"):
        NormalizedExperimentResult(
            ProcessOutcome.FAILED, EvaluationValidity.VALID,
            ScientificEvidenceStatus.LIMITED, ("Execution failed.",),
        )
