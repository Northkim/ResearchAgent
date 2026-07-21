"""Detached immutable persistence representation of an approval aggregate."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.domain.enums import ApprovalRequestStatus
from backend.domain.models import ApprovalRequest

from ._immutability import freeze_json, thaw_json


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    id: str
    project_id: str
    workflow_run_id: str
    step_run_id: str
    policy_key: str
    request_fingerprint: str
    prompt: str
    requested_action: Mapping[str, Any]
    requested_by: str
    permitted_approver_role: str
    requested_at: datetime
    expires_at: datetime | None
    status: ApprovalRequestStatus
    resolved_by: str | None
    resolved_at: datetime | None
    decision_reason: str | None
    decision_idempotency_key: str | None
    decision_metadata: Mapping[str, Any]
    row_version: int
    persistence_version: int

    def __post_init__(self) -> None:
        if self.persistence_version <= 0:
            raise ValueError("ApprovalRecord.persistence_version must be positive")
        object.__setattr__(
            self,
            "requested_action",
            freeze_json(self.requested_action, path="ApprovalRecord.requested_action"),
        )
        object.__setattr__(
            self,
            "decision_metadata",
            freeze_json(self.decision_metadata, path="ApprovalRecord.decision_metadata"),
        )

    @classmethod
    def from_approval(
        cls,
        approval: ApprovalRequest,
        *,
        persistence_version: int,
    ) -> ApprovalRecord:
        return cls(
            id=approval.id,
            project_id=approval.project_id,
            workflow_run_id=approval.workflow_run_id,
            step_run_id=approval.step_run_id,
            policy_key=approval.policy_key,
            request_fingerprint=approval.request_fingerprint,
            prompt=approval.prompt,
            requested_action=approval.requested_action,
            requested_by=approval.requested_by,
            permitted_approver_role=approval.permitted_approver_role,
            requested_at=approval.requested_at,
            expires_at=approval.expires_at,
            status=approval.status,
            resolved_by=approval.resolved_by,
            resolved_at=approval.resolved_at,
            decision_reason=approval.decision_reason,
            decision_idempotency_key=approval.decision_idempotency_key,
            decision_metadata=approval.decision_metadata,
            row_version=approval.row_version,
            persistence_version=persistence_version,
        )

    def to_approval(self) -> ApprovalRequest:
        return ApprovalRequest(
            id=self.id,
            project_id=self.project_id,
            workflow_run_id=self.workflow_run_id,
            step_run_id=self.step_run_id,
            policy_key=self.policy_key,
            request_fingerprint=self.request_fingerprint,
            prompt=self.prompt,
            requested_action=thaw_json(self.requested_action),
            requested_by=self.requested_by,
            permitted_approver_role=self.permitted_approver_role,
            requested_at=self.requested_at,
            expires_at=self.expires_at,
            status=self.status,
            resolved_by=self.resolved_by,
            resolved_at=self.resolved_at,
            decision_reason=self.decision_reason,
            decision_idempotency_key=self.decision_idempotency_key,
            decision_metadata=thaw_json(self.decision_metadata),
            row_version=self.row_version,
        )
