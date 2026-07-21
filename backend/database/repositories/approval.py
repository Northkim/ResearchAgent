"""SQLAlchemy ApprovalRepository adapter."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database.orm import ApprovalRequestORM
from backend.domain.enums import ApprovalRequestStatus
from backend.domain.models import ApprovalRequest
from backend.persistence.models import ApprovalRecord
from backend.persistence.models._immutability import thaw_json
from backend.persistence.ports import ApprovalRepository, StaleStateError

from ._helpers import pending_by_id, pending_instances


class SQLAlchemyApprovalRepository(ApprovalRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(
        self,
        approval: ApprovalRequest,
        *,
        expected_version: int | None,
    ) -> int:
        row = pending_by_id(self.session, ApprovalRequestORM, approval.id)
        if row is None:
            row = self.session.get(ApprovalRequestORM, approval.id)
        if expected_version is None:
            if row is not None:
                raise StaleStateError(
                    f"ApprovalRequest {approval.id} already exists at persistence "
                    f"version {row.persistence_version}"
                )
            next_version = 1
            row = ApprovalRequestORM(id=approval.id)
            self._apply(row, approval, next_version)
            self.session.add(row)
        else:
            if row is None:
                raise StaleStateError(
                    f"ApprovalRequest {approval.id} does not exist"
                )
            if row.persistence_version != expected_version:
                raise StaleStateError(
                    f"ApprovalRequest {approval.id} expected persistence version "
                    f"{expected_version}; found {row.persistence_version}"
                )
            next_version = expected_version + 1
            self._apply(row, approval, next_version)
        return next_version

    def get(self, approval_id: str) -> ApprovalRequest | None:
        row = pending_by_id(self.session, ApprovalRequestORM, approval_id)
        if row is None:
            row = self.session.get(ApprovalRequestORM, approval_id)
        return self._to_domain(row) if row is not None else None

    def get_version(self, approval_id: str) -> int | None:
        row = pending_by_id(self.session, ApprovalRequestORM, approval_id)
        if row is None:
            row = self.session.get(ApprovalRequestORM, approval_id)
        return row.persistence_version if row is not None else None

    def get_by_fingerprint(
        self,
        project_id: str,
        workflow_run_id: str,
        request_fingerprint: str,
    ) -> ApprovalRequest | None:
        matches = [
            row
            for row in pending_instances(self.session, ApprovalRequestORM)
            if row.project_id == project_id
            and row.workflow_run_id == workflow_run_id
            and row.request_fingerprint == request_fingerprint
        ]
        row = self.session.scalar(
            select(ApprovalRequestORM)
            .where(
                ApprovalRequestORM.project_id == project_id,
                ApprovalRequestORM.workflow_run_id == workflow_run_id,
                ApprovalRequestORM.request_fingerprint == request_fingerprint,
            )
            .order_by(
                ApprovalRequestORM.requested_at.desc(),
                ApprovalRequestORM.id.desc(),
            )
            .limit(1)
        )
        if row is not None:
            matches.append(row)
        if not matches:
            return None
        latest = max(matches, key=lambda item: (item.requested_at, item.id))
        return self._to_domain(latest)

    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ApprovalRequest, ...]:
        rows = list(
            self.session.scalars(
                select(ApprovalRequestORM)
                .where(
                    ApprovalRequestORM.project_id == project_id,
                    ApprovalRequestORM.workflow_run_id == workflow_run_id,
                )
                .order_by(
                    ApprovalRequestORM.requested_at,
                    ApprovalRequestORM.id,
                )
            )
        )
        rows.extend(
            row
            for row in pending_instances(self.session, ApprovalRequestORM)
            if row.project_id == project_id
            and row.workflow_run_id == workflow_run_id
            and row not in rows
        )
        rows.sort(key=lambda row: (row.requested_at, row.id))
        return tuple(self._to_domain(row) for row in rows)

    def list_pending_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ApprovalRequest, ...]:
        return tuple(
            approval
            for approval in self.list_for_run(project_id, workflow_run_id)
            if approval.status is ApprovalRequestStatus.PENDING
        )

    def list_requests(
        self,
        *,
        status: ApprovalRequestStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[ApprovalRequest, ...]:
        statement = select(ApprovalRequestORM)
        if status is not None:
            statement = statement.where(ApprovalRequestORM.status == status.value)
        rows = self.session.scalars(
            statement.order_by(
                ApprovalRequestORM.requested_at.desc(),
                ApprovalRequestORM.id.desc(),
            ).offset(offset).limit(limit)
        )
        return tuple(self._to_domain(row) for row in rows)

    def count_requests(
        self,
        *,
        status: ApprovalRequestStatus | None = None,
    ) -> int:
        statement = select(func.count()).select_from(ApprovalRequestORM)
        if status is not None:
            statement = statement.where(ApprovalRequestORM.status == status.value)
        return int(self.session.scalar(statement) or 0)

    @staticmethod
    def _apply(
        row: ApprovalRequestORM,
        approval: ApprovalRequest,
        persistence_version: int,
    ) -> None:
        row.project_id = approval.project_id
        row.workflow_run_id = approval.workflow_run_id
        row.step_run_id = approval.step_run_id
        row.policy_key = approval.policy_key
        row.request_fingerprint = approval.request_fingerprint
        row.prompt = approval.prompt
        row.requested_action_json = thaw_json(approval.requested_action)
        row.requested_by = approval.requested_by
        row.permitted_approver_role = approval.permitted_approver_role
        row.requested_at = approval.requested_at
        row.expires_at = approval.expires_at
        row.status = approval.status.value
        row.resolved_by = approval.resolved_by
        row.resolved_at = approval.resolved_at
        row.decision_reason = approval.decision_reason
        row.decision_idempotency_key = approval.decision_idempotency_key
        row.decision_metadata_json = thaw_json(approval.decision_metadata)
        row.row_version = approval.row_version
        row.persistence_version = persistence_version

    @staticmethod
    def _to_domain(row: ApprovalRequestORM) -> ApprovalRequest:
        return ApprovalRecord(
            id=row.id,
            project_id=row.project_id,
            workflow_run_id=row.workflow_run_id,
            step_run_id=row.step_run_id,
            policy_key=row.policy_key,
            request_fingerprint=row.request_fingerprint,
            prompt=row.prompt,
            requested_action=row.requested_action_json,
            requested_by=row.requested_by,
            permitted_approver_role=row.permitted_approver_role,
            requested_at=row.requested_at,
            expires_at=row.expires_at,
            status=ApprovalRequestStatus(row.status),
            resolved_by=row.resolved_by,
            resolved_at=row.resolved_at,
            decision_reason=row.decision_reason,
            decision_idempotency_key=row.decision_idempotency_key,
            decision_metadata=row.decision_metadata_json,
            row_version=row.row_version,
            persistence_version=row.persistence_version,
        ).to_approval()
