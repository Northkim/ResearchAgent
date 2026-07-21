"""Pure, framework-independent Skill System contracts and runtime."""

from .exceptions import (
    DuplicateSkillRegistrationError,
    InvalidSkillDefinitionError,
    InvalidSkillReferenceError,
    SkillDecisionMismatchError,
    SkillExecutionFailure,
    SkillNotFoundError,
    SkillSystemError,
    SkillValidationError,
)
from .models import (
    Skill,
    SkillDefinition,
    SkillExecutionContext,
    SkillImplementation,
    SkillMetadata,
    SkillReference,
)
from .registry import RegisteredSkill, SkillRegistry
from .results import SkillError, SkillResult
from .runtime import SkillExecutor, register_fake_skills
from .schemas import FieldSchema, SkillSchema

__all__ = [
    "DuplicateSkillRegistrationError",
    "FieldSchema",
    "InvalidSkillDefinitionError",
    "InvalidSkillReferenceError",
    "RegisteredSkill",
    "SkillDecisionMismatchError",
    "Skill",
    "SkillDefinition",
    "SkillError",
    "SkillExecutionContext",
    "SkillExecutionFailure",
    "SkillExecutor",
    "SkillImplementation",
    "SkillMetadata",
    "SkillNotFoundError",
    "SkillReference",
    "SkillRegistry",
    "SkillResult",
    "SkillSchema",
    "SkillSystemError",
    "SkillValidationError",
    "register_fake_skills",
]
