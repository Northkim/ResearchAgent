from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.resource_references.contracts import (
    ProjectResourceReference,
    ResourceBindingState,
    ResourceKind,
    ResourceLifecycle,
    ResourceProvider,
    WorkflowResourceBinding,
    WorkflowResourceRequirement,
)
from backend.resource_references.experiment_requirement_contracts import (
    ExperimentResourceContractError,
    ExperimentResourceReadinessEvidence,
    ExperimentResourceRequirementRef,
    ResourceReadiness,
)

SHA = "sha256:" + "a" * 64
NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)


def requirement() -> WorkflowResourceRequirement:
    return WorkflowResourceRequirement(
        "reproduction-experiment-local-experimental", "0.6.0", "source_material",
        ResourceKind.GENERIC_FILE, 1, 1, True, (ResourceProvider.LOCAL_TEST,),
        "One exact registered research input required by the reviewed Capability.", NOW, NOW,
    )


def test_capability_requirement_reuses_existing_resource_authority() -> None:
    projected = ExperimentResourceRequirementRef.from_workflow_requirement(SHA, requirement())
    assert projected.resource_kind == ResourceKind.GENERIC_FILE.value
    assert projected.allowed_providers == (ResourceProvider.LOCAL_TEST.value,)
    unbound = ExperimentResourceReadinessEvidence.from_existing_state(projected)
    assert unbound.readiness is ResourceReadiness.UNBOUND


def test_exact_binding_and_local_verified_index_form_one_readiness_receipt() -> None:
    projected = ExperimentResourceRequirementRef.from_workflow_requirement(SHA, requirement())
    resource = ProjectResourceReference(
        "resource-" + "a" * 32, "project-" + "b" * 32,
        ResourceKind.GENERIC_FILE, ResourceProvider.LOCAL_TEST, "fixture/material",
        "revision-001", SHA, "Reviewed source material", {}, ResourceLifecycle.ACTIVE,
        NOW, NOW,
    )
    binding = WorkflowResourceBinding(
        "resource-binding-" + "c" * 32, resource.project_id, "wfi-" + "d" * 32,
        projected.workflow_definition_id, projected.workflow_version,
        projected.requirement_key, resource.resource_id, SHA, ResourceBindingState.ACTIVE,
        "00000000-0000-0000-0000-000000000001", NOW, NOW,
    )
    bound = ExperimentResourceReadinessEvidence.from_existing_state(
        projected, binding=binding, resource=resource,
    )
    assert bound.readiness is ResourceReadiness.BOUND_METADATA_ONLY
    ready = ExperimentResourceReadinessEvidence.from_existing_state(
        projected, binding=binding, resource=resource,
        local_resolution_status="RESOLVED_VERIFIED", verified_content_checksum=SHA,
    )
    assert ready.readiness is ResourceReadiness.RESOLVED_VERIFIED
    with pytest.raises(ExperimentResourceContractError, match="do not match"):
        ExperimentResourceReadinessEvidence.from_existing_state(
            projected, binding=binding, resource=resource,
            local_resolution_status="RESOLVED_VERIFIED",
            verified_content_checksum="sha256:" + "b" * 64,
        )
