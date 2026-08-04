"""PostgreSQL repository and Unit of Work for the independent Proxy domain."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.orm import ProxyCapabilityTokenORM, ProxyOperationORM

from .contracts import (
    CloudProxyRequestEnvelope,
    ProxyAuthorizationScope,
    ProxyCapabilityToken,
    ProxyOperation,
    ProxyOperationStatus,
    ProxyUsage,
    RequestRetentionMode,
    format_timestamp,
    operation_from_dict,
    parse_timestamp,
)


class SQLProxyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_token(self, token: ProxyCapabilityToken) -> None:
        self.session.add(self._token_row(token))

    def find_token_by_digest(self, digest: str) -> ProxyCapabilityToken | None:
        row = self.session.scalar(
            select(ProxyCapabilityTokenORM).where(
                ProxyCapabilityTokenORM.token_digest_sha256 == digest
            )
        )
        return self._token(row) if row is not None else None

    def get_token(self, token_id: str, *, for_update: bool = False) -> ProxyCapabilityToken | None:
        statement = select(ProxyCapabilityTokenORM).where(
            ProxyCapabilityTokenORM.token_id == token_id
        )
        if for_update:
            statement = statement.with_for_update()
        row = self.session.scalar(statement)
        return self._token(row) if row is not None else None

    def save_token(self, token: ProxyCapabilityToken) -> None:
        row = self.session.get(ProxyCapabilityTokenORM, token.scope.token_id)
        if row is None:
            raise ValueError("Proxy token not found")
        row.admitted_operations = token.admitted_operations
        row.used_provider_calls = token.used_provider_calls
        row.reserved_provider_cost_microusd = token.reserved_provider_cost_microusd
        row.reported_provider_cost_microusd = token.reported_provider_cost_microusd
        row.revoked = token.revoked
        row.revoked_at = _parse_optional(token.revoked_at)

    def get_operation(self, operation_id: str) -> ProxyOperation | None:
        row = self.session.get(ProxyOperationORM, operation_id)
        return self._operation(row) if row is not None else None

    def find_by_idempotency(self, token_id: str, idempotency_key: str) -> ProxyOperation | None:
        row = self.session.scalar(
            select(ProxyOperationORM).where(
                ProxyOperationORM.token_id == token_id,
                ProxyOperationORM.idempotency_key == idempotency_key,
            )
        )
        return self._operation(row) if row is not None else None

    def add_operation(self, operation: ProxyOperation) -> None:
        request = operation.request
        request_json = operation.retained_request_json or request.to_dict()
        usage = operation.usage
        self.session.add(
            ProxyOperationORM(
                operation_id=operation.operation_id,
                token_id=operation.token_id,
                proxy_contract_version=request.proxy_contract_version,
                authorization_scope_checksum=operation.authorization_scope_checksum,
                project_id=request.project_id,
                package_id=request.package_id,
                package_checksum=request.package_checksum,
                workflow_id=request.workflow_id,
                workflow_version=request.workflow_version,
                workflow_checksum=request.workflow_checksum,
                capability=request.capability,
                adapter_id=operation.adapter_id,
                idempotency_key=request.idempotency_key,
                request_content_checksum=request.request_content_checksum,
                request_json=request_json,
                request_retention_mode=request.retention_mode.value,
                query_checksum=request.query_checksum,
                query_utf8_bytes=request.query_utf8_bytes,
                query_characters=request.query_characters,
                status=operation.status.value,
                provider_data_json=operation.provider_data,
                provider_data_checksum=operation.provider_data_checksum,
                provider_data_size=operation.provider_data_size,
                response_content_checksum=operation.response_content_checksum,
                estimated_cost_minor_units=0,
                retry_count=0,
                provider_http_calls=usage.provider_http_calls if usage else 0,
                reserved_cost_microusd=usage.reserved_cost_microusd if usage else 0,
                reported_cost_microusd=usage.reported_cost_microusd if usage else 0,
                provider_response_checksum=operation.provider_response_checksum,
                provider_http_status=operation.provider_http_status,
                provider_adapter_version=operation.provider_adapter_version,
                provider_rate_limit_json=_rate_limit_json(usage),
                usage_json=usage.to_dict() if usage else None,
                error_code=operation.error_code,
                reconciliation_evidence=operation.reconciliation_evidence,
                created_at=parse_timestamp(operation.admitted_at, "admitted_at"),
                updated_at=parse_timestamp(operation.updated_at, "updated_at"),
                started_at=_parse_optional(operation.started_at),
                completed_at=_parse_optional(operation.completed_at),
            )
        )

    def save_operation(self, operation: ProxyOperation) -> None:
        row = self.session.get(ProxyOperationORM, operation.operation_id)
        if row is None:
            raise ValueError("Proxy operation not found")
        row.status = operation.status.value
        row.provider_data_json = operation.provider_data
        row.provider_data_checksum = operation.provider_data_checksum
        row.provider_data_size = operation.provider_data_size
        row.response_content_checksum = operation.response_content_checksum
        row.provider_response_checksum = operation.provider_response_checksum
        row.provider_http_status = operation.provider_http_status
        row.provider_adapter_version = operation.provider_adapter_version
        row.provider_http_calls = operation.usage.provider_http_calls if operation.usage else 0
        row.reserved_cost_microusd = operation.usage.reserved_cost_microusd if operation.usage else 0
        row.reported_cost_microusd = operation.usage.reported_cost_microusd if operation.usage else 0
        row.provider_rate_limit_json = _rate_limit_json(operation.usage)
        row.usage_json = operation.usage.to_dict() if operation.usage else None
        row.error_code = operation.error_code
        row.reconciliation_evidence = operation.reconciliation_evidence
        row.updated_at = parse_timestamp(operation.updated_at, "updated_at")
        row.started_at = _parse_optional(operation.started_at)
        row.completed_at = _parse_optional(operation.completed_at)

    def count_active(self, token_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(ProxyOperationORM).where(
                    ProxyOperationORM.token_id == token_id,
                    ProxyOperationORM.status.in_(("RECEIVED", "RUNNING")),
                )
            )
            or 0
        )

    def reconcile_running(self, evidence: str) -> int:
        rows = list(
            self.session.scalars(
                select(ProxyOperationORM)
                .where(ProxyOperationORM.status == ProxyOperationStatus.RUNNING.value)
                .with_for_update()
            )
        )
        now = format_timestamp(datetime.now(UTC))
        for row in rows:
            operation = replace(
                self._operation(row),
                status=ProxyOperationStatus.RECONCILIATION_REQUIRED,
                error_code="INTERRUPTED_OPERATION",
                reconciliation_evidence=evidence,
                updated_at=now,
                response_content_checksum=None,
            ).with_response_checksum()
            self.save_operation(operation)
        return len(rows)

    @staticmethod
    def _token_row(token: ProxyCapabilityToken) -> ProxyCapabilityTokenORM:
        scope = token.scope
        return ProxyCapabilityTokenORM(
            token_id=scope.token_id,
            token_digest_sha256=token.token_digest_sha256,
            tenant_id=scope.tenant_id,
            subject_id=scope.subject_id,
            project_id=scope.project_id,
            package_id=scope.package_id,
            package_checksum=scope.package_checksum,
            workflow_id=scope.workflow_id,
            workflow_version=scope.workflow_version,
            workflow_checksum=scope.workflow_checksum,
            allowed_capability=scope.capability,
            allowed_adapter=scope.adapter_id,
            maximum_operations=scope.maximum_operations,
            admitted_operations=token.admitted_operations,
            maximum_provider_calls=scope.maximum_provider_calls,
            used_provider_calls=token.used_provider_calls,
            maximum_provider_cost_microusd=scope.maximum_provider_cost_microusd,
            reserved_provider_cost_microusd=token.reserved_provider_cost_microusd,
            reported_provider_cost_microusd=token.reported_provider_cost_microusd,
            issued_at=parse_timestamp(token.issued_at, "issued_at"),
            expires_at=parse_timestamp(token.expires_at, "expires_at"),
            revoked=token.revoked,
            revoked_at=_parse_optional(token.revoked_at),
        )

    @staticmethod
    def _token(row: ProxyCapabilityTokenORM) -> ProxyCapabilityToken:
        return ProxyCapabilityToken(
            scope=ProxyAuthorizationScope(
                token_id=row.token_id,
                tenant_id=row.tenant_id,
                subject_id=row.subject_id,
                project_id=row.project_id,
                package_id=row.package_id,
                package_checksum=row.package_checksum,
                workflow_id=row.workflow_id,
                workflow_version=row.workflow_version,
                workflow_checksum=row.workflow_checksum,
                capability=row.allowed_capability,
                adapter_id=row.allowed_adapter,
                maximum_operations=row.maximum_operations,
                maximum_provider_calls=row.maximum_provider_calls,
                maximum_provider_cost_microusd=row.maximum_provider_cost_microusd,
            ),
            token_digest_sha256=row.token_digest_sha256,
            issued_at=format_timestamp(row.issued_at),
            expires_at=format_timestamp(row.expires_at),
            admitted_operations=row.admitted_operations,
            used_provider_calls=row.used_provider_calls,
            reserved_provider_cost_microusd=row.reserved_provider_cost_microusd,
            reported_provider_cost_microusd=row.reported_provider_cost_microusd,
            revoked=row.revoked,
            revoked_at=format_timestamp(row.revoked_at) if row.revoked_at else None,
        )

    @staticmethod
    def _operation(row: ProxyOperationORM) -> ProxyOperation:
        retention = RequestRetentionMode(row.request_retention_mode)
        retained_request_json = None
        if retention is RequestRetentionMode.CHECKSUM_ONLY:
            request_evidence = row.request_json
        else:
            envelope = CloudProxyRequestEnvelope.from_dict(row.request_json)
            request_evidence = envelope.privacy_evidence(retention).to_dict()
            retained_request_json = row.request_json
        value = {
            "operation_id": row.operation_id,
            "token_id": row.token_id,
            "authorization_scope_checksum": row.authorization_scope_checksum,
            "request": request_evidence,
            "adapter_id": row.adapter_id,
            "status": row.status,
            "admitted_at": format_timestamp(row.created_at),
            "updated_at": format_timestamp(row.updated_at),
            "started_at": format_timestamp(row.started_at) if row.started_at else None,
            "completed_at": format_timestamp(row.completed_at) if row.completed_at else None,
            "provider_data": row.provider_data_json,
            "provider_data_checksum": row.provider_data_checksum,
            "provider_data_size": row.provider_data_size,
            "response_content_checksum": row.response_content_checksum,
            "usage": row.usage_json,
            "error_code": row.error_code,
            "reconciliation_evidence": row.reconciliation_evidence,
            "retained_request_json": retained_request_json,
            "provider_response_checksum": row.provider_response_checksum,
            "provider_http_status": row.provider_http_status,
            "provider_adapter_version": row.provider_adapter_version,
        }
        return operation_from_dict(value)


class SQLProxyUnitOfWork:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session = session_factory()
        self.proxy = SQLProxyRepository(self.session)

    def __enter__(self) -> SQLProxyUnitOfWork:
        self.session.begin()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None and self.session.in_transaction():
            self.session.rollback()
        elif self.session.in_transaction():
            self.session.rollback()
        self.session.close()

    def commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise

    def rollback(self) -> None:
        self.session.rollback()


def _parse_optional(value: str | None) -> datetime | None:
    return parse_timestamp(value, "timestamp") if value is not None else None


def _rate_limit_json(usage: ProxyUsage | None) -> dict | None:
    if usage is None or all(
        value is None
        for value in (
            usage.provider_credits_used,
            usage.rate_limit_limit,
            usage.rate_limit_remaining,
            usage.rate_limit_reset,
        )
    ):
        return None
    return {
        "provider_credits_used": usage.provider_credits_used,
        "rate_limit_limit": usage.rate_limit_limit,
        "rate_limit_remaining": usage.rate_limit_remaining,
        "rate_limit_reset": usage.rate_limit_reset,
    }
