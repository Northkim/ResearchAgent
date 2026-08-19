"""Workspace-owned state and environment discovery for Generic Experiments."""

from __future__ import annotations

import json
import os
import platform
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .generic_harness_contracts import (
    GenericHarnessContractError,
    GenericHarnessExecutionManifest,
    GenericHarnessImplementationSpec,
    GenericHarnessValidationReceipt,
    HarnessUnitState,
    HarnessUnitStatus,
)
from .generic_experiment_contracts import LocalRuntimeCandidate
from .serialization import canonical_hash, canonical_json, sha256_bytes

MANAGED_EXPERIMENT_ROOT = ".reagent/experiments"
MARKER_SCHEMA = "reagent.generic-harness-workspace/v0.1"
RUNTIME_DISCOVERY_SCHEMA = "reagent.generic-harness-runtime-discovery/v0.1"
_PROJECT_ID = re.compile(r"^project-[0-9a-f]{32}$")
_WORKFLOW_ID = re.compile(r"^wfi-[0-9a-f]{32}$")
_VERSION = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?")


class GenericHarnessWorkspaceError(RuntimeError):
    """Managed Generic Experiment state is unsafe or inconsistent."""


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (canonical_json(value) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise GenericHarnessWorkspaceError(f"{label} must be one regular managed file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GenericHarnessWorkspaceError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise GenericHarnessWorkspaceError(f"{label} must be a JSON object")
    return value


@dataclass(frozen=True, slots=True)
class RuntimeDiscovery:
    requirement_family: str
    version_constraint: str
    required_packages: tuple[str, ...]
    candidates: tuple[LocalRuntimeCandidate, ...]
    rejected: tuple[tuple[str, tuple[str, ...]], ...]
    installation_performed: bool = False
    schema: str = RUNTIME_DISCOVERY_SCHEMA

    def __post_init__(self) -> None:
        if self.installation_performed:
            raise GenericHarnessWorkspaceError("runtime discovery must never install dependencies")


class GenericHarnessWorkspace:
    """Own only exact ReAgent-managed state outside immutable Capsules."""

    def __init__(self, root: Path, project_id: str, workflow_instance_id: str) -> None:
        self.workspace_root = root.resolve()
        if _PROJECT_ID.fullmatch(project_id) is None or _WORKFLOW_ID.fullmatch(workflow_instance_id) is None:
            raise GenericHarnessWorkspaceError("managed Experiment identity is invalid")
        self.project_id = project_id
        self.workflow_instance_id = workflow_instance_id
        self.root = self.workspace_root / MANAGED_EXPERIMENT_ROOT / workflow_instance_id
        self.marker_path = self.root / "owner.json"

    def initialize(self) -> Path:
        if self.root.exists() and (self.root.is_symlink() or not self.root.is_dir()):
            raise GenericHarnessWorkspaceError("managed Experiment root is unsafe")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker = {
            "schema": MARKER_SCHEMA,
            "project_id": self.project_id,
            "workflow_instance_id": self.workflow_instance_id,
            "managed_root": f"{MANAGED_EXPERIMENT_ROOT}/{self.workflow_instance_id}",
        }
        if self.marker_path.exists():
            if _object(self.marker_path, "managed Experiment marker") != marker:
                raise GenericHarnessWorkspaceError("managed Experiment ownership conflicts")
        else:
            _atomic_json(self.marker_path, marker)
        for name in ("contracts", "implementation", "validated-package", "environment", "execution", "outputs", "evaluation", "sync"):
            path = self.root / name
            path.mkdir(exist_ok=True, mode=0o700)
            if path.is_symlink() or not path.is_dir():
                raise GenericHarnessWorkspaceError("managed Experiment subtree is unsafe")
        return self.root

    def verify_owner(self) -> None:
        expected = {
            "schema": MARKER_SCHEMA,
            "project_id": self.project_id,
            "workflow_instance_id": self.workflow_instance_id,
            "managed_root": f"{MANAGED_EXPERIMENT_ROOT}/{self.workflow_instance_id}",
        }
        if _object(self.marker_path, "managed Experiment marker") != expected:
            raise GenericHarnessWorkspaceError("managed Experiment ownership conflicts")

    def write_contract(self, name: str, value: Any) -> Path:
        self.verify_owner()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}\.json", name):
            raise GenericHarnessWorkspaceError("managed contract name is invalid")
        path = self.root / "contracts" / name
        _atomic_json(path, value)
        return path

    def write_execution_manifest(self, manifest: GenericHarnessExecutionManifest) -> Path:
        self.verify_owner()
        path = self.root / "execution/manifest.json"
        _atomic_json(path, manifest)
        return path

    def reconcile_execution_manifest(
        self,
        spec: GenericHarnessImplementationSpec,
        validation: GenericHarnessValidationReceipt,
        run_approval_checksum: str,
    ) -> GenericHarnessExecutionManifest:
        self.verify_owner()
        path = self.root / "execution/manifest.json"
        if not path.exists():
            manifest = GenericHarnessExecutionManifest(
                spec.specification_checksum,
                validation.validation_checksum,
                run_approval_checksum,
                tuple(HarnessUnitState(unit.unit_id, HarnessUnitStatus.PENDING) for unit in spec.execution_units),
            )
            self.write_execution_manifest(manifest)
            return manifest
        raw = _object(path, "execution manifest")
        try:
            manifest = GenericHarnessExecutionManifest(
                raw["specification_checksum"], raw["validation_checksum"],
                raw["run_approval_checksum"],
                tuple(HarnessUnitState(
                    item["unit_id"], HarnessUnitStatus(item["status"]),
                    tuple(tuple(value) for value in item.get("output_checksums", [])),
                    item.get("attempt_count", 0),
                    item.get("started_at"), item.get("completed_at"),
                ) for item in raw["units"]),
            )
        except (KeyError, TypeError, ValueError, GenericHarnessContractError) as error:
            raise GenericHarnessWorkspaceError("execution manifest is invalid") from error
        if (
            manifest.specification_checksum != spec.specification_checksum
            or manifest.validation_checksum != validation.validation_checksum
            or manifest.run_approval_checksum != run_approval_checksum
            or tuple(item.unit_id for item in manifest.units)
            != tuple(item.unit_id for item in spec.execution_units)
        ):
            raise GenericHarnessWorkspaceError("execution manifest lineage drifted")
        for state in manifest.units:
            if state.status is not HarnessUnitStatus.COMPLETED:
                continue
            for name, checksum in state.output_checksums:
                output = self.root / "outputs" / state.unit_id / name
                if (
                    output.is_symlink() or not output.is_file()
                    or output.stat().st_nlink != 1
                    or sha256_bytes(output.read_bytes()) != checksum
                ):
                    raise GenericHarnessWorkspaceError("completed execution-unit evidence drifted")
        return manifest

    def mark_unit_completed(
        self,
        manifest: GenericHarnessExecutionManifest,
        spec: GenericHarnessImplementationSpec,
        unit_id: str,
        outputs: dict[str, bytes],
        *,
        started_at: str,
        completed_at: str,
    ) -> GenericHarnessExecutionManifest:
        self.verify_owner()
        if not outputs:
            raise GenericHarnessWorkspaceError("completed unit requires outputs")
        states = list(manifest.units)
        index = next((index for index, item in enumerate(states) if item.unit_id == unit_id), None)
        if index is None or states[index].status is HarnessUnitStatus.COMPLETED:
            raise GenericHarnessWorkspaceError("execution unit is unavailable for completion")
        unit = next((item for item in spec.execution_units if item.unit_id == unit_id), None)
        if (
            manifest.specification_checksum != spec.specification_checksum
            or unit is None
            or set(outputs) != set(unit.expected_output_names)
        ):
            raise GenericHarnessWorkspaceError("execution unit outputs differ from the exact plan")
        target = self.root / "outputs" / unit_id
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        checksums: list[tuple[str, str]] = []
        for name, content in sorted(outputs.items()):
            if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,159}", name):
                raise GenericHarnessWorkspaceError("execution output name is invalid")
            path = target / name
            if path.exists():
                raise GenericHarnessWorkspaceError("execution output already exists")
            path.write_bytes(content)
            checksums.append((name, sha256_bytes(content)))
        states[index] = HarnessUnitState(
            unit_id, HarnessUnitStatus.COMPLETED, tuple(checksums),
            states[index].attempt_count + 1, started_at, completed_at,
        )
        updated = replace(manifest, units=tuple(states))
        self.write_execution_manifest(updated)
        return updated


def _version_tuple(value: str) -> tuple[int, ...] | None:
    match = _VERSION.match(value)
    if match is None:
        return None
    return tuple(int(item or 0) for item in match.groups())


def _satisfies(actual: str, constraint: str) -> bool:
    version = _version_tuple(actual)
    if version is None:
        return False
    for raw in constraint.split(","):
        clause = raw.strip()
        operation = next((value for value in (">=", "<=", "==", ">", "<") if clause.startswith(value)), "==")
        expected = _version_tuple(clause[len(operation):] if clause.startswith(operation) else clause)
        if expected is None:
            return False
        width = max(len(version), len(expected))
        left = version + (0,) * (width - len(version))
        right = expected + (0,) * (width - len(expected))
        if not {"==": left == right, ">=": left >= right, "<=": left <= right, ">": left > right, "<": left < right}[operation]:
            return False
    return True


def _inspect_python(executable: Path, packages: tuple[str, ...]) -> dict[str, Any]:
    script = (
        "import importlib.metadata,json,platform;"
        f"names={list(packages)!r};"
        "values={};"
        "\nfor name in names:\n"
        " try: values[name]=importlib.metadata.version(name)\n"
        " except importlib.metadata.PackageNotFoundError: values[name]=None\n"
        "print(json.dumps({'implementation':platform.python_implementation(),"
        "'version':platform.python_version(),'packages':values},sort_keys=True))"
    )
    completed = subprocess.run(
        [str(executable), "-I", "-c", script], capture_output=True, text=True,
        timeout=15, check=False, env={"PATH": os.environ.get("PATH", "")},
    )
    if completed.returncode != 0 or len(completed.stdout) > 65_536:
        raise GenericHarnessWorkspaceError("runtime candidate inspection failed")
    value = json.loads(completed.stdout)
    if not isinstance(value, dict) or set(value) != {"implementation", "version", "packages"}:
        raise GenericHarnessWorkspaceError("runtime candidate response is invalid")
    return value


def discover_python_runtimes(
    *, version_constraint: str, required_packages: tuple[str, ...],
    package_constraints: tuple[tuple[str, str], ...] = (),
    candidate_paths: tuple[str, ...] = (),
) -> RuntimeDiscovery:
    """Inspect explicit existing candidates; never install, upgrade, or download."""

    constraints = dict(package_constraints)
    if (
        len(constraints) != len(package_constraints)
        or set(constraints) - set(required_packages)
    ):
        raise GenericHarnessWorkspaceError("package constraints are invalid")
    candidates = candidate_paths or (sys.executable,)
    compatible: list[LocalRuntimeCandidate] = []
    rejected: list[tuple[str, tuple[str, ...]]] = []
    seen: set[str] = set()
    for raw in candidates:
        path = Path(raw).resolve()
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        reasons: list[str] = []
        try:
            metadata = path.stat()
            if not stat.S_ISREG(metadata.st_mode) or not os.access(path, os.X_OK):
                raise OSError
            inspected = _inspect_python(path, required_packages)
            if not _satisfies(inspected["version"], version_constraint):
                reasons.append(
                    f"Python {inspected['version']} does not satisfy {version_constraint}."
                )
            missing = tuple(name for name, version in inspected["packages"].items() if version is None)
            if missing:
                reasons.append("Missing required packages: " + ", ".join(missing) + ".")
            incompatible = tuple(
                name for name, constraint in constraints.items()
                if inspected["packages"].get(name) is not None
                and not _satisfies(inspected["packages"][name], constraint)
            )
            if incompatible:
                reasons.append(
                    "Installed package versions do not satisfy the declaration: "
                    + ", ".join(incompatible) + "."
                )
            if reasons:
                rejected.append((key, tuple(reasons)))
                continue
            environment = {
                "implementation": inspected["implementation"],
                "version": inspected["version"],
                "packages": inspected["packages"],
                "platform": platform.system(),
            }
            dependencies = tuple(
                canonical_hash(
                    {"name": name, "version_constraint": constraints[name]}
                    if name in constraints
                    else {"name": name, "version": inspected["packages"][name]}
                )
                for name in required_packages
            )
            compatible.append(LocalRuntimeCandidate(
                "python-" + sha256_bytes(key.encode())[7:23], "PYTHON",
                inspected["version"], key, ("PYTHON_SCRIPT",),
                canonical_hash(environment), dependencies, True,
            ))
        except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError, GenericHarnessContractError) as error:
            rejected.append((key, ("Candidate could not be safely inspected.",)))
    return RuntimeDiscovery(
        "PYTHON", version_constraint, required_packages,
        tuple(compatible), tuple(rejected), False,
    )
