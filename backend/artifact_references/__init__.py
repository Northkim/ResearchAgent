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
]
