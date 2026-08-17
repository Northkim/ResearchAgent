from __future__ import annotations

from dataclasses import replace

import pytest

from backend.artifact_references import PRODUCTION_ARTIFACT_CONTRACTS
from backend.artifact_references.generic_experiment_v5_contracts import (
    BOUNDED_SCIENTIFIC_EVIDENCE_SCHEMA,
    EvidenceKind,
    EvidenceSourceKind,
    EvidenceSourceRef,
    ExperimentRecordV5Error,
    ScientificEvidenceBlock,
    finalize_experiment_record_v5,
    validate_experiment_record_v5,
)
from backend.artifact_references.generic_experiment_contracts import (
    GenericExperimentPresentation, PresentationBlock, PresentationKind,
)
from backend.artifact_references.tests.test_generic_experiment_record_v4 import record
from backend.workflow_packages.experiment_capability_runtime import CapabilityEvaluationResult
from backend.workflow_packages.generic_experiment_contracts import (
    EvaluationValidity, NormalizedExperimentResult, ProcessOutcome,
    ScientificEvidenceStatus,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json, sha256_bytes


def _result(payload=None, *, validity=EvaluationValidity.VALID):
    payload = payload or {"finding": "Three archival statements remained concordant."}
    lifecycle = record()
    receipt = replace(
        lifecycle.capability_evaluation,
        result_payload_checksum=canonical_hash(payload), validity=validity,
    )
    normalized = replace(lifecycle.normalized_result, evaluation_validity=validity)
    lifecycle = replace(
        lifecycle, capability_evaluation=receipt, normalized_result=normalized,
        limitations=normalized.limitations,
    )
    return lifecycle, CapabilityEvaluationResult(
        receipt, normalized.scientific_evidence_status.value, payload,
    )


def _source(result):
    return (EvidenceSourceRef(
        EvidenceSourceKind.RESULT_PAYLOAD, "result-payload",
        result.receipt.result_payload_checksum,
    ),)


def test_v5_materializes_domain_neutral_findings_without_presentation() -> None:
    lifecycle, result = _result()
    blocks = (
        ScientificEvidenceBlock(
            "evidence-categorical-summary", EvidenceKind.PROSE, "Finding",
            "Three archival statements remained concordant.", _source(result),
        ),
        ScientificEvidenceBlock(
            "evidence-categorical-table", EvidenceKind.TABLE, "Observed categories",
            {"columns": ("Statement", "Category"), "rows": (("A", "concordant"),)},
            _source(result),
        ),
    )
    value = finalize_experiment_record_v5(lifecycle, result, blocks)
    materialized = validate_experiment_record_v5(value.to_dict())

    assert value.schema == "experiment-record/v5"
    assert materialized["bounded_scientific_evidence"]["schema"] == BOUNDED_SCIENTIFIC_EVIDENCE_SCHEMA
    assert materialized["lifecycle_record"]["normalized_result"] == {
        "process_outcome": "SUCCEEDED", "evaluation_validity": "VALID",
        "scientific_evidence_status": "LIMITED",
        "limitations": ["Bounded source set."],
    }
    assert materialized["lifecycle_record"]["methodology"]["claim_boundaries"]
    assert materialized["bounded_scientific_evidence"]["blocks"][0]["value"].startswith("Three")
    assert "experiment-record/v5" in PRODUCTION_ARTIFACT_CONTRACTS
    assert PRODUCTION_ARTIFACT_CONTRACTS["experiment-record/v5"].validator(value.to_dict()) == materialized
    assert "presentation_payload" not in materialized


def test_v5_materializes_exact_figure_and_output_references() -> None:
    lifecycle, result = _result()
    output = lifecycle.capability_evaluation.execution_outputs[0]
    output_source = (EvidenceSourceRef(
        EvidenceSourceKind.EXECUTION_OUTPUT, output.name, output.checksum,
    ),)
    blocks = tuple(
        ScientificEvidenceBlock(
            f"evidence-{kind.value.casefold().replace('_', '-')}", kind,
            "Bounded output", {"output_id": "output-categorical", "checksum": output.checksum},
            output_source,
        )
        for kind in (EvidenceKind.FIGURE_REFERENCE, EvidenceKind.OUTPUT_REFERENCE)
    )
    value = validate_experiment_record_v5(
        finalize_experiment_record_v5(lifecycle, result, blocks).to_dict()
    )
    assert [item["kind"] for item in value["bounded_scientific_evidence"]["blocks"]] == [
        "FIGURE_REFERENCE", "OUTPUT_REFERENCE",
    ]


def test_optional_presentation_binds_exact_v5_bytes_without_becoming_evidence() -> None:
    lifecycle, result = _result()
    record = finalize_experiment_record_v5(lifecycle, result, (
        ScientificEvidenceBlock(
            "evidence-canonical", EvidenceKind.PROSE, "Canonical finding",
            "The materialized Artifact retains the canonical finding.", _source(result),
        ),
    ))
    artifact_checksum = sha256_bytes(canonical_json(record.to_dict()).encode("utf-8"))
    first = GenericExperimentPresentation(
        "artifact-" + "a" * 32, artifact_checksum,
        (PresentationBlock(
            PresentationKind.PROSE, "UI summary", "A bounded display summary.",
        ),),
    )
    changed = GenericExperimentPresentation(
        first.artifact_id, artifact_checksum,
        (PresentationBlock(
            PresentationKind.PROSE, "UI summary", "A changed bounded display summary.",
        ),),
    )
    assert first.artifact_checksum == artifact_checksum
    assert first.presentation_checksum != changed.presentation_checksum
    assert record.record_checksum == validate_experiment_record_v5(record.to_dict())["record_checksum"]
    assert record.bounded_scientific_evidence.blocks[0].value.startswith("The materialized")


def test_v5_status_cases_preserve_failure_invalid_insufficient_and_sufficient() -> None:
    lifecycle, result = _result()
    source = _source(result)
    observation = ScientificEvidenceBlock(
        "evidence-observation", EvidenceKind.PROSE, "Bounded observation",
        "One bounded categorical observation was retained.", source,
    )
    for validity, status, blocks in (
        (EvaluationValidity.INVALID, ScientificEvidenceStatus.INCONCLUSIVE, (observation,)),
        (EvaluationValidity.VALID, ScientificEvidenceStatus.INCONCLUSIVE, (observation,)),
        (EvaluationValidity.VALID, ScientificEvidenceStatus.SUPPORTS_BOUNDED_FINDINGS, (observation,)),
    ):
        receipt = replace(result.receipt, validity=validity)
        normalized = NormalizedExperimentResult(
            ProcessOutcome.SUCCEEDED, validity, status, ("Preserve this limitation.",),
        )
        current = replace(
            lifecycle, capability_evaluation=receipt, normalized_result=normalized,
            limitations=normalized.limitations,
        )
        evaluated = CapabilityEvaluationResult(receipt, status.value, result.result_payload)
        value = finalize_experiment_record_v5(current, evaluated, blocks)
        assert value.lifecycle_record.normalized_result.scientific_evidence_status is status

    failed_receipt = replace(result.receipt, validity=EvaluationValidity.NOT_EVALUATED)
    failed_result = CapabilityEvaluationResult(
        failed_receipt, ScientificEvidenceStatus.NOT_AVAILABLE.value, result.result_payload,
    )
    failed_normalized = NormalizedExperimentResult(
        ProcessOutcome.FAILED, EvaluationValidity.NOT_EVALUATED,
        ScientificEvidenceStatus.NOT_AVAILABLE, ("The process failed.",),
    )
    failed = replace(
        lifecycle, capability_evaluation=failed_receipt,
        normalized_result=failed_normalized, limitations=failed_normalized.limitations,
    )
    assert finalize_experiment_record_v5(failed, failed_result, ()).bounded_scientific_evidence.blocks == ()
    with pytest.raises(ExperimentRecordV5Error, match="unavailable"):
        finalize_experiment_record_v5(failed, failed_result, (observation,))


@pytest.mark.parametrize("unsafe", (
    "/Users/alice/private/result.json", "```python\nprint('x')", "<script>alert(1)</script>",
    "Traceback: raw execution log", "-----BEGIN PRIVATE KEY-----",
    "https://user:password@example.invalid/result", "token=credential-value",
    '{"arbitrary":"json"}',
))
def test_v5_rejects_private_executable_or_log_evidence(unsafe: str) -> None:
    with pytest.raises(ExperimentRecordV5Error):
        ScientificEvidenceBlock("evidence-unsafe", EvidenceKind.PROSE, "Unsafe", unsafe)


def test_v5_rejects_nonfinite_arbitrary_and_oversized_evidence() -> None:
    with pytest.raises(ExperimentRecordV5Error, match="finite"):
        ScientificEvidenceBlock("evidence-nan", EvidenceKind.SCALAR, "NaN", float("nan"))
    with pytest.raises(ExperimentRecordV5Error, match="scalar"):
        ScientificEvidenceBlock(
            "evidence-nested", EvidenceKind.TABLE, "Nested",
            {"columns": ("Value",), "rows": (({"arbitrary": "nested"},),)},
        )
    lifecycle, result = _result()
    blocks = tuple(
        ScientificEvidenceBlock(
            f"evidence-large-{index}", EvidenceKind.PROSE, f"Finding {index}",
            "bounded observation " * 100, _source(result),
        ) for index in range(40)
    )
    with pytest.raises(ExperimentRecordV5Error, match="byte limit"):
        finalize_experiment_record_v5(lifecycle, result, blocks)


@pytest.mark.parametrize("schema", (
    "experiment-record/v1", "experiment-record/v2", "experiment-record/v3", "experiment-record/v4",
))
def test_exact_v5_consumer_rejects_every_historical_record(schema: str) -> None:
    with pytest.raises(ExperimentRecordV5Error, match="fields mismatch"):
        validate_experiment_record_v5({"schema": schema})
