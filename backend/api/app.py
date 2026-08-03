"""FastAPI application factory and transport-level error mapping."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.application.errors import (
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
    health_router,
    progress_reports_router,
    runs_router,
    workflows_router,
)


def create_app(container: ApplicationContainer | None = None) -> FastAPI:
    composition = container or ApplicationContainer.from_environment()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        composition.close()

    application = FastAPI(
        title="ReAgent API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.container = composition
    application.include_router(health_router)
    application.include_router(runs_router)
    application.include_router(approvals_router)
    application.include_router(workflows_router)
    application.include_router(artifacts_router)
    application.include_router(progress_reports_router)

    @application.exception_handler(ApplicationError)
    async def handle_application_error(
        _: Request,
        error: ApplicationError,
    ) -> JSONResponse:
        if isinstance(error, ApplicationNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(error, ApplicationConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(error, ApplicationValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        elif isinstance(error, ApplicationUnavailableError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": str(error),
                }
            },
        )

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=jsonable_encoder(
                {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Request body failed DTO validation",
                        "details": error.errors(),
                    }
                }
            ),
        )

    return application


app = create_app()
