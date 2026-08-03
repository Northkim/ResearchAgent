"""Cloud management endpoints for uploaded local Progress Reports only."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response, status

from backend.application.errors import (
    ApplicationConflictError,
    ApplicationNotFoundError,
    ApplicationValidationError,
)
from backend.progress_reports import ChainState, ValidationStatus

from ..dependencies import ProgressServicesDependency
from ..schemas import (
    ProgressReportUploadRequest,
    ProgressUploadReceiptResponse,
    ProjectProgressResponse,
    UploadedProgressReportResponse,
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
        receipt = services.progress_reports.upload(envelope)
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


@router.get("/progress", response_model=ProjectProgressResponse)
async def get_project_progress(
    project_id: str,
    services: ProgressServicesDependency,
    package_id: str | None = Query(default=None),
) -> ProjectProgressResponse:
    projection = services.progress_reports.get_projection(
        project_id=project_id,
        package_id=package_id,
    )
    if projection is None:
        raise ApplicationNotFoundError("Accepted local progress is not available")
    return ProjectProgressResponse.from_contract(projection)
