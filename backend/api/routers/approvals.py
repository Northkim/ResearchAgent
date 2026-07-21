"""Human approval endpoints containing transport mapping only."""

from fastapi import APIRouter, Query

from backend.domain.enums import ApprovalRequestStatus

from ..dependencies import ServicesDependency
from ..schemas import (
    ApprovalDecisionResponse,
    ApprovalPageResponse,
    ApproveRequest,
    RejectRequest,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=ApprovalPageResponse)
async def list_approvals(
    services: ServicesDependency,
    status_filter: ApprovalRequestStatus | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> ApprovalPageResponse:
    view = services.list_approvals.execute(
        status=status_filter,
        offset=offset,
        limit=limit,
    )
    return ApprovalPageResponse.from_view(view)


@router.post("/{approval_id}/approve", response_model=ApprovalDecisionResponse)
async def approve(
    approval_id: str,
    request: ApproveRequest,
    services: ServicesDependency,
) -> ApprovalDecisionResponse:
    view = await services.decide_approval.execute(request.to_command(approval_id))
    return ApprovalDecisionResponse.from_view(view)


@router.post("/{approval_id}/reject", response_model=ApprovalDecisionResponse)
async def reject(
    approval_id: str,
    request: RejectRequest,
    services: ServicesDependency,
) -> ApprovalDecisionResponse:
    view = await services.decide_approval.execute(request.to_command(approval_id))
    return ApprovalDecisionResponse.from_view(view)
