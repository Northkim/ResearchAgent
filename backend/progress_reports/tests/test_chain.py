from __future__ import annotations

from dataclasses import replace

from backend.progress_reports.chain import ProgressReportChainValidator
from backend.progress_reports.contracts import ChainState, ProgressStatus
from backend.progress_reports.normalization import ProgressReportNormalizer

from .factories import HASH_A, HASH_B, HASH_C, native_report, report_bytes


def _normalized(report):
    return ProgressReportNormalizer().normalize(report_bytes(report))


def _accepted(report):
    from backend.progress_reports.contracts import UploadedProgressReport, ValidationStatus

    return UploadedProgressReport(
        receipt_id="fictional-receipt-" + report.report_id,
        project_id=report.project_id,
        workflow_instance_id="wfi-00000000000000000000000000000001",
        package_id=report.package_id,
        package_checksum=report.package_checksum,
        report_id=report.report_id,
        report_checksum=report.report_checksum,
        report_schema_version=report.schema_version,
        original_report_checksum=HASH_A,
        original_report_size=1,
        original_report_media_type="application/json",
        original_storage_key="fictional/report.json",
        envelope_checksum=HASH_B,
        uploaded_at="2026-08-03T09:00:00Z",
        received_at="2026-08-03T09:00:00Z",
        uploader_type="local-cli",
        client_version="fictional/1.0",
        source_path_hint="memory/progress/reports/fictional.json",
        validation_status=ValidationStatus.ACCEPTED,
        validation_errors=(),
        validation_warnings=(),
        chain_state=ChainState.VALID_CHAIN,
        accepted_for_projection=True,
        normalized_record=_normalized(report),
    )


def test_round_one_and_valid_round_two() -> None:
    validator = ProgressReportChainValidator()
    first = native_report(context_after_checksum=HASH_B)
    second = native_report(
        execution_round=2,
        previous=first,
        context_before_checksum=HASH_B,
        context_after_checksum=HASH_C,
    )

    assert validator.validate(_normalized(first), ()).state is ChainState.VALID_CHAIN
    result = validator.validate(_normalized(second), (_accepted(first),))
    assert result.state is ChainState.VALID_CHAIN
    assert result.accepted_for_projection


def test_missing_predecessor_context_mismatch_and_cross_package_are_blocked() -> None:
    validator = ProgressReportChainValidator()
    first = native_report(context_after_checksum=HASH_B)
    missing = replace(
        native_report(execution_round=2, previous=first),
        previous_report_id="prv2-" + "9" * 64,
    ).with_computed_identity()
    mismatch = native_report(
        execution_round=2,
        previous=first,
        context_before_checksum=HASH_A,
    )
    other_package = native_report(
        execution_round=2,
        previous=first,
        package_id="another-fictional-package",
    )

    assert validator.validate(_normalized(missing), ()).state is ChainState.INCOMPLETE_CHAIN
    assert (
        validator.validate(_normalized(mismatch), (_accepted(first),)).state
        is ChainState.CONTINUITY_CONFLICT
    )
    assert (
        validator.validate(_normalized(other_package), (_accepted(first),)).state
        is ChainState.IDENTITY_CONFLICT
    )


def test_duplicate_round_is_branch_and_non_monotonic_round_is_incomplete() -> None:
    validator = ProgressReportChainValidator()
    first = native_report()
    branch = native_report(current_state="Fictional branch.")
    skipped = native_report(execution_round=3, previous=first)

    assert (
        validator.validate(_normalized(branch), (_accepted(first),)).state
        is ChainState.BRANCHED_HISTORY
    )
    assert (
        validator.validate(_normalized(skipped), (_accepted(first),)).state
        is ChainState.INCOMPLETE_CHAIN
    )


def test_terminal_completed_supersedes_stale_in_progress_checkpoint() -> None:
    validator = ProgressReportChainValidator()
    checkpoint = native_report(
        status=ProgressStatus.IN_PROGRESS,
        current_state="Search plan review.",
    )
    terminal = native_report(
        status=ProgressStatus.COMPLETED,
        current_state="Round completed with selected papers.",
    )
    result = validator.validate(_normalized(terminal), (_accepted(checkpoint),))
    assert result.state is ChainState.VALID_CHAIN
    assert result.accepted_for_projection
    assert "supersedes" in result.warnings[0]


def test_completed_duplicate_of_completed_round_still_branches() -> None:
    validator = ProgressReportChainValidator()
    first = native_report(
        status=ProgressStatus.COMPLETED,
        current_state="First completed outcome.",
    )
    second = native_report(
        status=ProgressStatus.COMPLETED,
        current_state="Second completed outcome.",
    )
    assert (
        validator.validate(_normalized(second), (_accepted(first),)).state
        is ChainState.BRANCHED_HISTORY
    )


def test_checkpoint_with_accepted_successor_blocks_supersession() -> None:
    validator = ProgressReportChainValidator()
    checkpoint = native_report(status=ProgressStatus.IN_PROGRESS)
    successor = native_report(
        execution_round=2,
        previous=checkpoint,
        context_before_checksum=checkpoint.context_after_checksum,
    )
    terminal = native_report(
        status=ProgressStatus.COMPLETED,
        current_state="A different terminal outcome.",
    )
    result = validator.validate(
        _normalized(terminal),
        (_accepted(checkpoint), _accepted(successor)),
    )
    assert result.state is ChainState.BRANCHED_HISTORY
    assert not result.accepted_for_projection


def test_completed_round_requires_explicit_new_request_reason() -> None:
    validator = ProgressReportChainValidator()
    first = native_report(status=ProgressStatus.COMPLETED)
    unjustified = native_report(
        execution_round=2,
        previous=first,
        context_before_checksum=first.context_after_checksum,
    )
    justified = native_report(
        execution_round=2,
        previous=first,
        context_before_checksum=first.context_after_checksum,
        continuation_reason="The owner supplied a new fictional request.",
    )

    assert (
        validator.validate(_normalized(unjustified), (_accepted(first),)).state
        is ChainState.CONTINUITY_CONFLICT
    )
    assert (
        validator.validate(_normalized(justified), (_accepted(first),)).state
        is ChainState.VALID_CHAIN
    )
