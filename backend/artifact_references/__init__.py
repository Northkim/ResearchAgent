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
PRODUCTION_ARTIFACT_CONTRACTS = MappingProxyType({
    **ARTIFACT_CONTRACTS,
    **GENERIC_EXPERIMENT_ARTIFACT_CONTRACTS,
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
    "PRODUCTION_ARTIFACT_CONTRACTS",
    "FUTURE_WORKFLOW_CONTRACTS",
    "ResearchFlowContractError",
    "build_selected_research_idea",
    "validate_experiment_record",
    "validate_experiment_record_v2",
    "validate_experiment_record_v4",
    "validate_manuscript_draft",
    "validate_manuscript_draft_v2",
    "validate_review_report",
    "validate_review_report_v2",
    "validate_selected_research_idea",
]
