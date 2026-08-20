from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from backend.local_projects.contracts import LocalPackageMetadata, LocalProject
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.progress_reports.aggregation import (
    ProjectProgressAggregationService,
    _readiness,
)
from backend.progress_reports.contracts import (
    ChainState,
    ProgressStatus,
    UploadedProgressReport,
    ValidationStatus,
)
from backend.progress_reports.normalization import ProgressReportNormalizer
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.workflow_packages.template import WORKFLOW_ID, WORKFLOW_VERSION

from .factories import HASH_A, HASH_B, HASH_C, native_report, report_bytes


def test_fixed_query_aggregation_handles_twenty_instances_and_one_thousand_reports() -> None:
    database = InMemoryDatabase()
    seed = InMemoryUnitOfWork(database)
    project_id = "project-77777777777777777777777777777777"
    package = LocalPackageMetadata(
        package_id="fictional-scale-package",
        package_schema_version="workflow-package/v0.1",
        package_checksum=HASH_C,
        manifest_checksum=HASH_A,
        zip_checksum=HASH_B,
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        workflow_checksum=HASH_A,
        archive_storage_key="fictional/scale.zip",
        file_count=1,
        package_size_bytes=1,
        generated_at="2026-08-07T00:00:00Z",
    )
    local_project = LocalProject(
        project_id=project_id,
        name="Fictional aggregation scale",
        research_topic="Fictional public scale topic",
        selected_workflow="LITERATURE_SEARCH",
        created_at="2026-08-07T00:00:00Z",
        updated_at="2026-08-07T00:00:00Z",
        current_package=package,
    )
    seed.local_projects.add(local_project)
    application = ProjectWorkspaceApplicationService(
        unit_of_work=seed,
        clock=lambda: datetime(2026, 8, 7, tzinfo=UTC),
    )
    application.initialize_project(local_project)
    seed.commit()
    initial = next(iter(database.project_workflow_instances.values()))
    for number in range(1, 20):
        mutation_scope = InMemoryUnitOfWork(database)
        ProjectWorkspaceApplicationService(
            unit_of_work=mutation_scope,
            clock=lambda: datetime(2026, 8, 7, tzinfo=UTC),
            instance_id_factory=lambda number=number: f"wfi-{number:032x}",
        ).create_instance(
            project_id=project_id,
            workflow_definition_id=WORKFLOW_ID,
            workflow_version=WORKFLOW_VERSION,
            capsule_id=initial.capsule_id or "",
            capsule_version=initial.capsule_version or "",
            display_name=f"Literature Search {number + 1}",
            base_revision=number,
        )

    report_scope = InMemoryUnitOfWork(database)
    base_record = ProgressReportNormalizer().normalize(
        report_bytes(native_report(project_id=project_id, package_id=package.package_id))
    )
    start = datetime(2026, 8, 7, tzinfo=UTC)
    instances = report_scope.workflow_foundation.list_workflow_instances(project_id)
    for instance_number, instance in enumerate(instances):
        for report_number in range(50):
            ordinal = instance_number * 50 + report_number
            activity = start + timedelta(minutes=ordinal)
            digest = f"{ordinal + 1:064x}"
            checksum = f"sha256:{digest}"
            normalized = replace(
                base_record,
                report_id=f"prv2-{digest}",
                report_checksum=checksum,
                package_id=f"scale-package-{instance_number}",
                execution_round=report_number + 1,
                current_state=f"Instance {instance_number} report {report_number}",
                started_at=(activity - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
                completed_at=activity.isoformat().replace("+00:00", "Z"),
            )
            report_scope.progress_reports.append(
                UploadedProgressReport(
                    receipt_id=f"progress-receipt-{digest}",
                    project_id=project_id,
                    workflow_instance_id=instance.workflow_instance_id,
                    package_id=normalized.package_id,
                    package_checksum=HASH_C,
                    report_id=normalized.report_id,
                    report_checksum=checksum,
                    report_schema_version=normalized.source_schema_version,
                    original_report_checksum=checksum,
                    original_report_size=100,
                    original_report_media_type="application/json",
                    original_storage_key=f"fictional/{digest}.json",
                    envelope_checksum=checksum,
                    uploaded_at=activity.isoformat().replace("+00:00", "Z"),
                    received_at=activity.isoformat().replace("+00:00", "Z"),
                    uploader_type="scale-test",
                    client_version="scale-test/1.0",
                    source_path_hint=f"memory/progress/reports/{digest}.json",
                    validation_status=ValidationStatus.ACCEPTED,
                    validation_errors=(),
                    validation_warnings=(),
                    chain_state=ChainState.VALID_CHAIN,
                    accepted_for_projection=True,
                    normalized_record=normalized,
                )
            )
    report_scope.commit()

    read_scope = InMemoryUnitOfWork(database)
    projection = ProjectProgressAggregationService(
        unit_of_work=read_scope,
        clock=lambda: datetime(2026, 8, 8, tzinfo=UTC),
    ).project_progress(project_id=project_id, history_limit=100)

    assert len(projection.instances) == 20
    assert projection.total_progress_report_count == 1_000
    assert projection.history_total == 1_000
    assert len(projection.history) == 100
    assert all(item.report_count == 50 for item in projection.instances)
    assert all(
        item.core_capability_maturity == "REVIEWED_CORE"
        for item in projection.instances
    )
    assert len({item.workflow_instance_id for item in projection.instances}) == 20
    assert projection.latest_project_activity_at == (
        start + timedelta(minutes=999)
    ).isoformat().replace("+00:00", "Z")


def test_optional_evidence_decision_precedes_materialization_projection() -> None:
    common = {
        "lifecycle": "ACTIVE",
        "installation_state": "ACKNOWLEDGED_CURRENT",
        "missing": (),
        "compatible_counts": {"manuscript": 1},
        "report_count": 0,
        "research_status": "NOT_STARTED",
        "result_count": 0,
        "stable_key": "review-local-experimental",
    }

    assert _readiness(**common, optional_decision_required=True) == (
        "WAITING_FOR_INPUT",
        "SELECT_INPUT",
    )
    assert _readiness(**common, optional_decision_required=False) == (
        "NEEDS_MATERIALIZATION",
        "MATERIALIZE",
    )


def test_aggregation_prefers_terminal_completed_round_representative() -> None:
    database = InMemoryDatabase()
    seed = InMemoryUnitOfWork(database)
    project_id = "project-88888888888888888888888888888888"
    package = LocalPackageMetadata(
        package_id="fictional-terminal-package",
        package_schema_version="workflow-package/v0.1",
        package_checksum=HASH_C,
        manifest_checksum=HASH_A,
        zip_checksum=HASH_B,
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        workflow_checksum=HASH_A,
        archive_storage_key="fictional/terminal.zip",
        file_count=1,
        package_size_bytes=1,
        generated_at="2026-08-07T00:00:00Z",
    )
    seed.local_projects.add(LocalProject(
        project_id=project_id,
        name="Fictional terminal supersession",
        research_topic="Fictional bounded topic",
        selected_workflow="LITERATURE_SEARCH",
        created_at="2026-08-07T00:00:00Z",
        updated_at="2026-08-07T00:00:00Z",
        current_package=package,
    ))
    local_project = seed.local_projects.get(project_id)
    application = ProjectWorkspaceApplicationService(
        unit_of_work=seed,
        clock=lambda: datetime(2026, 8, 7, tzinfo=UTC),
    )
    application.initialize_project(local_project)
    seed.commit()
    instance = next(iter(database.project_workflow_instances.values()))
    activity = "2026-08-07T10:00:00+00:00"
    base = ProgressReportNormalizer().normalize(
        report_bytes(native_report(
            project_id=project_id,
            package_id=package.package_id,
        ))
    )

    def row(record, receipt_suffix: str) -> UploadedProgressReport:
        return UploadedProgressReport(
            receipt_id=f"progress-receipt-{receipt_suffix}",
            project_id=project_id,
            workflow_instance_id=instance.workflow_instance_id,
            package_id=record.package_id,
            package_checksum=HASH_C,
            report_id=record.report_id,
            report_checksum=record.report_checksum,
            report_schema_version=record.source_schema_version,
            original_report_checksum=record.report_checksum,
            original_report_size=100,
            original_report_media_type="application/json",
            original_storage_key=f"fictional/{receipt_suffix}.json",
            envelope_checksum=record.report_checksum,
            uploaded_at=activity,
            received_at=activity,
            uploader_type="scale-test",
            client_version="scale-test/1.0",
            source_path_hint=f"memory/progress/reports/{receipt_suffix}.json",
            validation_status=ValidationStatus.ACCEPTED,
            validation_errors=(),
            validation_warnings=(),
            chain_state=ChainState.VALID_CHAIN,
            accepted_for_projection=True,
            normalized_record=record,
        )

    checkpoint = row(
        replace(
            base,
            status=ProgressStatus.IN_PROGRESS,
            report_id="prv2-" + "a" * 64,
            report_checksum="sha256:" + "a" * 64,
            completed_at=activity,
            started_at=activity,
            current_state="SEARCH_PLAN_DECISION_REQUIRED",
        ),
        "a" * 64,
    )
    terminal = row(
        replace(
            base,
            status=ProgressStatus.COMPLETED,
            report_id="prv2-" + "b" * 64,
            report_checksum="sha256:" + "b" * 64,
            completed_at=activity,
            started_at=activity,
            current_state="Round completed with selected papers.",
        ),
        "b" * 64,
    )
    report_scope = InMemoryUnitOfWork(database)
    report_scope.progress_reports.append(checkpoint)
    report_scope.progress_reports.append(terminal)
    report_scope.commit()

    read_scope = InMemoryUnitOfWork(database)
    projection = ProjectProgressAggregationService(
        unit_of_work=read_scope,
        clock=lambda: datetime(2026, 8, 8, tzinfo=UTC),
    ).project_progress(project_id=project_id, history_limit=100)
    instance_projection = projection.instances[0]
    assert instance_projection.report_count == 2
    assert instance_projection.latest_report_id == terminal.report_id
    assert instance_projection.latest_report_checksum == terminal.report_checksum
    assert instance_projection.research_status == "COMPLETED"
