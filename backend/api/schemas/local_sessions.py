"""Strict local-only Workflow-session DTOs."""

from __future__ import annotations

from typing import Literal

from backend.local_sessions import LocalWorkflowSession

from .common import StrictDTO


class CreateLocalWorkflowSessionRequest(StrictDTO):
    package_id: str
    package_checksum: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str
    mode: Literal["NORMAL", "DEMO", "UPLOAD_ONLY"]
    execution_round: int | None = None
    report_id: str | None = None
    report_content_checksum: str | None = None


class LocalWorkflowSessionResponse(StrictDTO):
    session_id: str
    session_token: str
    mode: str
    expires_at: str
    project_id: str
    package_id: str
    workflow_id: str
    maximum_query_variants: int
    maximum_results_per_query: int
    maximum_provider_calls: int
    maximum_provider_cost_microusd: int

    @classmethod
    def from_contract(
        cls,
        session: LocalWorkflowSession,
    ) -> LocalWorkflowSessionResponse:
        return cls(
            session_id=session.session_id,
            session_token=session.session_token,
            mode=session.mode.value,
            expires_at=session.expires_at,
            project_id=session.project_id,
            package_id=session.package_id,
            workflow_id=session.workflow_id,
            maximum_query_variants=session.maximum_query_variants,
            maximum_results_per_query=session.maximum_results_per_query,
            maximum_provider_calls=session.maximum_provider_calls,
            maximum_provider_cost_microusd=session.maximum_provider_cost_microusd,
        )


class LocalLiteratureExecutionModeResponse(StrictDTO):
    package_id: str
    package_checksum: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str
    mode: Literal["NORMAL", "DEMO"]
