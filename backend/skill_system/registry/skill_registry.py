"""Explicit allow-listed registry populated at application composition time."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from backend.skill_system.exceptions import (
    DuplicateSkillRegistrationError,
    SkillNotFoundError,
)
from backend.skill_system.models import (
    SkillDefinition,
    SkillExecutionContext,
    SkillImplementation,
    SkillReference,
)


@dataclass(frozen=True, slots=True)
class RegisteredSkill:
    definition: SkillDefinition
    implementation: SkillImplementation

    def metadata(self) -> SkillDefinition:
        return self.definition

    async def execute(
        self,
        inputs: Mapping[str, Any],
        context: SkillExecutionContext,
    ) -> Mapping[str, Any]:
        return await self.implementation(inputs, context)


class SkillRegistry:
    """Deterministic exact-version registry with no dynamic code discovery."""

    def __init__(self) -> None:
        self._skills: dict[tuple[str, str], RegisteredSkill] = {}

    def register(
        self,
        definition: SkillDefinition,
        implementation: SkillImplementation,
    ) -> None:
        key = (definition.name, definition.version)
        if key in self._skills:
            raise DuplicateSkillRegistrationError(
                f"Skill {definition.reference} is already registered"
            )
        self._skills[key] = RegisteredSkill(
            definition=definition,
            implementation=implementation,
        )

    def resolve(self, reference: SkillReference) -> RegisteredSkill:
        try:
            return self._skills[(reference.name, reference.version)]
        except KeyError as exc:
            raise SkillNotFoundError(f"Skill {reference} is not registered") from exc

    def get_definition(self, name: str, version: str) -> SkillDefinition:
        return self.resolve(SkillReference(name=name, version=version)).definition

    def list_definitions(self) -> tuple[SkillDefinition, ...]:
        return tuple(
            self._skills[key].definition
            for key in sorted(self._skills)
        )

    def __len__(self) -> int:
        return len(self._skills)
