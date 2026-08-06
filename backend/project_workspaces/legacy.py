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


def workspace_id_for_project(project_id: str) -> str:
    """Map the globally unique Project payload to its one logical Workspace."""

    prefix = "project-"
    if not project_id.startswith(prefix) or len(project_id) != len(prefix) + 32:
        raise ValueError("project_id has an invalid canonical format")
    payload = project_id.removeprefix(prefix)
    if any(character not in "0123456789abcdef" for character in payload):
        raise ValueError("project_id has an invalid canonical format")
    return "workspace-" + payload


def initial_manifest_idempotency_key(project_id: str) -> str:
    name = f"legacy-project-manifest/v1|project={project_id}|revision=1"
    return str(uuid5(LEGACY_WORKFLOW_INSTANCE_NAMESPACE, name))
