"""Capability-owned reference projection into the forward v5 evidence carrier."""

from __future__ import annotations

import math
from typing import Any, Mapping

from backend.artifact_references.generic_experiment_contracts import ExperimentRecordV4
from backend.artifact_references.generic_experiment_v5_contracts import (
    EvidenceKind,
    EvidenceSourceKind,
    EvidenceSourceRef,
    ExperimentRecordV5,
    ExperimentRecordV5Error,
    ScientificEvidenceBlock,
    finalize_experiment_record_v5,
)

from .experiment_capability_runtime import CapabilityEvaluationResult

REFERENCE_EVALUATION_SCHEMA = "reagent.sklearn-tabular-classification-evaluation/v0.1"


def sklearn_reference_evidence_blocks(
    result: CapabilityEvaluationResult,
) -> tuple[ScientificEvidenceBlock, ...]:
    """Project only the reviewed reference payload; Generic Core never calls this."""

    if result.receipt.evaluation_schema != REFERENCE_EVALUATION_SCHEMA:
        raise ExperimentRecordV5Error("reference Capability evaluation identity is invalid")
    if result.receipt.validity.value != "VALID":
        return ()
    payload = result.result_payload
    if not isinstance(payload, Mapping) or payload.get("schema_version") != "reagent.experiment-result/v0.2":
        raise ExperimentRecordV5Error("reference Capability result schema is invalid")
    conditions = payload.get("conditions")
    if not isinstance(conditions, list) or not conditions or len(conditions) > 40:
        raise ExperimentRecordV5Error("reference Capability conditions are invalid")
    rows: list[tuple[Any, ...]] = []
    series: list[dict[str, Any]] = []
    first_metric: str | None = None
    for raw in conditions:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("condition"), str):
            raise ExperimentRecordV5Error("reference Capability condition is invalid")
        metrics = raw.get("metrics")
        if not isinstance(metrics, Mapping) or not metrics or len(metrics) > 20:
            raise ExperimentRecordV5Error("reference Capability metrics are invalid")
        for name, value in sorted(metrics.items()):
            if (
                not isinstance(name, str) or not name.strip()
                or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ExperimentRecordV5Error("reference Capability metric is invalid")
            rows.append((raw["condition"], name, value))
            first_metric = first_metric or name
        if first_metric in metrics:
            series.append({"x": raw["condition"], "y": metrics[first_metric]})
    source = (EvidenceSourceRef(
        EvidenceSourceKind.RESULT_PAYLOAD, "result-payload",
        result.receipt.result_payload_checksum,
    ),)
    blocks = [
        ScientificEvidenceBlock(
            "evidence-reference-condition-count", EvidenceKind.SCALAR,
            "Evaluated conditions", len(conditions), source,
        ),
        ScientificEvidenceBlock(
            "evidence-reference-condition-table", EvidenceKind.TABLE,
            "Condition observations",
            {"columns": ("Condition", "Measure", "Value"), "rows": tuple(rows)},
            source,
        ),
    ]
    if series:
        blocks.append(ScientificEvidenceBlock(
            "evidence-reference-condition-series", EvidenceKind.SERIES,
            f"{first_metric} by condition", tuple(series), source,
        ))
    return tuple(blocks)


def finalize_sklearn_reference_record_v5(
    lifecycle_record: ExperimentRecordV4,
    result: CapabilityEvaluationResult,
) -> ExperimentRecordV5:
    return finalize_experiment_record_v5(
        lifecycle_record, result, sklearn_reference_evidence_blocks(result),
    )
