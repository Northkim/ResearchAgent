"""Canonical serialization helpers for experimental Workflow Packages."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any


def to_json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
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


class SerializableContract:
    def to_dict(self) -> dict[str, Any]:
        value = to_json_value(self)
        if not isinstance(value, dict):
            raise TypeError("contract must serialize to a JSON object")
        return value

    def canonical_json(self) -> str:
        return canonical_json(self)

    def canonical_hash(self) -> str:
        return canonical_hash(self)
