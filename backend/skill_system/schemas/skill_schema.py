"""A small immutable schema contract for deterministic Phase 3 skills."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal

from backend.skill_system._immutability import freeze_json
from backend.skill_system.exceptions import SkillValidationError

FieldKind = Literal["string", "integer", "number", "boolean", "array", "object"]
_FIELD_KINDS = {"string", "integer", "number", "boolean", "array", "object"}


@dataclass(frozen=True, slots=True)
class FieldSchema:
    """Schema for one field in a JSON-compatible object."""

    kind: FieldKind
    required: bool = True
    nullable: bool = False
    items: FieldSchema | None = None
    properties: Mapping[str, FieldSchema] = field(default_factory=dict)
    allow_extra: bool = False
    enum_values: tuple[Any, ...] = ()
    min_length: int | None = None
    max_length: int | None = None
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in _FIELD_KINDS:
            raise ValueError(f"Unsupported field schema kind: {self.kind}")
        object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))
        object.__setattr__(self, "enum_values", tuple(self.enum_values))
        if self.kind == "array" and self.items is None:
            raise ValueError("Array fields must define an items schema")
        if self.kind != "array" and self.items is not None:
            raise ValueError("Only array fields can define items")
        if self.kind != "object" and self.properties:
            raise ValueError("Only object fields can define properties")
        if self.kind != "object" and self.allow_extra:
            raise ValueError("Only object fields can allow extra properties")
        for name, schema in self.properties.items():
            if not isinstance(name, str) or not name:
                raise ValueError("Object property names must be non-empty strings")
            if not isinstance(schema, FieldSchema):
                raise ValueError("Object properties must contain FieldSchema values")
        if self.min_length is not None and self.min_length < 0:
            raise ValueError("min_length cannot be negative")
        if self.max_length is not None and self.max_length < 0:
            raise ValueError("max_length cannot be negative")
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            raise ValueError("min_length cannot exceed max_length")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum cannot exceed maximum")


@dataclass(frozen=True, slots=True)
class SkillSchema:
    """Immutable object schema used by a SkillDefinition."""

    fields: Mapping[str, FieldSchema] = field(default_factory=dict)
    allow_extra: bool = False

    def __post_init__(self) -> None:
        copied = dict(self.fields)
        for name, schema in copied.items():
            if not isinstance(name, str) or not name:
                raise ValueError("Schema field names must be non-empty strings")
            if not isinstance(schema, FieldSchema):
                raise ValueError("Schema fields must contain FieldSchema values")
        object.__setattr__(self, "fields", MappingProxyType(copied))

    def validate(self, value: Mapping[str, Any], *, label: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise SkillValidationError(label, "must be an object")
        validated = _validate_object(
            value,
            self.fields,
            allow_extra=self.allow_extra,
            path=label,
        )
        try:
            return freeze_json(validated, path=label)
        except ValueError as exc:
            raise SkillValidationError(label, str(exc)) from exc


def _validate_object(
    value: Mapping[str, Any],
    properties: Mapping[str, FieldSchema],
    *,
    allow_extra: bool,
    path: str,
) -> dict[str, Any]:
    for key in value:
        if not isinstance(key, str):
            raise SkillValidationError(path, "contains a non-string field name")

    missing = [name for name, schema in properties.items() if schema.required and name not in value]
    if missing:
        raise SkillValidationError(path, f"missing required field {missing[0]!r}")

    unknown = sorted(set(value) - set(properties))
    if unknown and not allow_extra:
        raise SkillValidationError(path, f"contains unknown field {unknown[0]!r}")

    result: dict[str, Any] = {}
    for name, item in value.items():
        schema = properties.get(name)
        if schema is None:
            result[name] = item
            continue
        result[name] = _validate_field(item, schema, path=f"{path}.{name}")
    return result


def _validate_field(value: Any, schema: FieldSchema, *, path: str) -> Any:
    if value is None:
        if schema.nullable:
            return None
        raise SkillValidationError(path, "cannot be null")

    if schema.enum_values and value not in schema.enum_values:
        raise SkillValidationError(path, f"must be one of {schema.enum_values!r}")

    if schema.kind == "string":
        if not isinstance(value, str):
            raise SkillValidationError(path, "must be a string")
        if schema.min_length is not None and len(value) < schema.min_length:
            raise SkillValidationError(
                path,
                f"must contain at least {schema.min_length} characters",
            )
        if schema.max_length is not None and len(value) > schema.max_length:
            raise SkillValidationError(path, f"must contain at most {schema.max_length} characters")
        return value
    if schema.kind == "boolean":
        if not isinstance(value, bool):
            raise SkillValidationError(path, "must be a boolean")
        return value
    if schema.kind == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise SkillValidationError(path, "must be an integer")
        _validate_number_bounds(value, schema, path)
        return value
    if schema.kind == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SkillValidationError(path, "must be a number")
        if isinstance(value, float) and not math.isfinite(value):
            raise SkillValidationError(path, "must be finite")
        _validate_number_bounds(value, schema, path)
        return value
    if schema.kind == "array":
        if not isinstance(value, (list, tuple)):
            raise SkillValidationError(path, "must be an array")
        assert schema.items is not None
        return [
            _validate_field(item, schema.items, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if schema.kind == "object":
        if not isinstance(value, Mapping):
            raise SkillValidationError(path, "must be an object")
        return _validate_object(
            value,
            schema.properties,
            allow_extra=schema.allow_extra,
            path=path,
        )
    raise AssertionError(f"Unhandled schema kind: {schema.kind}")


def _validate_number_bounds(value: int | float, schema: FieldSchema, path: str) -> None:
    if schema.minimum is not None and value < schema.minimum:
        raise SkillValidationError(path, f"must be at least {schema.minimum}")
    if schema.maximum is not None and value > schema.maximum:
        raise SkillValidationError(path, f"must be at most {schema.maximum}")
