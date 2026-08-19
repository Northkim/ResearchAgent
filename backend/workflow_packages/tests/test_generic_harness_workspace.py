from __future__ import annotations

from pathlib import Path

import pytest

from backend.workflow_packages.generic_harness_contracts import (
    GenericHarnessImplementationSpec,
    GenericHarnessValidationReceipt,
    HarnessDependency,
    HarnessExecutionUnit,
    HarnessExpectedOutput,
)
from backend.workflow_packages.generic_harness_workspace import (
    GenericHarnessWorkspace,
    GenericHarnessWorkspaceError,
    discover_python_runtimes,
)
from backend.workflow_packages.generic_experiment_v5_publication import (
    build_generic_experiment_v0_10_package,
)

SHA = tuple("sha256:" + value * 64 for value in "abcdef")
PROJECT = "project-" + "a" * 32
WORKFLOW = "wfi-" + "b" * 32


def _spec() -> GenericHarnessImplementationSpec:
    return GenericHarnessImplementationSpec(
        SHA[0], SHA[1], "run.py", "PYTHON", ">=3.11,<4", (),
        ("PYTHON_SCRIPT",),
        (HarnessExpectedOutput("metrics.json", "results/metrics.json", "application/json"),),
        (
            HarnessExecutionUnit("unit-001", ("--unit", "1"), ("metrics.json",), "First unit."),
            HarnessExecutionUnit("unit-002", ("--unit", "2"), ("metrics.json",), "Second unit."),
        ),
        (("python", "-m", "compileall", "-q", "."),),
        (("wall_seconds", "60"),), "DISABLED", ("Deterministic fixture.",),
    )


def _validation(spec: GenericHarnessImplementationSpec) -> GenericHarnessValidationReceipt:
    return GenericHarnessValidationReceipt(
        spec.specification_checksum, spec.methodology_checksum, SHA[2], SHA[3],
        (SHA[4],), True, True, "2026-08-20T10:00:00Z",
    )


def test_managed_state_is_outside_capsule_and_does_not_contaminate_validation(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    capsule = build_generic_experiment_v0_10_package(
        project_id=PROJECT, project_name="Controlled", research_topic="Controlled",
        output_root=workspace / "capsules", package_id="experiment",
    ).package_root
    managed = GenericHarnessWorkspace(workspace, PROJECT, WORKFLOW)
    root = managed.initialize()
    managed.write_contract("methodology.json", {"checksum": SHA[0]})
    assert root == workspace / ".reagent/experiments" / WORKFLOW
    assert not root.is_relative_to(capsule)
    validator = __import__("runpy").run_path(str(capsule / "validate_package.py"))
    assert validator["validate"](capsule, pristine=False)["valid"] is True


def test_execution_manifest_reuses_only_checksum_verified_completed_units(
    tmp_path: Path,
) -> None:
    managed = GenericHarnessWorkspace(tmp_path, PROJECT, WORKFLOW)
    managed.initialize()
    spec = _spec()
    validation = _validation(spec)
    manifest = managed.reconcile_execution_manifest(spec, validation, SHA[5])
    assert manifest.next_pending_unit == "unit-001"
    manifest = managed.mark_unit_completed(
        manifest, spec, "unit-001", {"metrics.json": b'{"accuracy":0.5}\n'},
    )
    recovered = managed.reconcile_execution_manifest(spec, validation, SHA[5])
    assert recovered.next_pending_unit == "unit-002"
    output = managed.root / "outputs/unit-001/metrics.json"
    output.write_bytes(b"drifted")
    with pytest.raises(GenericHarnessWorkspaceError, match="evidence drifted"):
        managed.reconcile_execution_manifest(spec, validation, SHA[5])


def test_execution_unit_rejects_outputs_outside_the_exact_plan(tmp_path: Path) -> None:
    managed = GenericHarnessWorkspace(tmp_path, PROJECT, WORKFLOW)
    managed.initialize()
    spec = _spec()
    manifest = managed.reconcile_execution_manifest(spec, _validation(spec), SHA[5])
    with pytest.raises(GenericHarnessWorkspaceError, match="exact plan"):
        managed.mark_unit_completed(
            manifest, spec, "unit-001", {"unexpected.json": b"{}\n"},
        )


def test_runtime_discovery_uses_existing_environment_and_never_installs() -> None:
    report = discover_python_runtimes(
        version_constraint=">=3.11,<4", required_packages=(),
    )
    assert len(report.candidates) == 1
    assert report.installation_performed is False
    incompatible = discover_python_runtimes(
        version_constraint=">=99", required_packages=(),
    )
    assert not incompatible.candidates
    assert "does not satisfy" in incompatible.rejected[0][1][0]


def test_managed_root_refuses_conflicting_owner_marker(tmp_path: Path) -> None:
    managed = GenericHarnessWorkspace(tmp_path, PROJECT, WORKFLOW)
    managed.initialize()
    managed.marker_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(GenericHarnessWorkspaceError, match="ownership conflicts"):
        managed.initialize()
