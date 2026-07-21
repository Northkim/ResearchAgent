"""Execution dispatcher contract tests."""

from __future__ import annotations

import asyncio

from backend.application.execution import ExecutionRequest, SyncExecutionDispatcher
from backend.workflow_engine.models import ApprovalOutcome


def test_sync_dispatcher_executes_runtime() -> None:
    calls: list[tuple[str, ApprovalOutcome | None]] = []
    result = object()

    class StubRuntime:
        async def run(
            self,
            workflow_run_id: str,
            *,
            approval_outcome: ApprovalOutcome | None = None,
        ):
            calls.append((workflow_run_id, approval_outcome))
            return result

    dispatcher = SyncExecutionDispatcher(StubRuntime())  # type: ignore[arg-type]
    request = ExecutionRequest(
        workflow_run_id="run-1",
        approval_outcome=ApprovalOutcome.APPROVED,
    )

    dispatched = asyncio.run(dispatcher.submit(request))

    assert dispatched is result
    assert calls == [("run-1", ApprovalOutcome.APPROVED)]
