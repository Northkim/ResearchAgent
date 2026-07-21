"""Persistence boundary for durable human approval requests."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.domain.enums import ApprovalRequestStatus
from backend.domain.models import ApprovalRequest


class ApprovalRepository(ABC):
    @abstractmethod
    def save(
        self,
        approval: ApprovalRequest,
        *,
        expected_version: int | None,
    ) -> int:
        """Stage a detached insert or optimistic update and return its next version."""

    @abstractmethod
    def get(self, approval_id: str) -> ApprovalRequest | None:
        """Return a detached approval aggregate by identity."""

    @abstractmethod
    def get_version(self, approval_id: str) -> int | None:
        """Return the independent persistence concurrency version."""

    @abstractmethod
    def get_by_fingerprint(
        self,
        project_id: str,
        workflow_run_id: str,
        request_fingerprint: str,
    ) -> ApprovalRequest | None:
        """Resolve an idempotent logical approval request."""

    @abstractmethod
    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ApprovalRequest, ...]:
        """List all requests deterministically for one project-scoped run."""

    @abstractmethod
    def list_pending_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ApprovalRequest, ...]:
        """List unresolved requests used during restart recovery."""

    @abstractmethod
    def list_requests(
        self,
        *,
        status: ApprovalRequestStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[ApprovalRequest, ...]:
        """Return a deterministic newest-first page for product queries."""

    @abstractmethod
    def count_requests(
        self,
        *,
        status: ApprovalRequestStatus | None = None,
    ) -> int:
        """Count requests matching the same status filter as list_requests."""
