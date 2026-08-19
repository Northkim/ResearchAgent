"""Typed Artifact Reference foundation for the local-product architecture."""

from types import MappingProxyType

from .contracts import (
    ARTIFACT_PAGE_SCHEMA,
    ARTIFACT_REFERENCE_SCHEMA,
    MATERIALIZATION_PLAN_SCHEMA,
    ArtifactDeclaration,
    ArtifactDependencyBinding,
    ArtifactMaterializationPlan,
    ArtifactReference,
    ArtifactState,
    CompatibilityMode,
    DependencyBindingState,
    MaterializationMode,
    WorkflowArtifactRequirement,
)
from .ports import ArtifactReferenceRepository
from .research_flow_contracts import (
    ArtifactContract,
    ARTIFACT_CONTRACTS,
    FUTURE_WORKFLOW_CONTRACTS,
    ResearchFlowContractError,
    build_selected_research_idea,
    validate_experiment_record,
    validate_experiment_record_v2,
    validate_manuscript_draft,
    validate_manuscript_draft_v2,
    validate_review_report,
    validate_review_report_v2,
    validate_selected_research_idea,
)
from .generic_experiment_contracts import (
    EXPERIMENT_RECORD_V4_SCHEMA,
    ExperimentRecordV4,
)
from .generic_experiment_v5_contracts import (
    EXPERIMENT_RECORD_V5_SCHEMA,
    BOUNDED_SCIENTIFIC_EVIDENCE_SCHEMA,
    ExperimentRecordV5,
    validate_experiment_record_v5,
)
from .forward_downstream_contracts import (
    MANUSCRIPT_DRAFT_V4,
    REVIEW_REPORT_V3,
    MANUSCRIPT_DRAFT_V5,
    validate_manuscript_draft_v4,
)
from .review_contract_compatibility import validate_review_report_v3
from .revision_contract_compatibility import validate_manuscript_draft_v5
from backend.workflow_packages.serialization import to_json_value


def validate_experiment_record_v4(value):
    """Validate the typed generic v4 instance without parsing Capability data."""

    if not isinstance(value, ExperimentRecordV4):
        raise TypeError("experiment-record/v4 requires the exact typed generic contract")
    return to_json_value(value)


GENERIC_EXPERIMENT_ARTIFACT_CONTRACTS = MappingProxyType({
    EXPERIMENT_RECORD_V4_SCHEMA: ArtifactContract(
        EXPERIMENT_RECORD_V4_SCHEMA,
        EXPERIMENT_RECORD_V4_SCHEMA,
        "application/json",
        validate_experiment_record_v4,
        True,
    ),
})
GENERIC_EXPERIMENT_V5_ARTIFACT_CONTRACTS = MappingProxyType({
    EXPERIMENT_RECORD_V5_SCHEMA: ArtifactContract(
        EXPERIMENT_RECORD_V5_SCHEMA,
        EXPERIMENT_RECORD_V5_SCHEMA,
        "application/json",
        validate_experiment_record_v5,
        True,
    ),
})
FORWARD_DOWNSTREAM_ARTIFACT_CONTRACTS = MappingProxyType({
    MANUSCRIPT_DRAFT_V4: ArtifactContract(
        MANUSCRIPT_DRAFT_V4, MANUSCRIPT_DRAFT_V4, "application/json",
        validate_manuscript_draft_v4, True,
    ),
    REVIEW_REPORT_V3: ArtifactContract(
        REVIEW_REPORT_V3, REVIEW_REPORT_V3, "application/json",
        validate_review_report_v3, True,
    ),
    MANUSCRIPT_DRAFT_V5: ArtifactContract(
        MANUSCRIPT_DRAFT_V5, MANUSCRIPT_DRAFT_V5, "application/json",
        validate_manuscript_draft_v5, True,
    ),
})
PRODUCTION_ARTIFACT_CONTRACTS = MappingProxyType({
    **ARTIFACT_CONTRACTS,
    **GENERIC_EXPERIMENT_ARTIFACT_CONTRACTS,
    **GENERIC_EXPERIMENT_V5_ARTIFACT_CONTRACTS,
    **FORWARD_DOWNSTREAM_ARTIFACT_CONTRACTS,
})

__all__ = [
    "ARTIFACT_PAGE_SCHEMA",
    "ARTIFACT_REFERENCE_SCHEMA",
    "MATERIALIZATION_PLAN_SCHEMA",
    "ArtifactDeclaration",
    "ArtifactDependencyBinding",
    "ArtifactMaterializationPlan",
    "ArtifactReference",
    "ArtifactReferenceRepository",
    "ArtifactState",
    "CompatibilityMode",
    "DependencyBindingState",
    "MaterializationMode",
    "WorkflowArtifactRequirement",
    "ARTIFACT_CONTRACTS",
    "GENERIC_EXPERIMENT_ARTIFACT_CONTRACTS",
    "GENERIC_EXPERIMENT_V5_ARTIFACT_CONTRACTS",
    "FORWARD_DOWNSTREAM_ARTIFACT_CONTRACTS",
    "PRODUCTION_ARTIFACT_CONTRACTS",
    "FUTURE_WORKFLOW_CONTRACTS",
    "ResearchFlowContractError",
    "build_selected_research_idea",
    "validate_experiment_record",
    "validate_experiment_record_v2",
    "validate_experiment_record_v4",
    "validate_experiment_record_v5",
    "validate_manuscript_draft_v4",
    "validate_review_report_v3",
    "validate_manuscript_draft_v5",
    "validate_manuscript_draft",
    "validate_manuscript_draft_v2",
    "validate_review_report",
    "validate_review_report_v2",
    "validate_selected_research_idea",
]
