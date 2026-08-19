"""Truthful adapter from Generic Agent Harness evidence to the v5 lifecycle carrier.

The immutable v4/v5 lifecycle names its implementation slot ``capability``.
This forward-only adapter uses that slot structurally while recording an exact
``GENERIC_AGENT_HARNESS`` path.  It is neither a reviewed Capability nor a User
Skill and never chooses or evaluates scientific meaning from chat text.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Mapping

from .experiment_capability_runtime import (
    CapabilityEvaluationResult,
    CapabilityPreparationContext,
    CapabilityRequirementDeclaration,
    PreparedCapabilityCandidate,
    ValidatedOpaqueSpecification,
)
from .generic_experiment_contracts import (
    CAPABILITY_SCHEMA,
    CapabilityAssessment,
    CapabilityEvaluationReceipt,
    CapabilityOperation,
    CapabilitySelection,
    ContractRef,
    EvaluationValidity,
    ExactIdentity,
    ExperimentCapability,
    GenericMethodology,
    ImplementationSpecificationRef,
    NamedChecksum,
    ResearchObjectiveRef,
    RuntimeRequirement,
    ScientificEvidenceStatus,
    SelectionMateriality,
    SupportStatus,
)
from .generic_experiment_coordinator import (
    CheckpointCode,
    CoordinatorResult,
    CoordinatorStatus,
    GenericExperimentContinuation,
    GenericExperimentCoordinator,
)
from .generic_experiment_package import (
    DependencyDeclaration,
    ExperimentPackageManifest,
    LaunchTarget,
    PackageOrigin,
    PreparedExperimentPackageReceipt,
)
from .generic_harness_contracts import (
    GENERIC_HARNESS_CLASSIFICATION,
    GenericHarnessImplementationSpec,
    GenericHarnessPath,
)
from .security import require_sha256
from .serialization import SerializableContract, canonical_hash, canonical_json, sha256_bytes, to_json_value

GENERIC_HARNESS_DESCRIPTOR_SCHEMA = "reagent.generic-harness-lifecycle-adapter/v0.1"
GENERIC_HARNESS_EVALUATION_SCHEMA = "reagent.generic-harness-evaluation/v0.1"
GENERIC_HARNESS_PRESENTATION_SCHEMA = "reagent.artifact-presentation.experiment-record/v0.2"


class GenericHarnessAdapterError(ValueError):
    """The Generic Harness adapter or its exact evidence is invalid."""


def _hash_without(value: SerializableContract, name: str) -> str:
    return canonical_hash({
        item.name: to_json_value(getattr(value, item.name))
        for item in fields(value) if item.name != name
    })


def _spec_payload(specification: GenericHarnessImplementationSpec) -> dict[str, Any]:
    return {
        item.name: to_json_value(getattr(specification, item.name))
        for item in fields(specification) if item.name != "specification_checksum"
    }


@dataclass(frozen=True, slots=True)
class GenericHarnessLifecycleDescriptor(SerializableContract):
    """Exact forward descriptor that makes the structural carrier truthful."""

    capability: ExperimentCapability
    path: GenericHarnessPath
    interface_identity: str = CAPABILITY_SCHEMA
    classification: str = field(default=GENERIC_HARNESS_CLASSIFICATION, init=False)
    reviewed_capability: bool = field(default=False, init=False)
    user_skill_authority: bool = field(default=False, init=False)
    fallback_equivalence_key: str | None = field(default=None, init=False)
    schema: str = field(default=GENERIC_HARNESS_DESCRIPTOR_SCHEMA, init=False)
    descriptor_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if self.interface_identity != CAPABILITY_SCHEMA:
            raise GenericHarnessAdapterError("Generic Harness carrier interface drifted")
        if self.path.classification != GENERIC_HARNESS_CLASSIFICATION:
            raise GenericHarnessAdapterError("Generic Harness path classification drifted")
        if self.capability.implementation_spec_schema != self.path.implementation_contract.schema_identity:
            raise GenericHarnessAdapterError("Generic Harness implementation contract drifted")
        if self.capability.evaluation_schema != self.path.evaluation_contract.schema_identity:
            raise GenericHarnessAdapterError("Generic Harness evaluation contract drifted")
        object.__setattr__(self, "descriptor_checksum", _hash_without(self, "descriptor_checksum"))


@dataclass(frozen=True, slots=True)
class GenericHarnessEvaluation(SerializableContract):
    """Independently validated bounded evaluation supplied after local execution."""

    specification_checksum: str
    execution_plan_checksum: str
    execution_outputs: tuple[NamedChecksum, ...]
    result_payload: Mapping[str, Any]
    validity: EvaluationValidity
    scientific_evidence_status: ScientificEvidenceStatus
    limitations: tuple[str, ...]
    evaluated_at: str
    contract_validation_passed: bool
    schema: str = field(default=GENERIC_HARNESS_EVALUATION_SCHEMA, init=False)
    evaluation_input_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("specification_checksum", "execution_plan_checksum"):
            require_sha256(getattr(self, name), name)
        if not self.execution_outputs or len({item.name for item in self.execution_outputs}) != len(self.execution_outputs):
            raise GenericHarnessAdapterError("Generic Harness evaluation outputs are invalid")
        if not self.contract_validation_passed:
            raise GenericHarnessAdapterError("Generic Harness result did not pass contract validation")
        if not self.evaluated_at.endswith("Z"):
            raise GenericHarnessAdapterError("Generic Harness evaluation time is invalid")
        if len(self.limitations) > 40 or any(not item.strip() or len(item) > 1_000 for item in self.limitations):
            raise GenericHarnessAdapterError("Generic Harness limitations are invalid")
        if (
            self.validity is not EvaluationValidity.VALID
            and self.scientific_evidence_status is ScientificEvidenceStatus.SUPPORTS_BOUNDED_FINDINGS
        ):
            raise GenericHarnessAdapterError("Invalid evaluation cannot support bounded findings")
        object.__setattr__(self, "evaluation_input_checksum", _hash_without(self, "evaluation_input_checksum"))


@dataclass(frozen=True, slots=True)
class GenericHarnessBinding:
    descriptor: GenericHarnessLifecycleDescriptor
    implementation: object

    def __post_init__(self) -> None:
        if getattr(self.implementation, "descriptor", None) != self.descriptor:
            raise GenericHarnessAdapterError("Generic Harness implementation drifted")


class HybridExperimentResolver:
    """Bounded exact resolver for reviewed bindings plus one generic fallback."""

    def __init__(self, bindings: tuple[Any, ...]) -> None:
        if not bindings or len(bindings) > 40:
            raise GenericHarnessAdapterError("Experiment implementation set is empty or unbounded")
        checksums = tuple(item.descriptor.capability.capability_checksum for item in bindings)
        if len(checksums) != len(set(checksums)):
            raise GenericHarnessAdapterError("Experiment implementations must be exact and unique")
        generic = tuple(
            item for item in bindings
            if item.descriptor.classification == GENERIC_HARNESS_CLASSIFICATION
        )
        if len(generic) != 1:
            raise GenericHarnessAdapterError("Exactly one Generic Harness fallback is required")
        if generic[0].descriptor.reviewed_capability or generic[0].descriptor.user_skill_authority:
            raise GenericHarnessAdapterError("Generic Harness gained forbidden authority")
        self._bindings = bindings

    @property
    def bindings(self) -> tuple[Any, ...]:
        return self._bindings

    def resolve(self, capability: ExperimentCapability) -> Any:
        matches = tuple(
            item for item in self._bindings
            if item.descriptor.capability.capability_checksum == capability.capability_checksum
        )
        if len(matches) != 1 or matches[0].descriptor.capability != capability:
            raise GenericHarnessAdapterError("Experiment implementation drifted")
        return matches[0]

    @staticmethod
    def invoke(binding: Any, operation: CapabilityOperation, *args: Any) -> Any:
        if operation not in binding.descriptor.capability.operations:
            raise GenericHarnessAdapterError(f"Experiment operation is unavailable: {operation.value}")
        method = {
            CapabilityOperation.ASSESS_SUPPORT: "assess_support",
            CapabilityOperation.DECLARE_REQUIREMENTS: "declare_requirements",
            CapabilityOperation.PREPARE: "prepare",
            CapabilityOperation.EVALUATE: "evaluate",
            CapabilityOperation.PRESENT: "present",
        }[operation]
        return getattr(binding.implementation, method)(*args)


class GenericHarnessExperimentCoordinator(GenericExperimentCoordinator):
    """Select reviewed support first, then the truthful system fallback."""

    def assess_and_select(
        self,
        objective: ResearchObjectiveRef,
        methodology: GenericMethodology | None,
        *,
        owner_selected_capability_checksum: str | None = None,
        owner_confirmation_checksum: str | None = None,
    ) -> CoordinatorResult:
        start = GenericExperimentContinuation(objective, methodology)
        if methodology is None or methodology.research_objective != objective or methodology.unresolved_material_decisions:
            current = replace(start, checkpoint=CheckpointCode.METHODOLOGY_DECISION_REQUIRED)
            return CoordinatorResult(
                CoordinatorStatus.CHECKPOINT, current,
                CheckpointCode.METHODOLOGY_DECISION_REQUIRED,
                "A bounded methodology decision remains unresolved.",
            )
        reviewed_assessments: list[CapabilityAssessment] = []
        generic_assessment: CapabilityAssessment | None = None
        for binding in self._resolver.bindings:
            assessment = self._resolver.invoke(
                binding, CapabilityOperation.ASSESS_SUPPORT, objective, methodology,
            )
            if assessment.capability_checksum != binding.descriptor.capability.capability_checksum:
                raise GenericHarnessAdapterError("Experiment assessment lineage drifted")
            if binding.descriptor.classification == GENERIC_HARNESS_CLASSIFICATION:
                generic_assessment = assessment
            else:
                reviewed_assessments.append(assessment)
        reviewed_supported = tuple(
            item for item in reviewed_assessments if item.status is SupportStatus.SUPPORTED
        )
        if any(item.status is SupportStatus.NEEDS_OWNER_DECISION for item in reviewed_assessments):
            current = replace(start, checkpoint=CheckpointCode.METHODOLOGY_DECISION_REQUIRED)
            return CoordinatorResult(
                CoordinatorStatus.CHECKPOINT, current,
                CheckpointCode.METHODOLOGY_DECISION_REQUIRED,
                "Reviewed support depends on an unresolved methodology decision.",
            )
        if reviewed_supported:
            assessments = tuple(reviewed_assessments)
            if len(reviewed_supported) == 1:
                selected = reviewed_supported[0].capability_checksum
                materiality = SelectionMateriality.NOT_APPLICABLE
                confirmation = None
            else:
                materiality = SelectionMateriality.MATERIAL_DIFFERENCE
                selected = owner_selected_capability_checksum
                confirmation = owner_confirmation_checksum
            rationale = "Exact reviewed Capability support was selected without changing the methodology."
        else:
            if generic_assessment is None or generic_assessment.status is not SupportStatus.SUPPORTED:
                raise GenericHarnessAdapterError("Generic Harness fallback is unavailable")
            assessments = (*reviewed_assessments, generic_assessment)
            selected = generic_assessment.capability_checksum
            materiality = SelectionMateriality.NOT_APPLICABLE
            confirmation = None
            rationale = (
                "No exact reviewed Capability supports the methodology; the system-owned "
                "Generic Agent Harness path will implement it under exact validation."
            )
        selection = CapabilitySelection(
            methodology.methodology_checksum, assessments, materiality,
            selected, rationale, confirmation,
        )
        if selection.selected_capability_checksum is None:
            current = replace(start, selection=selection, checkpoint=CheckpointCode.CAPABILITY_SELECTION_REQUIRED)
            return CoordinatorResult(
                CoordinatorStatus.CHECKPOINT, current,
                CheckpointCode.CAPABILITY_SELECTION_REQUIRED,
                "Materially different reviewed Capabilities require Owner selection.",
            )
        capability = next(
            item.descriptor.capability for item in self._resolver.bindings
            if item.descriptor.capability.capability_checksum == selection.selected_capability_checksum
        )
        current = replace(
            start, selection=selection, capability=capability,
            checkpoint=CheckpointCode.DESIGN_APPROVAL_REQUIRED,
        )
        return CoordinatorResult(
            CoordinatorStatus.CHECKPOINT, current,
            CheckpointCode.DESIGN_APPROVAL_REQUIRED,
            "The exact methodology and implementation path require Owner approval.",
        )


class GenericHarnessImplementation:
    """System adapter over a Harness-authored, ReAgent-validated local package."""

    def __init__(
        self,
        *,
        implementation_root: Path,
        workflow: ExactIdentity,
        path: GenericHarnessPath,
        evaluation: GenericHarnessEvaluation | None = None,
    ) -> None:
        self.implementation_root = implementation_root.resolve()
        self.workflow = workflow
        self.path = path
        self.evaluation = evaluation
        carrier_package = ExactIdentity(
            "generic-agent-harness-managed-execution", "0.1.0",
            canonical_hash({"identity": "generic-agent-harness-managed-execution", "version": "0.1.0"}),
        )
        system_identity = ExactIdentity(
            "generic-agent-harness-system-adapter", "0.1.0",
            canonical_hash({"identity": "generic-agent-harness-system-adapter", "version": "0.1.0"}),
        )
        entrypoint = "backend/workflow_packages/generic_harness_adapter.py"
        entrypoint_checksum = sha256_bytes(Path(__file__).read_bytes())
        self.capability = ExperimentCapability(
            "0.1.0", system_identity, carrier_package,
            entrypoint, entrypoint_checksum,
            (
                CapabilityOperation.ASSESS_SUPPORT,
                CapabilityOperation.DECLARE_REQUIREMENTS,
                CapabilityOperation.PREPARE,
                CapabilityOperation.EVALUATE,
                CapabilityOperation.PRESENT,
            ),
            path.implementation_contract.schema_identity,
            path.evaluation_contract.schema_identity,
            GENERIC_HARNESS_PRESENTATION_SCHEMA,
        )
        self.descriptor = GenericHarnessLifecycleDescriptor(self.capability, path)

    def assess_support(
        self, objective: ResearchObjectiveRef, methodology: GenericMethodology,
    ) -> CapabilityAssessment:
        status = (
            SupportStatus.NEEDS_OWNER_DECISION
            if methodology.unresolved_material_decisions else SupportStatus.SUPPORTED
        )
        return CapabilityAssessment(
            self.capability.capability_checksum,
            objective.objective_ref_checksum,
            methodology.methodology_checksum,
            status,
            ("Generic Harness can implement the frozen methodology without claiming reviewed Capability authority.",),
            10_000,
        )

    def validate_specification(
        self, methodology: GenericMethodology, specification: Any,
    ) -> ValidatedOpaqueSpecification:
        if not isinstance(specification, GenericHarnessImplementationSpec):
            raise GenericHarnessAdapterError("Generic Harness specification type is invalid")
        if (
            specification.objective_checksum != methodology.research_objective.objective_ref_checksum
            or specification.methodology_checksum != methodology.methodology_checksum
        ):
            raise GenericHarnessAdapterError("Generic Harness specification lineage drifted")
        payload = _spec_payload(specification)
        if canonical_hash(payload) != specification.specification_checksum:
            raise GenericHarnessAdapterError("Generic Harness specification checksum drifted")
        receipt = ContractRef(
            "reagent.generic-harness-specification-validation/v0.1",
            canonical_hash({
                "path": self.path.path_checksum,
                "methodology": methodology.methodology_checksum,
                "specification": specification.specification_checksum,
            }),
        )
        reference = ImplementationSpecificationRef(
            self.capability.capability_checksum,
            specification.schema,
            methodology.methodology_checksum,
            specification.specification_checksum,
            receipt,
            tuple(("Implementation", item) for item in specification.implementation_summary),
        )
        return ValidatedOpaqueSpecification(reference, payload)

    def declare_requirements(
        self, methodology: GenericMethodology, specification: ValidatedOpaqueSpecification,
    ) -> CapabilityRequirementDeclaration:
        payload = specification.local_data
        dependencies = tuple(
            ContractRef(
                "reagent.generic-harness-dependency/v0.1",
                canonical_hash({"name": item["name"], "version_constraint": item["version_constraint"]}),
            )
            for item in payload["dependencies"]
        )
        runtime = RuntimeRequirement(
            payload["runtime_family"], payload["runtime_version_constraint"],
            tuple(payload["required_runtime_capabilities"]), dependencies,
            ContractRef(
                "reagent.launch-contract/generic-harness-package/v0.1",
                canonical_hash({"entrypoint": payload["entrypoint_relative_path"]}),
            ),
            "DISABLED", tuple(tuple(item) for item in payload["compute_limits"]),
        )
        return CapabilityRequirementDeclaration(
            self.capability.capability_checksum,
            specification.reference.reference_checksum,
            (), (), runtime,
        )

    def prepare(
        self, candidate_root: Path, context: CapabilityPreparationContext,
    ) -> PreparedCapabilityCandidate:
        if self.implementation_root.is_symlink() or not self.implementation_root.is_dir():
            raise GenericHarnessAdapterError("Generic Harness implementation root is unsafe")
        spec = context.specification.local_data
        for source in sorted(self.implementation_root.rglob("*")):
            relative = source.relative_to(self.implementation_root)
            target = candidate_root / relative
            if source.is_symlink():
                raise GenericHarnessAdapterError("Generic Harness package contains a symbolic link")
            if source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif source.is_file() and source.stat().st_nlink == 1:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            else:
                raise GenericHarnessAdapterError("Generic Harness package contains an unsafe file")
        dependency_declarations: list[DependencyDeclaration] = []
        for index, identity in enumerate(context.requirements.runtime_requirement.dependency_declarations):
            relative = f".reagent-generated/dependency-{index}.json"
            content = canonical_json(spec["dependencies"][index]).encode("utf-8")
            if sha256_bytes(content) != identity.checksum:
                raise GenericHarnessAdapterError("Generic Harness dependency identity drifted")
            target = candidate_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            dependency_declarations.append(
                DependencyDeclaration("GENERIC_HARNESS_DECLARATION", relative, identity.checksum)
            )
        entrypoint = candidate_root / spec["entrypoint_relative_path"]
        if entrypoint.is_symlink() or not entrypoint.is_file() or entrypoint.stat().st_nlink != 1:
            raise GenericHarnessAdapterError("Generic Harness entrypoint is unavailable")
        expected = tuple(
            NamedChecksum(item["name"], canonical_hash(item))
            for item in spec["expected_outputs"]
        )
        manifest = ExperimentPackageManifest(
            self.capability.capability_checksum,
            context.specification.reference,
            LaunchTarget(
                spec["entrypoint_relative_path"], sha256_bytes(entrypoint.read_bytes()),
                context.requirements.runtime_requirement.launch_contract,
            ),
            tuple(dependency_declarations), (),
            (NamedChecksum("research-objective", context.objective.source_artifact_checksum),),
            context.resource_identity_checksums,
            context.requirements.runtime_requirement.requirement_checksum,
            expected,
        )
        tree_checksum = GenericExperimentCoordinator._scan_package(candidate_root)
        receipt = PreparedExperimentPackageReceipt(
            PackageOrigin.LOCAL_PROJECT,
            context.objective,
            context.methodology.methodology_checksum,
            ExactIdentity(
                "generic-agent-harness-system-adapter", "0.1.0",
                self.capability.capability_checksum,
            ),
            context.specification.reference,
            tree_checksum,
            manifest.manifest_checksum,
            manifest.launch_target.checksum,
            tuple(item.checksum for item in dependency_declarations),
            context.requirements.runtime_requirement,
            context.resource_identity_checksums,
            self.workflow,
            self.capability.capsule,
            ExactIdentity(
                "qualified-agent-harness", "0.1.0",
                canonical_hash({"classification": GENERIC_HARNESS_CLASSIFICATION}),
            ),
            ContractRef(self.path.schema, self.path.path_checksum),
            context.prepared_at,
        )
        return PreparedCapabilityCandidate(manifest, receipt)

    def evaluate(self, context: Mapping[str, Any]) -> CapabilityEvaluationResult:
        evaluation = self.evaluation
        if evaluation is None:
            raise GenericHarnessAdapterError("Generic Harness evaluation evidence is unavailable")
        outputs = context["execution_evidence"].outputs
        if (
            evaluation.specification_checksum
            != context["specification"].reference.specification_checksum
            or evaluation.execution_plan_checksum != context["plan"].plan_checksum
            or evaluation.execution_outputs != outputs
        ):
            raise GenericHarnessAdapterError("Generic Harness evaluation lineage drifted")
        receipt = CapabilityEvaluationReceipt(
            self.capability.capability_checksum,
            context["objective"].objective_ref_checksum,
            context["methodology"].methodology_checksum,
            evaluation.specification_checksum,
            evaluation.execution_plan_checksum,
            evaluation.execution_outputs,
            context["plan"].capability_output_contract.checksum,
            GENERIC_HARNESS_EVALUATION_SCHEMA,
            canonical_hash(evaluation.result_payload),
            evaluation.validity,
            evaluation.limitations,
            evaluation.evaluated_at,
        )
        return CapabilityEvaluationResult(
            receipt, evaluation.scientific_evidence_status.value,
            dict(evaluation.result_payload),
        )

    def present(self, context: Mapping[str, Any]) -> ContractRef:
        return ContractRef(
            GENERIC_HARNESS_PRESENTATION_SCHEMA,
            canonical_hash({
                "evaluation": context["evaluation"].receipt.evaluation_checksum,
                "normalized": context["normalized_result"],
                "owner_review": context["owner_review"].review_checksum,
            }),
        )
