"""Frozen deterministic identities for legacy local Projects."""

from __future__ import annotations

from uuid import UUID, uuid5

from backend.local_projects.contracts import LITERATURE_SEARCH_WORKFLOW

LEGACY_WORKFLOW_INSTANCE_NAMESPACE = UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")


def legacy_workflow_instance_id(project_id: str) -> str:
    """Return the owner-frozen UUIDv5 identity for one legacy Project."""

    canonical_name = (
        f"legacy-workflow-instance/v1|project={project_id}|"
        f"workflow={LITERATURE_SEARCH_WORKFLOW}"
    )
    return "wfi-" + uuid5(LEGACY_WORKFLOW_INSTANCE_NAMESPACE, canonical_name).hex
