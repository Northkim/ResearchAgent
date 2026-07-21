"""Exact version reference used at the Workflow Engine boundary."""

from __future__ import annotations

from dataclasses import dataclass

from backend.skill_system.exceptions import InvalidSkillReferenceError


@dataclass(frozen=True, slots=True, order=True)
class SkillReference:
    name: str
    version: str

    def __post_init__(self) -> None:
        if not self.name or "@" in self.name:
            raise InvalidSkillReferenceError("Skill reference name is invalid")
        if not self.version or "@" in self.version:
            raise InvalidSkillReferenceError("Skill reference version is invalid")

    @classmethod
    def parse(cls, value: str) -> SkillReference:
        if not isinstance(value, str) or value.count("@") != 1:
            raise InvalidSkillReferenceError(
                f"Skill reference must be name@version, got {value!r}"
            )
        name, version = value.split("@", maxsplit=1)
        return cls(name=name, version=version)

    def __str__(self) -> str:
        return f"{self.name}@{self.version}"
