"""Immutable, versioned skill definition models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.skill_system.exceptions import InvalidSkillDefinitionError
from backend.skill_system.schemas import SkillSchema

from .skill_reference import SkillReference

_SKILL_NAME = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_SIDE_EFFECTS = {"none", "read_external", "write_external", "execute_code"}


@dataclass(frozen=True, slots=True)
class SkillMetadata:
    """Execution-policy metadata fixed for one published skill version."""

    required_permissions: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    side_effect: str = "none"
    idempotency_supported: bool = True
    retry_safe: bool = True
    default_timeout_seconds: int = 30
    implementation_entrypoint: str = "builtin"
    api_version: str = "reagent.skill/v1alpha1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_permissions", tuple(self.required_permissions))
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        if self.side_effect not in _SIDE_EFFECTS:
            raise InvalidSkillDefinitionError(
                f"Unsupported side-effect classification: {self.side_effect}"
            )
        if self.default_timeout_seconds <= 0:
            raise InvalidSkillDefinitionError("default_timeout_seconds must be positive")
        if not self.implementation_entrypoint:
            raise InvalidSkillDefinitionError("implementation_entrypoint cannot be empty")
        if not self.api_version:
            raise InvalidSkillDefinitionError("api_version cannot be empty")


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """Published contract for one exact skill name and semantic version."""

    name: str
    version: str
    description: str
    input_schema: SkillSchema
    output_schema: SkillSchema
    metadata: SkillMetadata = field(default_factory=SkillMetadata)

    def __post_init__(self) -> None:
        if not _SKILL_NAME.fullmatch(self.name):
            raise InvalidSkillDefinitionError(
                "Skill name must be a lowercase dotted identifier using letters, "
                "digits, and underscores"
            )
        if not _SEMVER.fullmatch(self.version):
            raise InvalidSkillDefinitionError(
                f"Skill version must be semantic versioning, got {self.version!r}"
            )
        if not self.description.strip():
            raise InvalidSkillDefinitionError("Skill description cannot be empty")
        if not isinstance(self.input_schema, SkillSchema):
            raise InvalidSkillDefinitionError("input_schema must be a SkillSchema")
        if not isinstance(self.output_schema, SkillSchema):
            raise InvalidSkillDefinitionError("output_schema must be a SkillSchema")
        if not isinstance(self.metadata, SkillMetadata):
            raise InvalidSkillDefinitionError("metadata must be SkillMetadata")

    @property
    def reference(self) -> SkillReference:
        return SkillReference(name=self.name, version=self.version)
