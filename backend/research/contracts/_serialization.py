"""Canonical JSON and immutable-value helpers for research contracts."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any


def freeze_json(value: Any, *, path: str = "$") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain only finite numbers")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string object key")
            frozen[key] = freeze_json(item, path=f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (tuple, list)):
        return tuple(
            freeze_json(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    raise ValueError(
        f"{path} contains non-JSON-compatible value {type(value).__name__}"
    )


def to_json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        require_aware(value, "timestamp")
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_json_value(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        to_json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


class SerializableContract:
    """Mixin providing deterministic JSON serialization and hashing."""

    def to_dict(self) -> dict[str, Any]:
        result = to_json_value(self)
        if not isinstance(result, dict):
            raise TypeError("SerializableContract must serialize to an object")
        return result

    def canonical_json(self) -> str:
        return canonical_json(self)

    def canonical_hash(self) -> str:
        return canonical_hash(self)

