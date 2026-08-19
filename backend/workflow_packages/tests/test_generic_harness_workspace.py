from __future__ import annotations

import sys
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
from backend.workflow_packages.serialization import canonical_hash

SHA = tuple("sha256:" + value * 64 for value in "abcdef")
PROJECT = "project-" + "a" * 32
WORKFLOW = "wfi-" + "b" * 32


def _spec() -> GenericHarnessImplementationSpec:
    return GenericHarnessImplementationSpec(
        SHA[0], SHA[1], "run.py", "PYTHON", ">=3.11,<4", (),
        ("PYTHON_SCRIPT",),
        (
            HarnessExpectedOutput(
                "metrics-001.json", "results/metrics-001.json", "application/json"
            ),
            HarnessExpectedOutput(
                "metrics-002.json", "results/metrics-002.json", "application/json"
            ),
        ),
        (
            HarnessExecutionUnit(
                "unit-001", ("--unit", "1"), ("metrics-001.json",), "First unit."
            ),
            HarnessExecutionUnit(
                "unit-002", ("--unit", "2"), ("metrics-002.json",), "Second unit."
            ),
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
        manifest, spec, "unit-001", {"metrics-001.json": b'{"accuracy":0.5}\n'},
        started_at="2026-08-20T10:00:00Z",
        completed_at="2026-08-20T10:00:01Z",
    )
    recovered = managed.reconcile_execution_manifest(spec, validation, SHA[5])
    assert recovered.next_pending_unit == "unit-002"
    assert recovered.units[0].started_at == "2026-08-20T10:00:00Z"
    assert recovered.units[0].completed_at == "2026-08-20T10:00:01Z"
    output = managed.root / "outputs/unit-001/metrics-001.json"
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
            started_at="2026-08-20T10:00:00Z",
            completed_at="2026-08-20T10:00:01Z",
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


def test_runtime_discovery_enforces_declared_package_constraints(monkeypatch) -> None:
    def compatible(_path, packages):
        assert packages == ("scikit-learn",)
        return {
            "implementation": "CPython", "version": "3.11.9",
            "packages": {"scikit-learn": "1.5.2"},
        }

    monkeypatch.setattr(
        "backend.workflow_packages.generic_harness_workspace._inspect_python",
        compatible,
    )
    accepted = discover_python_runtimes(
        version_constraint=">=3.11,<4", required_packages=("scikit-learn",),
        package_constraints=(("scikit-learn", ">=1.4,<2"),),
        candidate_paths=(sys.executable,),
    )
    assert len(accepted.candidates) == 1
    assert accepted.candidates[0].dependency_identity_checksums == (
        canonical_hash({
            "name": "scikit-learn", "version_constraint": ">=1.4,<2",
        }),
    )
    rejected = discover_python_runtimes(
        version_constraint=">=3.11,<4", required_packages=("scikit-learn",),
        package_constraints=(("scikit-learn", ">=2"),),
        candidate_paths=(sys.executable,),
    )
    assert not rejected.candidates
    assert "do not satisfy" in rejected.rejected[0][1][0]


def test_managed_root_refuses_conflicting_owner_marker(tmp_path: Path) -> None:
    managed = GenericHarnessWorkspace(tmp_path, PROJECT, WORKFLOW)
    managed.initialize()
    managed.marker_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(GenericHarnessWorkspaceError, match="ownership conflicts"):
        managed.initialize()
