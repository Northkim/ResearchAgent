"""Small standard-library helpers shared by domain entities."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any

from ..exceptions import DomainValidationError


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def require_non_empty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise DomainValidationError(f"{field_name} must be a non-empty string")


def require_aware(timestamp: datetime, field_name: str) -> None:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise DomainValidationError(f"{field_name} must be timezone-aware")


def freeze_value(value: Any) -> Any:
    """Recursively copy mutable containers into read-only equivalents."""

    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze_value(item) for item in value)
    return value


def thaw_value(value: Any) -> Any:
    """Convert frozen domain containers into JSON-compatible mutable values."""

    if isinstance(value, Mapping):
        return {str(key): thaw_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [thaw_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(thaw_value(item) for item in value)
    return value
