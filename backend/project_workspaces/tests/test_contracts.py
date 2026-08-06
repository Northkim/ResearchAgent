from datetime import datetime, timezone

import pytest

from backend.project_workspaces import (
    LITERATURE_SEARCH_CAPSULE_ID,
    legacy_workflow_instance_id,
    literature_search_capsule_definition_checksum,
    literature_search_contract_checksum,
)


def test_frozen_legacy_uuid_vectors() -> None:
    assert legacy_workflow_instance_id(
        "project-00000000000000000000000000000000"
    ) == "wfi-cbcb6781f7645ceb8a63f9742b61b80d"
    assert legacy_workflow_instance_id(
        "project-ffffffffffffffffffffffffffffffff"
    ) == "wfi-c3cee26b2aa955d4956a76da8298abf8"


def test_legacy_identity_excludes_package_and_user_text() -> None:
    project_id = "project-1234567890abcdef1234567890abcdef"
    first = legacy_workflow_instance_id(project_id)
    assert first == legacy_workflow_instance_id(project_id)
    assert first != legacy_workflow_instance_id(
        "project-1234567890abcdef1234567890abcdee"
    )


def test_accepted_literature_search_checksums_are_frozen() -> None:
    assert literature_search_contract_checksum() == (
        "sha256:efd338d84b33665da25118c7dce6927f62b231ff3bc73527f4132c7bcb410e7f"
    )
    assert literature_search_capsule_definition_checksum() == (
        "sha256:0f827b56ed6c5ecf6634f5eee0171ead2b050910ed1c9223ad64c9d135267611"
    )
    assert LITERATURE_SEARCH_CAPSULE_ID == "capsule-0f827b56ed6c5ecf6634f5eee0171ead"


def test_contracts_require_timezone_aware_timestamps() -> None:
    from backend.project_workspaces import WorkflowDefinition, WorkflowDefinitionLifecycle

    with pytest.raises(ValueError, match="timezone-aware"):
        WorkflowDefinition(
            workflow_definition_id="literature-search-local-experimental",
            display_name="Literature Search",
            description="",
            lifecycle=WorkflowDefinitionLifecycle.AVAILABLE,
            allows_multiple_instances=True,
            created_at=datetime.now(),
            updated_at=datetime.now(timezone.utc),
        )
