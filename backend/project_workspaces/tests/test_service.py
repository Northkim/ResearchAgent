from types import SimpleNamespace

import pytest

from backend.project_workspaces.errors import WorkflowFoundationConflictError
from backend.project_workspaces.service import reconcile_legacy_workflow_foundation


class _RecordingFoundation:
    def add_definition(self, value):
        pass

    def add_definition_version(self, value):
        pass

    def add_capsule_version(self, value):
        pass

    def add_workflow_instance(self, value):
        raise AssertionError("unsupported project must fail before instance creation")


def test_unsupported_legacy_workflow_fails_closed() -> None:
    uow = SimpleNamespace(
        workflow_foundation=_RecordingFoundation(),
        local_projects=SimpleNamespace(
            list_all=lambda: (
                SimpleNamespace(selected_workflow="UNSUPPORTED"),
            )
        ),
    )
    with pytest.raises(WorkflowFoundationConflictError, match="unsupported"):
        reconcile_legacy_workflow_foundation(uow)
