"""Approval HTTP DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from backend.application.commands import ApprovalDecision, ApprovalDecisionCommand
from backend.application.views import ApprovalDecisionView, ApprovalPageView, ApprovalView
from backend.domain.enums import ApprovalRequestStatus

from .common import StrictDTO
from .runs import WorkflowRunResponse


class ApprovalDecisionRequest(StrictDTO):
    resolved_by: str = Field(min_length=1)
    decision_idempotency_key: str = Field(min_length=1)
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApproveRequest(ApprovalDecisionRequest):
    current_fingerprint: str = Field(min_length=1)

    def to_command(self, approval_id: str) -> ApprovalDecisionCommand:
        return ApprovalDecisionCommand(
            approval_id=approval_id,
            decision=ApprovalDecision.APPROVE,
            resolved_by=self.resolved_by,
            decision_idempotency_key=self.decision_idempotency_key,
            current_fingerprint=self.current_fingerprint,
            reason=self.reason,
            metadata=self.metadata,
        )


class RejectRequest(ApprovalDecisionRequest):
    def to_command(self, approval_id: str) -> ApprovalDecisionCommand:
        return ApprovalDecisionCommand(
            approval_id=approval_id,
            decision=ApprovalDecision.REJECT,
            resolved_by=self.resolved_by,
            decision_idempotency_key=self.decision_idempotency_key,
            reason=self.reason,
            metadata=self.metadata,
        )


class ApprovalResponse(StrictDTO):
    id: str
    project_id: str
    workflow_run_id: str
    step_run_id: str
    policy_key: str
    request_fingerprint: str
    prompt: str
    requested_action: dict[str, Any]
    requested_by: str
    permitted_approver_role: str
    requested_at: datetime
    expires_at: datetime | None
    status: ApprovalRequestStatus
    resolved_by: str | None
    resolved_at: datetime | None
    decision_reason: str | None

    @classmethod
    def from_view(cls, view: ApprovalView) -> ApprovalResponse:
        return cls(**{field: getattr(view, field) for field in cls.model_fields})


class ApprovalPageResponse(StrictDTO):
    approvals: list[ApprovalResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_view(cls, view: ApprovalPageView) -> ApprovalPageResponse:
        return cls(
            approvals=[ApprovalResponse.from_view(item) for item in view.approvals],
            total=view.total,
            offset=view.offset,
            limit=view.limit,
        )


class ApprovalDecisionResponse(StrictDTO):
    approval: ApprovalResponse
    workflow_run: WorkflowRunResponse

    @classmethod
    def from_view(cls, view: ApprovalDecisionView) -> ApprovalDecisionResponse:
        return cls(
            approval=ApprovalResponse.from_view(view.approval),
            workflow_run=WorkflowRunResponse.from_view(view.workflow_run),
        )
