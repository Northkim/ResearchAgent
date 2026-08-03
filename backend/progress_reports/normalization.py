"""Native v0.2 validation and explicit v0.1 compatibility normalization."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from backend.workflow_packages.serialization import canonical_hash, sha256_bytes
from backend.workflow_packages.security import require_sha256

from .contracts import (
    EXPERIMENTAL_DECLARATION,
    NORMALIZED_SCHEMA_VERSION,
    NORMALIZER_VERSION,
    PROGRESS_REPORT_SCHEMA_V1,
    PROGRESS_REPORT_SCHEMA_V2,
    ChainState,
    NormalizedProgressRecord,
    OutputArtifactReference,
    ProgressReportV2,
    ProgressStatus,
)
from .security import parse_safe_json_document

_V1_REQUIRED = {
    "report_id",
    "package_id",
    "package_checksum",
    "project_identity",
    "workflow_id",
    "workflow_version",
    "skill_versions",
    "template_version",
    "execution_round",
    "harness_identity",
    "started_at",
    "completed_at",
    "status",
    "completed_work",
    "current_state",
    "next_recommended_action",
    "output_files",
    "context_checksum",
    "warnings",
    "errors",
    "unresolved_questions",
    "continuation_instructions",
    "schema_version",
    "report_checksum",
}


class ProgressReportNormalizer:
    """Convert untrusted report bytes into a deterministic cloud record."""

    def normalize(self, content: bytes) -> NormalizedProgressRecord:
        payload = parse_safe_json_document(content)
        schema = payload.get("schema_version")
        if schema == PROGRESS_REPORT_SCHEMA_V2:
            return self._normalize_v2(payload, content)
        if schema == PROGRESS_REPORT_SCHEMA_V1:
            return self._normalize_v1(payload, content)
        raise ValueError("unsupported Progress Report schema")

    @staticmethod
    def _normalize_v2(
        payload: Mapping[str, Any],
        content: bytes,
    ) -> NormalizedProgressRecord:
        report = ProgressReportV2.from_dict(payload)
        return NormalizedProgressRecord(
            normalized_schema_version=NORMALIZED_SCHEMA_VERSION,
            source_schema_version=PROGRESS_REPORT_SCHEMA_V2,
            normalizer_version=NORMALIZER_VERSION,
            report_id=report.report_id,
            report_checksum=report.report_checksum,
            report_content_checksum=report.report_content_checksum,
            original_report_checksum=sha256_bytes(content),
            package_id=report.package_id,
            package_schema_version=report.package_schema_version,
            package_checksum=report.package_checksum,
            project_id=report.project_id,
            workflow_id=report.workflow_id,
            workflow_version=report.workflow_version,
            workflow_checksum=report.workflow_checksum,
            execution_round=report.execution_round,
            harness_type=report.harness_type,
            harness_version=report.harness_version,
            harness_session_id=report.harness_session_id,
            previous_report_id=report.previous_report_id,
            previous_report_checksum=report.previous_report_checksum,
            started_at=report.started_at,
            completed_at=report.completed_at,
            status=report.status,
            completed_work=report.completed_work,
            current_state=report.current_state,
            next_recommended_action=report.next_recommended_action,
            continuation_reason=report.continuation_reason,
            output_artifacts=report.output_artifacts,
            context_before_checksum=report.context_before_checksum,
            context_after_checksum=report.context_after_checksum,
            legacy_context_checksum=None,
            warnings=report.warnings,
            errors=report.errors,
            unresolved_questions=report.unresolved_questions,
            continuation_instructions=report.continuation_instructions,
            skill_pins=report.skill_pins,
            template_pins=report.template_pins,
            generated_at=report.generated_at,
            experimental_declaration=report.experimental_declaration,
            compatibility_assumptions=(),
            unavailable_fields=(),
            evidence_limitations=(),
            chain_state=ChainState.VALID_CHAIN,
        )

    @staticmethod
    def _normalize_v1(
        payload: Mapping[str, Any],
        content: bytes,
    ) -> NormalizedProgressRecord:
        missing = _V1_REQUIRED - set(payload)
        unknown = set(payload) - (_V1_REQUIRED | {"previous_report_id"})
        if missing or unknown:
            raise ValueError(
                "legacy Progress Report fields mismatch"
                + (f"; missing={sorted(missing)}" if missing else "")
                + (f"; unknown={sorted(unknown)}" if unknown else "")
            )
        checksum_payload = dict(payload)
        expected_checksum = checksum_payload["report_checksum"]
        checksum_payload["report_checksum"] = None
        if expected_checksum != canonical_hash(checksum_payload):
            raise ValueError("legacy Progress Report checksum mismatch")
        for field in (
            "report_id",
            "package_id",
            "project_identity",
            "workflow_id",
            "workflow_version",
            "template_version",
            "harness_identity",
            "started_at",
            "completed_at",
            "current_state",
            "next_recommended_action",
        ):
            if not isinstance(payload[field], str) or not payload[field].strip():
                raise ValueError(f"legacy {field} must be a non-empty string")
        require_sha256(str(payload["package_checksum"]), "legacy package_checksum")
        require_sha256(str(payload["context_checksum"]), "legacy context_checksum")
        require_sha256(str(payload["report_checksum"]), "legacy report_checksum")
        for field in (
            "skill_versions",
            "completed_work",
            "warnings",
            "errors",
            "unresolved_questions",
            "continuation_instructions",
        ):
            value = payload[field]
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise ValueError(f"legacy {field} must be an array of strings")
        if payload.get("previous_report_id") is not None and not isinstance(
            payload["previous_report_id"], str
        ):
            raise ValueError("legacy previous_report_id must be a string or null")
        try:
            started = datetime.fromisoformat(payload["started_at"].replace("Z", "+00:00"))
            completed = datetime.fromisoformat(
                payload["completed_at"].replace("Z", "+00:00")
            )
        except ValueError as error:
            raise ValueError("legacy timestamps must be ISO-8601") from error
        if started.tzinfo is None or completed.tzinfo is None or completed < started:
            raise ValueError("legacy timestamps require timezones and monotonic order")
        status = ProgressStatus(payload["status"])
        if not isinstance(payload["execution_round"], int) or payload["execution_round"] < 1:
            raise ValueError("legacy execution_round must be positive")
        if not isinstance(payload["output_files"], list):
            raise ValueError("legacy output_files must be an array")
        output_values: list[OutputArtifactReference] = []
        for item in payload["output_files"]:
            if not isinstance(item, dict) or set(item) != {"relative_path", "checksum"}:
                raise ValueError("legacy output file fields mismatch")
            output_values.append(
                OutputArtifactReference(
                    relative_path=item["relative_path"],
                    artifact_kind="LEGACY_OUTPUT",
                    media_type="application/octet-stream",
                    checksum=item["checksum"],
                    size=None,
                )
            )
        outputs = tuple(output_values)
        harness_identity = str(payload["harness_identity"]).lower()
        harness_type = (
            "codex"
            if "codex" in harness_identity
            else "claude-code"
            if "claude" in harness_identity
            else "legacy-harness"
        )
        return NormalizedProgressRecord(
            normalized_schema_version=NORMALIZED_SCHEMA_VERSION,
            source_schema_version=PROGRESS_REPORT_SCHEMA_V1,
            normalizer_version=NORMALIZER_VERSION,
            report_id=str(payload["report_id"]),
            report_checksum=str(payload["report_checksum"]),
            report_content_checksum=None,
            original_report_checksum=sha256_bytes(content),
            package_id=str(payload["package_id"]),
            package_schema_version=None,
            package_checksum=str(payload["package_checksum"]),
            project_id=str(payload["project_identity"]),
            workflow_id=str(payload["workflow_id"]),
            workflow_version=str(payload["workflow_version"]),
            workflow_checksum=None,
            execution_round=int(payload["execution_round"]),
            harness_type=harness_type,
            harness_version=None,
            harness_session_id=None,
            previous_report_id=payload.get("previous_report_id"),
            previous_report_checksum=None,
            started_at=str(payload["started_at"]),
            completed_at=str(payload["completed_at"]),
            status=status,
            completed_work=tuple(payload["completed_work"]),
            current_state=str(payload["current_state"]),
            next_recommended_action=str(payload["next_recommended_action"]),
            continuation_reason=None,
            output_artifacts=outputs,
            context_before_checksum=None,
            context_after_checksum=None,
            legacy_context_checksum=str(payload["context_checksum"]),
            warnings=tuple(payload["warnings"]),
            errors=tuple(payload["errors"]),
            unresolved_questions=tuple(payload["unresolved_questions"]),
            continuation_instructions=tuple(payload["continuation_instructions"]),
            skill_pins=(),
            template_pins=(),
            generated_at=None,
            experimental_declaration="LEGACY_PROGRESS_REPORT_V0_1_COMPATIBILITY",
            compatibility_assumptions=(
                "project_identity is interpreted as cloud project_id",
                "legacy context_checksum is retained without before/after meaning",
                "legacy output references lack media type, size, and artifact kind",
            ),
            unavailable_fields=(
                "report_content_checksum",
                "package_schema_version",
                "workflow_checksum",
                "harness_version",
                "harness_session_id",
                "previous_report_checksum",
                "context_before_checksum",
                "context_after_checksum",
                "skill_pin_checksums",
                "template_pin_identity_and_checksum",
                "generated_at",
                "continuation_reason",
            ),
            evidence_limitations=(
                "v0.1 cannot prove a context transition",
                "v0.1 report identity was not derived from normalized content",
                "fresh-session process facts remain outside file-only evidence",
            ),
            chain_state=ChainState.LEGACY_CHAIN_WITH_WARNINGS,
        )
