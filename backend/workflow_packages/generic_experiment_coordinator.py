"""Unpublished generic coordinator for local computational Experiments.

The coordinator owns lifecycle and exact evidence.  Scientific specification,
preparation, evaluation, and optional presentation remain behind the injected
Experiment Capability boundary.
"""

from __future__ import annotations

import os
import stat
import uuid
from dataclasses import dataclass, field, fields, replace
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from backend.artifact_references.generic_experiment_contracts import ExperimentRecordV4
from backend.resource_references.experiment_requirement_contracts import (
    ExperimentResourceReadinessEvidence,
    ResourceReadiness,
)

from .experiment_capability_runtime import (
    BoundedCapabilityResolver,
    CapabilityBinding,
    CapabilityEvaluationResult,
    CapabilityPreparationContext,
    CapabilityRequirementDeclaration,
    ExperimentCapabilityRuntimeError,
    PreparedCapabilityCandidate,
    ValidatedOpaqueSpecification,
)
from .generic_experiment_contracts import (
    CapabilityAssessment,
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
    LocalRuntimeCandidate,
    NamedChecksum,
    NormalizedExperimentResult,
    PreparationRequirement,
    ProcessOutcome,
    ResearchObjectiveRef,
    RuntimeCompatibility,
    ScientificEvidenceStatus,
    SelectionMateriality,
    SelectionOutcome,
    SupportStatus,
)
from .generic_experiment_package import (
    PackageSafetyEvidence,
    ValidatedExperimentPackage,
)
from .security import reject_sensitive_content, require_relative_path, require_sha256
from .serialization import SerializableContract, canonical_hash, sha256_bytes, to_json_value

DESIGN_BINDING_SCHEMA = "reagent.experiment-design-approval-binding/v0.1"
PREPARATION_READINESS_SCHEMA = "reagent.experiment-preparation-readiness/v0.1"
EXECUTION_PLAN_SCHEMA = "reagent.experiment-execution-plan/v0.2"
RUN_APPROVAL_SCHEMA = "reagent.experiment-run-approval/v0.2"
RUN_CONSUMPTION_SCHEMA = "reagent.experiment-run-approval-consumption/v0.2"
EXECUTION_EVIDENCE_SCHEMA = "reagent.experiment-execution-evidence/v0.2"
OWNER_RESULT_REVIEW_SCHEMA = "reagent.experiment-owner-result-review/v0.1"
CONTINUATION_RECEIPT_SCHEMA = "reagent.experiment-local-continuation/v0.1"
MAX_PACKAGE_FILES = 200
MAX_PACKAGE_BYTES = 10_485_760
MAX_EXECUTION_OUTPUT_BYTES = 10_485_760


class GenericExperimentCoordinatorError(ValueError):
    """Integrity or call-order error, not an expected Owner checkpoint."""


def _hash_without(value: SerializableContract, field_name: str) -> str:
    return canonical_hash({
        item.name: to_json_value(getattr(value, item.name))
        for item in fields(value) if item.name != field_name
    })


class CheckpointCode(str, Enum):
    METHODOLOGY_DECISION_REQUIRED = "METHODOLOGY_DECISION_REQUIRED"
    CAPABILITY_SELECTION_REQUIRED = "CAPABILITY_SELECTION_REQUIRED"
    DESIGN_APPROVAL_REQUIRED = "DESIGN_APPROVAL_REQUIRED"
    RESOURCE_READINESS_REQUIRED = "RESOURCE_READINESS_REQUIRED"
    PREPARATION_REQUIREMENT_UNMET = "PREPARATION_REQUIREMENT_UNMET"
    RUNTIME_INCOMPATIBLE = "RUNTIME_INCOMPATIBLE"
    RUN_APPROVAL_REQUIRED = "RUN_APPROVAL_REQUIRED"
    RESULT_REVIEW_REQUIRED = "RESULT_REVIEW_REQUIRED"
    AUTOMATIC_PREPARATION_UNSUPPORTED = "AUTOMATIC_PREPARATION_UNSUPPORTED"
    CAPABILITY_PREPARATION_UNAVAILABLE = "CAPABILITY_PREPARATION_UNAVAILABLE"


class CoordinatorStatus(str, Enum):
    CHECKPOINT = "CHECKPOINT"
    DESIGN_APPROVED = "DESIGN_APPROVED"
    REQUIREMENTS_DECLARED = "REQUIREMENTS_DECLARED"
    REQUIREMENTS_READY = "REQUIREMENTS_READY"
    PACKAGE_CANDIDATE_CREATED = "PACKAGE_CANDIDATE_CREATED"
    PACKAGE_VALIDATED = "PACKAGE_VALIDATED"
    RUNTIME_COMPATIBLE = "RUNTIME_COMPATIBLE"
    EXECUTION_PLAN_READY = "EXECUTION_PLAN_READY"
    READY_FOR_EXECUTION = "READY_FOR_EXECUTION"
    EXECUTION_EVIDENCE_PRESENT = "EXECUTION_EVIDENCE_PRESENT"
    EVALUATION_COMPLETE = "EVALUATION_COMPLETE"
    READY_FOR_FINALIZATION = "READY_FOR_FINALIZATION"
    FINALIZED = "FINALIZED"


class ContinuationStage(str, Enum):
    METHODOLOGY_UNRESOLVED = "METHODOLOGY_UNRESOLVED"
    CAPABILITY_SELECTION_UNRESOLVED = "CAPABILITY_SELECTION_UNRESOLVED"
    DESIGN_APPROVAL_REQUIRED = "DESIGN_APPROVAL_REQUIRED"
    DESIGN_APPROVED = "DESIGN_APPROVED"
    REQUIREMENTS_DECLARED = "REQUIREMENTS_DECLARED"
    RESOURCES_UNRESOLVED = "RESOURCES_UNRESOLVED"
    PREPARATION_REQUIREMENTS_UNRESOLVED = "PREPARATION_REQUIREMENTS_UNRESOLVED"
    PACKAGE_CANDIDATE_CREATED = "PACKAGE_CANDIDATE_CREATED"
    PACKAGE_VALIDATED = "PACKAGE_VALIDATED"
    RUNTIME_INCOMPATIBLE = "RUNTIME_INCOMPATIBLE"
    RUNTIME_COMPATIBLE = "RUNTIME_COMPATIBLE"
    RUN_APPROVAL_REQUIRED = "RUN_APPROVAL_REQUIRED"
    READY_FOR_EXECUTION = "READY_FOR_EXECUTION"
    EXECUTION_EVIDENCE_PRESENT = "EXECUTION_EVIDENCE_PRESENT"
    EVALUATION_COMPLETE = "EVALUATION_COMPLETE"
    RESULT_REVIEW_REQUIRED = "RESULT_REVIEW_REQUIRED"
    READY_FOR_FINALIZATION = "READY_FOR_FINALIZATION"
    FINALIZED = "FINALIZED"


@dataclass(frozen=True, slots=True)
class DesignApprovalBinding(SerializableContract):
    design_approval_checksum: str
    capability_selection_checksum: str
    selected_capability_checksum: str
    schema: str = field(default=DESIGN_BINDING_SCHEMA, init=False)
    binding_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for item in (
            self.design_approval_checksum, self.capability_selection_checksum,
            self.selected_capability_checksum,
        ):
            require_sha256(item, "Design Approval binding checksum")
        object.__setattr__(self, "binding_checksum", _hash_without(self, "binding_checksum"))


@dataclass(frozen=True, slots=True)
class PreparationReadinessEvidence(SerializableContract):
    requirement_checksum: str
    requirement_family: str
    available_version: str | None
    available_capabilities: tuple[str, ...]
    environment_checksum: str | None
    available: bool
    schema: str = field(default=PREPARATION_READINESS_SCHEMA, init=False)
    readiness_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        require_sha256(self.requirement_checksum, "requirement_checksum")
        if not self.requirement_family or len(self.requirement_family) > 200:
            raise GenericExperimentCoordinatorError("Preparation family is invalid")
        if self.available:
            if not self.available_version:
                raise GenericExperimentCoordinatorError("Available preparation capability needs a version")
            require_sha256(self.environment_checksum, "environment_checksum")
        elif any((self.available_version, self.available_capabilities, self.environment_checksum)):
            raise GenericExperimentCoordinatorError("Unavailable preparation evidence carries local claims")
        object.__setattr__(self, "readiness_checksum", _hash_without(self, "readiness_checksum"))


@dataclass(frozen=True, slots=True)
class GenericExecutionPlan(SerializableContract):
    objective_checksum: str
    methodology_checksum: str
    capability_checksum: str
    implementation_specification_checksum: str
    resource_readiness_checksums: tuple[str, ...]
    validated_package_checksum: str
    runtime_compatibility_checksum: str
    launch_contract: ContractRef
    launch_target_relative_path: str
    execution_limits: tuple[tuple[str, str], ...]
    network_policy: str
    expected_outputs: tuple[NamedChecksum, ...]
    capability_output_contract: ContractRef
    schema: str = field(default=EXECUTION_PLAN_SCHEMA, init=False)
    plan_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for value in (
            self.objective_checksum, self.methodology_checksum, self.capability_checksum,
            self.implementation_specification_checksum, self.validated_package_checksum,
            self.runtime_compatibility_checksum,
        ):
            require_sha256(value, "Execution Plan lineage checksum")
        for value in self.resource_readiness_checksums:
            require_sha256(value, "Resource readiness checksum")
        require_relative_path(self.launch_target_relative_path, "launch target")
        if self.network_policy not in {"DISABLED", "BOUNDED_DECLARED"}:
            raise GenericExperimentCoordinatorError("Execution Plan network policy is invalid")
        if not self.expected_outputs or len(self.expected_outputs) > 50:
            raise GenericExperimentCoordinatorError("Execution Plan outputs are invalid")
        object.__setattr__(self, "plan_checksum", _hash_without(self, "plan_checksum"))


@dataclass(frozen=True, slots=True)
class GenericRunApproval(SerializableContract):
    execution_plan_checksum: str
    validated_package_checksum: str
    runtime_compatibility_checksum: str
    approved_at: str
    decision: str = "APPROVED"
    scope: str = "ONE_EXECUTION"
    schema: str = field(default=RUN_APPROVAL_SCHEMA, init=False)
    approval_checksum: str = field(init=False)

    @classmethod
    def approve(cls, plan: GenericExecutionPlan, approved_at: str) -> "GenericRunApproval":
        return cls(
            plan.plan_checksum, plan.validated_package_checksum,
            plan.runtime_compatibility_checksum, approved_at,
        )

    def __post_init__(self) -> None:
        for value in (
            self.execution_plan_checksum, self.validated_package_checksum,
            self.runtime_compatibility_checksum,
        ):
            require_sha256(value, "Run Approval checksum")
        if self.decision != "APPROVED" or self.scope != "ONE_EXECUTION" or not self.approved_at.endswith("Z"):
            raise GenericExperimentCoordinatorError("Run Approval semantics are invalid")
        object.__setattr__(self, "approval_checksum", _hash_without(self, "approval_checksum"))

    def validate(self, plan: GenericExecutionPlan) -> None:
        if (
            self.execution_plan_checksum != plan.plan_checksum
            or self.validated_package_checksum != plan.validated_package_checksum
            or self.runtime_compatibility_checksum != plan.runtime_compatibility_checksum
        ):
            raise GenericExperimentCoordinatorError("Execution Plan drift invalidates Run Approval")


@dataclass(frozen=True, slots=True)
class RunApprovalConsumption(SerializableContract):
    approval_checksum: str
    execution_plan_checksum: str
    attempt_id: str
    consumed_at: str
    schema: str = field(default=RUN_CONSUMPTION_SCHEMA, init=False)
    consumption_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        require_sha256(self.approval_checksum, "approval_checksum")
        require_sha256(self.execution_plan_checksum, "execution_plan_checksum")
        if not self.attempt_id or len(self.attempt_id) > 200 or not self.consumed_at.endswith("Z"):
            raise GenericExperimentCoordinatorError("Run Approval consumption is invalid")
        object.__setattr__(self, "consumption_checksum", _hash_without(self, "consumption_checksum"))


@dataclass(frozen=True, slots=True)
class ExecutionEvidence(SerializableContract):
    execution_plan_checksum: str
    run_approval_checksum: str
    approval_consumption_checksum: str
    process_outcome: ProcessOutcome
    outputs: tuple[NamedChecksum, ...]
    bounds_respected: bool
    network_policy: str
    started_at: str
    completed_at: str
    schema: str = field(default=EXECUTION_EVIDENCE_SCHEMA, init=False)
    evidence_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for value in (
            self.execution_plan_checksum, self.run_approval_checksum,
            self.approval_consumption_checksum,
        ):
            require_sha256(value, "Execution evidence lineage checksum")
        if not self.outputs or len(self.outputs) > 50 or len({item.name for item in self.outputs}) != len(self.outputs):
            raise GenericExperimentCoordinatorError("Execution outputs are invalid")
        if not self.bounds_respected or self.network_policy not in {"DISABLED", "BOUNDED_DECLARED"}:
            raise GenericExperimentCoordinatorError("Execution violated its admitted bounds")
        if not self.started_at.endswith("Z") or not self.completed_at.endswith("Z"):
            raise GenericExperimentCoordinatorError("Execution timestamps are invalid")
        object.__setattr__(self, "evidence_checksum", _hash_without(self, "evidence_checksum"))


@dataclass(frozen=True, slots=True)
class ExecutionOutput:
    name: str
    content: bytes

    def __post_init__(self) -> None:
        if not self.name or len(self.name) > 200 or not isinstance(self.content, bytes):
            raise GenericExperimentCoordinatorError("Execution output is invalid")


@dataclass(frozen=True, slots=True)
class SuppliedExecution:
    evidence: ExecutionEvidence
    outputs: tuple[ExecutionOutput, ...]


@dataclass(frozen=True, slots=True)
class ExecutionHandoff:
    plan: GenericExecutionPlan
    approval: GenericRunApproval
    consumption: RunApprovalConsumption
    package_root: Path
    local_runtime: LocalRuntimeCandidate


class BoundedRunnerCollaborator(Protocol):
    def execute(self, handoff: ExecutionHandoff) -> SuppliedExecution: ...


@dataclass(frozen=True, slots=True)
class OwnerResultReview(SerializableContract):
    evaluation_checksum: str
    normalized_result_checksum: str
    decision: str
    reviewed_at: str
    schema: str = field(default=OWNER_RESULT_REVIEW_SCHEMA, init=False)
    review_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        require_sha256(self.evaluation_checksum, "evaluation_checksum")
        require_sha256(self.normalized_result_checksum, "normalized_result_checksum")
        if self.decision not in {"ACCEPT_BOUNDED_RESULT", "ACKNOWLEDGE_LIMITED_OR_INVALID"}:
            raise GenericExperimentCoordinatorError("Owner result review decision is invalid")
        if not self.reviewed_at.endswith("Z"):
            raise GenericExperimentCoordinatorError("Owner result review timestamp is invalid")
        object.__setattr__(self, "review_checksum", _hash_without(self, "review_checksum"))


@dataclass(frozen=True, slots=True)
class GenericExperimentContinuationReceipt(SerializableContract):
    """Minimal durable projection; detailed facts remain in their exact receipts."""

    stage: ContinuationStage
    checkpoint: CheckpointCode | None
    objective_checksum: str
    fact_checksums: tuple[tuple[str, str], ...]
    schema: str = field(default=CONTINUATION_RECEIPT_SCHEMA, init=False)
    continuation_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        require_sha256(self.objective_checksum, "objective_checksum")
        if len(self.fact_checksums) > 30 or len({name for name, _ in self.fact_checksums}) != len(self.fact_checksums):
            raise GenericExperimentCoordinatorError("Continuation facts are invalid")
        for name, checksum in self.fact_checksums:
            if not name or len(name) > 100:
                raise GenericExperimentCoordinatorError("Continuation fact name is invalid")
            require_sha256(checksum, "Continuation fact checksum")
        object.__setattr__(self, "continuation_checksum", _hash_without(self, "continuation_checksum"))


@dataclass(frozen=True, slots=True)
class GenericExperimentContinuation:
    objective: ResearchObjectiveRef
    methodology: GenericMethodology | None = None
    selection: CapabilitySelection | None = None
    capability: ExperimentCapability | None = None
    design_approval: DesignApproval | None = None
    design_binding: DesignApprovalBinding | None = None
    specification: ValidatedOpaqueSpecification | None = None
    requirements: CapabilityRequirementDeclaration | None = None
    resource_readiness: tuple[ExperimentResourceReadinessEvidence, ...] = ()
    preparation_readiness: tuple[PreparationReadinessEvidence, ...] = ()
    candidate: PreparedCapabilityCandidate | None = None
    candidate_root: Path | None = None
    validated_package: ValidatedExperimentPackage | None = None
    validated_package_root: Path | None = None
    local_runtime: LocalRuntimeCandidate | None = None
    runtime_compatibility: RuntimeCompatibility | None = None
    execution_plan: GenericExecutionPlan | None = None
    run_approval: GenericRunApproval | None = None
    run_consumption: RunApprovalConsumption | None = None
    supplied_execution: SuppliedExecution | None = None
    evaluation: CapabilityEvaluationResult | None = None
    normalized_result: NormalizedExperimentResult | None = None
    owner_result_review: OwnerResultReview | None = None
    presentation: ContractRef | None = None
    finalized_record: ExperimentRecordV4 | None = None
    checkpoint: CheckpointCode | None = None

    @property
    def stage(self) -> ContinuationStage:
        if self.finalized_record is not None:
            return ContinuationStage.FINALIZED
        if self.owner_result_review is not None:
            return ContinuationStage.READY_FOR_FINALIZATION
        if self.evaluation is not None:
            return (
                ContinuationStage.RESULT_REVIEW_REQUIRED
                if self.checkpoint is CheckpointCode.RESULT_REVIEW_REQUIRED
                else ContinuationStage.EVALUATION_COMPLETE
            )
        if self.supplied_execution is not None:
            return ContinuationStage.EXECUTION_EVIDENCE_PRESENT
        if self.run_approval is not None:
            return ContinuationStage.READY_FOR_EXECUTION
        if self.execution_plan is not None:
            return ContinuationStage.RUN_APPROVAL_REQUIRED
        if self.runtime_compatibility is not None:
            return ContinuationStage.RUNTIME_COMPATIBLE
        if self.validated_package is not None:
            return (
                ContinuationStage.RUNTIME_INCOMPATIBLE
                if self.checkpoint is CheckpointCode.RUNTIME_INCOMPATIBLE
                else ContinuationStage.PACKAGE_VALIDATED
            )
        if self.candidate is not None:
            return ContinuationStage.PACKAGE_CANDIDATE_CREATED
        if self.requirements is not None:
            if self.checkpoint is CheckpointCode.RESOURCE_READINESS_REQUIRED:
                return ContinuationStage.RESOURCES_UNRESOLVED
            if self.checkpoint is CheckpointCode.PREPARATION_REQUIREMENT_UNMET:
                return ContinuationStage.PREPARATION_REQUIREMENTS_UNRESOLVED
            return ContinuationStage.REQUIREMENTS_DECLARED
        if self.design_binding is not None:
            return ContinuationStage.DESIGN_APPROVED
        if self.selection is None or self.selection.selected_capability_checksum is None:
            return (
                ContinuationStage.METHODOLOGY_UNRESOLVED
                if self.checkpoint is CheckpointCode.METHODOLOGY_DECISION_REQUIRED
                else ContinuationStage.CAPABILITY_SELECTION_UNRESOLVED
            )
        return ContinuationStage.DESIGN_APPROVAL_REQUIRED

    def durable_receipt(self) -> GenericExperimentContinuationReceipt:
        facts = (
            ("methodology", None if self.methodology is None else self.methodology.methodology_checksum),
            ("capability_selection", None if self.selection is None else self.selection.selection_checksum),
            ("design_approval", None if self.design_approval is None else self.design_approval.approval_checksum),
            ("design_binding", None if self.design_binding is None else self.design_binding.binding_checksum),
            ("specification", None if self.specification is None else self.specification.reference.reference_checksum),
            ("requirements", None if self.requirements is None else self.requirements.declaration_checksum),
            ("candidate", None if self.candidate is None else self.candidate.receipt.receipt_checksum),
            ("validated_package", None if self.validated_package is None else self.validated_package.validated_package_checksum),
            ("runtime_compatibility", None if self.runtime_compatibility is None else self.runtime_compatibility.compatibility_checksum),
            ("execution_plan", None if self.execution_plan is None else self.execution_plan.plan_checksum),
            ("run_approval", None if self.run_approval is None else self.run_approval.approval_checksum),
            ("run_consumption", None if self.run_consumption is None else self.run_consumption.consumption_checksum),
            ("execution_evidence", None if self.supplied_execution is None else self.supplied_execution.evidence.evidence_checksum),
            ("evaluation", None if self.evaluation is None else self.evaluation.receipt.evaluation_checksum),
            ("owner_result_review", None if self.owner_result_review is None else self.owner_result_review.review_checksum),
            ("final_record", None if self.finalized_record is None else self.finalized_record.record_checksum),
        )
        return GenericExperimentContinuationReceipt(
            self.stage, self.checkpoint, self.objective.objective_ref_checksum,
            tuple((name, checksum) for name, checksum in facts if checksum is not None),
        )


@dataclass(frozen=True, slots=True)
class CoordinatorResult:
    status: CoordinatorStatus
    continuation: GenericExperimentContinuation
    checkpoint: CheckpointCode | None = None
    summary: str = ""


def _checkpoint(
    continuation: GenericExperimentContinuation, code: CheckpointCode, summary: str,
) -> CoordinatorResult:
    current = replace(continuation, checkpoint=code)
    return CoordinatorResult(CoordinatorStatus.CHECKPOINT, current, code, summary)


def _version_tuple(value: str) -> tuple[int, ...] | None:
    parts = value.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def _version_satisfies(version: str, constraint: str | None) -> bool:
    if constraint is None:
        return True
    actual = _version_tuple(version)
    if actual is None:
        return version == constraint.removeprefix("==")
    for clause in (item.strip() for item in constraint.split(",")):
        operator = next((item for item in (">=", "<=", "==", ">", "<") if clause.startswith(item)), "==")
        expected_text = clause[len(operator):] if clause.startswith(operator) else clause
        expected = _version_tuple(expected_text)
        if expected is None:
            return False
        width = max(len(actual), len(expected))
        left, right = actual + (0,) * (width - len(actual)), expected + (0,) * (width - len(expected))
        if not {"==": left == right, ">=": left >= right, "<=": left <= right, ">": left > right, "<": left < right}[operator]:
            return False
    return True


class GenericExperimentCoordinator:
    def __init__(
        self, resolver: BoundedCapabilityResolver, *, workflow: ExactIdentity,
    ) -> None:
        self._resolver = resolver
        self._workflow = workflow

    def assess_and_select(
        self, objective: ResearchObjectiveRef, methodology: GenericMethodology | None,
        *, owner_selected_capability_checksum: str | None = None,
        owner_confirmation_checksum: str | None = None,
    ) -> CoordinatorResult:
        start = GenericExperimentContinuation(objective, methodology)
        if methodology is None or methodology.research_objective != objective or methodology.unresolved_material_decisions:
            return _checkpoint(
                start, CheckpointCode.METHODOLOGY_DECISION_REQUIRED,
                "A bounded methodology decision remains unresolved.",
            )
        assessments: list[CapabilityAssessment] = []
        for binding in self._resolver.bindings:
            assessment = self._resolver.invoke(
                binding, CapabilityOperation.ASSESS_SUPPORT, objective, methodology,
            )
            if not isinstance(assessment, CapabilityAssessment) or (
                assessment.capability_checksum != binding.descriptor.capability.capability_checksum
                or assessment.objective_checksum != objective.objective_ref_checksum
                or assessment.methodology_checksum != methodology.methodology_checksum
            ):
                raise GenericExperimentCoordinatorError("Capability assessment lineage mismatch")
            assessments.append(assessment)
        supported = tuple(item for item in assessments if item.status is SupportStatus.SUPPORTED)
        needs_owner = any(item.status is SupportStatus.NEEDS_OWNER_DECISION for item in assessments)
        selected: str | None = None
        materiality = SelectionMateriality.NOT_APPLICABLE
        confirmation: str | None = None
        if not needs_owner and len(supported) == 1:
            selected = supported[0].capability_checksum
        elif not needs_owner and len(supported) > 1:
            supporting_bindings = tuple(
                item for item in self._resolver.bindings
                if item.descriptor.capability.capability_checksum
                in {entry.capability_checksum for entry in supported}
            )
            keys = {item.descriptor.fallback_equivalence_key for item in supporting_bindings}
            if len(keys) == 1 and None not in keys:
                materiality = SelectionMateriality.NON_MATERIAL_FALLBACK_EQUIVALENT
                selected = min(
                    supported, key=lambda item: (item.presentation_order, item.capability_checksum)
                ).capability_checksum
            else:
                materiality = SelectionMateriality.MATERIAL_DIFFERENCE
                if owner_selected_capability_checksum is not None and owner_confirmation_checksum is not None:
                    selected = owner_selected_capability_checksum
                    confirmation = owner_confirmation_checksum
        selection = CapabilitySelection(
            methodology.methodology_checksum, tuple(assessments), materiality, selected,
            "Exact reviewed Capability support was assessed without priority-based scientific choice.",
            confirmation,
        )
        current = replace(start, selection=selection)
        if selection.outcome is SelectionOutcome.CAPABILITY_ASSESSMENT_OWNER_DECISION_REQUIRED:
            return _checkpoint(
                current, CheckpointCode.METHODOLOGY_DECISION_REQUIRED,
                "Capability support depends on an unresolved Owner methodology decision.",
            )
        if selection.outcome is SelectionOutcome.AUTOMATIC_PREPARATION_UNSUPPORTED:
            return _checkpoint(
                current, CheckpointCode.AUTOMATIC_PREPARATION_UNSUPPORTED,
                "No exact reviewed Capability supports this methodology.",
            )
        if selection.outcome is SelectionOutcome.PREPARATION_CAPABILITY_SELECTION_REQUIRED:
            return _checkpoint(
                current, CheckpointCode.CAPABILITY_SELECTION_REQUIRED,
                "Materially different supported Capabilities require explicit Owner selection.",
            )
        capability = next(
            item.descriptor.capability for item in self._resolver.bindings
            if item.descriptor.capability.capability_checksum == selection.selected_capability_checksum
        )
        return _checkpoint(
            replace(current, capability=capability), CheckpointCode.DESIGN_APPROVAL_REQUIRED,
            "The exact methodology and Capability selection require Design Approval.",
        )

    def authorize_design(
        self, continuation: GenericExperimentContinuation, approval: DesignApproval | None,
    ) -> CoordinatorResult:
        if continuation.methodology is None or continuation.selection is None or continuation.capability is None:
            raise GenericExperimentCoordinatorError("Capability selection is incomplete")
        if approval is None:
            return _checkpoint(
                continuation, CheckpointCode.DESIGN_APPROVAL_REQUIRED,
                "Design Approval is required before preparation.",
            )
        try:
            approval.validate(continuation.methodology)
        except GenericExperimentContractError:
            return _checkpoint(
                continuation, CheckpointCode.DESIGN_APPROVAL_REQUIRED,
                "Methodology drift invalidated Design Approval.",
            )
        binding = DesignApprovalBinding(
            approval.approval_checksum, continuation.selection.selection_checksum,
            continuation.capability.capability_checksum,
        )
        current = replace(
            continuation, design_approval=approval, design_binding=binding, checkpoint=None,
        )
        return CoordinatorResult(CoordinatorStatus.DESIGN_APPROVED, current)

    def validate_specification_and_declare(
        self, continuation: GenericExperimentContinuation, specification: Any,
    ) -> CoordinatorResult:
        self._require_design(continuation)
        assert continuation.methodology and continuation.capability and continuation.design_binding
        binding = self._resolver.resolve(continuation.capability)
        validated = binding.implementation.validate_specification(
            continuation.methodology, specification,
        )
        if not isinstance(validated, ValidatedOpaqueSpecification) or (
            validated.reference.capability_checksum != continuation.capability.capability_checksum
            or validated.reference.methodology_checksum != continuation.methodology.methodology_checksum
            or validated.reference.specification_schema
            != continuation.capability.implementation_spec_schema
        ):
            raise GenericExperimentCoordinatorError("Capability specification validation lineage mismatch")
        declaration = self._resolver.invoke(
            binding, CapabilityOperation.DECLARE_REQUIREMENTS,
            continuation.methodology, validated,
        )
        if not isinstance(declaration, CapabilityRequirementDeclaration) or (
            declaration.capability_checksum != continuation.capability.capability_checksum
            or declaration.specification_reference_checksum != validated.reference.reference_checksum
        ):
            raise GenericExperimentCoordinatorError("Capability requirement declaration lineage mismatch")
        current = replace(
            continuation, specification=validated, requirements=declaration,
            resource_readiness=(), preparation_readiness=(), checkpoint=None,
        )
        return CoordinatorResult(CoordinatorStatus.REQUIREMENTS_DECLARED, current)

    def evaluate_requirement_readiness(
        self, continuation: GenericExperimentContinuation,
        *, resources: tuple[ExperimentResourceReadinessEvidence, ...],
        preparation: tuple[PreparationReadinessEvidence, ...],
    ) -> CoordinatorResult:
        if continuation.requirements is None:
            raise GenericExperimentCoordinatorError("Requirements have not been declared")
        declaration = continuation.requirements
        expected_resources = {item.requirement_checksum: item for item in declaration.resource_requirements}
        supplied_resources = {item.requirement_checksum: item for item in resources}
        if len(supplied_resources) != len(resources) or set(supplied_resources) - set(expected_resources):
            raise GenericExperimentCoordinatorError("Resource readiness evidence is not exact")
        unresolved_resources = []
        ordered_resources = []
        for checksum, requirement in expected_resources.items():
            evidence = supplied_resources.get(checksum)
            if evidence is None:
                if requirement.required:
                    unresolved_resources.append(requirement.requirement_key)
                continue
            ordered_resources.append(evidence)
            exact_verified = (
                evidence.readiness is ResourceReadiness.RESOLVED_VERIFIED
                and evidence.expected_content_checksum == evidence.verified_content_checksum
            )
            if not exact_verified and requirement.required:
                unresolved_resources.append(requirement.requirement_key)
        current = replace(continuation, resource_readiness=tuple(ordered_resources))
        if unresolved_resources:
            return _checkpoint(
                current, CheckpointCode.RESOURCE_READINESS_REQUIRED,
                "Required research-resource readiness is missing or drifted: "
                + ", ".join(unresolved_resources),
            )

        expected_preparation = {item.requirement_checksum: item for item in declaration.preparation_requirements}
        supplied_preparation = {item.requirement_checksum: item for item in preparation}
        if len(supplied_preparation) != len(preparation) or set(supplied_preparation) - set(expected_preparation):
            raise GenericExperimentCoordinatorError("Preparation readiness evidence is not exact")
        unresolved_preparation = []
        ordered_preparation = []
        for checksum, requirement in expected_preparation.items():
            evidence = supplied_preparation.get(checksum)
            if evidence is not None:
                ordered_preparation.append(evidence)
            if not self._preparation_satisfies(requirement, evidence):
                if requirement.required:
                    unresolved_preparation.append(requirement.requirement_key)
        current = replace(
            current, preparation_readiness=tuple(ordered_preparation), checkpoint=None,
        )
        if unresolved_preparation:
            return _checkpoint(
                current, CheckpointCode.PREPARATION_REQUIREMENT_UNMET,
                "Required local preparation capability is unavailable: "
                + ", ".join(unresolved_preparation),
            )
        return CoordinatorResult(CoordinatorStatus.REQUIREMENTS_READY, current)

    def prepare_candidate(
        self, continuation: GenericExperimentContinuation, preparation_root: Path,
        *, prepared_at: str,
    ) -> CoordinatorResult:
        self._require_ready_requirements(continuation)
        assert continuation.capability and continuation.methodology
        assert continuation.specification and continuation.requirements
        if CapabilityOperation.PREPARE not in continuation.capability.operations:
            return _checkpoint(
                continuation, CheckpointCode.CAPABILITY_PREPARATION_UNAVAILABLE,
                "The exact Capability has no PREPARE operation; a future Path B may supply a candidate.",
            )
        if preparation_root.is_symlink():
            raise GenericExperimentCoordinatorError("Preparation root must not be a symbolic link")
        preparation_root.mkdir(parents=True, exist_ok=True)
        if not preparation_root.is_dir():
            raise GenericExperimentCoordinatorError("Preparation root is unavailable")
        candidate_root = preparation_root / f"candidate-{uuid.uuid4().hex}"
        candidate_root.mkdir(mode=0o700)
        binding = self._resolver.resolve(continuation.capability)
        context = CapabilityPreparationContext(
            continuation.objective, continuation.methodology, continuation.specification,
            continuation.requirements,
            tuple(item.readiness_checksum for item in continuation.resource_readiness),
            prepared_at,
        )
        candidate = self._resolver.invoke(
            binding, CapabilityOperation.PREPARE, candidate_root, context,
        )
        if not isinstance(candidate, PreparedCapabilityCandidate):
            raise GenericExperimentCoordinatorError("Capability returned no candidate receipt")
        current = replace(
            continuation, candidate=candidate, candidate_root=candidate_root, checkpoint=None,
        )
        return CoordinatorResult(CoordinatorStatus.PACKAGE_CANDIDATE_CREATED, current)

    def validate_and_promote_candidate(
        self, continuation: GenericExperimentContinuation, *, validated_at: str,
        promoted_root: Path | None = None,
    ) -> CoordinatorResult:
        if continuation.candidate is None or continuation.candidate_root is None:
            raise GenericExperimentCoordinatorError("No Capability candidate exists")
        assert continuation.capability and continuation.methodology
        assert continuation.specification and continuation.requirements
        tree_checksum = self._scan_package(continuation.candidate_root)
        manifest, receipt = continuation.candidate.manifest, continuation.candidate.receipt
        launch_path = continuation.candidate_root / manifest.launch_target.relative_path
        if sha256_bytes(launch_path.read_bytes()) != manifest.launch_target.checksum:
            raise GenericExperimentCoordinatorError("Candidate launch target checksum mismatch")
        dependency_checksums = []
        for declaration in manifest.dependency_declarations:
            path = continuation.candidate_root / declaration.relative_path
            if sha256_bytes(path.read_bytes()) != declaration.checksum:
                raise GenericExperimentCoordinatorError("Candidate dependency declaration drift")
            dependency_checksums.append(declaration.checksum)
        expected_resource_checksums = tuple(
            item.readiness_checksum for item in continuation.resource_readiness
        )
        if (
            tree_checksum != receipt.package_tree_checksum
            or receipt.research_objective != continuation.objective
            or receipt.methodology_checksum != continuation.methodology.methodology_checksum
            or receipt.capability.checksum != continuation.capability.capability_checksum
            or receipt.capsule != continuation.capability.capsule
            or receipt.workflow != self._workflow
            or receipt.implementation_specification != continuation.specification.reference
            or manifest.implementation_specification != continuation.specification.reference
            or manifest.capability_checksum != continuation.capability.capability_checksum
            or manifest.runtime_requirement_checksum
            != continuation.requirements.runtime_requirement.requirement_checksum
            or receipt.runtime_requirement != continuation.requirements.runtime_requirement
            or manifest.launch_target.launch_contract
            != continuation.requirements.runtime_requirement.launch_contract
            or tuple(dependency_checksums)
            != tuple(item.checksum for item in continuation.requirements.runtime_requirement.dependency_declarations)
            or manifest.resource_identity_checksums != expected_resource_checksums
            or receipt.resource_identity_checksums != expected_resource_checksums
        ):
            raise GenericExperimentCoordinatorError("Candidate package exact lineage mismatch")
        safety = PackageSafetyEvidence(True, True, True, True, True, True, True)
        validated = ValidatedExperimentPackage(
            manifest, receipt, tree_checksum,
            continuation.requirements.runtime_requirement.requirement_checksum,
            expected_resource_checksums, safety, "VALIDATED", validated_at,
        )
        final_root = continuation.candidate_root
        if promoted_root is not None:
            if promoted_root.exists() or promoted_root.is_symlink():
                raise GenericExperimentCoordinatorError("Validated package destination already exists")
            promoted_root.parent.mkdir(parents=True, exist_ok=True)
            os.replace(continuation.candidate_root, promoted_root)
            final_root = promoted_root
        current = replace(
            continuation, validated_package=validated, validated_package_root=final_root,
            candidate_root=final_root, checkpoint=None,
        )
        return CoordinatorResult(CoordinatorStatus.PACKAGE_VALIDATED, current)

    def resolve_runtime(
        self, continuation: GenericExperimentContinuation,
        candidates: tuple[LocalRuntimeCandidate, ...], *, verified_at: str,
    ) -> CoordinatorResult:
        if continuation.validated_package is None or continuation.requirements is None:
            raise GenericExperimentCoordinatorError("A validated package is required")
        requirement = continuation.requirements.runtime_requirement
        compatible = tuple(
            candidate for candidate in candidates
            if candidate.locally_verified
            and candidate.runtime_family == requirement.runtime_family
            and _version_satisfies(candidate.runtime_version, requirement.version_constraint)
            and set(requirement.required_capabilities).issubset(candidate.available_capabilities)
            and candidate.dependency_identity_checksums
            == tuple(item.checksum for item in requirement.dependency_declarations)
        )
        if not compatible:
            return _checkpoint(
                replace(continuation, local_runtime=None, runtime_compatibility=None),
                CheckpointCode.RUNTIME_INCOMPATIBLE,
                "No explicitly supplied compatible local runtime is available.",
            )
        selected = min(compatible, key=lambda item: item.candidate_id)
        receipt = RuntimeCompatibility(
            requirement.requirement_checksum, selected.portable_identity_checksum,
            selected.environment_checksum, CompatibilityStatus.COMPATIBLE,
            ("The exact supplied local runtime satisfies the declared requirement.",),
            verified_at,
        )
        current = replace(
            continuation, local_runtime=selected, runtime_compatibility=receipt,
            checkpoint=None,
        )
        return CoordinatorResult(CoordinatorStatus.RUNTIME_COMPATIBLE, current)

    def build_execution_plan(
        self, continuation: GenericExperimentContinuation,
        *, capability_output_contract: ContractRef,
    ) -> CoordinatorResult:
        if (
            continuation.validated_package is None
            or continuation.runtime_compatibility is None
            or continuation.local_runtime is None
            or continuation.specification is None
            or continuation.methodology is None
            or continuation.capability is None
            or continuation.requirements is None
        ):
            raise GenericExperimentCoordinatorError("Package/runtime lineage is incomplete")
        self._validate_runtime_receipt(continuation)
        manifest = continuation.validated_package.manifest
        plan = GenericExecutionPlan(
            continuation.objective.objective_ref_checksum,
            continuation.methodology.methodology_checksum,
            continuation.capability.capability_checksum,
            continuation.specification.reference.specification_checksum,
            tuple(item.readiness_checksum for item in continuation.resource_readiness),
            continuation.validated_package.validated_package_checksum,
            continuation.runtime_compatibility.compatibility_checksum,
            manifest.launch_target.launch_contract, manifest.launch_target.relative_path,
            continuation.requirements.runtime_requirement.resource_constraints,
            continuation.requirements.runtime_requirement.network_policy,
            manifest.expected_outputs, capability_output_contract,
        )
        current = replace(continuation, execution_plan=plan, checkpoint=None)
        return CoordinatorResult(CoordinatorStatus.EXECUTION_PLAN_READY, current)

    def authorize_run(
        self, continuation: GenericExperimentContinuation,
        approval: GenericRunApproval | None,
    ) -> CoordinatorResult:
        if continuation.execution_plan is None:
            raise GenericExperimentCoordinatorError("Execution Plan is unavailable")
        if approval is None:
            return _checkpoint(
                continuation, CheckpointCode.RUN_APPROVAL_REQUIRED,
                "Owner approval of the exact execution plan is required.",
            )
        try:
            approval.validate(continuation.execution_plan)
        except GenericExperimentCoordinatorError:
            return _checkpoint(
                continuation, CheckpointCode.RUN_APPROVAL_REQUIRED,
                "Execution Plan drift invalidated Run Approval.",
            )
        current = replace(continuation, run_approval=approval, checkpoint=None)
        return CoordinatorResult(CoordinatorStatus.READY_FOR_EXECUTION, current)

    def handoff_execution(
        self, continuation: GenericExperimentContinuation,
        runner: BoundedRunnerCollaborator, *, attempt_id: str, consumed_at: str,
    ) -> CoordinatorResult:
        if (
            continuation.execution_plan is None or continuation.run_approval is None
            or continuation.validated_package_root is None or continuation.local_runtime is None
        ):
            raise GenericExperimentCoordinatorError("Execution is not approved and ready")
        if continuation.run_consumption is not None:
            raise GenericExperimentCoordinatorError("RUN_APPROVAL_ALREADY_CONSUMED")
        continuation.run_approval.validate(continuation.execution_plan)
        self._validate_runtime_receipt(continuation)
        consumption = RunApprovalConsumption(
            continuation.run_approval.approval_checksum,
            continuation.execution_plan.plan_checksum, attempt_id, consumed_at,
        )
        supplied = runner.execute(ExecutionHandoff(
            continuation.execution_plan, continuation.run_approval, consumption,
            continuation.validated_package_root, continuation.local_runtime,
        ))
        self._validate_supplied_execution(continuation, consumption, supplied)
        current = replace(
            continuation, run_consumption=consumption, supplied_execution=supplied,
            checkpoint=None,
        )
        return CoordinatorResult(CoordinatorStatus.EXECUTION_EVIDENCE_PRESENT, current)

    def accept_execution_evidence(
        self, continuation: GenericExperimentContinuation,
        supplied: SuppliedExecution, consumption: RunApprovalConsumption,
    ) -> CoordinatorResult:
        """Accept evidence supplied by the existing bounded-runner boundary."""
        if continuation.run_consumption is not None:
            raise GenericExperimentCoordinatorError("RUN_APPROVAL_ALREADY_CONSUMED")
        self._validate_supplied_execution(continuation, consumption, supplied)
        current = replace(
            continuation, run_consumption=consumption, supplied_execution=supplied,
            checkpoint=None,
        )
        return CoordinatorResult(CoordinatorStatus.EXECUTION_EVIDENCE_PRESENT, current)

    def evaluate(self, continuation: GenericExperimentContinuation) -> CoordinatorResult:
        if continuation.supplied_execution is None or continuation.capability is None:
            raise GenericExperimentCoordinatorError("Execution evidence is unavailable")
        assert continuation.methodology and continuation.specification and continuation.execution_plan
        binding = self._resolver.resolve(continuation.capability)
        result = self._resolver.invoke(
            binding, CapabilityOperation.EVALUATE,
            {
                "objective": continuation.objective,
                "methodology": continuation.methodology,
                "specification": continuation.specification,
                "plan": continuation.execution_plan,
                "execution_evidence": continuation.supplied_execution.evidence,
                "outputs": continuation.supplied_execution.outputs,
            },
        )
        if not isinstance(result, CapabilityEvaluationResult):
            raise GenericExperimentCoordinatorError("Capability evaluation result is invalid")
        receipt = result.receipt
        evidence = continuation.supplied_execution.evidence
        if (
            receipt.capability_checksum != continuation.capability.capability_checksum
            or receipt.objective_checksum != continuation.objective.objective_ref_checksum
            or receipt.methodology_checksum != continuation.methodology.methodology_checksum
            or receipt.implementation_specification_checksum
            != continuation.specification.reference.specification_checksum
            or receipt.execution_plan_checksum != continuation.execution_plan.plan_checksum
            or receipt.execution_outputs != evidence.outputs
            or receipt.expected_output_contract_checksum
            != continuation.execution_plan.capability_output_contract.checksum
            or receipt.evaluation_schema != continuation.capability.evaluation_schema
            or receipt.result_payload_checksum != canonical_hash(to_json_value(result.result_payload))
        ):
            raise GenericExperimentCoordinatorError("Capability evaluation lineage mismatch")
        try:
            scientific_status = ScientificEvidenceStatus(result.scientific_evidence_status)
        except ValueError as error:
            raise GenericExperimentCoordinatorError("Capability scientific evidence status is invalid") from error
        normalized = NormalizedExperimentResult(
            evidence.process_outcome, receipt.validity, scientific_status, receipt.limitations,
        )
        current = replace(
            continuation, evaluation=result, normalized_result=normalized, checkpoint=None,
        )
        return CoordinatorResult(CoordinatorStatus.EVALUATION_COMPLETE, current)

    def require_result_review(self, continuation: GenericExperimentContinuation) -> CoordinatorResult:
        if continuation.evaluation is None:
            raise GenericExperimentCoordinatorError("Evaluation is incomplete")
        return _checkpoint(
            continuation, CheckpointCode.RESULT_REVIEW_REQUIRED,
            "Owner review of the bounded evaluated result is required.",
        )

    def accept_result_review(
        self, continuation: GenericExperimentContinuation,
        review: OwnerResultReview | None,
    ) -> CoordinatorResult:
        if continuation.evaluation is None or continuation.normalized_result is None:
            raise GenericExperimentCoordinatorError("Evaluation is incomplete")
        if review is None:
            return self.require_result_review(continuation)
        if (
            review.evaluation_checksum != continuation.evaluation.receipt.evaluation_checksum
            or review.normalized_result_checksum != canonical_hash(continuation.normalized_result)
        ):
            return _checkpoint(
                continuation, CheckpointCode.RESULT_REVIEW_REQUIRED,
                "Evaluation drift invalidated Owner result review.",
            )
        current = replace(continuation, owner_result_review=review, checkpoint=None)
        return CoordinatorResult(CoordinatorStatus.READY_FOR_FINALIZATION, current)

    def finalize(
        self, continuation: GenericExperimentContinuation,
    ) -> CoordinatorResult:
        if (
            continuation.owner_result_review is None or continuation.evaluation is None
            or continuation.normalized_result is None or continuation.capability is None
            or continuation.methodology is None or continuation.design_approval is None
            or continuation.selection is None or continuation.specification is None
            or continuation.validated_package is None or continuation.requirements is None
            or continuation.runtime_compatibility is None or continuation.execution_plan is None
            or continuation.run_approval is None
        ):
            raise GenericExperimentCoordinatorError("Experiment is not ready for finalization")
        binding = self._resolver.resolve(continuation.capability)
        if CapabilityOperation.PRESENT in continuation.capability.operations:
            presentation = self._resolver.invoke(
                binding, CapabilityOperation.PRESENT,
                {
                    "evaluation": continuation.evaluation,
                    "normalized_result": continuation.normalized_result,
                    "owner_review": continuation.owner_result_review,
                },
            )
            if not isinstance(presentation, ContractRef):
                raise GenericExperimentCoordinatorError("Capability presentation receipt is invalid")
        else:
            presentation = ContractRef(
                "reagent.artifact-presentation.experiment-record/v0.2",
                canonical_hash({
                    "evaluation": continuation.evaluation.receipt.evaluation_checksum,
                    "normalized": continuation.normalized_result,
                }),
            )
        record = ExperimentRecordV4(
            continuation.objective, continuation.methodology,
            continuation.design_approval, continuation.selection,
            continuation.capability, continuation.specification.reference,
            tuple(ContractRef(item.schema, item.readiness_checksum) for item in continuation.resource_readiness),
            continuation.validated_package, continuation.requirements.runtime_requirement,
            continuation.runtime_compatibility,
            ContractRef(EXECUTION_PLAN_SCHEMA, continuation.execution_plan.plan_checksum),
            ContractRef(RUN_APPROVAL_SCHEMA, continuation.run_approval.approval_checksum),
            continuation.evaluation.receipt, continuation.normalized_result,
            ContractRef(OWNER_RESULT_REVIEW_SCHEMA, continuation.owner_result_review.review_checksum),
            presentation, continuation.normalized_result.limitations,
        )
        current = replace(
            continuation, presentation=presentation, finalized_record=record, checkpoint=None,
        )
        return CoordinatorResult(CoordinatorStatus.FINALIZED, current)

    @staticmethod
    def _preparation_satisfies(
        requirement: PreparationRequirement,
        evidence: PreparationReadinessEvidence | None,
    ) -> bool:
        if evidence is None:
            return not requirement.required
        return (
            evidence.available
            and evidence.requirement_family == requirement.requirement_family
            and _version_satisfies(evidence.available_version or "", requirement.version_constraint)
            and set(requirement.required_capabilities).issubset(evidence.available_capabilities)
        )

    @staticmethod
    def _scan_package(root: Path) -> str:
        if root.is_symlink() or not root.is_dir():
            raise GenericExperimentCoordinatorError("Candidate package root is unsafe")
        entries: list[dict[str, Any]] = []
        folded: set[str] = set()
        total = 0

        def visit(directory: Path) -> None:
            nonlocal total
            with os.scandir(directory) as iterator:
                children = sorted(iterator, key=lambda item: item.name)
            for child in children:
                path = Path(child.path)
                relative = path.relative_to(root).as_posix()
                require_relative_path(relative, "candidate package path")
                GenericExperimentCoordinator._record_package_path(relative, folded)
                mode = child.stat(follow_symlinks=False).st_mode
                if stat.S_ISLNK(mode):
                    raise GenericExperimentCoordinatorError("Candidate package contains a symbolic link")
                if stat.S_ISDIR(mode):
                    visit(path)
                    continue
                if not stat.S_ISREG(mode) or child.stat(follow_symlinks=False).st_nlink != 1:
                    raise GenericExperimentCoordinatorError("Candidate package contains a link or special file")
                content = path.read_bytes()
                reject_sensitive_content(content, path=relative)
                total += len(content)
                entries.append({"path": relative, "sha256": sha256_bytes(content), "size_bytes": len(content)})
                if len(entries) > MAX_PACKAGE_FILES or total > MAX_PACKAGE_BYTES:
                    raise GenericExperimentCoordinatorError("Candidate package exceeds its bounds")

        visit(root)
        if not entries:
            raise GenericExperimentCoordinatorError("Candidate package is empty")
        return canonical_hash(entries)

    @staticmethod
    def _record_package_path(relative: str, folded: set[str]) -> None:
        folded_name = relative.casefold()
        if folded_name in folded:
            raise GenericExperimentCoordinatorError("Candidate package contains a case collision")
        folded.add(folded_name)

    @staticmethod
    def _validate_supplied_execution(
        continuation: GenericExperimentContinuation,
        consumption: RunApprovalConsumption,
        supplied: SuppliedExecution,
    ) -> None:
        if continuation.execution_plan is None or continuation.run_approval is None:
            raise GenericExperimentCoordinatorError("Execution is not approved")
        evidence = supplied.evidence
        if (
            consumption.approval_checksum != continuation.run_approval.approval_checksum
            or consumption.execution_plan_checksum != continuation.execution_plan.plan_checksum
            or evidence.execution_plan_checksum != continuation.execution_plan.plan_checksum
            or evidence.run_approval_checksum != continuation.run_approval.approval_checksum
            or evidence.approval_consumption_checksum != consumption.consumption_checksum
            or evidence.network_policy != continuation.execution_plan.network_policy
        ):
            raise GenericExperimentCoordinatorError("Execution evidence lineage mismatch")
        if len(supplied.outputs) != len(evidence.outputs):
            raise GenericExperimentCoordinatorError("Execution output receipt count mismatch")
        if {item.name for item in evidence.outputs} != {
            item.name for item in continuation.execution_plan.expected_outputs
        }:
            raise GenericExperimentCoordinatorError("Execution output identities do not match the exact plan")
        output_map = {item.name: item for item in supplied.outputs}
        if len(output_map) != len(supplied.outputs):
            raise GenericExperimentCoordinatorError("Execution output payload identities are not unique")
        total = 0
        for identity in evidence.outputs:
            output = output_map.get(identity.name)
            if output is None or sha256_bytes(output.content) != identity.checksum:
                raise GenericExperimentCoordinatorError("Execution output checksum mismatch")
            total += len(output.content)
        if total > MAX_EXECUTION_OUTPUT_BYTES:
            raise GenericExperimentCoordinatorError("Execution outputs exceed their bound")

    @staticmethod
    def _validate_runtime_receipt(continuation: GenericExperimentContinuation) -> None:
        assert continuation.local_runtime and continuation.runtime_compatibility
        if (
            continuation.runtime_compatibility.portable_runtime_identity_checksum
            != continuation.local_runtime.portable_identity_checksum
            or continuation.runtime_compatibility.environment_checksum
            != continuation.local_runtime.environment_checksum
            or continuation.runtime_compatibility.status is not CompatibilityStatus.COMPATIBLE
        ):
            raise GenericExperimentCoordinatorError("Runtime environment drift invalidated compatibility")

    @staticmethod
    def _require_design(continuation: GenericExperimentContinuation) -> None:
        if (
            continuation.methodology is None or continuation.selection is None
            or continuation.capability is None or continuation.design_approval is None
            or continuation.design_binding is None
        ):
            raise GenericExperimentCoordinatorError("Design Approval is incomplete")
        continuation.design_approval.validate(continuation.methodology)
        if (
            continuation.design_binding.design_approval_checksum
            != continuation.design_approval.approval_checksum
            or continuation.design_binding.capability_selection_checksum
            != continuation.selection.selection_checksum
            or continuation.design_binding.selected_capability_checksum
            != continuation.capability.capability_checksum
        ):
            raise GenericExperimentCoordinatorError("Design Approval or Capability-selection drift")

    @classmethod
    def _require_ready_requirements(cls, continuation: GenericExperimentContinuation) -> None:
        cls._require_design(continuation)
        if continuation.requirements is None or continuation.specification is None:
            raise GenericExperimentCoordinatorError("Requirement declaration is incomplete")
        if continuation.checkpoint in {
            CheckpointCode.RESOURCE_READINESS_REQUIRED,
            CheckpointCode.PREPARATION_REQUIREMENT_UNMET,
        }:
            raise GenericExperimentCoordinatorError("Declared requirements are not ready")
