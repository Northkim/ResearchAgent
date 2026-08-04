"""Value-free structural diagnostics for the experimental OpenAlex adapter."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import OPENALEX_ADAPTER_ID, canonical_hash, canonical_json

STRUCTURAL_DIAGNOSTIC_CONTRACT_VERSION = "reagent.openalex-structural-diagnostic/v0.1"
STRUCTURAL_SHAPE_DESCRIPTOR_VERSION = "reagent.openalex-structural-shape/v0.1"
STRUCTURAL_DIAGNOSTIC_EVENT_NAME = "openalex_structural_diagnostic"
STRUCTURAL_DIAGNOSTIC_FEATURE_FLAG = (
    "REAGENT_EXPERIMENTAL_OPENALEX_STRUCTURAL_DIAGNOSTICS_ENABLED"
)

_CHECKSUM = re.compile(r"sha256:[0-9a-f]{64}\Z")
_OPERATION_ID = re.compile(r"proxyop-v1-[0-9a-f]{64}\Z")
_MAX_STRUCTURAL_COUNT = 100_000
_MISSING = object()
_UNAVAILABLE = object()


class FailureStage(str, Enum):
    RESPONSE_BYTES = "RESPONSE_BYTES"
    JSON_ROOT = "JSON_ROOT"
    COST_USAGE = "COST_USAGE"
    RESULTS_ARRAY = "RESULTS_ARRAY"
    WORK_NORMALIZATION = "WORK_NORMALIZATION"
    AUTHORSHIP_NORMALIZATION = "AUTHORSHIP_NORMALIZATION"
    ABSTRACT_RECONSTRUCTION = "ABSTRACT_RECONSTRUCTION"
    PAPER_MODEL_VALIDATION = "PAPER_MODEL_VALIDATION"
    NORMALIZED_SERIALIZATION = "NORMALIZED_SERIALIZATION"
    SERVICE_SAFETY = "SERVICE_SAFETY"
    RESULT_SIZE = "RESULT_SIZE"
    UNCLASSIFIED_INTERNAL = "UNCLASSIFIED_INTERNAL"


class ObservedKind(str, Enum):
    MISSING = "MISSING"
    NULL = "NULL"
    WRONG_TYPE = "WRONG_TYPE"
    EMPTY = "EMPTY"
    INVALID_VALUE = "INVALID_VALUE"
    INVALID_POSITION = "INVALID_POSITION"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    CONTROL_CHARACTER = "CONTROL_CHARACTER"
    SENSITIVE_CONTENT = "SENSITIVE_CONTENT"
    MODEL_VALIDATION = "MODEL_VALIDATION"
    UNKNOWN = "UNKNOWN"


class ValidatorCode(str, Enum):
    RESPONSE_BYTES_LIMIT = "RESPONSE_BYTES_LIMIT"
    HTTP_STATUS_REJECTED = "HTTP_STATUS_REJECTED"
    JSON_DECODE = "JSON_DECODE"
    JSON_ROOT_OBJECT = "JSON_ROOT_OBJECT"
    META_OBJECT = "META_OBJECT"
    COST_REQUIRED = "COST_REQUIRED"
    COST_EXACT_DECIMAL = "COST_EXACT_DECIMAL"
    RATE_HEADERS_REQUIRED = "RATE_HEADERS_REQUIRED"
    RATE_HEADERS_BOUNDED = "RATE_HEADERS_BOUNDED"
    RATE_HEADERS_CONSISTENT = "RATE_HEADERS_CONSISTENT"
    COST_QUALIFIED_PRICE = "COST_QUALIFIED_PRICE"
    RESULTS_ARRAY_REQUIRED = "RESULTS_ARRAY_REQUIRED"
    RESULT_COUNT_LIMIT = "RESULT_COUNT_LIMIT"
    WORK_OBJECT_REQUIRED = "WORK_OBJECT_REQUIRED"
    WORK_ID_REQUIRED_STRING = "WORK_ID_REQUIRED_STRING"
    WORK_ID_FORMAT = "WORK_ID_FORMAT"
    DOI_STRING_OR_NULL = "DOI_STRING_OR_NULL"
    DISPLAY_NAME_REQUIRED_TEXT = "DISPLAY_NAME_REQUIRED_TEXT"
    DISPLAY_NAME_LENGTH = "DISPLAY_NAME_LENGTH"
    DISPLAY_NAME_CONTROL = "DISPLAY_NAME_CONTROL"
    AUTHORSHIPS_ARRAY_REQUIRED = "AUTHORSHIPS_ARRAY_REQUIRED"
    AUTHORSHIPS_COUNT_LIMIT = "AUTHORSHIPS_COUNT_LIMIT"
    AUTHORSHIP_OBJECT_REQUIRED = "AUTHORSHIP_OBJECT_REQUIRED"
    AUTHOR_OBJECT_REQUIRED = "AUTHOR_OBJECT_REQUIRED"
    AUTHOR_DISPLAY_NAME_REQUIRED_TEXT = "AUTHOR_DISPLAY_NAME_REQUIRED_TEXT"
    AUTHOR_DISPLAY_NAME_LENGTH = "AUTHOR_DISPLAY_NAME_LENGTH"
    AUTHOR_DISPLAY_NAME_CONTROL = "AUTHOR_DISPLAY_NAME_CONTROL"
    AUTHOR_ID_FORMAT = "AUTHOR_ID_FORMAT"
    AUTHOR_ORCID_REQUIRED_TEXT = "AUTHOR_ORCID_REQUIRED_TEXT"
    AUTHOR_ORCID_LENGTH = "AUTHOR_ORCID_LENGTH"
    AUTHOR_ORCID_CONTROL = "AUTHOR_ORCID_CONTROL"
    PAPER_AUTHOR_MODEL = "PAPER_AUTHOR_MODEL"
    ABSTRACT_OBJECT_OR_NULL = "ABSTRACT_OBJECT_OR_NULL"
    ABSTRACT_TOKEN_COUNT_LIMIT = "ABSTRACT_TOKEN_COUNT_LIMIT"
    ABSTRACT_TOKEN_REQUIRED_TEXT = "ABSTRACT_TOKEN_REQUIRED_TEXT"
    ABSTRACT_TOKEN_LENGTH = "ABSTRACT_TOKEN_LENGTH"
    ABSTRACT_TOKEN_CONTROL = "ABSTRACT_TOKEN_CONTROL"
    ABSTRACT_POSITIONS_ARRAY = "ABSTRACT_POSITIONS_ARRAY"
    ABSTRACT_POSITIONS_COUNT_LIMIT = "ABSTRACT_POSITIONS_COUNT_LIMIT"
    ABSTRACT_POSITION_INTEGER = "ABSTRACT_POSITION_INTEGER"
    ABSTRACT_POSITION_RANGE = "ABSTRACT_POSITION_RANGE"
    ABSTRACT_POSITION_UNIQUE = "ABSTRACT_POSITION_UNIQUE"
    ABSTRACT_POSITIONS_CONTIGUOUS = "ABSTRACT_POSITIONS_CONTIGUOUS"
    ABSTRACT_RESULT_SIZE = "ABSTRACT_RESULT_SIZE"
    PUBLICATION_YEAR_INTEGER = "PUBLICATION_YEAR_INTEGER"
    PUBLICATION_YEAR_RANGE = "PUBLICATION_YEAR_RANGE"
    PRIMARY_LOCATION_OBJECT_OR_NULL = "PRIMARY_LOCATION_OBJECT_OR_NULL"
    PRIMARY_SOURCE_OBJECT_OR_NULL = "PRIMARY_SOURCE_OBJECT_OR_NULL"
    VENUE_REQUIRED_TEXT = "VENUE_REQUIRED_TEXT"
    VENUE_LENGTH = "VENUE_LENGTH"
    VENUE_CONTROL = "VENUE_CONTROL"
    LANGUAGE_REQUIRED_TEXT = "LANGUAGE_REQUIRED_TEXT"
    LANGUAGE_LENGTH = "LANGUAGE_LENGTH"
    LANGUAGE_CONTROL = "LANGUAGE_CONTROL"
    PAPER_RECORD_MODEL = "PAPER_RECORD_MODEL"
    NORMALIZED_CANONICAL_SERIALIZATION = "NORMALIZED_CANONICAL_SERIALIZATION"
    NORMALIZED_RESULT_SIZE = "NORMALIZED_RESULT_SIZE"
    SERVICE_SENSITIVE_CONTENT = "SERVICE_SENSITIVE_CONTENT"
    UNCLASSIFIED_INTERNAL = "UNCLASSIFIED_INTERNAL"


APPROVED_JSON_PATHS = frozenset(
    {
        "/",
        "/meta",
        "/meta/cost_usd",
        "/results",
        "/results/*",
        "/results/*/id",
        "/results/*/doi",
        "/results/*/display_name",
        "/results/*/authorships",
        "/results/*/authorships/*",
        "/results/*/authorships/*/author",
        "/results/*/authorships/*/author/id",
        "/results/*/authorships/*/author/display_name",
        "/results/*/authorships/*/author/orcid",
        "/results/*/abstract_inverted_index",
        "/results/*/publication_year",
        "/results/*/primary_location",
        "/results/*/primary_location/source",
        "/results/*/primary_location/source/display_name",
        "/results/*/language",
        "/normalized_results",
        "/service_safety",
    }
)


def _bounded_count(value: Any) -> int | None:
    if not isinstance(value, (list, dict)):
        return None
    return min(len(value), _MAX_STRUCTURAL_COUNT)


def _json_kind(value: Any) -> str:
    if value is _MISSING:
        return "MISSING"
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, float):
        return "NUMBER"
    from decimal import Decimal

    if isinstance(value, Decimal):
        return "NUMBER"
    if isinstance(value, str):
        return "STRING"
    if isinstance(value, list):
        return "ARRAY"
    if isinstance(value, dict):
        return "OBJECT"
    return "OTHER"


def observed_kind(value: Any, *, missing: bool = False) -> ObservedKind:
    if missing:
        return ObservedKind.MISSING
    if value is None:
        return ObservedKind.NULL
    return ObservedKind.WRONG_TYPE


def _entry(
    path: str,
    value: Any,
    *,
    record_index: int | None = None,
    nested_element_index: int | None = None,
    approved_object_keys: tuple[str, ...] | None = None,
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    count = _bounded_count(value)
    if isinstance(value, dict) and approved_object_keys is not None:
        count = sum(key in value for key in approved_object_keys)
    return {
        "approved_json_path": path,
        "bounded_count": count,
        "children": children,
        "json_kind": _json_kind(value),
        "nested_element_index": nested_element_index,
        "record_index": record_index,
    }


def _field(container: dict[str, Any], key: str) -> Any:
    return container[key] if key in container else _MISSING


def provider_structural_shape_checksum(value: Any) -> str:
    """Hash only selected-field presence, kinds, and bounded container counts."""

    entries: list[dict[str, Any]] = [
        _entry("/", value, approved_object_keys=("meta", "results"))
    ]
    if not isinstance(value, dict):
        return canonical_hash(
            {"descriptor_version": STRUCTURAL_SHAPE_DESCRIPTOR_VERSION, "entries": entries}
        )

    meta = _field(value, "meta")
    entries.append(_entry("/meta", meta, approved_object_keys=("cost_usd",)))
    if isinstance(meta, dict):
        entries.append(_entry("/meta/cost_usd", _field(meta, "cost_usd")))

    results = _field(value, "results")
    entries.append(_entry("/results", results))
    if isinstance(results, list):
        for record_index, work in enumerate(results):
            entries.append(
                _entry(
                    "/results/*",
                    work,
                    record_index=record_index,
                    approved_object_keys=(
                        "id",
                        "doi",
                        "display_name",
                        "authorships",
                        "abstract_inverted_index",
                        "publication_year",
                        "primary_location",
                        "language",
                    ),
                )
            )
            if not isinstance(work, dict):
                continue
            for key, path in (
                ("id", "/results/*/id"),
                ("doi", "/results/*/doi"),
                ("display_name", "/results/*/display_name"),
                ("authorships", "/results/*/authorships"),
                ("publication_year", "/results/*/publication_year"),
                ("primary_location", "/results/*/primary_location"),
                ("language", "/results/*/language"),
            ):
                entries.append(_entry(path, _field(work, key), record_index=record_index))

            authorships = _field(work, "authorships")
            if isinstance(authorships, list):
                for nested_index, authorship in enumerate(authorships):
                    entries.append(
                        _entry(
                            "/results/*/authorships/*",
                            authorship,
                            record_index=record_index,
                            nested_element_index=nested_index,
                            approved_object_keys=("author",),
                        )
                    )
                    if not isinstance(authorship, dict):
                        continue
                    author = _field(authorship, "author")
                    entries.append(
                        _entry(
                            "/results/*/authorships/*/author",
                            author,
                            record_index=record_index,
                            nested_element_index=nested_index,
                            approved_object_keys=("id", "display_name", "orcid"),
                        )
                    )
                    if isinstance(author, dict):
                        for key, path in (
                            ("id", "/results/*/authorships/*/author/id"),
                            (
                                "display_name",
                                "/results/*/authorships/*/author/display_name",
                            ),
                            ("orcid", "/results/*/authorships/*/author/orcid"),
                        ):
                            entries.append(
                                _entry(
                                    path,
                                    _field(author, key),
                                    record_index=record_index,
                                    nested_element_index=nested_index,
                                )
                            )

            abstract = _field(work, "abstract_inverted_index")
            abstract_children: list[dict[str, Any]] | None = None
            if isinstance(abstract, dict):
                abstract_children = []
                for positions in abstract.values():
                    child = {
                        "bounded_count": _bounded_count(positions),
                        "element_kinds": (
                            sorted(_json_kind(item) for item in positions)
                            if isinstance(positions, list)
                            else None
                        ),
                        "json_kind": _json_kind(positions),
                    }
                    abstract_children.append(child)
                abstract_children.sort(key=canonical_json)
            entries.append(
                _entry(
                    "/results/*/abstract_inverted_index",
                    abstract,
                    record_index=record_index,
                    children=abstract_children,
                )
            )

            location = _field(work, "primary_location")
            if isinstance(location, dict):
                source = _field(location, "source")
                entries.append(
                    _entry(
                        "/results/*/primary_location/source",
                        source,
                        record_index=record_index,
                        approved_object_keys=("display_name",),
                    )
                )
                if isinstance(source, dict):
                    entries.append(
                        _entry(
                            "/results/*/primary_location/source/display_name",
                            _field(source, "display_name"),
                            record_index=record_index,
                        )
                    )

    return canonical_hash(
        {"descriptor_version": STRUCTURAL_SHAPE_DESCRIPTOR_VERSION, "entries": entries}
    )


_UNAVAILABLE_SHAPE_CHECKSUM = canonical_hash(
    {
        "descriptor_version": STRUCTURAL_SHAPE_DESCRIPTOR_VERSION,
        "entries": [{"json_kind": "UNAVAILABLE"}],
    }
)


@dataclass(frozen=True, slots=True)
class OpenAlexStructuralFailure:
    failure_stage: FailureStage
    approved_json_path: str
    observed_kind: ObservedKind
    validator_code: ValidatorCode
    normalized_records_before_failure: int
    structural_shape_checksum: str
    record_index: int | None = None
    nested_element_index: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.failure_stage, FailureStage):
            object.__setattr__(self, "failure_stage", FailureStage(self.failure_stage))
        if not isinstance(self.observed_kind, ObservedKind):
            object.__setattr__(self, "observed_kind", ObservedKind(self.observed_kind))
        if not isinstance(self.validator_code, ValidatorCode):
            object.__setattr__(self, "validator_code", ValidatorCode(self.validator_code))
        if self.approved_json_path not in APPROVED_JSON_PATHS:
            raise ValueError("OpenAlex diagnostic path is not approved")
        for value, field in (
            (self.record_index, "record_index"),
            (self.nested_element_index, "nested_element_index"),
        ):
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError(f"{field} must be a non-negative integer or null")
        if (
            isinstance(self.normalized_records_before_failure, bool)
            or not isinstance(self.normalized_records_before_failure, int)
            or self.normalized_records_before_failure < 0
        ):
            raise ValueError("normalized_records_before_failure must be non-negative")
        if not _CHECKSUM.fullmatch(self.structural_shape_checksum):
            raise ValueError("structural_shape_checksum must be canonical SHA-256")


def structural_failure(
    *,
    failure_stage: FailureStage,
    approved_json_path: str,
    observed_kind: ObservedKind,
    validator_code: ValidatorCode,
    normalized_records_before_failure: int = 0,
    record_index: int | None = None,
    nested_element_index: int | None = None,
    provider_value: Any = _UNAVAILABLE,
    provider_shape_checksum: str | None = None,
) -> OpenAlexStructuralFailure:
    if provider_shape_checksum is None:
        provider_shape_checksum = (
            _UNAVAILABLE_SHAPE_CHECKSUM
            if provider_value is _UNAVAILABLE
            else provider_structural_shape_checksum(provider_value)
        )
    if not _CHECKSUM.fullmatch(provider_shape_checksum):
        raise ValueError("provider structural shape checksum is invalid")
    checksum = canonical_hash(
        {
            "approved_json_path": approved_json_path,
            "failure_stage": failure_stage,
            "nested_element_index": nested_element_index,
            "normalized_records_before_failure": normalized_records_before_failure,
            "observed_kind": observed_kind,
            "provider_structural_shape_checksum": provider_shape_checksum,
            "record_index": record_index,
            "validator_code": validator_code,
        }
    )
    return OpenAlexStructuralFailure(
        failure_stage=failure_stage,
        approved_json_path=approved_json_path,
        observed_kind=observed_kind,
        validator_code=validator_code,
        normalized_records_before_failure=normalized_records_before_failure,
        structural_shape_checksum=checksum,
        record_index=record_index,
        nested_element_index=nested_element_index,
    )


@dataclass(frozen=True, slots=True)
class OpenAlexStructuralDiagnostic:
    adapter_id: str
    adapter_version: str
    operation_id: str
    request_content_checksum: str
    failure_stage: FailureStage
    approved_json_path: str
    observed_kind: ObservedKind
    validator_code: ValidatorCode
    normalized_records_before_failure: int
    structural_shape_checksum: str
    record_index: int | None = None
    nested_element_index: int | None = None
    diagnostic_contract_version: str = STRUCTURAL_DIAGNOSTIC_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.failure_stage, FailureStage):
            object.__setattr__(self, "failure_stage", FailureStage(self.failure_stage))
        if not isinstance(self.observed_kind, ObservedKind):
            object.__setattr__(self, "observed_kind", ObservedKind(self.observed_kind))
        if not isinstance(self.validator_code, ValidatorCode):
            object.__setattr__(self, "validator_code", ValidatorCode(self.validator_code))
        if self.diagnostic_contract_version != STRUCTURAL_DIAGNOSTIC_CONTRACT_VERSION:
            raise ValueError("Unsupported OpenAlex structural diagnostic contract")
        if self.adapter_id != OPENALEX_ADAPTER_ID:
            raise ValueError("Structural diagnostic adapter is not OpenAlex")
        if not isinstance(self.adapter_version, str) or not self.adapter_version:
            raise ValueError("adapter_version must be non-empty")
        if not isinstance(self.operation_id, str) or not _OPERATION_ID.fullmatch(self.operation_id):
            raise ValueError("operation_id must be a Proxy operation ID")
        if not _CHECKSUM.fullmatch(self.request_content_checksum):
            raise ValueError("request_content_checksum must be canonical SHA-256")
        OpenAlexStructuralFailure(
            failure_stage=self.failure_stage,
            approved_json_path=self.approved_json_path,
            observed_kind=self.observed_kind,
            validator_code=self.validator_code,
            normalized_records_before_failure=self.normalized_records_before_failure,
            structural_shape_checksum=self.structural_shape_checksum,
            record_index=self.record_index,
            nested_element_index=self.nested_element_index,
        )

    @classmethod
    def from_failure(
        cls,
        failure: OpenAlexStructuralFailure,
        *,
        adapter_version: str,
        operation_id: str,
        request_content_checksum: str,
    ) -> OpenAlexStructuralDiagnostic:
        return cls(
            adapter_id=OPENALEX_ADAPTER_ID,
            adapter_version=adapter_version,
            operation_id=operation_id,
            request_content_checksum=request_content_checksum,
            failure_stage=failure.failure_stage,
            approved_json_path=failure.approved_json_path,
            record_index=failure.record_index,
            nested_element_index=failure.nested_element_index,
            observed_kind=failure.observed_kind,
            validator_code=failure.validator_code,
            normalized_records_before_failure=failure.normalized_records_before_failure,
            structural_shape_checksum=failure.structural_shape_checksum,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagnostic_contract_version": self.diagnostic_contract_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "operation_id": self.operation_id,
            "request_content_checksum": self.request_content_checksum,
            "failure_stage": self.failure_stage.value,
            "approved_json_path": self.approved_json_path,
            "record_index": self.record_index,
            "nested_element_index": self.nested_element_index,
            "observed_kind": self.observed_kind.value,
            "validator_code": self.validator_code.value,
            "normalized_records_before_failure": self.normalized_records_before_failure,
            "structural_shape_checksum": self.structural_shape_checksum,
        }


class OpenAlexStructuralDiagnosticEmitter:
    """Emit one canonical JSON event only when the server-side flag is enabled."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        logger: logging.Logger | None = None,
    ) -> None:
        self.enabled = enabled
        self.logger = logger or logging.getLogger("reagent.openalex_structural_diagnostic")

    def emit(self, diagnostic: OpenAlexStructuralDiagnostic) -> None:
        if not self.enabled:
            return
        payload = {"event": STRUCTURAL_DIAGNOSTIC_EVENT_NAME, **diagnostic.to_dict()}
        try:
            self.logger.warning(
                canonical_json(payload),
                extra={
                    "event_name": STRUCTURAL_DIAGNOSTIC_EVENT_NAME,
                    "diagnostic_contract_version": diagnostic.diagnostic_contract_version,
                },
            )
        except Exception:
            # Observability must never change the already-durable public outcome.
            return
