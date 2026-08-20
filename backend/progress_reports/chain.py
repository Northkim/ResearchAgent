"""Deterministic, non-merging Progress Report chain validation."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import (
    PROGRESS_REPORT_SCHEMA_V1,
    ChainState,
    NormalizedProgressRecord,
    ProgressStatus,
    UploadedProgressReport,
)


@dataclass(frozen=True, slots=True)
class ChainValidation:
    state: ChainState
    accepted_for_projection: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class ProgressReportChainValidator:
    def validate(
        self,
        candidate: NormalizedProgressRecord,
        history: tuple[UploadedProgressReport, ...],
    ) -> ChainValidation:
        normalized_history = tuple(
            item.normalized_record
            for item in history
            if item.normalized_record is not None and item.accepted_for_projection
        )
        same_scope = tuple(
            item
            for item in normalized_history
            if item.project_id == candidate.project_id
            and item.package_id == candidate.package_id
            and item.package_checksum == candidate.package_checksum
            and item.workflow_id == candidate.workflow_id
            and item.workflow_version == candidate.workflow_version
        )
        same_round = tuple(
            item for item in same_scope if item.execution_round == candidate.execution_round
        )
        if same_round and all(item.report_id != candidate.report_id for item in same_round):
            # A terminal COMPLETED report supersedes a stale IN_PROGRESS
            # checkpoint of the same exact scope/round when that checkpoint has
            # no accepted successor. This is the round's eventual outcome, not
            # a competing branch: two COMPLETED reports for one round remain a
            # conflict, and any accepted later round chained from the
            # checkpoint blocks the supersession.
            supersedable = all(
                item.status is ProgressStatus.IN_PROGRESS
                and not any(
                    other.previous_report_id == item.report_id
                    for other in normalized_history
                )
                for item in same_round
            )
            if not (
                candidate.status is ProgressStatus.COMPLETED and supersedable
            ):
                return ChainValidation(
                    state=ChainState.BRANCHED_HISTORY,
                    accepted_for_projection=False,
                    errors=("another accepted report already occupies this execution round",),
                )
            superseding_checkpoint = True
        else:
            superseding_checkpoint = False

        legacy = candidate.source_schema_version == PROGRESS_REPORT_SCHEMA_V1
        if candidate.execution_round == 1:
            if candidate.previous_report_id is not None:
                return ChainValidation(
                    state=ChainState.IDENTITY_CONFLICT,
                    accepted_for_projection=False,
                    errors=("round 1 must not reference a previous report",),
                )
            if legacy:
                return ChainValidation(
                    state=ChainState.LEGACY_CHAIN_WITH_WARNINGS,
                    accepted_for_projection=True,
                    warnings=(
                        "legacy round accepted without context-transition verification",
                    ),
                )
            return ChainValidation(
                state=ChainState.VALID_CHAIN,
                accepted_for_projection=True,
                warnings=(
                    (
                        "terminal report supersedes an earlier IN_PROGRESS "
                        "checkpoint for this execution round",
                    )
                    if superseding_checkpoint
                    else ()
                ),
            )

        if candidate.previous_report_id is None:
            return ChainValidation(
                state=ChainState.INCOMPLETE_CHAIN,
                accepted_for_projection=False,
                errors=("later round does not identify its predecessor",),
            )
        predecessor_upload = next(
            (
                item
                for item in history
                if item.report_id == candidate.previous_report_id
                and item.normalized_record is not None
                and item.accepted_for_projection
            ),
            None,
        )
        if predecessor_upload is None:
            return ChainValidation(
                state=ChainState.INCOMPLETE_CHAIN,
                accepted_for_projection=False,
                errors=("previous report is not present in accepted history",),
            )
        predecessor = predecessor_upload.normalized_record
        assert predecessor is not None
        if (
            predecessor.project_id != candidate.project_id
            or predecessor.package_id != candidate.package_id
            or predecessor.package_checksum != candidate.package_checksum
            or predecessor.workflow_id != candidate.workflow_id
            or predecessor.workflow_version != candidate.workflow_version
        ):
            return ChainValidation(
                state=ChainState.IDENTITY_CONFLICT,
                accepted_for_projection=False,
                errors=("previous report belongs to another project/package/workflow",),
            )
        if (
            candidate.previous_report_checksum is not None
            and candidate.previous_report_checksum != predecessor.report_checksum
        ):
            return ChainValidation(
                state=ChainState.IDENTITY_CONFLICT,
                accepted_for_projection=False,
                errors=("previous report checksum does not resolve",),
            )
        if candidate.execution_round != predecessor.execution_round + 1:
            return ChainValidation(
                state=ChainState.INCOMPLETE_CHAIN,
                accepted_for_projection=False,
                errors=("execution round is not monotonic from its predecessor",),
            )
        if (
            predecessor.context_after_checksum is not None
            and candidate.context_before_checksum is not None
            and predecessor.context_after_checksum != candidate.context_before_checksum
        ):
            return ChainValidation(
                state=ChainState.CONTINUITY_CONFLICT,
                accepted_for_projection=False,
                errors=("context transition checksum does not continue the predecessor",),
            )
        if (
            predecessor.status is ProgressStatus.COMPLETED
            and not (candidate.continuation_reason or "").strip()
        ):
            return ChainValidation(
                state=ChainState.CONTINUITY_CONFLICT,
                accepted_for_projection=False,
                errors=("a completed report requires a new-request continuation reason",),
            )
        if legacy or predecessor.source_schema_version == PROGRESS_REPORT_SCHEMA_V1:
            return ChainValidation(
                state=ChainState.LEGACY_CHAIN_WITH_WARNINGS,
                accepted_for_projection=True,
                warnings=("chain includes legacy context semantics",),
            )
        return ChainValidation(
            state=ChainState.VALID_CHAIN,
            accepted_for_projection=True,
            warnings=(
                (
                    "terminal report supersedes an earlier IN_PROGRESS "
                    "checkpoint for this execution round",
                )
                if superseding_checkpoint
                else ()
            ),
        )
