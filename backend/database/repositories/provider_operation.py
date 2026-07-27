"""SQLAlchemy ProviderOperationRepository adapter."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.orm import ProviderOperationORM
from backend.persistence.ports import (
    DuplicateEntityError,
    ProviderOperationRepository,
    StaleStateError,
)
from backend.persistence.models._immutability import thaw_json
from backend.research.contracts import (
    ProviderCategory,
    ProviderFailureCategory,
    ProviderOperation,
    ProviderOperationKind,
    ProviderOperationStatus,
    ProviderReservation,
    ProviderUsage,
    SettlementState,
)

from ._helpers import pending_by_id, pending_instances


class SQLAlchemyProviderOperationRepository(ProviderOperationRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(
        self,
        operation: ProviderOperation,
        *,
        expected_version: int | None,
    ) -> int:
        row = pending_by_id(self.session, ProviderOperationORM, operation.id)
        if row is None:
            row = self.session.get(ProviderOperationORM, operation.id)
        if expected_version is None:
            if row is not None:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} already exists at persistence "
                    f"version {row.persistence_version}"
                )
            owner = self.get_by_idempotency_key(
                operation.project_id,
                operation.idempotency_key,
            )
            if owner is not None and owner.id != operation.id:
                raise DuplicateEntityError(
                    "Provider operation idempotency key is already owned by "
                    f"ProviderOperation {owner.id}"
                )
            next_version = 1
            row = ProviderOperationORM(id=operation.id)
            self._apply(row, operation, next_version)
            self.session.add(row)
        else:
            if row is None:
                raise StaleStateError(f"ProviderOperation {operation.id} does not exist")
            if row.persistence_version != expected_version:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} expected persistence version "
                    f"{expected_version}; found {row.persistence_version}"
                )
            current = self._to_contract(row)
            if operation.row_version != current.row_version + 1:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} domain row version must advance "
                    f"from {current.row_version} to {current.row_version + 1}"
                )
            if (
                current.project_id != operation.project_id
                or current.workflow_run_id != operation.workflow_run_id
                or current.logical_step_id != operation.logical_step_id
                or current.step_run_id != operation.step_run_id
                or current.provider_category is not operation.provider_category
                or current.operation_kind is not operation.operation_kind
                or current.provider_identity != operation.provider_identity
                or current.adapter_version != operation.adapter_version
                or current.model_or_endpoint != operation.model_or_endpoint
                or current.idempotency_key != operation.idempotency_key
                or current.request_fingerprint != operation.request_fingerprint
                or current.reservation != operation.reservation
                or current.is_live_provider is not operation.is_live_provider
                or current.created_at != operation.created_at
            ):
                raise DuplicateEntityError(
                    "ProviderOperation immutable request identity cannot change"
                )
            next_version = expected_version + 1
            self._apply(row, operation, next_version)
        return next_version

    def get(self, operation_id: str) -> ProviderOperation | None:
        row = pending_by_id(self.session, ProviderOperationORM, operation_id)
        if row is None:
            row = self.session.get(ProviderOperationORM, operation_id)
        return self._to_contract(row) if row is not None else None

    def get_version(self, operation_id: str) -> int | None:
        row = pending_by_id(self.session, ProviderOperationORM, operation_id)
        if row is None:
            row = self.session.get(ProviderOperationORM, operation_id)
        return row.persistence_version if row is not None else None

    def get_by_idempotency_key(
        self,
        project_id: str,
        idempotency_key: str,
    ) -> ProviderOperation | None:
        pending = sorted(
            (
                row
                for row in pending_instances(self.session, ProviderOperationORM)
                if row.project_id == project_id
                and row.idempotency_key == idempotency_key
            ),
            key=lambda item: item.id,
        )
        if pending:
            return self._to_contract(pending[0])
        row = self.session.scalar(
            select(ProviderOperationORM)
            .where(
                ProviderOperationORM.project_id == project_id,
                ProviderOperationORM.idempotency_key == idempotency_key,
            )
            .order_by(ProviderOperationORM.id)
            .limit(1)
        )
        return self._to_contract(row) if row is not None else None

    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ProviderOperation, ...]:
        rows = list(
            self.session.scalars(
                select(ProviderOperationORM)
                .where(
                    ProviderOperationORM.project_id == project_id,
                    ProviderOperationORM.workflow_run_id == workflow_run_id,
                )
                .order_by(ProviderOperationORM.created_at, ProviderOperationORM.id)
            )
        )
        rows.extend(
            row
            for row in pending_instances(self.session, ProviderOperationORM)
            if row.project_id == project_id
            and row.workflow_run_id == workflow_run_id
            and row not in rows
        )
        rows.sort(key=lambda item: (item.created_at, item.id))
        return tuple(self._to_contract(row) for row in rows)

    def list_unsettled(
        self,
        *,
        project_id: str | None = None,
    ) -> tuple[ProviderOperation, ...]:
        statement = select(ProviderOperationORM).where(
            ProviderOperationORM.settlement_state == SettlementState.UNSETTLED.value
        )
        if project_id is not None:
            statement = statement.where(ProviderOperationORM.project_id == project_id)
        rows = list(
            self.session.scalars(
                statement.order_by(
                    ProviderOperationORM.updated_at,
                    ProviderOperationORM.id,
                )
            )
        )
        rows.extend(
            row
            for row in pending_instances(self.session, ProviderOperationORM)
            if row.settlement_state == SettlementState.UNSETTLED.value
            and (project_id is None or row.project_id == project_id)
            and row not in rows
        )
        rows.sort(key=lambda item: (item.updated_at, item.id))
        return tuple(self._to_contract(row) for row in rows)

    @staticmethod
    def _apply(
        row: ProviderOperationORM,
        operation: ProviderOperation,
        persistence_version: int,
    ) -> None:
        row.project_id = operation.project_id
        row.workflow_run_id = operation.workflow_run_id
        row.logical_step_id = operation.logical_step_id
        row.step_run_id = operation.step_run_id
        row.provider_category = operation.provider_category.value
        row.operation_kind = operation.operation_kind.value
        row.provider_identity = operation.provider_identity
        row.adapter_version = operation.adapter_version
        row.model_or_endpoint = operation.model_or_endpoint
        row.idempotency_key = operation.idempotency_key
        row.request_fingerprint = operation.request_fingerprint
        row.reserved_request_count = operation.reservation.request_count
        row.reserved_input_tokens = operation.reservation.input_tokens
        row.reserved_output_tokens = operation.reservation.output_tokens
        row.reserved_cost_minor_units = operation.reservation.cost_minor_units
        row.cost_currency = operation.reservation.cost_currency
        row.is_live_provider = operation.is_live_provider
        row.status = operation.status.value
        row.settlement_state = operation.settlement_state.value
        row.actual_usage_json = (
            operation.actual_usage.to_dict() if operation.actual_usage is not None else None
        )
        row.failure_category = (
            operation.failure_category.value
            if operation.failure_category is not None
            else None
        )
        row.retry_count = operation.retry_count
        row.diagnostic_metadata_json = thaw_json(operation.diagnostic_metadata)
        row.created_at = operation.created_at
        row.updated_at = operation.updated_at
        row.started_at = operation.started_at
        row.finished_at = operation.finished_at
        row.row_version = operation.row_version
        row.persistence_version = persistence_version

    @staticmethod
    def _to_contract(row: ProviderOperationORM) -> ProviderOperation:
        usage_data = row.actual_usage_json
        usage = None
        if usage_data is not None:
            usage = ProviderUsage(
                provider=usage_data["provider"],
                model_or_endpoint=usage_data["model_or_endpoint"],
                operation_kind=ProviderOperationKind(usage_data["operation_kind"]),
                request_count=usage_data["request_count"],
                input_tokens=usage_data["input_tokens"],
                output_tokens=usage_data["output_tokens"],
                estimated_cost_minor_units=usage_data["estimated_cost_minor_units"],
                cost_currency=usage_data["cost_currency"],
                latency_ms=usage_data["latency_ms"],
                retry_count=usage_data["retry_count"],
                failure_category=(
                    ProviderFailureCategory(usage_data["failure_category"])
                    if usage_data["failure_category"] is not None
                    else None
                ),
                provider_request_ids=tuple(usage_data["provider_request_ids"]),
                schema_version=usage_data["schema_version"],
            )
        return ProviderOperation(
            id=row.id,
            project_id=row.project_id,
            workflow_run_id=row.workflow_run_id,
            logical_step_id=row.logical_step_id,
            step_run_id=row.step_run_id,
            provider_category=ProviderCategory(row.provider_category),
            operation_kind=ProviderOperationKind(row.operation_kind),
            provider_identity=row.provider_identity,
            adapter_version=row.adapter_version,
            model_or_endpoint=row.model_or_endpoint,
            idempotency_key=row.idempotency_key,
            request_fingerprint=row.request_fingerprint,
            reservation=ProviderReservation(
                request_count=row.reserved_request_count,
                input_tokens=row.reserved_input_tokens,
                output_tokens=row.reserved_output_tokens,
                cost_minor_units=row.reserved_cost_minor_units,
                cost_currency=row.cost_currency,
            ),
            is_live_provider=row.is_live_provider,
            status=ProviderOperationStatus(row.status),
            settlement_state=SettlementState(row.settlement_state),
            actual_usage=usage,
            failure_category=(
                ProviderFailureCategory(row.failure_category)
                if row.failure_category is not None
                else None
            ),
            retry_count=row.retry_count,
            diagnostic_metadata=row.diagnostic_metadata_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            row_version=row.row_version,
        )
