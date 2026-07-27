"""Artifact and sanitized provider-operation DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.application.views import ArtifactView, ProviderOperationView

from .common import StrictDTO


class ArtifactResponse(StrictDTO):
    id: str
    logical_name: str
    version: int
    kind: str
    checksum: str
    media_type: str
    size: int
    producer_run_id: str | None
    producer_step_run_id: str | None
    metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_view(cls, view: ArtifactView) -> ArtifactResponse:
        return cls(**{field: getattr(view, field) for field in cls.model_fields})


class ProviderOperationResponse(StrictDTO):
    id: str
    logical_step_id: str
    provider_category: str
    operation_kind: str
    provider_identity: str
    adapter_version: str
    model_or_endpoint: str
    status: str
    settlement_state: str
    request_count: int
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_minor_units: int | None
    cost_currency: str | None
    failure_category: str | None
    created_at: datetime
    finished_at: datetime | None

    @classmethod
    def from_view(
        cls,
        view: ProviderOperationView,
    ) -> ProviderOperationResponse:
        return cls(**{field: getattr(view, field) for field in cls.model_fields})
