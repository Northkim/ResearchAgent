"""Persistence and adapter ports exclusive to the teacher-aligned Proxy."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from .contracts import PaperSearchV01Request, ProxyCapabilityToken, ProxyOperation
from .openalex_diagnostics import OpenAlexStructuralFailure


class ProxyRepository(Protocol):
    def add_token(self, token: ProxyCapabilityToken) -> None: ...
    def find_token_by_digest(self, digest: str) -> ProxyCapabilityToken | None: ...
    def get_token(self, token_id: str, *, for_update: bool = False) -> ProxyCapabilityToken | None: ...
    def save_token(self, token: ProxyCapabilityToken) -> None: ...
    def get_operation(self, operation_id: str) -> ProxyOperation | None: ...
    def find_by_idempotency(self, token_id: str, idempotency_key: str) -> ProxyOperation | None: ...
    def add_operation(self, operation: ProxyOperation) -> None: ...
    def save_operation(self, operation: ProxyOperation) -> None: ...
    def count_active(self, token_id: str) -> int: ...
    def reconcile_running(self, evidence: str) -> int: ...


class ProxyUnitOfWork(Protocol):
    proxy: ProxyRepository
    def __enter__(self) -> ProxyUnitOfWork: ...
    def __exit__(self, exc_type, exc, traceback) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


ProxyUnitOfWorkFactory = Callable[[], ProxyUnitOfWork]


class PaperSearchAdapter(Protocol):
    adapter_id: str
    invocation_count: int
    def search(self, request: PaperSearchV01Request) -> dict | ProxyAdapterResult: ...


@dataclass(frozen=True, slots=True)
class ProxyAdapterResult:
    provider_data: dict
    provider_http_calls: int = 0
    reported_cost_microusd: int = 0
    provider_response_checksum: str | None = None
    provider_http_status: int | None = None
    provider_credits_used: str | None = None
    rate_limit_limit: int | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset: str | None = None
    provider_structural_shape_checksum: str | None = None


class ProxyAdapterError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        provider_http_calls: int,
        uncertain: bool = False,
        provider_http_status: int | None = None,
        provider_response_checksum: str | None = None,
        reported_cost_microusd: int = 0,
        structural_failure: OpenAlexStructuralFailure | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider_http_calls = provider_http_calls
        self.uncertain = uncertain
        self.provider_http_status = provider_http_status
        self.provider_response_checksum = provider_response_checksum
        self.reported_cost_microusd = reported_cost_microusd
        self.structural_failure = structural_failure


class ProxyAdapterInternalError(RuntimeError):
    """Safe typed internal adapter failure that preserves the public category."""

    def __init__(self, structural_failure: OpenAlexStructuralFailure) -> None:
        super().__init__("Provider normalization failed internally")
        self.structural_failure = structural_failure


@dataclass(frozen=True, slots=True)
class ProviderHTTPResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes


class OpenAlexTransport(Protocol):
    def get(
        self,
        *,
        url: str,
        params: Sequence[tuple[str, str]],
        timeout_seconds: float,
        maximum_response_bytes: int,
    ) -> ProviderHTTPResponse: ...


class OpenAlexCredentialSource(Protocol):
    def get(self) -> str: ...
