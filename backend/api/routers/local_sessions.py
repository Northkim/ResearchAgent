"""Loopback-only session, automatic upload, and verification endpoints."""

from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, Query, Request, Response, status

from backend.application.errors import (
    ApplicationAuthenticationError,
    ApplicationAuthorizationError,
    ApplicationCodedAuthenticationError,
    ApplicationCodedAuthorizationError,
    ApplicationConflictError,
    ApplicationNotFoundError,
    ApplicationUnavailableError,
    ApplicationValidationError,
)
from backend.cloud_api_proxy.contracts import (
    LOCAL_PROGRESS_READ_CAPABILITY,
    LOCAL_PROGRESS_UPLOAD_CAPABILITY,
    ProxyCapabilityToken,
)
from backend.cloud_api_proxy.errors import ProxyError
from backend.local_sessions import LocalSessionMode, LocalWorkflowSessionService
from backend.progress_reports import ChainState, ValidationStatus

from ..dependencies import LocalProductServicesDependency
from ..schemas import (
    CreateLocalWorkflowSessionRequest,
    LocalWorkflowSessionResponse,
    ProgressReportUploadRequest,
    ProgressUploadReceiptResponse,
    ProjectProgressResponse,
    UploadedProgressReportResponse,
)

router = APIRouter(
    prefix="/projects/{project_id}/local-sessions",
    tags=["local-literature-search-session"],
)


def _require_loopback(request: Request) -> None:
    peer = request.client.host if request.client else None
    host = request.headers.get("host", "")
    try:
        parsed = urllib.parse.urlsplit("//" + host)
        valid_host = (
            parsed.hostname == "127.0.0.1"
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        valid_host = False
    if peer != "127.0.0.1" or not valid_host:
        raise ApplicationValidationError(
            "Local Workflow sessions require literal loopback HTTP"
        )


def _proxy(request: Request):
    container = getattr(request.app.state, "proxy_container", None)
    if container is None:
        raise ApplicationUnavailableError(
            "Local Workflow session capabilities are unavailable"
        )
    return container.service


def _bearer(request: Request) -> str:
    value = request.headers.get("authorization")
    if value is None or not value.startswith("Bearer ") or value.count(" ") != 1:
        raise ApplicationAuthenticationError("Local session bearer is required")
    token = value.removeprefix("Bearer ")
    if not token:
        raise ApplicationAuthenticationError("Local session bearer is required")
    return token


def _service(request: Request, services) -> LocalWorkflowSessionService:
    return LocalWorkflowSessionService(
        local_projects=services.local_projects,
        proxy=_proxy(request),
        package_identity_resolver=services.workspace_sync.local_session_package_identity,
    )


def _authorize(
    *,
    request: Request,
    services,
    project_id: str,
    session_id: str,
    package_id: str,
    package_checksum: str,
    workflow_id: str,
    workflow_version: str,
    workflow_checksum: str,
    capability: str,
) -> ProxyCapabilityToken:
    try:
        return _service(request, services).authorize(
            bearer_token=_bearer(request),
            session_id=session_id,
            project_id=project_id,
            package_id=package_id,
            package_checksum=package_checksum,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            workflow_checksum=workflow_checksum,
            capability=capability,
        )
    except ProxyError as error:
        if error.http_status == status.HTTP_401_UNAUTHORIZED:
            raise ApplicationCodedAuthenticationError(
                "Local session authorization failed", code=error.code
            ) from error
        raise ApplicationCodedAuthorizationError(
            "Local session authorization failed", code=error.code
        ) from error


def _authorize_identity(
    *,
    request: Request,
    services,
    project_id: str,
    session_id: str,
    package_id: str,
    package_checksum: str,
    workflow_id: str,
    workflow_version: str,
    workflow_checksum: str,
) -> ProxyCapabilityToken:
    try:
        return _service(request, services).authorize_identity(
            bearer_token=_bearer(request),
            session_id=session_id,
            project_id=project_id,
            package_id=package_id,
            package_checksum=package_checksum,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            workflow_checksum=workflow_checksum,
        )
    except ProxyError as error:
        if error.http_status == status.HTTP_401_UNAUTHORIZED:
            raise ApplicationCodedAuthenticationError(
                "Local session authorization failed", code=error.code
            ) from error
        raise ApplicationCodedAuthorizationError(
            "Local session authorization failed", code=error.code
        ) from error


@router.post(
    "",
    response_model=LocalWorkflowSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_local_workflow_session(
    project_id: str,
    request_body: CreateLocalWorkflowSessionRequest,
    request: Request,
    response: Response,
    services: LocalProductServicesDependency,
) -> LocalWorkflowSessionResponse:
    _require_loopback(request)
    try:
        session = _service(request, services).open(
            project_id=project_id,
            mode=LocalSessionMode(request_body.mode),
            **request_body.model_dump(exclude={"mode"}),
        )
    except (ValueError, ProxyError) as error:
        raise ApplicationValidationError("Local Workflow session could not be issued") from error
    response.headers["Cache-Control"] = "no-store"
    return LocalWorkflowSessionResponse.from_contract(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_local_workflow_session(
    project_id: str,
    session_id: str,
    request: Request,
    services: LocalProductServicesDependency,
    package_id: str = Query(...),
    package_checksum: str = Query(...),
    workflow_id: str = Query(...),
    workflow_version: str = Query(...),
    workflow_checksum: str = Query(...),
) -> Response:
    _require_loopback(request)
    _authorize_identity(
        request=request,
        services=services,
        project_id=project_id,
        session_id=session_id,
        package_id=package_id,
        package_checksum=package_checksum,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        workflow_checksum=workflow_checksum,
    )
    _service(request, services).close(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{session_id}/progress-reports",
    response_model=ProgressUploadReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_session_progress_report(
    project_id: str,
    session_id: str,
    request_body: ProgressReportUploadRequest,
    response: Response,
    request: Request,
    services: LocalProductServicesDependency,
    workflow_id: str = Query(...),
    workflow_version: str = Query(...),
    workflow_checksum: str = Query(...),
) -> ProgressUploadReceiptResponse:
    _require_loopback(request)
    try:
        envelope = request_body.to_contract()
    except ValueError as error:
        raise ApplicationValidationError(str(error)) from error
    token = _authorize(
        request=request,
        services=services,
        project_id=project_id,
        session_id=session_id,
        package_id=envelope.package_id,
        package_checksum=envelope.package_checksum,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        workflow_checksum=workflow_checksum,
        capability=LOCAL_PROGRESS_UPLOAD_CAPABILITY,
    )
    try:
        normalized = services.progress_reports.validate_report(
            envelope.original_report_bytes()
        )
    except ValueError as error:
        raise ApplicationValidationError(
            "Progress Report failed local-session validation"
        ) from error
    report_scope = token.scope.local_progress_report_scope
    if report_scope is None or (
        report_scope.execution_round != normalized.execution_round
        or report_scope.report_id != normalized.report_id
        or report_scope.report_content_checksum != normalized.report_content_checksum
    ):
        raise ApplicationCodedAuthorizationError(
            "Progress Report is outside the upload-only session scope",
            code="REPORT_SCOPE_MISMATCH",
        )
    if (
        normalized.project_id != project_id
        or normalized.package_id != envelope.package_id
        or normalized.package_checksum != envelope.package_checksum
        or normalized.workflow_id != workflow_id
        or normalized.workflow_version != workflow_version
        or normalized.workflow_checksum != workflow_checksum
    ):
        raise ApplicationAuthorizationError(
            "Progress Report is outside the local session scope"
        )
    receipt = services.progress_reports.upload(
        envelope,
        workflow_instance_id=request_body.workflow_instance_id,
        artifact_declarations=request_body.to_artifact_declarations(),
    )
    if receipt.validation_status is ValidationStatus.REJECTED:
        message = "Progress Report retained but rejected"
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
    "/{session_id}/progress-reports",
    response_model=list[UploadedProgressReportResponse],
)
async def list_session_progress_reports(
    project_id: str,
    session_id: str,
    request: Request,
    services: LocalProductServicesDependency,
    package_id: str = Query(...),
    package_checksum: str = Query(...),
    workflow_id: str = Query(...),
    workflow_version: str = Query(...),
    workflow_checksum: str = Query(...),
) -> list[UploadedProgressReportResponse]:
    _require_loopback(request)
    token = _authorize(
        request=request,
        services=services,
        project_id=project_id,
        session_id=session_id,
        package_id=package_id,
        package_checksum=package_checksum,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        workflow_checksum=workflow_checksum,
        capability=LOCAL_PROGRESS_READ_CAPABILITY,
    )
    report_scope = token.scope.local_progress_report_scope
    if report_scope is None:
        raise ApplicationCodedAuthorizationError(
            "Report history requires an upload-only report scope",
            code="REPORT_SCOPE_MISMATCH",
        )
    return [
        UploadedProgressReportResponse.from_contract(item)
        for item in services.progress_reports.list_reports(
            project_id=project_id,
            package_id=package_id,
        )
        if item.report_id == report_scope.report_id
    ]


@router.get(
    "/{session_id}/progress",
    response_model=ProjectProgressResponse,
)
async def get_session_progress(
    project_id: str,
    session_id: str,
    request: Request,
    services: LocalProductServicesDependency,
    package_id: str = Query(...),
    package_checksum: str = Query(...),
    workflow_id: str = Query(...),
    workflow_version: str = Query(...),
    workflow_checksum: str = Query(...),
) -> ProjectProgressResponse:
    _require_loopback(request)
    token = _authorize(
        request=request,
        services=services,
        project_id=project_id,
        session_id=session_id,
        package_id=package_id,
        package_checksum=package_checksum,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        workflow_checksum=workflow_checksum,
        capability=LOCAL_PROGRESS_READ_CAPABILITY,
    )
    projection = services.progress_reports.get_projection(
        project_id=project_id,
        package_id=package_id,
    )
    if projection is None:
        raise ApplicationNotFoundError("Accepted local progress is not available")
    report_scope = token.scope.local_progress_report_scope
    if (
        report_scope is None
        or projection.latest_execution_round != report_scope.execution_round
        or projection.latest_accepted_report_id != report_scope.report_id
    ):
        raise ApplicationCodedAuthorizationError(
            "Project Progress is outside the upload-only report scope",
            code="REPORT_SCOPE_MISMATCH",
        )
    return ProjectProgressResponse.from_contract(projection)
