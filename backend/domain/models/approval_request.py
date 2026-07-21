"""Durable human-in-the-loop approval aggregate."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..enums import ApprovalRequestStatus
from ..exceptions import DomainValidationError, InvalidStateTransition
from ._utils import (
    freeze_value,
    require_aware,
    require_non_empty,
    thaw_value,
    utc_now,
)


def _freeze_json_object(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    frozen = freeze_value(value)
    try:
        json.dumps(thaw_value(frozen), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise DomainValidationError(
            f"{field_name} must contain only JSON-compatible values"
        ) from error
    return frozen


@dataclass(slots=True)
class ApprovalRequest:
    """A fingerprinted request that can be resolved exactly once."""

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
    requested_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None
    status: ApprovalRequestStatus = ApprovalRequestStatus.PENDING
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    decision_reason: str | None = None
    decision_idempotency_key: str | None = None
    decision_metadata: Mapping[str, Any] = field(default_factory=dict)
    row_version: int = 0

    def __post_init__(self) -> None:
        for value, name in (
            (self.id, "ApprovalRequest.id"),
            (self.project_id, "ApprovalRequest.project_id"),
            (self.workflow_run_id, "ApprovalRequest.workflow_run_id"),
            (self.step_run_id, "ApprovalRequest.step_run_id"),
            (self.policy_key, "ApprovalRequest.policy_key"),
            (self.request_fingerprint, "ApprovalRequest.request_fingerprint"),
            (self.prompt, "ApprovalRequest.prompt"),
            (self.requested_by, "ApprovalRequest.requested_by"),
            (
                self.permitted_approver_role,
                "ApprovalRequest.permitted_approver_role",
            ),
        ):
            require_non_empty(value, name)
        require_aware(self.requested_at, "ApprovalRequest.requested_at")
        if self.expires_at is not None:
            require_aware(self.expires_at, "ApprovalRequest.expires_at")
            if self.expires_at <= self.requested_at:
                raise DomainValidationError(
                    "ApprovalRequest.expires_at must be after requested_at"
                )
        if self.row_version < 0:
            raise DomainValidationError("ApprovalRequest.row_version cannot be negative")
        self.requested_action = _freeze_json_object(
            self.requested_action,
            "ApprovalRequest.requested_action",
        )
        self.decision_metadata = _freeze_json_object(
            self.decision_metadata,
            "ApprovalRequest.decision_metadata",
        )
        self._validate_resolution_fields()

    def approve(
        self,
        *,
        resolved_by: str,
        decision_idempotency_key: str,
        current_fingerprint: str,
        at: datetime | None = None,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Approve the exact action represented by the stored fingerprint."""

        self._resolve(
            ApprovalRequestStatus.APPROVED,
            resolved_by=resolved_by,
            decision_idempotency_key=decision_idempotency_key,
            current_fingerprint=current_fingerprint,
            at=at,
            reason=reason,
            metadata=metadata,
        )

    def reject(
        self,
        *,
        resolved_by: str,
        decision_idempotency_key: str,
        at: datetime | None = None,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Reject the request and preserve resolver/audit metadata."""

        self._resolve(
            ApprovalRequestStatus.REJECTED,
            resolved_by=resolved_by,
            decision_idempotency_key=decision_idempotency_key,
            current_fingerprint=None,
            at=at,
            reason=reason,
            metadata=metadata,
        )

    def expire(
        self,
        *,
        at: datetime | None = None,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Expire a pending request once its configured deadline is reached."""

        timestamp = at or utc_now()
        require_aware(timestamp, "ApprovalRequest expiry timestamp")
        if self.expires_at is None:
            raise DomainValidationError(
                "ApprovalRequest cannot expire without expires_at"
            )
        if timestamp < self.expires_at:
            raise DomainValidationError(
                "ApprovalRequest cannot expire before expires_at"
            )
        self._ensure_pending(ApprovalRequestStatus.EXPIRED)
        self.status = ApprovalRequestStatus.EXPIRED
        self.resolved_at = timestamp
        self.decision_reason = reason
        self.decision_metadata = _freeze_json_object(
            metadata or {},
            "ApprovalRequest.decision_metadata",
        )
        self.row_version += 1

    def _resolve(
        self,
        target: ApprovalRequestStatus,
        *,
        resolved_by: str,
        decision_idempotency_key: str,
        current_fingerprint: str | None,
        at: datetime | None,
        reason: str | None,
        metadata: Mapping[str, Any] | None,
    ) -> None:
        self._ensure_pending(target)
        require_non_empty(resolved_by, "ApprovalRequest.resolved_by")
        require_non_empty(
            decision_idempotency_key,
            "ApprovalRequest.decision_idempotency_key",
        )
        timestamp = at or utc_now()
        require_aware(timestamp, "ApprovalRequest decision timestamp")
        if self.expires_at is not None and timestamp >= self.expires_at:
            raise DomainValidationError(
                "Expired ApprovalRequest must be marked EXPIRED before resolution"
            )
        if target is ApprovalRequestStatus.APPROVED:
            if current_fingerprint != self.request_fingerprint:
                raise DomainValidationError(
                    "ApprovalRequest fingerprint no longer matches the planned action"
                )
        self.status = target
        self.resolved_by = resolved_by
        self.resolved_at = timestamp
        self.decision_reason = reason
        self.decision_idempotency_key = decision_idempotency_key
        self.decision_metadata = _freeze_json_object(
            metadata or {},
            "ApprovalRequest.decision_metadata",
        )
        self.row_version += 1

    def _ensure_pending(self, target: ApprovalRequestStatus) -> None:
        if self.status is not ApprovalRequestStatus.PENDING:
            raise InvalidStateTransition(
                "ApprovalRequest",
                self.id,
                self.status.value,
                target.value,
            )

    def _validate_resolution_fields(self) -> None:
        if self.status is ApprovalRequestStatus.PENDING:
            if any(
                value is not None
                for value in (
                    self.resolved_by,
                    self.resolved_at,
                    self.decision_reason,
                    self.decision_idempotency_key,
                )
            ) or self.decision_metadata:
                raise DomainValidationError(
                    "Pending ApprovalRequest cannot contain decision metadata"
                )
            return

        if self.resolved_at is None:
            raise DomainValidationError(
                "Resolved ApprovalRequest requires resolved_at"
            )
        require_aware(self.resolved_at, "ApprovalRequest.resolved_at")
        if self.status in {
            ApprovalRequestStatus.APPROVED,
            ApprovalRequestStatus.REJECTED,
        }:
            if self.resolved_by is None or self.decision_idempotency_key is None:
                raise DomainValidationError(
                    "Approved or rejected request requires resolver and idempotency key"
                )
            require_non_empty(self.resolved_by, "ApprovalRequest.resolved_by")
            require_non_empty(
                self.decision_idempotency_key,
                "ApprovalRequest.decision_idempotency_key",
            )
        elif self.status is ApprovalRequestStatus.EXPIRED and any(
            value is not None
            for value in (self.resolved_by, self.decision_idempotency_key)
        ):
            raise DomainValidationError(
                "Expired ApprovalRequest cannot contain a human resolver"
            )
