"""Application service for one bounded, fake-only Proxy operation."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Callable

from backend.workflow_packages.security import reject_sensitive_content

from .contracts import (
    ADAPTER_ID,
    MAX_ACTIVE_OPERATIONS,
    MAX_RESULT_BYTES,
    MAX_TIMESTAMP_SKEW_SECONDS,
    MAX_TIMEOUT_SECONDS,
    MAX_TOKEN_OPERATIONS,
    TOKEN_DEFAULT_MINUTES,
    TOKEN_MAX_MINUTES,
    CloudProxyRequestEnvelope,
    ProxyAuthorizationScope,
    ProxyCapabilityToken,
    ProxyOperation,
    ProxyOperationStatus,
    ProxyUsage,
    build_operation_id,
    canonical_json,
    format_timestamp,
    parse_timestamp,
    sha256_bytes,
    token_id_from_digest,
)
from .errors import ProxyError, conflict, forbidden, invalid, limited, not_found, unauthorized
from .ports import PaperSearchAdapter, ProxyUnitOfWorkFactory

_OPAQUE_TOKEN = re.compile(r"[A-Za-z0-9_-]{43,128}\Z")
_DUMMY_DIGEST = "sha256:" + hashlib.sha256(b"r3b-dummy-token-comparison").hexdigest()


def token_digest(plaintext: str) -> str:
    return sha256_bytes(plaintext.encode("utf-8"))


class CloudAPIProxyService:
    """Authenticates, admits, executes and reads fake Proxy operations only."""

    def __init__(
        self,
        *,
        unit_of_work_factory: ProxyUnitOfWorkFactory,
        adapter: PaperSearchAdapter,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        if adapter.adapter_id != ADAPTER_ID:
            raise ValueError("R3B composition accepts only the deterministic fake adapter")
        self.unit_of_work_factory = unit_of_work_factory
        self.adapter = adapter
        self.clock = clock or (lambda: datetime.now(UTC))
        self.monotonic = monotonic or time.monotonic

    def issue_token(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        project_id: str,
        package_id: str,
        package_checksum: str,
        workflow_id: str,
        workflow_version: str,
        workflow_checksum: str,
        lifetime_minutes: int = TOKEN_DEFAULT_MINUTES,
        maximum_operations: int = MAX_TOKEN_OPERATIONS,
    ) -> tuple[ProxyCapabilityToken, str]:
        if isinstance(lifetime_minutes, bool) or not isinstance(lifetime_minutes, int):
            raise ValueError("token lifetime must be an integer number of minutes")
        if not 1 <= lifetime_minutes <= TOKEN_MAX_MINUTES:
            raise ValueError("token lifetime must be between 1 and 120 minutes")
        if isinstance(maximum_operations, bool) or not isinstance(maximum_operations, int):
            raise ValueError("maximum operations must be an integer")
        if not 1 <= maximum_operations <= MAX_TOKEN_OPERATIONS:
            raise ValueError("maximum operations must be between 1 and 50")
        plaintext = secrets.token_urlsafe(32)
        digest = token_digest(plaintext)
        now = self._now()
        scope = ProxyAuthorizationScope(
            token_id=token_id_from_digest(digest),
            tenant_id=tenant_id,
            subject_id=subject_id,
            project_id=project_id,
            package_id=package_id,
            package_checksum=package_checksum,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            workflow_checksum=workflow_checksum,
            capability="paper.search/v0.1",
            adapter_id=ADAPTER_ID,
            maximum_operations=maximum_operations,
        )
        token = ProxyCapabilityToken(
            scope=scope,
            token_digest_sha256=digest,
            issued_at=format_timestamp(now),
            expires_at=format_timestamp(now + timedelta(minutes=lifetime_minutes)),
        )
        with self.unit_of_work_factory() as uow:
            uow.proxy.add_token(token)
            uow.commit()
        return token, plaintext

    def revoke_token(self, token_id: str) -> ProxyCapabilityToken:
        with self.unit_of_work_factory() as uow:
            token = uow.proxy.get_token(token_id, for_update=True)
            if token is None:
                raise not_found("Proxy capability token was not found")
            if token.revoked:
                return token
            revoked = replace(token, revoked=True, revoked_at=format_timestamp(self._now()))
            uow.proxy.save_token(revoked)
            uow.commit()
            return revoked

    def submit(
        self,
        *,
        bearer_token: str,
        path_project_id: str,
        request: CloudProxyRequestEnvelope,
    ) -> dict:
        request.verify_checksum()
        try:
            reject_sensitive_content(
                canonical_json(request.semantic_content()).encode("utf-8"),
                path="Proxy request",
            )
        except ValueError as error:
            raise invalid("request contains prohibited sensitive or machine-specific content", "UNSAFE_REQUEST_CONTENT") from error
        now = self._now()
        self._validate_client_timestamp(request, now)
        with self.unit_of_work_factory() as uow:
            token = self._authenticate(uow.proxy, bearer_token, now)
            locked = uow.proxy.get_token(token.scope.token_id, for_update=True)
            if locked is None:
                raise unauthorized()
            self._validate_token(locked, now)
            self._authorize(locked.scope, path_project_id, request)
            existing = uow.proxy.find_by_idempotency(locked.scope.token_id, request.idempotency_key)
            if existing is not None:
                if existing.request.request_content_checksum != request.request_content_checksum:
                    raise conflict()
                return existing.delivery(replayed=True, server_timestamp=now)
            if locked.admitted_operations >= locked.scope.maximum_operations:
                raise limited("OPERATION_LIMIT_EXHAUSTED", "Token operation limit is exhausted")
            if uow.proxy.count_active(locked.scope.token_id) >= MAX_ACTIVE_OPERATIONS:
                raise limited("CONCURRENCY_LIMIT_EXCEEDED", "Token has two active operations")
            operation = ProxyOperation(
                operation_id=build_operation_id(request, locked.scope),
                token_id=locked.scope.token_id,
                authorization_scope_checksum=locked.scope.checksum,
                request=request,
                adapter_id=locked.scope.adapter_id,
                status=ProxyOperationStatus.RECEIVED,
                admitted_at=format_timestamp(now),
                updated_at=format_timestamp(now),
            ).with_response_checksum()
            uow.proxy.add_operation(operation)
            uow.proxy.save_token(replace(locked, admitted_operations=locked.admitted_operations + 1))
            uow.commit()

        running_at = self._now()
        operation = replace(
            operation,
            status=ProxyOperationStatus.RUNNING,
            started_at=format_timestamp(running_at),
            updated_at=format_timestamp(running_at),
            response_content_checksum=None,
        ).with_response_checksum()
        self._save_operation(operation)

        started = self.monotonic()
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="r3b-fake-proxy")
        try:
            future = executor.submit(self.adapter.search, request.parameters)
            try:
                provider_data = future.result(timeout=MAX_TIMEOUT_SECONDS)
            except FutureTimeoutError:
                future.cancel()
                return self._finish_failure(operation, "OPERATION_TIMEOUT", MAX_TIMEOUT_SECONDS)
            elapsed = self.monotonic() - started
            if elapsed > MAX_TIMEOUT_SECONDS:
                return self._finish_failure(operation, "OPERATION_TIMEOUT", elapsed)
            encoded = canonical_json(provider_data).encode("utf-8")
            if len(encoded) > MAX_RESULT_BYTES:
                return self._finish_failure(operation, "RESPONSE_LIMIT_EXCEEDED", elapsed)
            try:
                reject_sensitive_content(encoded, path="normalized fake-provider result")
            except ValueError:
                return self._finish_failure(operation, "UNSAFE_PROVIDER_DATA", elapsed)
            completed = self._now()
            succeeded = replace(
                operation,
                status=ProxyOperationStatus.SUCCEEDED,
                provider_data=provider_data,
                provider_data_checksum=sha256_bytes(encoded),
                provider_data_size=len(encoded),
                usage=ProxyUsage(latency_ms=max(0, int(elapsed * 1000))),
                completed_at=format_timestamp(completed),
                updated_at=format_timestamp(completed),
                response_content_checksum=None,
            ).with_response_checksum()
            self._save_operation(succeeded)
            return succeeded.delivery(replayed=False, server_timestamp=self._now())
        except ProxyError:
            raise
        except Exception:
            return self._finish_failure(operation, "FAKE_ADAPTER_FAILURE", self.monotonic() - started)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def get_operation(
        self,
        *,
        bearer_token: str,
        path_project_id: str,
        operation_id: str,
    ) -> dict:
        now = self._now()
        with self.unit_of_work_factory() as uow:
            token = self._authenticate(uow.proxy, bearer_token, now)
            operation = uow.proxy.get_operation(operation_id)
            if operation is None:
                raise not_found()
            self._authorize_operation(token.scope, path_project_id, operation)
            return operation.delivery(replayed=True, server_timestamp=now)

    def find_operation(
        self,
        *,
        bearer_token: str,
        path_project_id: str,
        package_id: str,
        idempotency_key: str,
    ) -> dict:
        from .contracts import parse_uuid4

        key = parse_uuid4(idempotency_key)
        now = self._now()
        with self.unit_of_work_factory() as uow:
            token = self._authenticate(uow.proxy, bearer_token, now)
            if token.scope.project_id != path_project_id or token.scope.package_id != package_id:
                raise forbidden()
            operation = uow.proxy.find_by_idempotency(token.scope.token_id, key)
            if operation is None:
                raise not_found()
            return operation.delivery(replayed=True, server_timestamp=now)

    def reconcile_interrupted(self) -> int:
        with self.unit_of_work_factory() as uow:
            count = uow.proxy.reconcile_running("PROCESS_RESTART_NO_LIVE_ADAPTER_EXECUTION")
            uow.commit()
            return count

    def _authenticate(self, repository, plaintext: str, now: datetime) -> ProxyCapabilityToken:
        if not isinstance(plaintext, str) or not _OPAQUE_TOKEN.fullmatch(plaintext):
            hmac.compare_digest(_DUMMY_DIGEST, token_digest("invalid-token-shape"))
            raise unauthorized()
        digest = token_digest(plaintext)
        token = repository.find_token_by_digest(digest)
        stored = token.token_digest_sha256 if token is not None else _DUMMY_DIGEST
        matched = hmac.compare_digest(stored, digest)
        if token is None or not matched:
            raise unauthorized()
        self._validate_token(token, now)
        return token

    @staticmethod
    def _validate_token(token: ProxyCapabilityToken, now: datetime) -> None:
        if token.revoked:
            raise unauthorized("Bearer capability token is revoked")
        if now >= parse_timestamp(token.expires_at, "expires_at"):
            raise unauthorized("Bearer capability token is expired")

    @staticmethod
    def _authorize(scope: ProxyAuthorizationScope, path_project_id: str, request: CloudProxyRequestEnvelope) -> None:
        values = (
            (scope.project_id, path_project_id),
            (scope.project_id, request.project_id),
            (scope.package_id, request.package_id),
            (scope.package_checksum, request.package_checksum),
            (scope.workflow_id, request.workflow_id),
            (scope.workflow_version, request.workflow_version),
            (scope.workflow_checksum, request.workflow_checksum),
            (scope.capability, request.capability),
            (scope.adapter_id, ADAPTER_ID),
        )
        if any(expected != actual for expected, actual in values):
            raise forbidden()

    @staticmethod
    def _authorize_operation(scope: ProxyAuthorizationScope, path_project_id: str, operation: ProxyOperation) -> None:
        if (
            scope.project_id != path_project_id
            or scope.token_id != operation.token_id
            or scope.checksum != operation.authorization_scope_checksum
        ):
            raise forbidden()

    @staticmethod
    def _validate_client_timestamp(request: CloudProxyRequestEnvelope, now: datetime) -> None:
        timestamp = parse_timestamp(request.client_timestamp, "client_timestamp")
        if abs((timestamp - now).total_seconds()) > MAX_TIMESTAMP_SKEW_SECONDS:
            raise invalid("client_timestamp exceeds the allowed five-minute skew", "CLIENT_TIMESTAMP_OUT_OF_RANGE")

    def _save_operation(self, operation: ProxyOperation) -> None:
        with self.unit_of_work_factory() as uow:
            uow.proxy.save_operation(operation)
            uow.commit()

    def _finish_failure(self, operation: ProxyOperation, code: str, elapsed: float) -> dict:
        completed = self._now()
        failed = replace(
            operation,
            status=ProxyOperationStatus.FAILED,
            provider_data=None,
            provider_data_checksum=None,
            provider_data_size=None,
            usage=ProxyUsage(latency_ms=max(0, int(elapsed * 1000))),
            error_code=code,
            completed_at=format_timestamp(completed),
            updated_at=format_timestamp(completed),
            response_content_checksum=None,
        ).with_response_checksum()
        self._save_operation(failed)
        return failed.delivery(replayed=False, server_timestamp=self._now())

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Proxy clock must return a timezone-aware timestamp")
        return now.astimezone(UTC)
