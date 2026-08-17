"""Immutable forward publication for Experiment 0.7 / Capsule 0.10 / v5."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.artifact_references import generic_experiment_v5_contracts

from . import generic_experiment_v5_evidence
from .generic_experiment_publication import (
    GENERIC_EXPERIMENT_ARTIFACT_TYPE,
    GENERIC_EXPERIMENT_CAPSULE_CHECKSUM,
    REFERENCE_CAPABILITY_SKILL,
    _generic_experiment_files,
    generic_experiment_workflow_document,
)
from .production_workflows import (
    EXPERIMENT_TEMPLATE_ID, EXPERIMENT_WORKFLOW_ID, _build_scaffold_package,
    _replace_spec, scaffold_output_contract,
)
from .serialization import canonical_hash, canonical_json, sha256_bytes
from .template import FileSpec

GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION = "0.7.0"
GENERIC_EXPERIMENT_V5_CAPSULE_VERSION = "0.10.0"
GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE = "experiment-record/v5"
BOUNDED_EVIDENCE_SCHEMA = "reagent.experiment-bounded-scientific-evidence/v0.1"


def generic_experiment_v5_workflow_document() -> dict[str, Any]:
    document = generic_experiment_workflow_document()
    document["workflow_version"] = GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION
    document["artifact_outputs"] = [
        scaffold_output_contract(GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE)
    ]
    document["bounded_scientific_evidence"] = {
        "schema": BOUNDED_EVIDENCE_SCHEMA,
        "authority": "LOCAL_FINAL_ARTIFACT",
        "presentation_companion_authoritative": False,
        "maximum_blocks": generic_experiment_v5_contracts.MAX_EVIDENCE_BLOCKS,
        "maximum_serialized_bytes": generic_experiment_v5_contracts.MAX_EVIDENCE_BYTES,
    }
    document["immutable_versioning"] = (
        "Experiment 0.4/0.5/0.6, Capsules 0.7/0.8/0.9, and v2/v3/v4 remain unchanged"
    )
    return document


def generic_experiment_v5_contract_checksum() -> str:
    return canonical_hash(generic_experiment_v5_workflow_document())


def _forward_runtime_source() -> bytes:
    source = Path(__file__).with_name("generic_experiment_workspace_runtime.py").read_text(
        encoding="utf-8"
    )
    source = source.replace(
        "Public Local Workspace entrypoint for generic Experiment 0.6",
        "Public Local Workspace entrypoint for generic Experiment 0.7",
        1,
    )
    replacements = {
        'WORKFLOW_VERSION = "0.6.0"': 'WORKFLOW_VERSION = "0.7.0"',
        'CAPSULE_VERSION = "0.9.0"': 'CAPSULE_VERSION = "0.10.0"',
        'contract.get("output_artifact_type") != "experiment-record/v4"':
            'contract.get("output_artifact_type") != "experiment-record/v5"',
    }
    for old, new in replacements.items():
        if old not in source:
            raise RuntimeError("Generic Experiment forward runtime seam is unavailable")
        source = source.replace(old, new, 1)
    return source.encode("utf-8")


def generic_experiment_v5_capsule_checksum() -> str:
    return canonical_hash({
        "generator_version": (
            f"reagent-{EXPERIMENT_WORKFLOW_ID}-compiler/"
            f"{GENERIC_EXPERIMENT_V5_CAPSULE_VERSION}"
        ),
        "workflow_checksum": generic_experiment_v5_contract_checksum(),
        "base_capsule_checksum": GENERIC_EXPERIMENT_CAPSULE_CHECKSUM,
        "forward_source_checksums": {
            "artifact_references/generic_experiment_v5_contracts.py": sha256_bytes(
                Path(generic_experiment_v5_contracts.__file__).read_bytes()
            ),
            "workflow_packages/generic_experiment_v5_evidence.py": sha256_bytes(
                Path(generic_experiment_v5_evidence.__file__).read_bytes()
            ),
            "workflow_packages/generic_experiment_workspace_runtime.v0.7.py":
                sha256_bytes(_forward_runtime_source()),
        },
        "artifact_output": GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE,
        "evidence_schema": BOUNDED_EVIDENCE_SCHEMA,
        "capability_interface": "reagent.experiment-capability/v0.1",
        "execution_boundary": "UNCHANGED_EXISTING_BOUNDED_RUNNER",
    })


GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM = generic_experiment_v5_contract_checksum()
GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM = generic_experiment_v5_capsule_checksum()
GENERIC_EXPERIMENT_V5_CAPSULE_ID = (
    "capsule-" + GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM[7:39]
)


def _json(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _generic_experiment_v5_files(**kwargs: Any) -> dict[str, FileSpec]:
    files = dict(_generic_experiment_files(**kwargs))
    workflow = generic_experiment_v5_workflow_document()
    contract = json.loads(files["workflow/generic-experiment.json"].content)
    contract.update({
        "schema": "reagent.generic-experiment-workflow/v0.2",
        "output_artifact_type": GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE,
        "bounded_scientific_evidence_schema": BOUNDED_EVIDENCE_SCHEMA,
        "workflow_checksum": GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM,
        "workflow_capsule": {
            "workflow_definition_id": EXPERIMENT_WORKFLOW_ID,
            "workflow_version": GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION,
            "workflow_checksum": GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM,
            "capsule_id": GENERIC_EXPERIMENT_V5_CAPSULE_ID,
            "capsule_version": GENERIC_EXPERIMENT_V5_CAPSULE_VERSION,
            "capsule_checksum": GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM,
        },
    })
    contract["runtime_dynamic_paths"] = [
        *contract["runtime_dynamic_paths"], "memory/bounded-scientific-evidence.json",
    ]
    _replace_spec(files, "workflow/workflow.json", _json(workflow))
    _replace_spec(files, "workflow/generic-experiment.json", _json(contract))
    _replace_spec(files, "reagent_local.py", _forward_runtime_source())
    _replace_spec(files, "validate_package.py", _forward_runtime_source())
    _replace_spec(files, "workflow/artifact-outputs.json", _json({
        "schema_version": "reagent.artifact-output-contract/v0.1",
        **scaffold_output_contract(GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE),
        "producer_core_capability_maturity": "REVIEWED_CORE",
        "validity_point": "OWNER_RESULT_REVIEWED_WITH_MATERIALIZABLE_BOUNDED_EVIDENCE",
    }))
    _replace_spec(files, "AGENT.md", files["AGENT.md"].content + b"\nAt finalization, the selected Capability must project its exact local evaluation payload into bounded scientific evidence v0.1. Core validates structure and lineage only. Cloud presentation is never research evidence authority.\n")
    _replace_spec(files, "outputs/README.md", b"# Generic Experiment v5 outputs\n\nOnly one validated content-addressed experiment-record/v5 containing canonical bounded scientific evidence may be finalized. Raw outputs remain local.\n")
    files[
        "runtime_lib/backend/artifact_references/generic_experiment_v5_contracts.py"
    ] = FileSpec(
        Path(generic_experiment_v5_contracts.__file__).read_bytes(), "text/x-python",
        "bounded materializable evidence contract", False, "INSTRUCTION",
    )
    files[
        "runtime_lib/backend/workflow_packages/generic_experiment_v5_evidence.py"
    ] = FileSpec(
        Path(generic_experiment_v5_evidence.__file__).read_bytes(), "text/x-python",
        "reference Capability evidence projection", False, "INSTRUCTION",
    )
    return files


def build_generic_experiment_v0_10_package(**kwargs: Any):
    return _build_scaffold_package(
        renderer=_generic_experiment_v5_files,
        workflow_id=EXPERIMENT_WORKFLOW_ID,
        workflow_type="Reproduction & Experiment",
        template_id=EXPERIMENT_TEMPLATE_ID,
        workflow_version=GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION,
        capsule_version=GENERIC_EXPERIMENT_V5_CAPSULE_VERSION,
        **kwargs,
    )


assert GENERIC_EXPERIMENT_ARTIFACT_TYPE == "experiment-record/v4"
assert REFERENCE_CAPABILITY_SKILL.version == "0.1.0"
