"""Shared HTTP DTOs."""

from pydantic import BaseModel, ConfigDict


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictDTO):
    status: str


class ReadinessResponse(StrictDTO):
    status: str
    checks: dict[str, str]


class ErrorDetail(StrictDTO):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(StrictDTO):
    error: ErrorDetail
