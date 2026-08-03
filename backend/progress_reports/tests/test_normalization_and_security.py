from __future__ import annotations

import json

import pytest

from backend.progress_reports.contracts import (
    MAX_REPORT_BYTES,
    PROGRESS_REPORT_SCHEMA_V1,
    ChainState,
)
from backend.progress_reports.normalization import ProgressReportNormalizer
from backend.progress_reports.security import UnsafeProgressReportError
from backend.workflow_packages.serialization import canonical_json

from .factories import legacy_report_bytes, native_report, report_bytes


def test_native_normalization_is_deterministic() -> None:
    normalizer = ProgressReportNormalizer()
    content = report_bytes(native_report())

    assert normalizer.normalize(content) == normalizer.normalize(content)
    assert normalizer.normalize(content).unavailable_fields == ()


def test_legacy_original_semantics_remain_ambiguous_without_fabrication() -> None:
    normalizer = ProgressReportNormalizer()
    content = legacy_report_bytes()
    record = normalizer.normalize(content)

    assert record.source_schema_version == PROGRESS_REPORT_SCHEMA_V1
    assert record.context_before_checksum is None
    assert record.context_after_checksum is None
    assert record.legacy_context_checksum is not None
    assert record.report_content_checksum is None
    assert record.skill_pins == record.template_pins == ()
    assert record.chain_state is ChainState.LEGACY_CHAIN_WITH_WARNINGS
    assert "context_before_checksum" in record.unavailable_fields
    assert normalizer.normalize(content) == record


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("sk-proj-fictionalsecret123", "secret-like"),
        ("/Users/fictional/private/report.json", "absolute path"),
        ("<script>alert('fictional')</script>", "hostile script"),
        ("bad\u0001control", "control"),
    ],
)
def test_unsafe_uploaded_text_is_rejected(replacement: str, message: str) -> None:
    payload = native_report().to_dict()
    payload["current_state"] = replacement
    content = json.dumps(payload).encode("utf-8")

    with pytest.raises(UnsafeProgressReportError, match=message):
        ProgressReportNormalizer().normalize(content)


def test_unsupported_schema_and_oversized_report_are_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        ProgressReportNormalizer().normalize(
            canonical_json({"schema_version": "progress-report/v9"}).encode()
        )
    with pytest.raises(UnsafeProgressReportError, match="oversized"):
        ProgressReportNormalizer().normalize(b"{" + b" " * MAX_REPORT_BYTES + b"}")
    with pytest.raises(UnsafeProgressReportError, match="UTF-8"):
        ProgressReportNormalizer().normalize(b"\xff\xfe")


def test_benign_html_is_retained_as_untrusted_text_for_projection_escaping() -> None:
    report = native_report(current_state="<b>Fictional state</b>")
    record = ProgressReportNormalizer().normalize(report_bytes(report))

    assert record.current_state == "<b>Fictional state</b>"
