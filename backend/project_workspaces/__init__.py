"""Teacher-aligned Project Workspace persistence contracts."""

from .contracts import (
    CapsuleTrustClassification,
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
)
from .errors import WorkflowFoundationConflictError
from .ports import WorkflowFoundationRepository
from .service import reconcile_legacy_workflow_foundation
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
    "LEGACY_WORKFLOW_INSTANCE_NAMESPACE",
    "LITERATURE_SEARCH_CAPSULE_ID",
    "LITERATURE_SEARCH_CAPSULE_VERSION",
    "LITERATURE_SEARCH_DEFINITION_ID",
    "LITERATURE_SEARCH_DEFINITION_VERSION",
    "LITERATURE_SEARCH_STABLE_KEY",
    "ProjectWorkflowInstance",
    "WorkflowCapsuleVersion",
    "WorkflowDefinition",
    "WorkflowDefinitionLifecycle",
    "WorkflowDefinitionVersion",
    "WorkflowInstanceDesiredState",
    "WorkflowFoundationConflictError",
    "WorkflowFoundationRepository",
    "WorkflowReviewStatus",
    "legacy_workflow_instance_id",
    "literature_search_capsule_definition_checksum",
    "literature_search_contract_checksum",
    "reconcile_legacy_workflow_foundation",
]
