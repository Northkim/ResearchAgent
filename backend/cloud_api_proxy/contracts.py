"""Immutable contracts and non-cyclic identities for the Cloud API Proxy."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

PROXY_CONTRACT_VERSION = "reagent.cloud-api-proxy/v0.1"
CAPABILITY = "paper.search/v0.1"
ADAPTER_ID = "reagent.deterministic-fake-paper-search/v0.1"
FAKE_ADAPTER_ID = ADAPTER_ID
OPENALEX_ADAPTER_ID = "reagent.openalex-paper-search/v0.1"
ALLOWED_ADAPTER_IDS = frozenset({FAKE_ADAPTER_ID, OPENALEX_ADAPTER_ID})
POLICY_VERSION = "r3b-experimental-policy/v0.1"
OPENALEX_POLICY_VERSION = "r3c-experimental-policy/v0.1"
MAX_REQUEST_BYTES = 16 * 1024
MAX_RESULT_BYTES = 512 * 1024
MAX_TIMEOUT_SECONDS = 10
MAX_ACTIVE_OPERATIONS = 2
MAX_TOKEN_OPERATIONS = 50
MAX_TIMESTAMP_SKEW_SECONDS = 5 * 60
TOKEN_DEFAULT_MINUTES = 60
TOKEN_MAX_MINUTES = 120
OPENALEX_MAX_PROVIDER_CALLS = 20
OPENALEX_MAX_PROVIDER_COST_MICROUSD = 50_000
OPENALEX_RESERVED_SEARCH_COST_MICROUSD = 1_000
MICROUSD_PER_USD = 1_000_000
REQUEST_EVIDENCE_SCHEMA_VERSION = "proxy-request-evidence/v0.1"

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_TOKEN_ID = re.compile(r"proxytok-v1-[0-9a-f]{64}\Z")
_OPERATION_ID = re.compile(r"proxyop-v1-[0-9a-f]{64}\Z")


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return format_timestamp(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def format_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a timezone-aware RFC 3339 timestamp")
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be a timezone-aware RFC 3339 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a UTC offset")
    return parsed.astimezone(UTC)


def _text(value: Any, field: str, *, maximum: int = 255) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    normalized = value.strip()
    if len(normalized) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    for character in normalized:
        if unicodedata.category(character).startswith("C"):
            raise ValueError(f"{field} contains a prohibited control character")
    return normalized


def _checksum(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def parse_uuid4(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("idempotency_key must be UUIDv4")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise ValueError("idempotency_key must be UUIDv4") from error
    if parsed.version != 4:
        raise ValueError("idempotency_key must be UUIDv4")
    return str(parsed)


class ProxyOperationStatus(str, Enum):
    RECEIVED = "RECEIVED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class RequestRetentionMode(str, Enum):
    FULL_PARAMETERS = "FULL_PARAMETERS"
    CHECKSUM_ONLY = "CHECKSUM_ONLY"


@dataclass(frozen=True, slots=True)
class PaperSearchV01Request:
    query: str
    max_results: int = 10

    def __post_init__(self) -> None:
        query = _text(self.query, "parameters.query", maximum=500)
        if isinstance(self.max_results, bool) or not isinstance(self.max_results, int):
            raise ValueError("parameters.max_results must be an integer")
        if not 1 <= self.max_results <= 20:
            raise ValueError("parameters.max_results must be between 1 and 20")
        object.__setattr__(self, "query", query)

    @classmethod
    def from_dict(cls, value: Any) -> PaperSearchV01Request:
        if not isinstance(value, dict):
            raise ValueError("parameters must be a JSON object")
        unknown = set(value) - {"query", "max_results"}
        if unknown:
            raise ValueError("parameters contain unsupported fields")
        if "query" not in value:
            raise ValueError("parameters.query is required")
        return cls(query=value["query"], max_results=value.get("max_results", 10))

    def to_dict(self) -> dict[str, Any]:
        return {"max_results": self.max_results, "query": self.query}


@dataclass(frozen=True, slots=True)
class CloudProxyRequestEnvelope:
    proxy_contract_version: str
    idempotency_key: str
    project_id: str
    package_id: str
    package_checksum: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str
    capability: str
    parameters: PaperSearchV01Request
    harness_type: str
    harness_version: str | None
    harness_session_id: str
    client_timestamp: str
    request_content_checksum: str

    def __post_init__(self) -> None:
        if self.proxy_contract_version != PROXY_CONTRACT_VERSION:
            raise ValueError("unsupported proxy_contract_version")
        if self.capability != CAPABILITY:
            raise ValueError("unsupported capability")
        object.__setattr__(self, "idempotency_key", parse_uuid4(self.idempotency_key))
        for field in ("project_id", "package_id", "workflow_id", "workflow_version"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(self, "package_checksum", _checksum(self.package_checksum, "package_checksum"))
        object.__setattr__(self, "workflow_checksum", _checksum(self.workflow_checksum, "workflow_checksum"))
        if self.harness_type not in {"CODEX", "CLAUDE_CODE"}:
            raise ValueError("harness_type is not allowlisted")
        if self.harness_version is not None:
            object.__setattr__(self, "harness_version", _text(self.harness_version, "harness_version"))
        object.__setattr__(self, "harness_session_id", _text(self.harness_session_id, "harness_session_id"))
        object.__setattr__(self, "client_timestamp", format_timestamp(parse_timestamp(self.client_timestamp, "client_timestamp")))
        object.__setattr__(self, "request_content_checksum", _checksum(self.request_content_checksum, "request_content_checksum"))

    @classmethod
    def from_dict(cls, value: Any) -> CloudProxyRequestEnvelope:
        if not isinstance(value, dict):
            raise ValueError("request must be a JSON object")
        fields = {
            "proxy_contract_version", "idempotency_key", "project_id", "package_id",
            "package_checksum", "workflow_id", "workflow_version", "workflow_checksum",
            "capability", "parameters", "harness_type", "harness_version",
            "harness_session_id", "client_timestamp", "request_content_checksum",
        }
        unknown = set(value) - fields
        if unknown:
            raise ValueError("request contains unsupported or authorization fields")
        missing = fields - {"harness_version"} - set(value)
        if missing:
            raise ValueError("request is missing required fields")
        return cls(
            proxy_contract_version=value["proxy_contract_version"],
            idempotency_key=value["idempotency_key"],
            project_id=value["project_id"],
            package_id=value["package_id"],
            package_checksum=value["package_checksum"],
            workflow_id=value["workflow_id"],
            workflow_version=value["workflow_version"],
            workflow_checksum=value["workflow_checksum"],
            capability=value["capability"],
            parameters=PaperSearchV01Request.from_dict(value["parameters"]),
            harness_type=value["harness_type"],
            harness_version=value.get("harness_version"),
            harness_session_id=value["harness_session_id"],
            client_timestamp=value["client_timestamp"],
            request_content_checksum=value["request_content_checksum"],
        )

    @classmethod
    def create(cls, **values: Any) -> CloudProxyRequestEnvelope:
        initial = cls(request_content_checksum="sha256:" + "0" * 64, **values)
        return replace(initial, request_content_checksum=initial.computed_request_checksum())

    def semantic_content(self) -> dict[str, Any]:
        return {
            "proxy_contract_version": self.proxy_contract_version,
            "project_id": self.project_id,
            "package_id": self.package_id,
            "package_checksum": self.package_checksum,
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "workflow_checksum": self.workflow_checksum,
            "capability": self.capability,
            "parameters": self.parameters.to_dict(),
            "harness_type": self.harness_type,
            "harness_version": self.harness_version,
            "harness_session_id": self.harness_session_id,
            "client_timestamp": self.client_timestamp,
        }

    def computed_request_checksum(self) -> str:
        return canonical_hash(self.semantic_content())

    def verify_checksum(self) -> None:
        if self.request_content_checksum != self.computed_request_checksum():
            raise ValueError("request_content_checksum does not match canonical request content")

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.semantic_content(),
            "idempotency_key": self.idempotency_key,
            "request_content_checksum": self.request_content_checksum,
        }

    def privacy_evidence(self, retention_mode: RequestRetentionMode) -> ProxyRequestEvidence:
        query_bytes = self.parameters.query.encode("utf-8")
        return ProxyRequestEvidence(
            proxy_contract_version=self.proxy_contract_version,
            idempotency_key=self.idempotency_key,
            project_id=self.project_id,
            package_id=self.package_id,
            package_checksum=self.package_checksum,
            workflow_id=self.workflow_id,
            workflow_version=self.workflow_version,
            workflow_checksum=self.workflow_checksum,
            capability=self.capability,
            request_content_checksum=self.request_content_checksum,
            max_results=self.parameters.max_results,
            query_checksum=sha256_bytes(query_bytes),
            query_utf8_bytes=len(query_bytes),
            query_characters=len(self.parameters.query),
            harness_type=self.harness_type,
            harness_version=self.harness_version,
            harness_session_id=self.harness_session_id,
            client_timestamp=self.client_timestamp,
            retention_mode=retention_mode,
        )


@dataclass(frozen=True, slots=True)
class ProxyRequestEvidence:
    proxy_contract_version: str
    idempotency_key: str
    project_id: str
    package_id: str
    package_checksum: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str
    capability: str
    request_content_checksum: str
    max_results: int
    query_checksum: str
    query_utf8_bytes: int
    query_characters: int
    harness_type: str
    harness_version: str | None
    harness_session_id: str
    client_timestamp: str
    retention_mode: RequestRetentionMode
    schema_version: str = REQUEST_EVIDENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != REQUEST_EVIDENCE_SCHEMA_VERSION:
            raise ValueError("unsupported request evidence schema")
        if self.proxy_contract_version != PROXY_CONTRACT_VERSION or self.capability != CAPABILITY:
            raise ValueError("request evidence contract is not supported")
        object.__setattr__(self, "idempotency_key", parse_uuid4(self.idempotency_key))
        for field in ("project_id", "package_id", "workflow_id", "workflow_version"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        for field in ("package_checksum", "workflow_checksum", "request_content_checksum", "query_checksum"):
            object.__setattr__(self, field, _checksum(getattr(self, field), field))
        if not 1 <= self.max_results <= 20:
            raise ValueError("request evidence max_results must be between 1 and 20")
        if self.query_utf8_bytes <= 0 or self.query_characters <= 0:
            raise ValueError("request evidence query lengths must be positive")
        if self.harness_type not in {"CODEX", "CLAUDE_CODE"}:
            raise ValueError("request evidence harness_type is not allowlisted")
        if self.harness_version is not None:
            object.__setattr__(self, "harness_version", _text(self.harness_version, "harness_version"))
        object.__setattr__(self, "harness_session_id", _text(self.harness_session_id, "harness_session_id"))
        object.__setattr__(self, "client_timestamp", format_timestamp(parse_timestamp(self.client_timestamp, "client_timestamp")))

    @classmethod
    def from_dict(cls, value: Any) -> ProxyRequestEvidence:
        if not isinstance(value, dict):
            raise ValueError("request evidence must be an object")
        return cls(
            proxy_contract_version=value["proxy_contract_version"],
            idempotency_key=value["idempotency_key"],
            project_id=value["project_id"],
            package_id=value["package_id"],
            package_checksum=value["package_checksum"],
            workflow_id=value["workflow_id"],
            workflow_version=value["workflow_version"],
            workflow_checksum=value["workflow_checksum"],
            capability=value["capability"],
            request_content_checksum=value["request_content_checksum"],
            max_results=value["max_results"],
            query_checksum=value["query_checksum"],
            query_utf8_bytes=value["query_utf8_bytes"],
            query_characters=value["query_characters"],
            harness_type=value["harness_type"],
            harness_version=value.get("harness_version"),
            harness_session_id=value["harness_session_id"],
            client_timestamp=value["client_timestamp"],
            retention_mode=RequestRetentionMode(value["retention_mode"]),
            schema_version=value.get("schema_version", REQUEST_EVIDENCE_SCHEMA_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "proxy_contract_version": self.proxy_contract_version,
            "idempotency_key": self.idempotency_key,
            "project_id": self.project_id,
            "package_id": self.package_id,
            "package_checksum": self.package_checksum,
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "workflow_checksum": self.workflow_checksum,
            "capability": self.capability,
            "request_content_checksum": self.request_content_checksum,
            "max_results": self.max_results,
            "query_checksum": self.query_checksum,
            "query_utf8_bytes": self.query_utf8_bytes,
            "query_characters": self.query_characters,
            "harness_type": self.harness_type,
            "harness_version": self.harness_version,
            "harness_session_id": self.harness_session_id,
            "client_timestamp": self.client_timestamp,
            "retention_mode": self.retention_mode.value,
        }


@dataclass(frozen=True, slots=True)
class ProxyAuthorizationScope:
    token_id: str
    tenant_id: str
    subject_id: str
    project_id: str
    package_id: str
    package_checksum: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str
    capability: str
    adapter_id: str
    maximum_operations: int
    maximum_provider_calls: int = 0
    maximum_provider_cost_microusd: int = 0

    def __post_init__(self) -> None:
        if not _TOKEN_ID.fullmatch(self.token_id):
            raise ValueError("token_id is invalid")
        for field in ("tenant_id", "subject_id", "project_id", "package_id", "workflow_id", "workflow_version"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        _checksum(self.package_checksum, "package_checksum")
        _checksum(self.workflow_checksum, "workflow_checksum")
        if self.capability != CAPABILITY or self.adapter_id not in ALLOWED_ADAPTER_IDS:
            raise ValueError("scope must bind a ratified capability and adapter")
        if not 1 <= self.maximum_operations <= MAX_TOKEN_OPERATIONS:
            raise ValueError("maximum_operations must be between 1 and 50")
        if self.adapter_id == OPENALEX_ADAPTER_ID:
            if not 1 <= self.maximum_operations <= OPENALEX_MAX_PROVIDER_CALLS:
                raise ValueError("OpenAlex maximum_operations must be between 1 and 20")
            if self.maximum_provider_calls != self.maximum_operations:
                raise ValueError("OpenAlex provider-call limit must equal maximum_operations")
            if self.maximum_provider_cost_microusd != OPENALEX_MAX_PROVIDER_COST_MICROUSD:
                raise ValueError("OpenAlex cost limit must be 50000 microusd")
        elif self.maximum_provider_calls != 0 or self.maximum_provider_cost_microusd != 0:
            raise ValueError("fake adapter scope must retain zero Provider call and cost limits")

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id, "tenant_id": self.tenant_id,
            "subject_id": self.subject_id, "project_id": self.project_id,
            "package_id": self.package_id, "package_checksum": self.package_checksum,
            "workflow_id": self.workflow_id, "workflow_version": self.workflow_version,
            "workflow_checksum": self.workflow_checksum, "capability": self.capability,
            "adapter_id": self.adapter_id, "maximum_operations": self.maximum_operations,
            "maximum_provider_calls": self.maximum_provider_calls,
            "maximum_provider_cost_microusd": self.maximum_provider_cost_microusd,
        }

    @property
    def checksum(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True, slots=True)
class ProxyCapabilityToken:
    scope: ProxyAuthorizationScope
    token_digest_sha256: str
    issued_at: str
    expires_at: str
    admitted_operations: int = 0
    used_provider_calls: int = 0
    reserved_provider_cost_microusd: int = 0
    reported_provider_cost_microusd: int = 0
    revoked: bool = False
    revoked_at: str | None = None

    def __post_init__(self) -> None:
        _checksum(self.token_digest_sha256, "token_digest_sha256")
        issued = parse_timestamp(self.issued_at, "issued_at")
        expires = parse_timestamp(self.expires_at, "expires_at")
        if expires <= issued:
            raise ValueError("expires_at must be after issued_at")
        if not 0 <= self.admitted_operations <= self.scope.maximum_operations:
            raise ValueError("admitted_operations is outside the token budget")
        if not 0 <= self.used_provider_calls <= self.scope.maximum_provider_calls:
            raise ValueError("used_provider_calls is outside the token Provider-call budget")
        if not 0 <= self.reserved_provider_cost_microusd <= self.scope.maximum_provider_cost_microusd:
            raise ValueError("reserved Provider cost is outside the token budget")
        if self.reported_provider_cost_microusd < 0:
            raise ValueError("reported Provider cost cannot be negative")
        if self.revoked_at is not None:
            parse_timestamp(self.revoked_at, "revoked_at")


@dataclass(frozen=True, slots=True)
class ProxyUsage:
    request_count: int = 1
    retry_count: int = 0
    estimated_cost_minor_units: int = 0
    cost_currency: str = "USD"
    latency_ms: int = 0
    provider_http_calls: int = 0
    reserved_cost_microusd: int = 0
    reported_cost_microusd: int = 0
    provider_credits_used: str | None = None
    rate_limit_limit: int | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset: str | None = None

    def __post_init__(self) -> None:
        numeric = (
            self.request_count,
            self.retry_count,
            self.estimated_cost_minor_units,
            self.latency_ms,
            self.provider_http_calls,
            self.reserved_cost_microusd,
            self.reported_cost_microusd,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in numeric):
            raise ValueError("Proxy usage counters and costs must be non-negative integers")
        if self.provider_http_calls > 1:
            raise ValueError("one Proxy operation may use at most one Provider HTTP call")
        if self.cost_currency != "USD":
            raise ValueError("Proxy cost currency must be USD")
        if self.rate_limit_limit is not None and self.rate_limit_limit < 0:
            raise ValueError("rate_limit_limit cannot be negative")
        if self.rate_limit_remaining is not None and self.rate_limit_remaining < 0:
            raise ValueError("rate_limit_remaining cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_count": self.request_count,
            "retry_count": self.retry_count,
            "estimated_cost_minor_units": self.estimated_cost_minor_units,
            "cost_currency": self.cost_currency,
            "latency_ms": self.latency_ms,
            "provider_http_calls": self.provider_http_calls,
            "reserved_cost_microusd": self.reserved_cost_microusd,
            "reported_cost_microusd": self.reported_cost_microusd,
            "provider_credits_used": self.provider_credits_used,
            "rate_limit_limit": self.rate_limit_limit,
            "rate_limit_remaining": self.rate_limit_remaining,
            "rate_limit_reset": self.rate_limit_reset,
        }


def build_operation_id(request: CloudProxyRequestEnvelope, scope: ProxyAuthorizationScope) -> str:
    digest = canonical_hash({
        "proxy_contract_version": request.proxy_contract_version,
        "project_id": request.project_id,
        "package_id": request.package_id,
        "workflow_id": request.workflow_id,
        "capability": request.capability,
        "idempotency_key": request.idempotency_key,
        "request_content_checksum": request.request_content_checksum,
        "authorization_scope_checksum": scope.checksum,
    }).removeprefix("sha256:")
    return "proxyop-v1-" + digest


@dataclass(frozen=True, slots=True)
class ProxyOperation:
    operation_id: str
    token_id: str
    authorization_scope_checksum: str
    request: ProxyRequestEvidence
    adapter_id: str
    status: ProxyOperationStatus
    admitted_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    provider_data: dict[str, Any] | None = None
    provider_data_checksum: str | None = None
    provider_data_size: int | None = None
    response_content_checksum: str | None = None
    usage: ProxyUsage | None = None
    error_code: str | None = None
    reconciliation_evidence: str | None = None
    retained_request_json: dict[str, Any] | None = None
    provider_response_checksum: str | None = None
    provider_http_status: int | None = None
    provider_adapter_version: str = "v0.1"

    def __post_init__(self) -> None:
        if not _OPERATION_ID.fullmatch(self.operation_id):
            raise ValueError("operation_id is invalid")
        if not _TOKEN_ID.fullmatch(self.token_id):
            raise ValueError("token_id is invalid")
        _checksum(self.authorization_scope_checksum, "authorization_scope_checksum")
        for value, field in ((self.admitted_at, "admitted_at"), (self.updated_at, "updated_at")):
            parse_timestamp(value, field)
        if self.started_at is not None:
            parse_timestamp(self.started_at, "started_at")
        if self.completed_at is not None:
            parse_timestamp(self.completed_at, "completed_at")
        if self.provider_data_checksum is not None:
            _checksum(self.provider_data_checksum, "provider_data_checksum")
        if self.response_content_checksum is not None:
            _checksum(self.response_content_checksum, "response_content_checksum")
        if self.provider_response_checksum is not None:
            _checksum(self.provider_response_checksum, "provider_response_checksum")
        if self.request.retention_mode is RequestRetentionMode.CHECKSUM_ONLY and self.retained_request_json is not None:
            raise ValueError("checksum-only request retention cannot retain request JSON")

    def semantic_response_content(self) -> dict[str, Any]:
        return {
            "proxy_contract_version": PROXY_CONTRACT_VERSION,
            "operation_id": self.operation_id,
            "project_id": self.request.project_id,
            "package_id": self.request.package_id,
            "workflow_id": self.request.workflow_id,
            "capability": self.request.capability,
            "provider_adapter": {"adapter_id": self.adapter_id},
            "request_content_checksum": self.request.request_content_checksum,
            "operation_status": self.status.value,
            "provider_data": self.provider_data,
            "provider_data_checksum": self.provider_data_checksum,
            "usage": self.usage.to_dict() if self.usage else None,
            "budget": {
                "monetary_limit_minor_units": 0,
                "settled_minor_units": 0,
                "cost_unit": "microusd",
                "reserved_cost_microusd": self.usage.reserved_cost_microusd if self.usage else 0,
                "reported_cost_microusd": self.usage.reported_cost_microusd if self.usage else 0,
            },
            "retry_classification": (
                "RECONCILE_FIRST" if self.status is ProxyOperationStatus.RECONCILIATION_REQUIRED
                else "NEVER_RETRY"
            ),
            "warnings": [],
            "provenance": {
                "policy_version": (
                    OPENALEX_POLICY_VERSION if self.adapter_id == OPENALEX_ADAPTER_ID else POLICY_VERSION
                ),
                "adapter_id": self.adapter_id,
                "adapter_version": self.provider_adapter_version,
                "request_schema_version": CAPABILITY,
                "untrusted_provider_data": True,
                "request_retention_mode": self.request.retention_mode.value,
                "provider_response_checksum": self.provider_response_checksum,
                "provider_http_status": self.provider_http_status,
            },
            "error_code": self.error_code,
        }

    def with_response_checksum(self) -> ProxyOperation:
        return replace(self, response_content_checksum=canonical_hash(self.semantic_response_content()))

    def delivery(self, *, replayed: bool, server_timestamp: datetime) -> dict[str, Any]:
        content = self.semantic_response_content()
        content["response_content_checksum"] = self.response_content_checksum
        content["idempotency_result"] = "REPLAYED" if replayed else "CREATED"
        content["server_timestamp"] = format_timestamp(server_timestamp)
        content["response_checksum"] = None
        content["response_checksum"] = canonical_hash({key: value for key, value in content.items() if key != "response_checksum"})
        return content


def token_id_from_digest(token_digest: str) -> str:
    _checksum(token_digest, "token_digest")
    return "proxytok-v1-" + canonical_hash({"proxy_contract_version": PROXY_CONTRACT_VERSION, "token_digest": token_digest}).removeprefix("sha256:")


def operation_from_dict(value: dict[str, Any]) -> ProxyOperation:
    return ProxyOperation(
        operation_id=value["operation_id"], token_id=value["token_id"],
        authorization_scope_checksum=value["authorization_scope_checksum"],
        request=ProxyRequestEvidence.from_dict(value["request"]),
        adapter_id=value["adapter_id"], status=ProxyOperationStatus(value["status"]),
        admitted_at=value["admitted_at"], updated_at=value["updated_at"],
        started_at=value.get("started_at"), completed_at=value.get("completed_at"),
        provider_data=value.get("provider_data"),
        provider_data_checksum=value.get("provider_data_checksum"),
        provider_data_size=value.get("provider_data_size"),
        response_content_checksum=value.get("response_content_checksum"),
        usage=ProxyUsage(**value["usage"]) if value.get("usage") else None,
        error_code=value.get("error_code"),
        reconciliation_evidence=value.get("reconciliation_evidence"),
        retained_request_json=value.get("retained_request_json"),
        provider_response_checksum=value.get("provider_response_checksum"),
        provider_http_status=value.get("provider_http_status"),
        provider_adapter_version=value.get("provider_adapter_version", "v0.1"),
    )


def operation_to_dict(value: ProxyOperation) -> dict[str, Any]:
    return {
        "operation_id": value.operation_id, "token_id": value.token_id,
        "authorization_scope_checksum": value.authorization_scope_checksum,
        "request": value.request.to_dict(), "adapter_id": value.adapter_id,
        "status": value.status.value, "admitted_at": value.admitted_at,
        "updated_at": value.updated_at, "started_at": value.started_at,
        "completed_at": value.completed_at, "provider_data": value.provider_data,
        "provider_data_checksum": value.provider_data_checksum,
        "provider_data_size": value.provider_data_size,
        "response_content_checksum": value.response_content_checksum,
        "usage": value.usage.to_dict() if value.usage else None,
        "error_code": value.error_code,
        "reconciliation_evidence": value.reconciliation_evidence,
        "retained_request_json": value.retained_request_json,
        "provider_response_checksum": value.provider_response_checksum,
        "provider_http_status": value.provider_http_status,
        "provider_adapter_version": value.provider_adapter_version,
    }
