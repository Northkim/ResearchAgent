"""Persistence port for auditable provider calls and budget reservations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.research.contracts import ProviderOperation


class ProviderOperationRepository(ABC):
    @abstractmethod
    def save(
        self,
        operation: ProviderOperation,
        *,
        expected_version: int | None,
    ) -> int:
        """Stage an insert/update and return the next persistence version."""

    @abstractmethod
    def get(self, operation_id: str) -> ProviderOperation | None: ...

    @abstractmethod
    def get_version(self, operation_id: str) -> int | None: ...

    @abstractmethod
    def get_by_idempotency_key(
        self,
        project_id: str,
        idempotency_key: str,
    ) -> ProviderOperation | None: ...

    @abstractmethod
    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ProviderOperation, ...]: ...

    @abstractmethod
    def list_unsettled(
        self,
        *,
        project_id: str | None = None,
    ) -> tuple[ProviderOperation, ...]: ...

