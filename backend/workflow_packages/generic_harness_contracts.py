"""Exact contracts for the supported Generic Agent Harness Experiment path.

These contracts are intentionally separate from reviewed ExperimentCapability
publication.  They describe system-owned implementation/evaluation evidence and
never make a User Skill or Harness conversation scientific authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from datetime import datetime
from enum import Enum

from .generic_experiment_contracts import ContractRef
from .security import require_relative_path, require_sha256
from .serialization import SerializableContract, canonical_hash, to_json_value

GENERIC_HARNESS_PATH_SCHEMA = "reagent.generic-agent-harness-path/v0.1"
GENERIC_HARNESS_SPEC_SCHEMA = "reagent.generic-harness-implementation-spec/v0.1"
GENERIC_HARNESS_VALIDATION_SCHEMA = "reagent.generic-harness-validation/v0.1"
GENERIC_HARNESS_EXECUTION_SCHEMA = "reagent.generic-harness-execution-manifest/v0.1"
GENERIC_HARNESS_EVALUATION_SCHEMA = "reagent.generic-harness-evaluation/v0.1"
GENERIC_HARNESS_CLASSIFICATION = "GENERIC_AGENT_HARNESS"

_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+\-]{0,199}$")
_UNIT_ID = re.compile(r"^unit-[a-z0-9][a-z0-9._-]{0,119}$")
_MEDIA_TYPE = re.compile(r"^[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*$")


class GenericHarnessContractError(ValueError):
    """The generic Harness contract or its exact lineage is invalid."""


def _hash_without(value: SerializableContract, name: str) -> str:
    return canonical_hash({
        item.name: to_json_value(getattr(value, item.name))
        for item in fields(value) if item.name != name
    })


def _text(value: str, name: str, maximum: int = 1_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise GenericHarnessContractError(f"{name} must be bounded non-empty text")
    return value


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or _IDENTITY.fullmatch(value) is None:
        raise GenericHarnessContractError(f"{name} is invalid")
    return value


@dataclass(frozen=True, slots=True)
class GenericHarnessPath(SerializableContract):
    """Truthful fallback identity; not a reviewed Capability or User Skill."""

    implementation_contract: ContractRef
    evaluation_contract: ContractRef
    execution_boundary: str = "EXISTING_BOUNDED_LOCAL_RUNNER"
    classification: str = field(default=GENERIC_HARNESS_CLASSIFICATION, init=False)
    reviewed_capability: bool = field(default=False, init=False)
    user_skill_authority: bool = field(default=False, init=False)
    schema: str = field(default=GENERIC_HARNESS_PATH_SCHEMA, init=False)
    path_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if self.execution_boundary != "EXISTING_BOUNDED_LOCAL_RUNNER":
            raise GenericHarnessContractError("Generic Harness execution boundary is invalid")
        object.__setattr__(self, "path_checksum", _hash_without(self, "path_checksum"))


@dataclass(frozen=True, slots=True)
class HarnessDependency(SerializableContract):
    name: str
    version_constraint: str

    def __post_init__(self) -> None:
        _identity(self.name, "dependency name")
        _text(self.version_constraint, "dependency version constraint", 120)


@dataclass(frozen=True, slots=True)
class HarnessExpectedOutput(SerializableContract):
    name: str
    relative_path: str
    media_type: str

    def __post_init__(self) -> None:
        _identity(self.name, "expected output name")
        require_relative_path(self.relative_path, "expected output path")
        if _MEDIA_TYPE.fullmatch(self.media_type) is None:
            raise GenericHarnessContractError("expected output media type is invalid")


@dataclass(frozen=True, slots=True)
class HarnessExecutionUnit(SerializableContract):
    unit_id: str
    arguments: tuple[str, ...]
    expected_output_names: tuple[str, ...]
    scientific_role: str

    def __post_init__(self) -> None:
        if _UNIT_ID.fullmatch(self.unit_id) is None:
            raise GenericHarnessContractError("execution unit identity is invalid")
        if not self.arguments or len(self.arguments) > 40:
            raise GenericHarnessContractError("execution unit arguments are invalid")
        for value in self.arguments:
            _text(value, "execution unit argument", 300)
        if not self.expected_output_names or len(self.expected_output_names) > 30:
            raise GenericHarnessContractError("execution unit outputs are invalid")
        for value in self.expected_output_names:
            _identity(value, "execution unit output name")
        if len(set(self.expected_output_names)) != len(self.expected_output_names):
            raise GenericHarnessContractError("execution unit outputs must be unique")
        _text(self.scientific_role, "execution unit scientific role", 500)


@dataclass(frozen=True, slots=True)
class GenericHarnessImplementationSpec(SerializableContract):
    objective_checksum: str
    methodology_checksum: str
    entrypoint_relative_path: str
    runtime_family: str
    runtime_version_constraint: str
    dependencies: tuple[HarnessDependency, ...]
    required_runtime_capabilities: tuple[str, ...]
    expected_outputs: tuple[HarnessExpectedOutput, ...]
    execution_units: tuple[HarnessExecutionUnit, ...]
    validation_commands: tuple[tuple[str, ...], ...]
    compute_limits: tuple[tuple[str, str], ...]
    network_policy: str
    implementation_summary: tuple[str, ...]
    schema: str = field(default=GENERIC_HARNESS_SPEC_SCHEMA, init=False)
    specification_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        require_sha256(self.objective_checksum, "objective_checksum")
        require_sha256(self.methodology_checksum, "methodology_checksum")
        require_relative_path(self.entrypoint_relative_path, "implementation entrypoint")
        _identity(self.runtime_family, "runtime family")
        _text(self.runtime_version_constraint, "runtime version constraint", 120)
        if len(self.dependencies) > 40 or len({item.name for item in self.dependencies}) != len(self.dependencies):
            raise GenericHarnessContractError("dependencies must be bounded and unique")
        if len(self.required_runtime_capabilities) > 40:
            raise GenericHarnessContractError("runtime capabilities exceed the bound")
        for value in self.required_runtime_capabilities:
            _identity(value, "runtime capability")
        if not self.expected_outputs or len(self.expected_outputs) > 50:
            raise GenericHarnessContractError("expected outputs are invalid")
        output_names = {item.name for item in self.expected_outputs}
        if len(output_names) != len(self.expected_outputs):
            raise GenericHarnessContractError("expected output names must be unique")
        if not self.execution_units or len(self.execution_units) > 1_000:
            raise GenericHarnessContractError("execution units are invalid")
        if len({item.unit_id for item in self.execution_units}) != len(self.execution_units):
            raise GenericHarnessContractError("execution unit identities must be unique")
        if any(not set(item.expected_output_names).issubset(output_names) for item in self.execution_units):
            raise GenericHarnessContractError("execution unit references an undeclared output")
        declared_unit_outputs = tuple(
            name for unit in self.execution_units for name in unit.expected_output_names
        )
        if len(declared_unit_outputs) != len(set(declared_unit_outputs)) or set(declared_unit_outputs) != output_names:
            raise GenericHarnessContractError(
                "every expected output must belong to exactly one execution unit"
            )
        if not self.validation_commands or len(self.validation_commands) > 20:
            raise GenericHarnessContractError("validation commands are invalid")
        for command in self.validation_commands:
            if not command or len(command) > 40:
                raise GenericHarnessContractError("validation command is invalid")
            for value in command:
                _text(value, "validation command argument", 300)
        if len(self.compute_limits) > 20:
            raise GenericHarnessContractError("compute limits exceed the bound")
        for name, value in self.compute_limits:
            _identity(name, "compute limit name")
            _text(value, "compute limit value", 120)
        if self.network_policy != "DISABLED":
            raise GenericHarnessContractError("R3 Generic Harness network must be disabled")
        if not self.implementation_summary or len(self.implementation_summary) > 20:
            raise GenericHarnessContractError("implementation summary is invalid")
        for value in self.implementation_summary:
            _text(value, "implementation summary", 500)
        object.__setattr__(self, "specification_checksum", _hash_without(self, "specification_checksum"))


@dataclass(frozen=True, slots=True)
class GenericHarnessValidationReceipt(SerializableContract):
    specification_checksum: str
    methodology_checksum: str
    package_tree_checksum: str
    entrypoint_checksum: str
    validation_command_checksums: tuple[str, ...]
    package_safe: bool
    methodology_conformant: bool
    validated_at: str
    schema: str = field(default=GENERIC_HARNESS_VALIDATION_SCHEMA, init=False)
    validation_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in (
            "specification_checksum", "methodology_checksum", "package_tree_checksum",
            "entrypoint_checksum",
        ):
            require_sha256(getattr(self, name), name)
        for value in self.validation_command_checksums:
            require_sha256(value, "validation command checksum")
        if not self.validation_command_checksums or not self.package_safe or not self.methodology_conformant:
            raise GenericHarnessContractError("only a safe conformant implementation may be validated")
        if not self.validated_at.endswith("Z"):
            raise GenericHarnessContractError("validated_at must be canonical UTC text")
        object.__setattr__(self, "validation_checksum", _hash_without(self, "validation_checksum"))


class HarnessUnitStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class HarnessUnitState(SerializableContract):
    unit_id: str
    status: HarnessUnitStatus
    output_checksums: tuple[tuple[str, str], ...] = ()
    attempt_count: int = 0
    started_at: str | None = None
    completed_at: str | None = None

    def __post_init__(self) -> None:
        if _UNIT_ID.fullmatch(self.unit_id) is None:
            raise GenericHarnessContractError("execution unit state identity is invalid")
        if not 0 <= self.attempt_count <= 1_000:
            raise GenericHarnessContractError("execution attempt count is invalid")
        if len({name for name, _ in self.output_checksums}) != len(self.output_checksums):
            raise GenericHarnessContractError("unit output identities must be unique")
        for name, checksum in self.output_checksums:
            _identity(name, "unit output name")
            require_sha256(checksum, "unit output checksum")
        if self.status is HarnessUnitStatus.COMPLETED and not self.output_checksums:
            raise GenericHarnessContractError("completed execution unit needs exact outputs")
        if self.status is HarnessUnitStatus.PENDING and self.output_checksums:
            raise GenericHarnessContractError("pending execution unit cannot claim outputs")
        times = (self.started_at, self.completed_at)
        if self.status is HarnessUnitStatus.COMPLETED:
            if any(value is None or not value.endswith("Z") for value in times):
                raise GenericHarnessContractError("completed execution unit needs exact times")
            try:
                started = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
                completed = datetime.fromisoformat(self.completed_at.replace("Z", "+00:00"))
            except ValueError as error:
                raise GenericHarnessContractError("execution unit times are invalid") from error
            if completed < started:
                raise GenericHarnessContractError("execution unit completed before it started")
        elif any(value is not None for value in times):
            raise GenericHarnessContractError("pending execution unit cannot claim times")


@dataclass(frozen=True, slots=True)
class GenericHarnessExecutionManifest(SerializableContract):
    specification_checksum: str
    validation_checksum: str
    run_approval_checksum: str
    units: tuple[HarnessUnitState, ...]
    schema: str = field(default=GENERIC_HARNESS_EXECUTION_SCHEMA, init=False)
    manifest_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("specification_checksum", "validation_checksum", "run_approval_checksum"):
            require_sha256(getattr(self, name), name)
        if not self.units or len(self.units) > 1_000:
            raise GenericHarnessContractError("execution manifest units are invalid")
        if len({item.unit_id for item in self.units}) != len(self.units):
            raise GenericHarnessContractError("execution manifest units must be unique")
        object.__setattr__(self, "manifest_checksum", _hash_without(self, "manifest_checksum"))

    @property
    def next_pending_unit(self) -> str | None:
        return next((item.unit_id for item in self.units if item.status is HarnessUnitStatus.PENDING), None)
