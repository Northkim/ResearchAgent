"""Cloud management endpoints for uploaded local Progress Reports only."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response, status

from backend.application.errors import (
    ApplicationCodedConflictError,
    ApplicationConflictError,
    ApplicationNotFoundError,
    ApplicationValidationError,
)
from backend.persistence.ports import DuplicateEntityError
from backend.progress_reports import ChainState, ValidationStatus

from ..dependencies import ProgressServicesDependency
from ..schemas import (
    ProgressReportUploadRequest,
    ProgressUploadReceiptResponse,
    ProjectWorkflowProgressResponse,
    UploadedProgressReportResponse,
    WorkflowInstanceProgressPageResponse,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["local-progress-reports"])


@router.post(
    "/progress-reports",
    response_model=ProgressUploadReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_progress_report(
    project_id: str,
    request: ProgressReportUploadRequest,
    response: Response,
    services: ProgressServicesDependency,
) -> ProgressUploadReceiptResponse:
    try:
        envelope = request.to_contract()
    except ValueError as error:
        raise ApplicationValidationError(str(error)) from error
    if envelope.project_id != project_id:
        raise ApplicationValidationError("path project does not match upload envelope")
    try:
        receipt = services.progress_reports.upload(
            envelope,
            workflow_instance_id=request.workflow_instance_id,
        )
    except DuplicateEntityError as error:
        raise ApplicationCodedConflictError(
            "Progress Report identity already exists with different content",
            code="PROGRESS_IDEMPOTENCY_CONFLICT",
        ) from error
    except ValueError as error:
        raise ApplicationValidationError(str(error)) from error
    if receipt.validation_status is ValidationStatus.REJECTED:
        message = (
            f"Progress Report retained but rejected; receipt={receipt.receipt_id}; "
            f"chain_state={receipt.chain_state.value}"
        )
        if receipt.chain_state in {
            ChainState.CONTINUITY_CONFLICT,
            ChainState.IDENTITY_CONFLICT,
            ChainState.BRANCHED_HISTORY,
        }:
            raise ApplicationConflictError(message)
        raise ApplicationValidationError(message)
    if receipt.idempotent_replay:
        response.status_code = status.HTTP_200_OK
    return ProgressUploadReceiptResponse.from_contract(receipt)


@router.get(
    "/progress-reports",
    response_model=list[UploadedProgressReportResponse],
)
async def list_progress_reports(
    project_id: str,
    services: ProgressServicesDependency,
    package_id: str | None = Query(default=None),
) -> list[UploadedProgressReportResponse]:
    return [
        UploadedProgressReportResponse.from_contract(item)
        for item in services.progress_reports.list_reports(
            project_id=project_id,
            package_id=package_id,
        )
    ]


@router.get(
    "/progress-reports/{report_id}",
    response_model=UploadedProgressReportResponse,
)
async def get_progress_report(
    project_id: str,
    report_id: str,
    services: ProgressServicesDependency,
    receipt_id: str | None = Query(default=None),
) -> UploadedProgressReportResponse:
    report = services.progress_reports.get_report(
        project_id=project_id,
        report_id=report_id,
        receipt_id=receipt_id,
    )
    if report is None:
        raise ApplicationNotFoundError("Progress Report not found")
    return UploadedProgressReportResponse.from_contract(report)


@router.get("/progress-reports/{report_id}/original")
async def read_original_progress_report(
    project_id: str,
    report_id: str,
    services: ProgressServicesDependency,
    receipt_id: str | None = Query(default=None),
) -> Response:
    report = services.progress_reports.get_report(
        project_id=project_id,
        report_id=report_id,
        receipt_id=receipt_id,
    )
    if report is None:
        raise ApplicationNotFoundError("Progress Report not found")
    content = services.progress_reports.read_original(report)
    return Response(
        content=content,
        media_type=report.original_report_media_type,
        headers={
            "ETag": f'"{report.original_report_checksum}"',
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "attachment; filename=progress-report.json",
        },
    )


@router.get("/progress", response_model=ProjectWorkflowProgressResponse)
async def get_project_progress(
    project_id: str,
    services: ProgressServicesDependency,
    workflow_instance_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> ProjectWorkflowProgressResponse:
    projection = services.project_progress.project_progress(
        project_id=project_id,
        workflow_instance_id=workflow_instance_id,
        history_offset=offset,
        history_limit=limit,
    )
    legacy = services.progress_reports.get_projection(project_id=project_id)
    return ProjectWorkflowProgressResponse.from_contract(
        projection,
        legacy_projection=legacy,
    )


@router.get(
    "/workflow-instances/{instance_id}/progress",
    response_model=WorkflowInstanceProgressPageResponse,
)
async def get_workflow_instance_progress(
    project_id: str,
    instance_id: str,
    services: ProgressServicesDependency,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> WorkflowInstanceProgressPageResponse:
    projection = services.project_progress.instance_progress(
        project_id=project_id,
        workflow_instance_id=instance_id,
        history_offset=offset,
        history_limit=limit,
    )
    return WorkflowInstanceProgressPageResponse.from_contract(
        projection,
        instance_id,
    )
