"""Application service for bounded teacher-aligned Proxy operations."""

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
    ALLOWED_ADAPTER_IDS,
    MAX_ACTIVE_OPERATIONS,
    MAX_RESULT_BYTES,
    MAX_TIMESTAMP_SKEW_SECONDS,
    MAX_TIMEOUT_SECONDS,
    MAX_TOKEN_OPERATIONS,
    OPENALEX_ADAPTER_ID,
    OPENALEX_MAX_PROVIDER_CALLS,
    OPENALEX_MAX_PROVIDER_COST_MICROUSD,
    OPENALEX_RESERVED_SEARCH_COST_MICROUSD,
    TOKEN_DEFAULT_MINUTES,
    TOKEN_MAX_MINUTES,
    CloudProxyRequestEnvelope,
    ProxyAuthorizationScope,
    ProxyCapabilityToken,
    ProxyOperation,
    ProxyOperationStatus,
    ProxyUsage,
    RequestRetentionMode,
    build_operation_id,
    canonical_json,
    format_timestamp,
    parse_timestamp,
    sha256_bytes,
    token_id_from_digest,
)
from .errors import ProxyError, conflict, forbidden, invalid, limited, not_found, unauthorized, unavailable
from .openalex_diagnostics import (
    FailureStage,
    ObservedKind,
    OpenAlexStructuralDiagnostic,
    OpenAlexStructuralDiagnosticEmitter,
    OpenAlexStructuralFailure,
    ValidatorCode,
    structural_failure as build_structural_failure,
)
from .ports import (
    PaperSearchAdapter,
    ProxyAdapterError,
    ProxyAdapterInternalError,
    ProxyAdapterResult,
    ProxyUnitOfWorkFactory,
)

_OPAQUE_TOKEN = re.compile(r"[A-Za-z0-9_-]{43,128}\Z")
_DUMMY_DIGEST = "sha256:" + hashlib.sha256(b"r3b-dummy-token-comparison").hexdigest()


def token_digest(plaintext: str) -> str:
    return sha256_bytes(plaintext.encode("utf-8"))


class CloudAPIProxyService:
    """Authenticate, admit, execute, and read one server-selected adapter call."""

    def __init__(
        self,
        *,
        unit_of_work_factory: ProxyUnitOfWorkFactory,
        adapter: PaperSearchAdapter | None = None,
        adapters: dict[str, PaperSearchAdapter] | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        openalex_structural_diagnostics: OpenAlexStructuralDiagnosticEmitter | None = None,
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory
        registry = dict(adapters or {})
        if adapter is not None:
            registry.setdefault(adapter.adapter_id, adapter)
        if not registry or any(key != value.adapter_id for key, value in registry.items()):
            raise ValueError("Proxy adapter registry is empty or inconsistent")
        if not set(registry) <= ALLOWED_ADAPTER_IDS:
            raise ValueError("Proxy adapter registry contains an unratified adapter")
        self.adapters = registry
        self.adapter = adapter or next(iter(registry.values()))
        self.clock = clock or (lambda: datetime.now(UTC))
        self.monotonic = monotonic or time.monotonic
        self.openalex_structural_diagnostics = (
            openalex_structural_diagnostics
            or OpenAlexStructuralDiagnosticEmitter(enabled=False)
        )

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
        maximum_operations: int | None = None,
        adapter_id: str = ADAPTER_ID,
    ) -> tuple[ProxyCapabilityToken, str]:
        if isinstance(lifetime_minutes, bool) or not isinstance(lifetime_minutes, int):
            raise ValueError("token lifetime must be an integer number of minutes")
        if not 1 <= lifetime_minutes <= TOKEN_MAX_MINUTES:
            raise ValueError("token lifetime must be between 1 and 120 minutes")
        if adapter_id not in ALLOWED_ADAPTER_IDS:
            raise ValueError("adapter_id is not ratified")
        if maximum_operations is None:
            maximum_operations = (
                OPENALEX_MAX_PROVIDER_CALLS
                if adapter_id == OPENALEX_ADAPTER_ID
                else MAX_TOKEN_OPERATIONS
            )
        if isinstance(maximum_operations, bool) or not isinstance(maximum_operations, int):
            raise ValueError("maximum operations must be an integer")
        maximum_allowed = (
            OPENALEX_MAX_PROVIDER_CALLS
            if adapter_id == OPENALEX_ADAPTER_ID
            else MAX_TOKEN_OPERATIONS
        )
        if not 1 <= maximum_operations <= maximum_allowed:
            raise ValueError(f"maximum operations must be between 1 and {maximum_allowed}")
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
            adapter_id=adapter_id,
            maximum_operations=maximum_operations,
            maximum_provider_calls=(maximum_operations if adapter_id == OPENALEX_ADAPTER_ID else 0),
            maximum_provider_cost_microusd=(
                OPENALEX_MAX_PROVIDER_COST_MICROUSD
                if adapter_id == OPENALEX_ADAPTER_ID
                else 0
            ),
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
            selected_adapter = self.adapters.get(locked.scope.adapter_id)
            if selected_adapter is None:
                raise unavailable("Authorized Proxy adapter is not configured")
            if locked.scope.adapter_id == OPENALEX_ADAPTER_ID and (
                locked.admitted_operations >= locked.scope.maximum_operations
                or locked.used_provider_calls + 1 > locked.scope.maximum_provider_calls
                or max(
                    locked.reserved_provider_cost_microusd,
                    locked.reported_provider_cost_microusd,
                )
                + OPENALEX_RESERVED_SEARCH_COST_MICROUSD
                > locked.scope.maximum_provider_cost_microusd
            ):
                raise limited("PROVIDER_BUDGET_EXHAUSTED", "Provider call or cost budget is exhausted")
            if locked.admitted_operations >= locked.scope.maximum_operations:
                raise limited("OPERATION_LIMIT_EXHAUSTED", "Token operation limit is exhausted")
            if uow.proxy.count_active(locked.scope.token_id) >= MAX_ACTIVE_OPERATIONS:
                raise limited("CONCURRENCY_LIMIT_EXCEEDED", "Token has two active operations")
            provider_calls = 0
            reserved_cost = 0
            retention_mode = RequestRetentionMode.FULL_PARAMETERS
            retained_request_json = request.to_dict()
            if locked.scope.adapter_id == OPENALEX_ADAPTER_ID:
                provider_calls = 1
                reserved_cost = OPENALEX_RESERVED_SEARCH_COST_MICROUSD
                retention_mode = RequestRetentionMode.CHECKSUM_ONLY
                retained_request_json = None
            operation = ProxyOperation(
                operation_id=build_operation_id(request, locked.scope),
                token_id=locked.scope.token_id,
                authorization_scope_checksum=locked.scope.checksum,
                request=request.privacy_evidence(retention_mode),
                adapter_id=locked.scope.adapter_id,
                status=ProxyOperationStatus.RECEIVED,
                admitted_at=format_timestamp(now),
                updated_at=format_timestamp(now),
                usage=(
                    ProxyUsage(
                        request_count=1,
                        provider_http_calls=provider_calls,
                        reserved_cost_microusd=reserved_cost,
                    )
                    if provider_calls
                    else None
                ),
                retained_request_json=retained_request_json,
                provider_adapter_version=getattr(selected_adapter, "adapter_version", "v0.1"),
            ).with_response_checksum()
            uow.proxy.add_operation(operation)
            uow.proxy.save_token(
                replace(
                    locked,
                    admitted_operations=locked.admitted_operations + 1,
                    used_provider_calls=locked.used_provider_calls + provider_calls,
                    reserved_provider_cost_microusd=(
                        locked.reserved_provider_cost_microusd + reserved_cost
                    ),
                )
            )
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
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="reagent-cloud-proxy")
        try:
            future = executor.submit(selected_adapter.search, request.parameters)
            try:
                raw_result = future.result(timeout=MAX_TIMEOUT_SECONDS)
            except FutureTimeoutError:
                future.cancel()
                if operation.adapter_id == OPENALEX_ADAPTER_ID:
                    return self._finish_failure(
                        operation,
                        "PROVIDER_RECONCILIATION_REQUIRED",
                        MAX_TIMEOUT_SECONDS,
                        reconciliation=True,
                    )
                return self._finish_failure(operation, "OPERATION_TIMEOUT", MAX_TIMEOUT_SECONDS)
            adapter_result = (
                raw_result
                if isinstance(raw_result, ProxyAdapterResult)
                else ProxyAdapterResult(provider_data=raw_result)
            )
            elapsed = self.monotonic() - started
            if elapsed > MAX_TIMEOUT_SECONDS:
                code = "PROVIDER_TIMEOUT" if operation.adapter_id == OPENALEX_ADAPTER_ID else "OPERATION_TIMEOUT"
                return self._finish_failure(
                    operation,
                    code,
                    elapsed,
                    adapter_result=adapter_result,
                )
            provider_data = adapter_result.provider_data
            normalized_records = _normalized_record_count(provider_data)
            try:
                encoded = canonical_json(provider_data).encode("utf-8")
            except Exception:
                if operation.adapter_id == OPENALEX_ADAPTER_ID:
                    return self._finish_failure(
                        operation,
                        "PROVIDER_UNAVAILABLE",
                        elapsed,
                        structural_failure=build_structural_failure(
                            failure_stage=FailureStage.NORMALIZED_SERIALIZATION,
                            approved_json_path="/normalized_results",
                            observed_kind=ObservedKind.UNKNOWN,
                            validator_code=ValidatorCode.NORMALIZED_CANONICAL_SERIALIZATION,
                            normalized_records_before_failure=normalized_records,
                            provider_shape_checksum=(
                                adapter_result.provider_structural_shape_checksum
                            ),
                        ),
                    )
                raise
            if len(encoded) > MAX_RESULT_BYTES:
                code = (
                    "PROVIDER_RESPONSE_TOO_LARGE"
                    if operation.adapter_id == OPENALEX_ADAPTER_ID
                    else "RESPONSE_LIMIT_EXCEEDED"
                )
                return self._finish_failure(
                    operation,
                    code,
                    elapsed,
                    adapter_result=adapter_result,
                    structural_failure=(
                        build_structural_failure(
                            failure_stage=FailureStage.RESULT_SIZE,
                            approved_json_path="/normalized_results",
                            observed_kind=ObservedKind.LIMIT_EXCEEDED,
                            validator_code=ValidatorCode.NORMALIZED_RESULT_SIZE,
                            normalized_records_before_failure=normalized_records,
                            provider_shape_checksum=(
                                adapter_result.provider_structural_shape_checksum
                            ),
                        )
                        if operation.adapter_id == OPENALEX_ADAPTER_ID
                        else None
                    ),
                )
            try:
                reject_sensitive_content(encoded, path="normalized fake-provider result")
            except ValueError:
                code = (
                    "PROVIDER_INVALID_RESPONSE"
                    if operation.adapter_id == OPENALEX_ADAPTER_ID
                    else "UNSAFE_PROVIDER_DATA"
                )
                return self._finish_failure(
                    operation,
                    code,
                    elapsed,
                    adapter_result=adapter_result,
                    structural_failure=(
                        build_structural_failure(
                            failure_stage=FailureStage.SERVICE_SAFETY,
                            approved_json_path="/service_safety",
                            observed_kind=ObservedKind.SENSITIVE_CONTENT,
                            validator_code=ValidatorCode.SERVICE_SENSITIVE_CONTENT,
                            normalized_records_before_failure=normalized_records,
                            provider_shape_checksum=(
                                adapter_result.provider_structural_shape_checksum
                            ),
                        )
                        if operation.adapter_id == OPENALEX_ADAPTER_ID
                        else None
                    ),
                )
            completed = self._now()
            succeeded = replace(
                operation,
                status=ProxyOperationStatus.SUCCEEDED,
                provider_data=provider_data,
                provider_data_checksum=sha256_bytes(encoded),
                provider_data_size=len(encoded),
                usage=ProxyUsage(
                    latency_ms=max(0, int(elapsed * 1000)),
                    provider_http_calls=adapter_result.provider_http_calls,
                    reserved_cost_microusd=(
                        OPENALEX_RESERVED_SEARCH_COST_MICROUSD
                        if operation.adapter_id == OPENALEX_ADAPTER_ID
                        else 0
                    ),
                    reported_cost_microusd=adapter_result.reported_cost_microusd,
                    provider_credits_used=adapter_result.provider_credits_used,
                    rate_limit_limit=adapter_result.rate_limit_limit,
                    rate_limit_remaining=adapter_result.rate_limit_remaining,
                    rate_limit_reset=adapter_result.rate_limit_reset,
                ),
                provider_response_checksum=adapter_result.provider_response_checksum,
                provider_http_status=adapter_result.provider_http_status,
                completed_at=format_timestamp(completed),
                updated_at=format_timestamp(completed),
                response_content_checksum=None,
            ).with_response_checksum()
            self._save_operation(
                succeeded,
                reported_cost_delta=adapter_result.reported_cost_microusd,
            )
            return succeeded.delivery(replayed=False, server_timestamp=self._now())
        except ProxyAdapterError as error:
            return self._finish_failure(
                operation,
                error.code,
                self.monotonic() - started,
                adapter_error=error,
                reconciliation=error.uncertain,
                structural_failure=error.structural_failure,
            )
        except ProxyAdapterInternalError as error:
            return self._finish_failure(
                operation,
                "PROVIDER_UNAVAILABLE",
                self.monotonic() - started,
                structural_failure=error.structural_failure,
            )
        except ProxyError:
            raise
        except Exception:
            code = (
                "PROVIDER_UNAVAILABLE"
                if operation.adapter_id == OPENALEX_ADAPTER_ID
                else "FAKE_ADAPTER_FAILURE"
            )
            return self._finish_failure(
                operation,
                code,
                self.monotonic() - started,
                structural_failure=(
                    build_structural_failure(
                        failure_stage=FailureStage.UNCLASSIFIED_INTERNAL,
                        approved_json_path="/",
                        observed_kind=ObservedKind.UNKNOWN,
                        validator_code=ValidatorCode.UNCLASSIFIED_INTERNAL,
                    )
                    if operation.adapter_id == OPENALEX_ADAPTER_ID
                    else None
                ),
            )
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

    def _save_operation(self, operation: ProxyOperation, *, reported_cost_delta: int = 0) -> None:
        with self.unit_of_work_factory() as uow:
            if reported_cost_delta:
                token = uow.proxy.get_token(operation.token_id, for_update=True)
                if token is None:
                    raise RuntimeError("Proxy token disappeared while settling Provider cost")
                uow.proxy.save_token(
                    replace(
                        token,
                        reported_provider_cost_microusd=(
                            token.reported_provider_cost_microusd + reported_cost_delta
                        ),
                    )
                )
            uow.proxy.save_operation(operation)
            uow.commit()

    def _finish_failure(
        self,
        operation: ProxyOperation,
        code: str,
        elapsed: float,
        *,
        adapter_result: ProxyAdapterResult | None = None,
        adapter_error: ProxyAdapterError | None = None,
        reconciliation: bool = False,
        structural_failure: OpenAlexStructuralFailure | None = None,
    ) -> dict:
        completed = self._now()
        reported_cost = (
            adapter_result.reported_cost_microusd
            if adapter_result is not None
            else (adapter_error.reported_cost_microusd if adapter_error is not None else 0)
        )
        provider_calls = (
            adapter_result.provider_http_calls
            if adapter_result is not None
            else (adapter_error.provider_http_calls if adapter_error is not None else 0)
        )
        response_checksum = (
            adapter_result.provider_response_checksum
            if adapter_result is not None
            else (adapter_error.provider_response_checksum if adapter_error is not None else None)
        )
        http_status = (
            adapter_result.provider_http_status
            if adapter_result is not None
            else (adapter_error.provider_http_status if adapter_error is not None else None)
        )
        failed = replace(
            operation,
            status=(
                ProxyOperationStatus.RECONCILIATION_REQUIRED
                if reconciliation
                else ProxyOperationStatus.FAILED
            ),
            provider_data=None,
            provider_data_checksum=None,
            provider_data_size=None,
            usage=ProxyUsage(
                latency_ms=max(0, int(elapsed * 1000)),
                provider_http_calls=provider_calls,
                reserved_cost_microusd=(
                    OPENALEX_RESERVED_SEARCH_COST_MICROUSD
                    if operation.adapter_id == OPENALEX_ADAPTER_ID
                    else 0
                ),
                reported_cost_microusd=reported_cost,
            ),
            error_code=code,
            reconciliation_evidence=(
                "PROVIDER_OUTCOME_UNCERTAIN_NO_AUTOMATIC_RETRY"
                if reconciliation
                else operation.reconciliation_evidence
            ),
            provider_response_checksum=response_checksum,
            provider_http_status=http_status,
            completed_at=format_timestamp(completed),
            updated_at=format_timestamp(completed),
            response_content_checksum=None,
        ).with_response_checksum()
        self._save_operation(failed, reported_cost_delta=reported_cost)
        if operation.adapter_id == OPENALEX_ADAPTER_ID and structural_failure is not None:
            diagnostic = OpenAlexStructuralDiagnostic.from_failure(
                structural_failure,
                adapter_version=operation.provider_adapter_version,
                operation_id=operation.operation_id,
                request_content_checksum=operation.request.request_content_checksum,
            )
            self.openalex_structural_diagnostics.emit(diagnostic)
        return failed.delivery(replayed=False, server_timestamp=self._now())

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Proxy clock must return a timezone-aware timestamp")
        return now.astimezone(UTC)


def _normalized_record_count(provider_data: object) -> int:
    if not isinstance(provider_data, dict):
        return 0
    papers = provider_data.get("papers")
    return len(papers) if isinstance(papers, list) else 0
