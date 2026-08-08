"""Typed Artifact Reference foundation for the local-product architecture."""

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
    ARTIFACT_CONTRACTS,
    FUTURE_WORKFLOW_CONTRACTS,
    ResearchFlowContractError,
    build_selected_research_idea,
    validate_experiment_record,
    validate_manuscript_draft,
    validate_review_report,
    validate_selected_research_idea,
)

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
    "FUTURE_WORKFLOW_CONTRACTS",
    "ResearchFlowContractError",
    "build_selected_research_idea",
    "validate_experiment_record",
    "validate_manuscript_draft",
    "validate_review_report",
    "validate_selected_research_idea",
]
