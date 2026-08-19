"""Forward publication for Experiment 0.8 / Capsule 0.11 Generic Harness path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import (
    generic_harness_adapter,
    generic_harness_contracts,
    generic_harness_lifecycle,
    generic_harness_public_runtime,
    generic_harness_workspace,
)
from .generic_experiment_contracts import ContractRef, ExactIdentity
from .generic_experiment_v5_publication import (
    BOUNDED_EVIDENCE_SCHEMA,
    GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE,
    GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM,
    _generic_experiment_v5_files,
    generic_experiment_v5_workflow_document,
)
from .generic_harness_adapter import (
    GenericHarnessImplementation,
    system_generic_harness_path,
)
from .generic_harness_contracts import (
    GENERIC_HARNESS_CLASSIFICATION,
    GenericHarnessPath,
)
from .production_workflows import (
    EXPERIMENT_TEMPLATE_ID,
    EXPERIMENT_WORKFLOW_ID,
    _build_scaffold_package,
    _replace_spec,
    scaffold_output_contract,
)
from .serialization import canonical_hash, canonical_json, sha256_bytes, to_json_value
from .template import FileSpec

GENERIC_HARNESS_WORKFLOW_VERSION = "0.8.0"
GENERIC_HARNESS_CAPSULE_VERSION = "0.11.0"
GENERIC_HARNESS_ARTIFACT_TYPE = "experiment-record/v5"


def generic_harness_workflow_document() -> dict[str, Any]:
    document = generic_experiment_v5_workflow_document()
    document["workflow_version"] = GENERIC_HARNESS_WORKFLOW_VERSION
    document["supported_mode"] = "GENERIC_AGENT_HARNESS_LOCAL_EXPERIMENT"
    document["installed_capability_policy"] = (
        "EXACT_REVIEWED_FAST_PATH_OR_SYSTEM_GENERIC_HARNESS"
    )
    document["unsupported_outcome"] = "GENERIC_AGENT_HARNESS"
    document["implementation_paths"] = {
        "reviewed": "EXACT_REVIEWED_EXPERIMENT_CAPABILITY",
        "fallback": GENERIC_HARNESS_CLASSIFICATION,
        "user_skill_authority": False,
        "generic_scientific_authority": False,
    }
    document["managed_execution_namespace"] = (
        ".reagent/experiments/<workflow-instance-id>"
    )
    document["durability"] = {
        "local_commit_before_cloud_sync": True,
        "execution_unit_manifest": "reagent.generic-harness-execution-manifest/v0.1",
        "verified_completed_units_reused": True,
    }
    document["immutable_versioning"] = (
        "Experiment 0.4/0.5/0.6/0.7 and Capsules 0.7/0.8/0.9/0.10 remain unchanged"
    )
    return document


def generic_harness_contract_checksum() -> str:
    return canonical_hash(generic_harness_workflow_document())


GENERIC_HARNESS_CONTRACT_CHECKSUM = generic_harness_contract_checksum()


def _path() -> GenericHarnessPath:
    return system_generic_harness_path()


def _generic_descriptor() -> Any:
    implementation = GenericHarnessImplementation(
        implementation_root=Path("."),
        workflow=ExactIdentity(
            EXPERIMENT_WORKFLOW_ID,
            GENERIC_HARNESS_WORKFLOW_VERSION,
            GENERIC_HARNESS_CONTRACT_CHECKSUM,
        ),
        path=_path(),
    )
    return implementation.descriptor


def _forward_sources() -> dict[str, Path]:
    modules = {
        "workflow_packages/generic_harness_contracts.py": generic_harness_contracts,
        "workflow_packages/generic_harness_workspace.py": generic_harness_workspace,
        "workflow_packages/generic_harness_adapter.py": generic_harness_adapter,
        "workflow_packages/generic_harness_lifecycle.py": generic_harness_lifecycle,
        "workflow_packages/generic_harness_public_runtime.py": generic_harness_public_runtime,
    }
    return {name: Path(module.__file__) for name, module in modules.items()}


def generic_harness_capsule_checksum() -> str:
    return canonical_hash({
        "generator_version": (
            f"reagent-{EXPERIMENT_WORKFLOW_ID}-compiler/"
            f"{GENERIC_HARNESS_CAPSULE_VERSION}"
        ),
        "workflow_checksum": GENERIC_HARNESS_CONTRACT_CHECKSUM,
        "base_capsule_checksum": GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM,
        "forward_source_checksums": {
            name: sha256_bytes(path.read_bytes())
            for name, path in sorted(_forward_sources().items())
        },
        "artifact_output": GENERIC_HARNESS_ARTIFACT_TYPE,
        "evidence_schema": BOUNDED_EVIDENCE_SCHEMA,
        "implementation_path": to_json_value(_path()),
        "lifecycle_adapter": to_json_value(_generic_descriptor()),
        "managed_execution_namespace": ".reagent/experiments/<workflow-instance-id>",
        "execution_boundary": "UNCHANGED_EXISTING_BOUNDED_RUNNER",
    })


GENERIC_HARNESS_CAPSULE_CHECKSUM = generic_harness_capsule_checksum()
GENERIC_HARNESS_CAPSULE_ID = "capsule-" + GENERIC_HARNESS_CAPSULE_CHECKSUM[7:39]


def _json(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _public_runtime_source() -> bytes:
    return Path(generic_harness_public_runtime.__file__).read_bytes()


def _generic_harness_files(**kwargs: Any) -> dict[str, FileSpec]:
    files = dict(_generic_experiment_v5_files(**kwargs))
    workflow = generic_harness_workflow_document()
    contract = json.loads(files["workflow/generic-experiment.json"].content)
    contract.update({
        "schema": "reagent.generic-experiment-workflow/v0.3",
        "output_artifact_type": GENERIC_HARNESS_ARTIFACT_TYPE,
        "workflow_checksum": GENERIC_HARNESS_CONTRACT_CHECKSUM,
        "workflow_capsule": {
            "workflow_definition_id": EXPERIMENT_WORKFLOW_ID,
            "workflow_version": GENERIC_HARNESS_WORKFLOW_VERSION,
            "workflow_checksum": GENERIC_HARNESS_CONTRACT_CHECKSUM,
            "capsule_id": GENERIC_HARNESS_CAPSULE_ID,
            "capsule_version": GENERIC_HARNESS_CAPSULE_VERSION,
            "capsule_checksum": GENERIC_HARNESS_CAPSULE_CHECKSUM,
        },
        "implementation_fallback": GENERIC_HARNESS_CLASSIFICATION,
        "managed_execution_namespace": ".reagent/experiments/<workflow-instance-id>",
        "generic_harness_path": to_json_value(_path()),
        "generic_harness_descriptor": to_json_value(_generic_descriptor()),
    })
    contract["runtime_dynamic_paths"] = list(dict.fromkeys((
        *contract["runtime_dynamic_paths"],
        "memory/current-artifact.json", "memory/progress",
    )))
    implementation_paths = {
        "schema": "reagent.experiment-implementation-paths/v0.1",
        "reviewed_fast_paths": json.loads(files["workflow/capabilities.json"].content),
        "generic_fallback": to_json_value(_generic_descriptor()),
        "selection": "REVIEWED_EXACT_FIRST_THEN_GENERIC_AGENT_HARNESS",
        "user_skill_authority": False,
    }
    _replace_spec(files, "workflow/workflow.json", _json(workflow))
    _replace_spec(files, "workflow/generic-experiment.json", _json(contract))
    _replace_spec(files, "reagent_local.py", _public_runtime_source())
    _replace_spec(files, "validate_package.py", _public_runtime_source())
    _replace_spec(files, "workflow/artifact-outputs.json", _json({
        "schema_version": "reagent.artifact-output-contract/v0.1",
        **scaffold_output_contract(GENERIC_HARNESS_ARTIFACT_TYPE),
        "producer_core_capability_maturity": "REVIEWED_CORE",
        "validity_point": "OWNER_REVIEWED_CONTRACT_VALID_GENERIC_EVIDENCE",
    }))
    files["workflow/implementation-paths.json"] = FileSpec(
        _json(implementation_paths), "application/json",
        "exact reviewed-fast-path and Generic Harness fallback identities",
        False, "INSTRUCTION",
    )
    files["AGENT.md"] = FileSpec(
        files["AGENT.md"].content
        + b"\nThe Generic Agent Harness is a system implementation path, not a reviewed ExperimentCapability or User Skill authority. Keep implementation, runtime, partial outputs, and evidence under the Workspace-managed .reagent/experiments/<workflow-instance-id>/ namespace. Never install dependencies or execute before exact Owner approval.\n",
        "text/markdown", "Agent Harness instructions", False, "INSTRUCTION",
    )
    for relative, path in _forward_sources().items():
        files[f"runtime_lib/backend/{relative}"] = FileSpec(
            path.read_bytes(), "text/x-python", "Generic Harness forward runtime",
            False, "INSTRUCTION",
        )
    return files


def build_generic_harness_v0_11_package(**kwargs: Any):
    return _build_scaffold_package(
        renderer=_generic_harness_files,
        workflow_id=EXPERIMENT_WORKFLOW_ID,
        workflow_type="Reproduction & Experiment",
        template_id=EXPERIMENT_TEMPLATE_ID,
        workflow_version=GENERIC_HARNESS_WORKFLOW_VERSION,
        capsule_version=GENERIC_HARNESS_CAPSULE_VERSION,
        **kwargs,
    )


assert GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE == GENERIC_HARNESS_ARTIFACT_TYPE
