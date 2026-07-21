"""Approval lifecycle and restart-recovery persistence tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.domain.enums import ApprovalRequestStatus
from backend.domain.exceptions import DomainValidationError, InvalidStateTransition
from backend.domain.models import ApprovalRequest
from backend.execution_events import EventPayload, ExecutionEvent, ExecutionEventType
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork


REQUESTED_AT = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
EXPIRES_AT = REQUESTED_AT + timedelta(hours=1)


def _approval(*, approval_id: str = "approval-1") -> ApprovalRequest:
    return ApprovalRequest(
        id=approval_id,
        project_id="project-approval",
        workflow_run_id="run-approval",
        step_run_id="step-run-approval",
        policy_key="project_reviewer",
        request_fingerprint="sha256:planned-action",
        prompt="Approve publication of the research report?",
        requested_action={
            "capability": "publish_report",
            "target": "project-library",
        },
        requested_by="agent-session-primary",
        permitted_approver_role="reviewer",
        requested_at=REQUESTED_AT,
        expires_at=EXPIRES_AT,
    )


def test_approval_lifecycle_supports_approve_reject_and_expire() -> None:
    approved = _approval(approval_id="approval-approved")
    approved.approve(
        resolved_by="reviewer-1",
        decision_idempotency_key="decision-approved",
        current_fingerprint=approved.request_fingerprint,
        at=REQUESTED_AT + timedelta(minutes=10),
        reason="Sources verified",
        metadata={"role": "reviewer"},
    )
    assert approved.status is ApprovalRequestStatus.APPROVED
    assert approved.row_version == 1
    assert approved.resolved_by == "reviewer-1"
    assert approved.decision_metadata["role"] == "reviewer"
    with pytest.raises(InvalidStateTransition):
        approved.reject(
            resolved_by="reviewer-2",
            decision_idempotency_key="second-decision",
        )

    rejected = _approval(approval_id="approval-rejected")
    rejected.reject(
        resolved_by="reviewer-2",
        decision_idempotency_key="decision-rejected",
        at=REQUESTED_AT + timedelta(minutes=20),
        reason="Insufficient evidence",
    )
    assert rejected.status is ApprovalRequestStatus.REJECTED

    expired = _approval(approval_id="approval-expired")
    with pytest.raises(DomainValidationError):
        expired.expire(at=EXPIRES_AT - timedelta(seconds=1))
    expired.expire(at=EXPIRES_AT, reason="Approval deadline elapsed")
    assert expired.status is ApprovalRequestStatus.EXPIRED
    assert expired.resolved_by is None

    fingerprint_changed = _approval(approval_id="approval-stale-action")
    with pytest.raises(DomainValidationError):
        fingerprint_changed.approve(
            resolved_by="reviewer-1",
            decision_idempotency_key="decision-stale-action",
            current_fingerprint="sha256:changed-action",
            at=REQUESTED_AT + timedelta(minutes=5),
        )


def test_pending_approval_is_recovered_and_resolved_after_restart() -> None:
    database = InMemoryDatabase()
    approval = _approval()
    approval_requested = ExecutionEvent(
        id="event-approval-requested",
        project_id=approval.project_id,
        workflow_run_id=approval.workflow_run_id,
        sequence=1,
        event_type=ExecutionEventType.APPROVAL_REQUESTED,
        payload=EventPayload(
            data={
                "approval_request_id": approval.id,
                "request_fingerprint": approval.request_fingerprint,
            }
        ),
        request_id="request-approval",
        occurred_at=REQUESTED_AT,
        agent_session_id="agent-session-primary",
        step_run_id=approval.step_run_id,
    )

    writer = InMemoryUnitOfWork(database)
    assert writer.approvals.save(approval, expected_version=None) == 1
    writer.events.append(approval_requested, expected_sequence=0)
    writer.commit()

    restarted = InMemoryUnitOfWork(database)
    pending = restarted.approvals.list_pending_for_run(
        approval.project_id,
        approval.workflow_run_id,
    )
    assert len(pending) == 1
    recovered = pending[0]
    assert recovered is not approval
    assert recovered.status is ApprovalRequestStatus.PENDING
    assert restarted.approvals.get_version(recovered.id) == 1
    assert restarted.events.replay(
        approval.project_id,
        approval.workflow_run_id,
    ) == (approval_requested,)

    recovered.approve(
        resolved_by="reviewer-1",
        decision_idempotency_key="decision-after-restart",
        current_fingerprint=recovered.request_fingerprint,
        at=REQUESTED_AT + timedelta(minutes=30),
        reason="Approved after worker restart",
        metadata={"source": "approval-api"},
    )
    assert restarted.approvals.save(recovered, expected_version=1) == 2
    restarted.commit()

    observer = InMemoryUnitOfWork(database)
    resolved = observer.approvals.get(approval.id)
    assert resolved is not None
    assert resolved.status is ApprovalRequestStatus.APPROVED
    assert resolved.resolved_by == "reviewer-1"
    assert resolved.decision_idempotency_key == "decision-after-restart"
    assert resolved.decision_metadata["source"] == "approval-api"
    assert observer.approvals.list_pending_for_run(
        approval.project_id,
        approval.workflow_run_id,
    ) == ()
    assert observer.approvals.get_version(approval.id) == 2
