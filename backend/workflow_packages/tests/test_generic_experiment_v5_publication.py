from __future__ import annotations

from dataclasses import replace
import json

from backend.artifact_references.generic_experiment_v5_contracts import (
    EvidenceKind, validate_experiment_record_v5,
)
from backend.artifact_references.tests.test_generic_experiment_record_v4 import record
from backend.workflow_packages.experiment_capability_runtime import CapabilityEvaluationResult
from backend.workflow_packages.generic_experiment_publication import (
    GENERIC_EXPERIMENT_CAPSULE_CHECKSUM, GENERIC_EXPERIMENT_CONTRACT_CHECKSUM,
)
from backend.workflow_packages.generic_experiment_v5_evidence import (
    REFERENCE_EVALUATION_SCHEMA, finalize_sklearn_reference_record_v5,
    sklearn_reference_evidence_blocks,
)
from backend.workflow_packages.generic_experiment_v5_publication import (
    BOUNDED_EVIDENCE_SCHEMA, GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE,
    GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM, GENERIC_EXPERIMENT_V5_CAPSULE_ID,
    GENERIC_EXPERIMENT_V5_CAPSULE_VERSION, GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM,
    GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION, build_generic_experiment_v0_10_package,
    generic_experiment_v5_workflow_document,
)
from backend.workflow_packages.serialization import canonical_hash, sha256_bytes


def _reference_result():
    payload = {
        "schema_version": "reagent.experiment-result/v0.2",
        "conditions": [
            {"condition": "RAW", "metrics": {"accuracy": 0.8, "macro_f1": 0.79}},
            {"condition": "STANDARD", "metrics": {"accuracy": 0.84, "macro_f1": 0.83}},
        ],
        "robustness": [],
    }
    lifecycle = record()
    receipt = replace(
        lifecycle.capability_evaluation,
        evaluation_schema=REFERENCE_EVALUATION_SCHEMA,
        result_payload_checksum=canonical_hash(payload),
    )
    lifecycle = replace(lifecycle, capability_evaluation=receipt)
    return lifecycle, CapabilityEvaluationResult(receipt, "LIMITED", payload)


def test_reference_capability_projection_is_scalar_table_series_and_stable() -> None:
    lifecycle, result = _reference_result()
    blocks = sklearn_reference_evidence_blocks(result)
    assert tuple(item.kind for item in blocks) == (
        EvidenceKind.SCALAR, EvidenceKind.TABLE, EvidenceKind.SERIES,
    )
    first = finalize_sklearn_reference_record_v5(lifecycle, result)
    second = finalize_sklearn_reference_record_v5(lifecycle, result)
    assert first.record_checksum == second.record_checksum
    assert first.bounded_scientific_evidence.evidence_checksum == second.bounded_scientific_evidence.evidence_checksum
    assert validate_experiment_record_v5(first.to_dict())["schema"] == "experiment-record/v5"


def test_forward_publication_builds_exact_isolated_capsule(tmp_path) -> None:
    built = build_generic_experiment_v0_10_package(
        project_id="project-" + "1" * 32,
        project_name="EP-D0 controlled project",
        research_topic="Materializable bounded evidence",
        output_root=tmp_path,
        package_id="generic-experiment-v5-controlled",
    )
    assert built.validation.valid and built.archive_validation.valid
    root = built.package_root
    workflow = json.loads((root / "workflow/workflow.json").read_text())
    contract = json.loads((root / "workflow/generic-experiment.json").read_text())
    outputs = json.loads((root / "workflow/artifact-outputs.json").read_text())
    assert workflow["workflow_version"] == "0.7.0"
    assert workflow["bounded_scientific_evidence"]["schema"] == BOUNDED_EVIDENCE_SCHEMA
    assert contract["workflow_capsule"] == {
        "workflow_definition_id": "reproduction-experiment-local-experimental",
        "workflow_version": GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION,
        "workflow_checksum": GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM,
        "capsule_id": GENERIC_EXPERIMENT_V5_CAPSULE_ID,
        "capsule_version": GENERIC_EXPERIMENT_V5_CAPSULE_VERSION,
        "capsule_checksum": GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM,
    }
    assert outputs["artifact_type"] == GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE
    assert (root / "runtime_lib/backend/artifact_references/generic_experiment_v5_contracts.py").is_file()
    assert (root / "runtime_lib/backend/workflow_packages/generic_experiment_v5_evidence.py").is_file()
    assert GENERIC_EXPERIMENT_V5_CAPSULE_VERSION == "0.10.0"


def test_v4_publication_and_checksum_bound_sources_are_unchanged() -> None:
    assert GENERIC_EXPERIMENT_CONTRACT_CHECKSUM == "sha256:5e91401ee48979ff1e61453c8e304565c9c35ab317d511fdb458b82347dff517"
    assert GENERIC_EXPERIMENT_CAPSULE_CHECKSUM == "sha256:2a40aa6dd4668a734bb83c48fcbac0886659d7a4281b96d4b84296ce728a21fe"
    assert generic_experiment_v5_workflow_document()["artifact_outputs"][0]["artifact_type"] == "experiment-record/v5"
    assert sha256_bytes(open("backend/workflow_packages/generic_experiment_coordinator.py", "rb").read()) == "sha256:fe13d58fe36a409e1573a8f00857482ce4afdad4de9eeed906973e3d21c0a718"
