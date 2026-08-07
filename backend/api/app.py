"""FastAPI application factory and transport-level error mapping."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.application.errors import (
    ApplicationAuthenticationError,
    ApplicationAuthorizationError,
    ApplicationConflictError,
    ApplicationError,
    ApplicationNotFoundError,
    ApplicationUnavailableError,
    ApplicationValidationError,
)

from .composition import ApplicationContainer
from .routers import (
    approvals_router,
    artifacts_router,
    artifact_references_router,
    health_router,
    local_client_router,
    local_projects_router,
    local_sessions_router,
    progress_reports_router,
    runs_router,
    workflows_router,
    project_workspaces_router,
)
from .deployment import DeploymentSettings
from .operations import (
    OperationalBoundaryMiddleware,
    configure_operational_logging,
    log_unhandled_error,
    operational_response_headers,
    request_id_from_scope,
)


def create_app(
    container: ApplicationContainer | None = None,
    *,
    proxy_container: Any | None = None,
    enable_experimental_proxy: bool | None = None,
    enable_local_workflow_sessions: bool | None = None,
    deployment_settings: DeploymentSettings | None = None,
) -> FastAPI:
    settings = deployment_settings or DeploymentSettings.from_environment()
    composition = container or ApplicationContainer.from_environment()
    if enable_experimental_proxy is None:
        from backend.cloud_api_proxy.composition import feature_enabled

        enable_experimental_proxy = feature_enabled()
    proxy_composition = None
    if enable_experimental_proxy:
        from backend.cloud_api_proxy.composition import ProxyApplicationContainer

        proxy_composition = proxy_container or ProxyApplicationContainer.from_environment()
    if enable_local_workflow_sessions is None:
        import os

        enable_local_workflow_sessions = (
            os.environ.get("REAGENT_V0_1_LOCAL_MODE_ENABLED") == "1"
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        configure_operational_logging()
        yield
        if proxy_composition is not None:
            proxy_composition.close()
        composition.close()

    application = FastAPI(
        title="ReAgent API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.expose_api_docs else None,
        redoc_url="/redoc" if settings.expose_api_docs else None,
        openapi_url="/openapi.json" if settings.expose_api_docs else None,
    )
    application.state.container = composition
    application.state.proxy_container = proxy_composition
    application.state.deployment_profile = settings.profile.value
    if settings.cors_allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_allowed_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["Accept", "Authorization", "Content-Type", "X-Request-ID"],
        )
    application.add_middleware(
        OperationalBoundaryMiddleware,
        maximum_request_bytes=settings.maximum_request_bytes,
    )
    application.include_router(health_router)
    application.include_router(local_client_router)
    application.include_router(local_projects_router)
    application.include_router(project_workspaces_router)
    if settings.expose_legacy_hosted_routes:
        application.include_router(runs_router)
        application.include_router(approvals_router)
        application.include_router(workflows_router)
        application.include_router(artifacts_router)
    application.include_router(artifact_references_router)
    application.include_router(progress_reports_router)
    if enable_local_workflow_sessions:
        application.include_router(local_sessions_router)
    if proxy_composition is not None:
        from backend.cloud_api_proxy.api import router as proxy_router

        application.include_router(proxy_router)

    @application.exception_handler(ApplicationError)
    async def handle_application_error(
        request: Request,
        error: ApplicationError,
    ) -> JSONResponse:
        if isinstance(error, ApplicationAuthenticationError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(error, ApplicationAuthorizationError):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(error, ApplicationNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(error, ApplicationConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(error, ApplicationValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        elif isinstance(error, ApplicationUnavailableError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_body: dict[str, Any] = {
            "code": error.code,
            "message": str(error),
        }
        details = getattr(error, "details", None)
        if details is not None:
            error_body["details"] = details
        return JSONResponse(
            status_code=status_code,
            content={"error": error_body},
        )

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=jsonable_encoder(
                {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Request body failed DTO validation",
                        "details": [
                            {
                                "type": item.get("type"),
                                "loc": item.get("loc"),
                                "msg": item.get("msg"),
                            }
                            for item in error.errors()
                        ],
                    }
                }
            ),
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        request_id = request_id_from_scope(request.scope)
        log_unhandled_error(
            request_id=request_id,
            error_class=type(error).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "The request could not be completed",
                    "request_id": request_id,
                }
            },
            headers=operational_response_headers(request_id),
        )

    return application


app = create_app()
