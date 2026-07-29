"""Immutable contracts for explicit multilingual search and safe diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ._serialization import (
    SerializableContract,
    canonical_hash,
    freeze_json,
    require_aware,
    require_non_empty,
)
from .models import ResearchQuery, require_sha256

QUERY_VARIANT_SCHEMA_VERSION = "reagent-query-variant/v1"
MULTILINGUAL_SEARCH_PLAN_SCHEMA_VERSION = "reagent-multilingual-search-plan/v1"
SEARCH_DIAGNOSTIC_SCHEMA_VERSION = "reagent-search-diagnostic/v1"
FIELD_REJECTION_DIAGNOSTIC_SCHEMA_VERSION = "reagent-field-rejection-diagnostic/v1"


class QueryVariantType(str, Enum):
    ORIGINAL = "ORIGINAL"
    MANUAL_SYNONYM = "MANUAL_SYNONYM"
    MANUAL_TRANSLATION = "MANUAL_TRANSLATION"
    QUOTED_TERM = "QUOTED_TERM"
    BOOLEAN_EXPANSION = "BOOLEAN_EXPANSION"
    ENGLISH_PIVOT = "ENGLISH_PIVOT"
    BILINGUAL_MIXED = "BILINGUAL_MIXED"


class SearchDiagnosticCode(str, Enum):
    ZERO_RESULTS = "ZERO_RESULTS"
    LOW_RESULT_COUNT = "LOW_RESULT_COUNT"
    NO_NORMALIZED_RESULTS = "NO_NORMALIZED_RESULTS"
    MISSING_ABSTRACT = "MISSING_ABSTRACT"
    MISSING_DOI = "MISSING_DOI"
    MISSING_AUTHORS = "MISSING_AUTHORS"
    MISSING_YEAR = "MISSING_YEAR"
    MISSING_VENUE = "MISSING_VENUE"
    FIELD_LENGTH_REJECTED = "FIELD_LENGTH_REJECTED"
    CONTROL_CHARACTER_REJECTED = "CONTROL_CHARACTER_REJECTED"
    INVALID_UNICODE = "INVALID_UNICODE"
    LANGUAGE_FIELD_MISSING = "LANGUAGE_FIELD_MISSING"
    LANGUAGE_MISMATCH = "LANGUAGE_MISMATCH"
    ONLY_ENGLISH_RESULTS = "ONLY_ENGLISH_RESULTS"
    ONLY_ORIGINAL_LANGUAGE_RESULTS = "ONLY_ORIGINAL_LANGUAGE_RESULTS"
    DUPLICATE_CONCENTRATION = "DUPLICATE_CONCENTRATION"
    ADVISORY_TITLE_YEAR_CLUSTER = "ADVISORY_TITLE_YEAR_CLUSTER"
    PARTIAL_VARIANT_FAILURE = "PARTIAL_VARIANT_FAILURE"
    TOTAL_REQUEST_BUDGET_EXCEEDED = "TOTAL_REQUEST_BUDGET_EXCEEDED"
    IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
    CANDIDATE_LIMIT_TRUNCATED = "CANDIDATE_LIMIT_TRUNCATED"


class DiagnosticCause(str, Enum):
    PROVIDER_COVERAGE = "PROVIDER_COVERAGE"
    QUERY_CONSTRUCTION = "QUERY_CONSTRUCTION"
    LOCAL_VALIDATION = "LOCAL_VALIDATION"
    METADATA_SHAPE = "METADATA_SHAPE"
    UNKNOWN = "UNKNOWN"
    COMBINED = "COMBINED"


@dataclass(frozen=True, slots=True)
class QueryVariant(SerializableContract):
    variant_id: str
    source_query: str
    source_language: str
    variant_language: str
    variant_type: QueryVariantType
    exact_provider_query: str
    generated_by: str
    generation_method: str
    generation_version: str
    owner_approved: bool
    created_at: datetime
    checksum: str = ""
    schema_version: str = QUERY_VARIANT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != QUERY_VARIANT_SCHEMA_VERSION:
            raise ValueError("Unsupported QueryVariant schema version")
        for value, name in (
            (self.variant_id, "QueryVariant.variant_id"),
            (self.source_query, "QueryVariant.source_query"),
            (self.source_language, "QueryVariant.source_language"),
            (self.variant_language, "QueryVariant.variant_language"),
            (self.exact_provider_query, "QueryVariant.exact_provider_query"),
            (self.generated_by, "QueryVariant.generated_by"),
            (self.generation_method, "QueryVariant.generation_method"),
            (self.generation_version, "QueryVariant.generation_version"),
        ):
            require_non_empty(value, name)
        require_aware(self.created_at, "QueryVariant.created_at")
        if not isinstance(self.variant_type, QueryVariantType):
            object.__setattr__(self, "variant_type", QueryVariantType(self.variant_type))
        expected = canonical_hash(self._checksum_payload())
        if self.checksum:
            require_sha256(self.checksum, "QueryVariant.checksum")
            if self.checksum != expected:
                raise ValueError("QueryVariant checksum does not match its immutable fields")
        else:
            object.__setattr__(self, "checksum", expected)

    def _checksum_payload(self) -> Mapping[str, Any]:
        return {
            "variant_id": self.variant_id,
            "source_query": self.source_query,
            "source_language": self.source_language,
            "variant_language": self.variant_language,
            "variant_type": self.variant_type,
            "exact_provider_query": self.exact_provider_query,
            "generated_by": self.generated_by,
            "generation_method": self.generation_method,
            "generation_version": self.generation_version,
            "owner_approved": self.owner_approved,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> QueryVariant:
        return cls(
            variant_id=str(value["variant_id"]),
            source_query=str(value["source_query"]),
            source_language=str(value["source_language"]),
            variant_language=str(value["variant_language"]),
            variant_type=QueryVariantType(str(value["variant_type"])),
            exact_provider_query=str(value["exact_provider_query"]),
            generated_by=str(value["generated_by"]),
            generation_method=str(value["generation_method"]),
            generation_version=str(value["generation_version"]),
            owner_approved=bool(value["owner_approved"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            checksum=str(value.get("checksum", "")),
            schema_version=str(value.get("schema_version", QUERY_VARIANT_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class MultilingualSearchPlan(SerializableContract):
    plan_id: str
    original_query: ResearchQuery
    original_language: str
    query_variants: tuple[QueryVariant, ...]
    language_filter: str | None
    merge_policy_version: str
    deduplication_policy_version: str
    per_variant_request_limit: int
    total_request_limit: int
    candidate_limit: int
    expansion_version: str
    coverage_warning_policy: Mapping[str, Any]
    plan_checksum: str = ""
    schema_version: str = MULTILINGUAL_SEARCH_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MULTILINGUAL_SEARCH_PLAN_SCHEMA_VERSION:
            raise ValueError("Unsupported MultilingualSearchPlan schema version")
        for value, name in (
            (self.plan_id, "MultilingualSearchPlan.plan_id"),
            (self.original_language, "MultilingualSearchPlan.original_language"),
            (self.merge_policy_version, "MultilingualSearchPlan.merge_policy_version"),
            (
                self.deduplication_policy_version,
                "MultilingualSearchPlan.deduplication_policy_version",
            ),
            (self.expansion_version, "MultilingualSearchPlan.expansion_version"),
        ):
            require_non_empty(value, name)
        variants = tuple(self.query_variants)
        if not variants:
            raise ValueError("MultilingualSearchPlan requires at least one query variant")
        ids = [item.variant_id for item in variants]
        if len(ids) != len(set(ids)):
            raise ValueError("MultilingualSearchPlan variant IDs must be unique")
        queries = [item.exact_provider_query for item in variants]
        if len(queries) != len(set(queries)):
            raise ValueError("MultilingualSearchPlan exact provider queries must be unique")
        if self.per_variant_request_limit <= 0:
            raise ValueError("per_variant_request_limit must be positive")
        if self.total_request_limit < len(variants):
            raise ValueError("total_request_limit must permit at least one request per variant")
        if self.total_request_limit > self.per_variant_request_limit * len(variants):
            raise ValueError("total_request_limit exceeds the sum of per-variant limits")
        if not 1 <= self.candidate_limit <= 80:
            raise ValueError("candidate_limit must be in [1, 80]")
        if self.language_filter is not None:
            require_non_empty(self.language_filter, "MultilingualSearchPlan.language_filter")
        object.__setattr__(self, "query_variants", variants)
        object.__setattr__(
            self,
            "coverage_warning_policy",
            freeze_json(self.coverage_warning_policy),
        )
        expected = canonical_hash(self._checksum_payload())
        if self.plan_checksum:
            require_sha256(self.plan_checksum, "MultilingualSearchPlan.plan_checksum")
            if self.plan_checksum != expected:
                raise ValueError(
                    "MultilingualSearchPlan checksum does not match its immutable fields"
                )
        else:
            object.__setattr__(self, "plan_checksum", expected)

    def _checksum_payload(self) -> Mapping[str, Any]:
        return {
            "plan_id": self.plan_id,
            "original_query": self.original_query,
            "original_language": self.original_language,
            "query_variants": self.query_variants,
            "language_filter": self.language_filter,
            "merge_policy_version": self.merge_policy_version,
            "deduplication_policy_version": self.deduplication_policy_version,
            "per_variant_request_limit": self.per_variant_request_limit,
            "total_request_limit": self.total_request_limit,
            "candidate_limit": self.candidate_limit,
            "expansion_version": self.expansion_version,
            "coverage_warning_policy": self.coverage_warning_policy,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class SearchDiagnostic(SerializableContract):
    code: SearchDiagnosticCode
    cause: DiagnosticCause
    message: str
    blocking: bool = False
    variant_id: str | None = None
    record_identity: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SEARCH_DIAGNOSTIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SEARCH_DIAGNOSTIC_SCHEMA_VERSION:
            raise ValueError("Unsupported SearchDiagnostic schema version")
        if not isinstance(self.code, SearchDiagnosticCode):
            object.__setattr__(self, "code", SearchDiagnosticCode(self.code))
        if not isinstance(self.cause, DiagnosticCause):
            object.__setattr__(self, "cause", DiagnosticCause(self.cause))
        require_non_empty(self.message, "SearchDiagnostic.message")
        if self.variant_id is not None:
            require_non_empty(self.variant_id, "SearchDiagnostic.variant_id")
        object.__setattr__(self, "details", freeze_json(self.details))


@dataclass(frozen=True, slots=True)
class FieldRejectionDiagnostic(SerializableContract):
    category: SearchDiagnosticCode
    field_name: str | None
    measured_normalized_length: int | None
    configured_limit: int | None
    record_identity: str | None
    value_sha256: str | None
    safe_preview: str | None
    preview_length: int
    adapter_version: str
    validator_version: str
    details_available: bool = True
    unavailable_reason: str | None = None
    schema_version: str = FIELD_REJECTION_DIAGNOSTIC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != FIELD_REJECTION_DIAGNOSTIC_SCHEMA_VERSION:
            raise ValueError("Unsupported FieldRejectionDiagnostic schema version")
        if not isinstance(self.category, SearchDiagnosticCode):
            object.__setattr__(self, "category", SearchDiagnosticCode(self.category))
        if self.category not in {
            SearchDiagnosticCode.FIELD_LENGTH_REJECTED,
            SearchDiagnosticCode.CONTROL_CHARACTER_REJECTED,
            SearchDiagnosticCode.INVALID_UNICODE,
        }:
            raise ValueError("FieldRejectionDiagnostic has an invalid category")
        require_non_empty(self.adapter_version, "FieldRejectionDiagnostic.adapter_version")
        require_non_empty(self.validator_version, "FieldRejectionDiagnostic.validator_version")
        if self.details_available:
            if self.field_name is None:
                raise ValueError("Available rejection details require a field name")
            require_non_empty(self.field_name, "FieldRejectionDiagnostic.field_name")
            if self.measured_normalized_length is None or self.measured_normalized_length < 0:
                raise ValueError("Available rejection details require measured length")
            if self.configured_limit is None or self.configured_limit <= 0:
                raise ValueError("Available rejection details require configured limit")
            if self.value_sha256 is None:
                raise ValueError("Available rejection details require a value hash")
            require_sha256(self.value_sha256, "FieldRejectionDiagnostic.value_sha256")
            if self.safe_preview is None:
                raise ValueError("Available rejection details require a safe preview")
        else:
            require_non_empty(
                self.unavailable_reason or "",
                "FieldRejectionDiagnostic.unavailable_reason",
            )
        if self.safe_preview is not None and len(self.safe_preview) != self.preview_length:
            raise ValueError("preview_length must match safe_preview")
        if self.preview_length < 0:
            raise ValueError("preview_length cannot be negative")
