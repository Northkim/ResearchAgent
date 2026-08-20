"""Cloud-only Progress Report ingestion, immutable history, and projection."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone

from backend.research.ports import ArtifactContentStorage
from backend.artifact_references.contracts import ArtifactDeclaration
from backend.workflow_packages.serialization import canonical_hash

from .chain import ProgressReportChainValidator
from .contracts import (
    ChainState,
    NormalizedProgressRecord,
    ProgressReportUploadEnvelope,
    ProgressUploadReceipt,
    ProjectProgressProjection,
    UploadedProgressReport,
    ValidationStatus,
)
from .normalization import ProgressReportNormalizer
from .ports import ProgressReportRepository
from .projection import build_projection
from .security import UnsafeProgressReportError


class ProgressReportService:
    """Receive report data; never execute or continue a research task."""

    def __init__(
        self,
        *,
        repository: ProgressReportRepository,
        content_storage: ArtifactContentStorage,
        commit_callback: Callable[[], None],
        workflow_identity_resolver: Callable[
            [ProgressReportUploadEnvelope, NormalizedProgressRecord | None, str | None],
            str,
        ],
        artifact_reference_service=None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._storage = content_storage
        self._commit = commit_callback
        self._resolve_workflow_identity = workflow_identity_resolver
        self._artifact_references = artifact_reference_service
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._normalizer = ProgressReportNormalizer()
        self._chain = ProgressReportChainValidator()

    def validate_report(self, content: bytes) -> NormalizedProgressRecord:
        """Validate untrusted bytes without storing or projecting them."""

        return self._normalizer.normalize(content)

    def upload(
        self,
        envelope: ProgressReportUploadEnvelope,
        *,
        workflow_instance_id: str | None = None,
        artifact_declarations: tuple[ArtifactDeclaration, ...] = (),
    ) -> ProgressUploadReceipt:
        content = envelope.original_report_bytes()
        derivation_record: NormalizedProgressRecord | None = None
        if not artifact_declarations and self._artifact_references is not None:
            try:
                derivation_record = self._normalizer.normalize(content)
            except ValueError:
                # Invalid reports retain their existing bounded audit behavior;
                # only valid reviewed Progress can derive canonical Artifacts.
                derivation_record = None
        self._repository.lock_report_identity(envelope.report_id)
        # Historical Packages may no longer be the Project's current Package.
        # An exact immutable replay can still be proven from the retained row,
        # and must remain retryable without guessing a new binding.
        exact_historical = tuple(
            item
            for item in self._repository.list_by_report_id(envelope.report_id)
            if item.project_id == envelope.project_id
            and item.package_id == envelope.package_id
            and item.package_checksum == envelope.package_checksum
            and item.report_checksum == envelope.report_checksum
            and item.original_report_checksum == envelope.original_report_checksum
        )
        # Only an ACCEPTED exact row is an idempotent replay. A previously
        # REJECTED exact row is retained audit evidence but must be re-validated
        # on retry so a later change of blocking conditions (for example a stale
        # IN_PROGRESS checkpoint superseded by the terminal report) can admit it.
        accepted_exact = tuple(
            item for item in exact_historical if item.accepted_for_projection
        )
        if len(accepted_exact) == 1:
            historical = accepted_exact[0]
            derived_replay = False
            if (
                not artifact_declarations
                and derivation_record is not None
                and historical.accepted_for_projection
            ):
                artifact_declarations = (
                    self._artifact_references.derive_reviewed_progress_declarations(
                        workflow_instance_id=historical.workflow_instance_id,
                        normalized=derivation_record,
                    )
                )
                derived_replay = bool(artifact_declarations)
            if derived_replay:
                # Repair the exact B7 adapter omission without creating another
                # Progress row. Immutable report metadata and the reviewed
                # Capsule contract fully determine this promotion.
                assert derivation_record is not None
                self._artifact_references.promote_progress_artifacts(
                    report=historical,
                    normalized=derivation_record,
                    declarations=artifact_declarations,
                )
                self._commit()
            self._assert_artifact_replay(historical.receipt_id, artifact_declarations)
            return self._receipt(historical, idempotent=True)
        if len(accepted_exact) > 1:
            raise ValueError("immutable Progress Report identity is ambiguous")
        resolved_instance_id = self._resolve_workflow_identity(
            envelope,
            None,
            workflow_instance_id,
        )
        replay = self._repository.find_exact(
            project_id=envelope.project_id,
            workflow_instance_id=resolved_instance_id,
            package_id=envelope.package_id,
            package_checksum=envelope.package_checksum,
            report_id=envelope.report_id,
            report_checksum=envelope.report_checksum,
            original_report_checksum=envelope.original_report_checksum,
        )
        if replay is not None and replay.accepted_for_projection:
            derived_replay = False
            if (
                not artifact_declarations
                and derivation_record is not None
                and replay.accepted_for_projection
            ):
                artifact_declarations = (
                    self._artifact_references.derive_reviewed_progress_declarations(
                        workflow_instance_id=resolved_instance_id,
                        normalized=derivation_record,
                    )
                )
                derived_replay = bool(artifact_declarations)
            if derived_replay:
                assert derivation_record is not None
                self._artifact_references.promote_progress_artifacts(
                    report=replay,
                    normalized=derivation_record,
                    declarations=artifact_declarations,
                )
                self._commit()
            self._assert_artifact_replay(replay.receipt_id, artifact_declarations)
            return self._receipt(replay, idempotent=True)

        identity_errors: list[str] = []
        for existing in self._repository.list_by_report_id(envelope.report_id):
            # Rejected audit evidence is retained, but cannot claim a
            # content-addressed identity and block the later canonical report.
            # Only an accepted immutable report is authoritative for collision
            # checks. Exact rejected retries were already handled above.
            if not existing.accepted_for_projection:
                continue
            if existing.report_checksum != envelope.report_checksum:
                identity_errors.append("report ID already exists with another checksum")
            elif existing.original_report_checksum != envelope.original_report_checksum:
                identity_errors.append("report ID already exists with different original bytes")
            if (
                existing.project_id != envelope.project_id
                or existing.package_id != envelope.package_id
            ):
                identity_errors.append("report ID is already bound to another identity")
        for existing in self._repository.list_by_original_checksum(
            envelope.original_report_checksum
        ):
            if not existing.accepted_for_projection:
                continue
            if (
                existing.project_id != envelope.project_id
                or existing.package_id != envelope.package_id
                or existing.package_checksum != envelope.package_checksum
            ):
                identity_errors.append(
                    "original report checksum is already bound to an incompatible identity"
                )
        normalized = None
        validation_errors: list[str] = []
        validation_warnings: list[str] = []
        try:
            normalized = self._normalizer.normalize(content)
            verified_instance_id = self._resolve_workflow_identity(
                envelope,
                normalized,
                workflow_instance_id,
            )
            if verified_instance_id != resolved_instance_id:
                raise ValueError("Progress Workflow Instance resolution changed")
            if normalized.source_schema_version != envelope.report_schema_version:
                validation_errors.append("envelope report schema does not match report")
            if normalized.project_id != envelope.project_id:
                identity_errors.append("envelope project does not match report")
            if normalized.package_id != envelope.package_id:
                identity_errors.append("envelope package does not match report")
            if normalized.package_checksum != envelope.package_checksum:
                identity_errors.append("envelope package checksum does not match report")
            if normalized.report_id != envelope.report_id:
                identity_errors.append("envelope report ID does not match report")
            if normalized.report_checksum != envelope.report_checksum:
                identity_errors.append("envelope report checksum does not match report")
            validation_warnings.extend(normalized.compatibility_assumptions)
            validation_warnings.extend(normalized.evidence_limitations)
        except UnsafeProgressReportError:
            # Secret-like, path-bearing, hostile, or otherwise unsafe bytes are
            # rejected before artifact storage. They are not safe audit evidence.
            raise
        except ValueError as error:
            validation_errors.append(str(error))

        storage_key = self._storage_key(envelope)
        self._storage.write_immutable(
            storage_key,
            content,
            media_type=envelope.original_report_media_type,
        )
        received_at = self._timestamp(self._clock())
        receipt_id = self._receipt_id(envelope)
        chain_state = (
            ChainState.IDENTITY_CONFLICT
            if identity_errors
            else ChainState.INCOMPLETE_CHAIN
        )
        accepted = False
        if normalized is not None and not validation_errors and not identity_errors:
            history = self._repository.list_for_project(
                envelope.project_id,
                workflow_instance_id=resolved_instance_id,
            )
            chain = self._chain.validate(normalized, history)
            chain_state = chain.state
            accepted = chain.accepted_for_projection
            validation_errors.extend(chain.errors)
            validation_warnings.extend(chain.warnings)
            normalized = replace(normalized, chain_state=chain.state)
        else:
            validation_errors.extend(identity_errors)
            if normalized is not None:
                normalized = replace(normalized, chain_state=chain_state)

        validation_status = (
            ValidationStatus.ACCEPTED
            if accepted and not validation_errors
            else ValidationStatus.REJECTED
        )
        uploaded = UploadedProgressReport(
            receipt_id=receipt_id,
            project_id=envelope.project_id,
            workflow_instance_id=resolved_instance_id,
            package_id=envelope.package_id,
            package_checksum=envelope.package_checksum,
            report_id=envelope.report_id,
            report_checksum=envelope.report_checksum,
            report_schema_version=envelope.report_schema_version,
            original_report_checksum=envelope.original_report_checksum,
            original_report_size=envelope.original_report_size,
            original_report_media_type=envelope.original_report_media_type,
            original_storage_key=storage_key,
            envelope_checksum=envelope.envelope_checksum,
            uploaded_at=envelope.uploaded_at,
            received_at=received_at,
            uploader_type=envelope.uploader_type,
            client_version=envelope.client_version,
            source_path_hint=envelope.source_path_hint,
            validation_status=validation_status,
            validation_errors=tuple(dict.fromkeys(validation_errors)),
            validation_warnings=tuple(dict.fromkeys(validation_warnings)),
            chain_state=chain_state,
            accepted_for_projection=accepted and not validation_errors,
            normalized_record=normalized,
        )
        self._repository.append(uploaded)
        if (
            not artifact_declarations
            and uploaded.accepted_for_projection
            and normalized is not None
            and self._artifact_references is not None
        ):
            artifact_declarations = (
                self._artifact_references.derive_reviewed_progress_declarations(
                    workflow_instance_id=resolved_instance_id,
                    normalized=normalized,
                )
            )
        if artifact_declarations:
            if self._artifact_references is None or normalized is None:
                raise ValueError(
                    "canonical Artifact declaration service is unavailable"
                )
            self._artifact_references.promote_progress_artifacts(
                report=uploaded,
                normalized=normalized,
                declarations=artifact_declarations,
            )
        if uploaded.accepted_for_projection and normalized is not None:
            scoped_history = tuple(
                item
                for item in self._repository.list_for_project(
                    envelope.project_id,
                    package_id=envelope.package_id,
                    workflow_instance_id=resolved_instance_id,
                )
                if item.normalized_record is not None
                and item.normalized_record.workflow_id == normalized.workflow_id
                and item.normalized_record.workflow_version == normalized.workflow_version
            )
            projection = build_projection(scoped_history)
            if projection is not None:
                self._repository.save_projection(projection)
        self._commit()
        return self._receipt(uploaded, idempotent=False)

    def _assert_artifact_replay(
        self,
        receipt_id: str,
        declarations: tuple[ArtifactDeclaration, ...],
    ) -> None:
        if self._artifact_references is None:
            if declarations:
                raise ValueError("canonical Artifact declaration service is unavailable")
            return
        self._artifact_references.assert_progress_replay(receipt_id, declarations)

    def get_report(
        self,
        *,
        project_id: str,
        report_id: str,
        receipt_id: str | None = None,
    ) -> UploadedProgressReport | None:
        if receipt_id is not None:
            report = self._repository.get_receipt(receipt_id)
            if (
                report is None
                or report.project_id != project_id
                or report.report_id != report_id
            ):
                return None
            return report
        matches = tuple(
            item
            for item in self._repository.list_by_report_id(report_id)
            if item.project_id == project_id
        )
        if not matches:
            return None
        return min(
            matches,
            key=lambda item: (
                not item.accepted_for_projection,
                item.received_at,
                item.receipt_id,
            ),
        )

    def list_reports(
        self,
        *,
        project_id: str,
        package_id: str | None = None,
        workflow_instance_id: str | None = None,
    ) -> tuple[UploadedProgressReport, ...]:
        return self._repository.list_for_project(
            project_id,
            package_id=package_id,
            workflow_instance_id=workflow_instance_id,
        )

    def get_projection(
        self,
        *,
        project_id: str,
        package_id: str | None = None,
    ) -> ProjectProgressProjection | None:
        history = self._repository.list_for_project(project_id, package_id=package_id)
        accepted = tuple(
            item
            for item in history
            if item.accepted_for_projection and item.normalized_record is not None
        )
        if not accepted:
            return None
        latest = max(
            accepted,
            key=lambda item: (
                item.received_at,
                item.normalized_record.execution_round,  # type: ignore[union-attr]
                item.report_id,
            ),
        )
        record = latest.normalized_record
        assert record is not None
        stored = self._repository.get_projection(
            project_id=record.project_id,
            package_id=record.package_id,
            workflow_id=record.workflow_id,
            workflow_version=record.workflow_version,
        )
        scoped = tuple(
            item
            for item in accepted
            if item.normalized_record is not None
            and item.normalized_record.package_id == record.package_id
            and item.normalized_record.workflow_id == record.workflow_id
            and item.normalized_record.workflow_version == record.workflow_version
        )
        rebuilt = build_projection(scoped)
        if rebuilt is None:
            return None
        if stored is not None and stored.projection_checksum != rebuilt.projection_checksum:
            raise ValueError("stored progress projection does not match immutable history")
        return rebuilt

    def read_original(self, report: UploadedProgressReport) -> bytes:
        verification = self._storage.verify(
            report.original_storage_key,
            expected_checksum=report.original_report_checksum,
            expected_size=report.original_report_size,
        )
        if not verification.valid:
            raise ValueError("stored original Progress Report failed integrity verification")
        return self._storage.read(report.original_storage_key)

    @staticmethod
    def _storage_key(envelope: ProgressReportUploadEnvelope) -> str:
        digest = envelope.original_report_checksum.split(":", 1)[1]
        return (
            f"progress-reports/{envelope.project_id}/{envelope.package_id}/"
            f"{digest}.json"
        )

    @staticmethod
    def _receipt_id(envelope: ProgressReportUploadEnvelope) -> str:
        digest = canonical_hash(
            {
                "project_id": envelope.project_id,
                "package_id": envelope.package_id,
                "package_checksum": envelope.package_checksum,
                "report_id": envelope.report_id,
                "report_checksum": envelope.report_checksum,
                "original_report_checksum": envelope.original_report_checksum,
            }
        ).split(":", 1)[1]
        return f"progress-receipt-{digest}"

    @staticmethod
    def _timestamp(value: datetime) -> str:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("cloud clock must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _receipt(
        report: UploadedProgressReport,
        *,
        idempotent: bool,
    ) -> ProgressUploadReceipt:
        receipt = ProgressUploadReceipt(
            receipt_id=report.receipt_id,
            project_id=report.project_id,
            workflow_instance_id=report.workflow_instance_id,
            package_id=report.package_id,
            report_id=report.report_id,
            report_checksum=report.report_checksum,
            original_report_checksum=report.original_report_checksum,
            validation_status=report.validation_status,
            chain_state=report.chain_state,
            accepted_for_projection=report.accepted_for_projection,
            idempotent_replay=idempotent,
            uploaded_at=report.uploaded_at,
            received_at=report.received_at,
            warning_count=len(report.validation_warnings),
            error_count=len(report.validation_errors),
            receipt_checksum="sha256:" + "0" * 64,
        )
        return receipt.with_computed_checksum()
