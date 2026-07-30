"""Framework- and queue-neutral execution submission contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any

from backend.agent_runtime import AgentRuntime, RuntimeResult
from backend.workflow_engine.models import ApprovalOutcome


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionRequest:
    workflow_run_id: str
    approval_outcome: ApprovalOutcome | None = None
    approval_outputs: Mapping[str, Any] | None = None


class ExecutionDispatcher(ABC):
    """Submission boundary replaceable by a future durable worker adapter."""

    @abstractmethod
    async def submit(self, request: ExecutionRequest) -> RuntimeResult:
        """Submit one execution request and return its current durable result."""


class SyncExecutionDispatcher(ExecutionDispatcher):
    """V1 inline adapter that invokes AgentRuntime in the caller process."""

    def __init__(self, runtime: AgentRuntime) -> None:
        self.runtime = runtime

    async def submit(self, request: ExecutionRequest) -> RuntimeResult:
        arguments = {"approval_outcome": request.approval_outcome}
        if request.approval_outputs is not None:
            arguments["approval_outputs"] = request.approval_outputs
        return await self.runtime.run(request.workflow_run_id, **arguments)
