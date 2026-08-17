"""Forward Capability wrapper for the frozen sklearn reference slice.

All sklearn/Wine/KNN knowledge stays in this module.  Importing it neither
imports scientific dependencies nor executes an Experiment.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .experiment_capability_runtime import (
    CapabilityEvaluationResult,
    CapabilityImplementationDescriptor,
    CapabilityPreparationContext,
    CapabilityRequirementDeclaration,
    PreparedCapabilityCandidate,
    ValidatedOpaqueSpecification,
)
from .generic_experiment_contracts import (
    CapabilityAssessment,
    CapabilityEvaluationReceipt,
    CapabilityOperation,
    ContractRef,
    EvaluationValidity,
    ExactIdentity,
    ExperimentCapability,
    GenericMethodology,
    NamedChecksum,
    PreparationRequirement,
    RuntimeRequirement,
    SupportStatus,
)
from .generic_experiment_package import (
    DependencyDeclaration,
    ExperimentPackageManifest,
    LaunchTarget,
    PackageOrigin,
    PreparedExperimentPackageReceipt,
)
from .serialization import canonical_hash, canonical_json, sha256_bytes
from .sklearn_tabular_builder import (
    BUILDER_VERSION,
    DEPENDENCIES,
    ENTRYPOINT,
    SPEC_SCHEMA,
    SklearnTabularClassificationSpec,
    rendered_files,
)

REFERENCE_CAPSULE = ExactIdentity(
    "capsule-5e02c832357355b6036b7e21cfbae306", "0.8.0",
    "sha256:5e02c832357355b6036b7e21cfbae3061306b16268d04ee75c764c56c759bd98",
)
REFERENCE_SKILL = ExactIdentity(
    "sklearn-tabular-classification-preparation-local-builtin", "0.1.0",
    canonical_hash({
        "identity": "sklearn-tabular-classification-preparation-local-builtin",
        "version": "0.1.0", "classification": "REFERENCE_EXPERIMENT_CAPABILITY",
    }),
)
FORWARD_WORKFLOW = ExactIdentity(
    "reproduction-experiment-local-experimental", "0.6.0",
    canonical_hash({"workflow": "reproduction-experiment-local-experimental", "version": "0.6.0"}),
)
_ENTRYPOINT = "backend/workflow_packages/sklearn_reference_capability.py"
_ENTRYPOINT_CHECKSUM = sha256_bytes(Path(__file__).read_bytes())
REFERENCE_CAPABILITY = ExperimentCapability(
    "0.1.0", REFERENCE_SKILL, REFERENCE_CAPSULE, _ENTRYPOINT,
    _ENTRYPOINT_CHECKSUM,
    (
        CapabilityOperation.ASSESS_SUPPORT, CapabilityOperation.DECLARE_REQUIREMENTS,
        CapabilityOperation.PREPARE, CapabilityOperation.EVALUATE,
        CapabilityOperation.PRESENT,
    ),
    SPEC_SCHEMA, "reagent.sklearn-tabular-classification-evaluation/v0.1",
    "reagent.sklearn-tabular-classification-presentation/v0.1",
)
REFERENCE_DESCRIPTOR = CapabilityImplementationDescriptor(
    REFERENCE_CAPABILITY, REFERENCE_CAPABILITY.schema,
    REFERENCE_SKILL.checksum, REFERENCE_CAPSULE.checksum,
    _ENTRYPOINT, _ENTRYPOINT_CHECKSUM, None,
    "REFERENCE_EXPERIMENT_CAPABILITY",
)


class SklearnReferenceCapability:
    descriptor = REFERENCE_DESCRIPTOR

    def assess_support(
        self, objective: Any, methodology: GenericMethodology,
    ) -> CapabilityAssessment:
        text = " ".join((
            methodology.research_objective.objective_summary,
            *methodology.questions_or_hypotheses, *methodology.inputs_or_materials,
            *methodology.protocol, *methodology.observations_or_outputs,
            *methodology.evaluation_criteria, *methodology.reproducibility_controls,
        )).casefold()
        required = ("wine", "classification", "nearest", "stratified", "accuracy")
        if methodology.unresolved_material_decisions:
            status = SupportStatus.NEEDS_OWNER_DECISION
            reasons = ("The sklearn reference family needs the remaining scientific choices resolved.",)
        elif all(term in text for term in required):
            status = SupportStatus.SUPPORTED
            reasons = ("The exact methodology fits the reviewed sklearn Wine/KNN reference family.",)
        else:
            status = SupportStatus.UNSUPPORTED
            reasons = ("The methodology is outside the reviewed sklearn Wine/KNN reference family.",)
        return CapabilityAssessment(
            REFERENCE_CAPABILITY.capability_checksum, objective.objective_ref_checksum,
            methodology.methodology_checksum, status, reasons, 100,
        )

    def validate_specification(
        self, methodology: GenericMethodology, specification: Any,
    ) -> ValidatedOpaqueSpecification:
        spec = SklearnTabularClassificationSpec.from_mapping(specification)
        text = " ".join((
            *methodology.questions_or_hypotheses, *methodology.inputs_or_materials, *methodology.protocol,
            *methodology.evaluation_criteria, *methodology.reproducibility_controls,
        )).casefold()
        required = ("wine", "nearest", "stratified", "accuracy", "neighbor")
        if spec.methodology_checksum != methodology.methodology_checksum or any(
            item not in text for item in required
        ):
            raise ValueError("AUTOMATIC_PREPARATION_UNSUPPORTED: methodology/specification mismatch")
        local_data = {"historical_specification": spec.to_dict()}
        specification_checksum = canonical_hash(local_data)
        receipt = ContractRef(
            "reagent.sklearn-specification-validation/v0.1",
            canonical_hash({
                "capability": REFERENCE_CAPABILITY.capability_checksum,
                "methodology": methodology.methodology_checksum,
                "specification": specification_checksum,
            }),
        )
        from .generic_experiment_contracts import ImplementationSpecificationRef
        reference = ImplementationSpecificationRef(
            REFERENCE_CAPABILITY.capability_checksum, SPEC_SCHEMA,
            methodology.methodology_checksum, specification_checksum, receipt,
            (("Reference family", "Reviewed sklearn Wine nearest-neighbor classification."),),
        )
        return ValidatedOpaqueSpecification(reference, local_data)

    def declare_requirements(
        self, methodology: GenericMethodology,
        specification: ValidatedOpaqueSpecification,
    ) -> CapabilityRequirementDeclaration:
        dependency = ContractRef(
            "reagent.dependency-declaration/python-lock/v0.1",
            sha256_bytes(DEPENDENCIES.encode()),
        )
        runtime = RuntimeRequirement(
            "PYTHON", ">=3.10,<3.13", ("NUMPY", "SCIKIT_LEARN"), (dependency,),
            ContractRef(
                "reagent.launch-contract/python-script/v0.1",
                canonical_hash({"argv": ("launcher", "script", "config")}),
            ),
            "DISABLED", (("wall_time_seconds", "300"), ("max_output_bytes", "10485760")),
        )
        preparation = PreparationRequirement(
            "reviewed_sklearn_builder", REFERENCE_CAPABILITY.capability_checksum,
            "SKLEARN_TABULAR_CLASSIFICATION_BUILDER", f"=={BUILDER_VERSION}",
            ("DETERMINISTIC_RENDER",), True,
        )
        return CapabilityRequirementDeclaration(
            REFERENCE_CAPABILITY.capability_checksum,
            specification.reference.reference_checksum, (), (preparation,), runtime,
        )

    def prepare(
        self, candidate_root: Path, context: CapabilityPreparationContext,
    ) -> PreparedCapabilityCandidate:
        spec = SklearnTabularClassificationSpec.from_mapping(
            context.specification.local_data["historical_specification"]
        )
        files = rendered_files(spec, "3.11")
        files.pop(".reagent-experiment.json")
        for relative, content in files.items():
            path = candidate_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        entries = tuple(
            {
                "path": path.relative_to(candidate_root).as_posix(),
                "sha256": sha256_bytes(path.read_bytes()), "size_bytes": path.stat().st_size,
            }
            for path in sorted(candidate_root.rglob("*")) if path.is_file()
        )
        runtime = context.requirements.runtime_requirement
        dependency = DependencyDeclaration(
            "PYTHON_LOCK", "requirements.lock", sha256_bytes(files["requirements.lock"]),
        )
        manifest = ExperimentPackageManifest(
            REFERENCE_CAPABILITY.capability_checksum, context.specification.reference,
            LaunchTarget("run_experiment.py", sha256_bytes(ENTRYPOINT.encode()), runtime.launch_contract),
            (dependency,),
            (NamedChecksum("experiment-config", sha256_bytes(files["experiment-config.json"])),),
            (NamedChecksum("research-objective", context.objective.source_artifact_checksum),),
            context.resource_identity_checksums, runtime.requirement_checksum,
            (NamedChecksum("experiment-result", sha256_bytes(files["result-expectations.json"])),),
        )
        receipt = PreparedExperimentPackageReceipt(
            PackageOrigin.REAGENT_PREPARED, context.objective,
            context.methodology.methodology_checksum,
            ExactIdentity(
                "SKLEARN_TABULAR_CLASSIFICATION_V1", BUILDER_VERSION,
                REFERENCE_CAPABILITY.capability_checksum,
            ),
            context.specification.reference, canonical_hash(entries),
            manifest.manifest_checksum, manifest.launch_target.checksum,
            (dependency.checksum,), runtime, context.resource_identity_checksums,
            FORWARD_WORKFLOW, REFERENCE_CAPSULE, None, None, context.prepared_at,
        )
        return PreparedCapabilityCandidate(manifest, receipt)

    def evaluate(self, context: Any) -> CapabilityEvaluationResult:
        evidence = context["execution_evidence"]
        output = next((item for item in context["outputs"] if item.name == "experiment-result"), None)
        limitations: tuple[str, ...]
        payload: dict[str, Any]
        validity = EvaluationValidity.INVALID
        status = "NOT_AVAILABLE"
        try:
            payload = json.loads(output.content.decode("utf-8")) if output is not None else {}
            rows = payload.get("conditions") if isinstance(payload, dict) else None
            if (
                evidence.process_outcome.value == "SUCCEEDED"
                and payload.get("schema_version") == "reagent.experiment-result/v0.2"
                and isinstance(rows, list) and rows
            ):
                validity = EvaluationValidity.VALID
                status = "LIMITED"
                limitations = ("Reference evidence is bounded to the declared Wine/KNN design.",)
            else:
                limitations = ("The reference result was absent, malformed, or scientifically incomplete.",)
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            payload = {"evaluation": "INVALID_REFERENCE_OUTPUT"}
            limitations = ("The reference result could not be parsed by its Capability.",)
        receipt = CapabilityEvaluationReceipt(
            REFERENCE_CAPABILITY.capability_checksum,
            context["objective"].objective_ref_checksum,
            context["methodology"].methodology_checksum,
            context["specification"].reference.specification_checksum,
            context["plan"].plan_checksum, evidence.outputs,
            context["plan"].capability_output_contract.checksum,
            REFERENCE_CAPABILITY.evaluation_schema or "", canonical_hash(payload),
            validity, limitations, evidence.completed_at,
        )
        return CapabilityEvaluationResult(receipt, status, payload)

    def present(self, context: Any) -> ContractRef:
        return ContractRef(
            REFERENCE_CAPABILITY.presentation_schema or "",
            canonical_hash({
                "evaluation": context["evaluation"].receipt.evaluation_checksum,
                "normalized": context["normalized_result"],
            }),
        )
