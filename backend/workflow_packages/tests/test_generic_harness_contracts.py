from __future__ import annotations

import pytest

from backend.workflow_packages.generic_experiment_contracts import ContractRef
from backend.workflow_packages.generic_harness_contracts import (
    GENERIC_HARNESS_CLASSIFICATION,
    GenericHarnessContractError,
    GenericHarnessImplementationSpec,
    GenericHarnessPath,
    HarnessDependency,
    HarnessExecutionUnit,
    HarnessExpectedOutput,
)

SHA = tuple("sha256:" + value * 64 for value in "abcdef")


def _spec() -> GenericHarnessImplementationSpec:
    return GenericHarnessImplementationSpec(
        SHA[0], SHA[1], "run_experiment.py", "PYTHON", ">=3.11,<3.13",
        (HarnessDependency("scikit-learn", ">=1.4,<2"),),
        ("PYTHON_SCRIPT",),
        (HarnessExpectedOutput("metrics", "results/metrics.json", "application/json"),),
        (
            HarnessExecutionUnit(
                "unit-fold-01", ("--fold", "1"), ("metrics",),
                "Evaluate one stable outer fold.",
            ),
        ),
        (("python", "-m", "pytest", "-q"),),
        (("wall_seconds", "120"),), "DISABLED",
        ("Compare the approved baseline and treatment.",),
    )


def test_generic_harness_path_is_not_reviewed_capability_or_user_skill() -> None:
    path = GenericHarnessPath(
        ContractRef("reagent.generic-harness-implementation-spec/v0.1", SHA[0]),
        ContractRef("reagent.generic-harness-evaluation/v0.1", SHA[1]),
    )
    assert path.classification == GENERIC_HARNESS_CLASSIFICATION
    assert path.reviewed_capability is False
    assert path.user_skill_authority is False


def test_implementation_spec_is_exact_bounded_and_network_disabled() -> None:
    spec = _spec()
    assert spec.execution_units[0].unit_id == "unit-fold-01"
    assert spec.specification_checksum.startswith("sha256:")
    with pytest.raises(GenericHarnessContractError, match="network"):
        GenericHarnessImplementationSpec(
            spec.objective_checksum, spec.methodology_checksum,
            spec.entrypoint_relative_path, spec.runtime_family,
            spec.runtime_version_constraint, spec.dependencies,
            spec.required_runtime_capabilities, spec.expected_outputs,
            spec.execution_units, spec.validation_commands, spec.compute_limits,
            "BOUNDED_DECLARED", spec.implementation_summary,
        )


def test_execution_units_may_not_reference_undeclared_outputs() -> None:
    spec = _spec()
    with pytest.raises(GenericHarnessContractError, match="undeclared output"):
        GenericHarnessImplementationSpec(
            spec.objective_checksum, spec.methodology_checksum,
            spec.entrypoint_relative_path, spec.runtime_family,
            spec.runtime_version_constraint, spec.dependencies,
            spec.required_runtime_capabilities, spec.expected_outputs,
            (HarnessExecutionUnit(
                "unit-fold-02", ("--fold", "2"), ("predictions",), "Second fold."
            ),),
            spec.validation_commands, spec.compute_limits, spec.network_policy,
            spec.implementation_summary,
        )
