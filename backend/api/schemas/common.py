"""Shared HTTP DTOs."""

from pydantic import BaseModel, ConfigDict


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictDTO):
    status: str


class ErrorDetail(StrictDTO):
    code: str
    message: str


class ErrorResponse(StrictDTO):
    error: ErrorDetail
