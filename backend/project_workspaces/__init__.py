"""Teacher-aligned Project Workspace persistence contracts."""

from .contracts import (
    CapsuleTrustClassification,
    CloudProject,
    CloudProjectStatus,
    DesiredProjectManifest,
    ManifestDesiredAction,
    ManifestEntryKind,
    ProjectManifestEntry,
    ProjectWorkflowInstance,
    WorkflowDefinition,
    WorkflowDefinitionLifecycle,
    WorkflowDefinitionVersion,
    WorkflowInstanceDesiredState,
    WorkflowReviewStatus,
    WorkflowCapsuleVersion,
)
from .legacy import (
    LEGACY_WORKFLOW_INSTANCE_NAMESPACE,
    legacy_workflow_instance_id,
    initial_manifest_idempotency_key,
    workspace_id_for_project,
)
from .manifest import build_desired_manifest, mutation_idempotency_key
from .errors import ManifestRevisionConflictError, WorkflowFoundationConflictError
from .ports import ProjectManifestRepository, WorkflowFoundationRepository
from .service import (
    ensure_literature_search_foundation,
    reconcile_legacy_workflow_foundation,
)
from .literature_search import (
    LITERATURE_SEARCH_CAPSULE_ID,
    LITERATURE_SEARCH_CAPSULE_VERSION,
    LITERATURE_SEARCH_DEFINITION_ID,
    LITERATURE_SEARCH_DEFINITION_VERSION,
    LITERATURE_SEARCH_STABLE_KEY,
    literature_search_capsule_definition_checksum,
    literature_search_contract_checksum,
)

__all__ = [
    "CapsuleTrustClassification",
    "CloudProject",
    "CloudProjectStatus",
    "DesiredProjectManifest",
    "LEGACY_WORKFLOW_INSTANCE_NAMESPACE",
    "LITERATURE_SEARCH_CAPSULE_ID",
    "LITERATURE_SEARCH_CAPSULE_VERSION",
    "LITERATURE_SEARCH_DEFINITION_ID",
    "LITERATURE_SEARCH_DEFINITION_VERSION",
    "LITERATURE_SEARCH_STABLE_KEY",
    "ProjectWorkflowInstance",
    "ProjectManifestEntry",
    "ProjectManifestRepository",
    "ManifestDesiredAction",
    "ManifestEntryKind",
    "ManifestRevisionConflictError",
    "WorkflowCapsuleVersion",
    "WorkflowDefinition",
    "WorkflowDefinitionLifecycle",
    "WorkflowDefinitionVersion",
    "WorkflowInstanceDesiredState",
    "WorkflowFoundationConflictError",
    "WorkflowFoundationRepository",
    "WorkflowReviewStatus",
    "legacy_workflow_instance_id",
    "initial_manifest_idempotency_key",
    "literature_search_capsule_definition_checksum",
    "literature_search_contract_checksum",
    "reconcile_legacy_workflow_foundation",
    "ensure_literature_search_foundation",
    "workspace_id_for_project",
    "build_desired_manifest",
    "mutation_idempotency_key",
]
