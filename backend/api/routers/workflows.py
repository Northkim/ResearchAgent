"""Workflow catalog query endpoint."""

from fastapi import APIRouter

from ..dependencies import ServicesDependency
from ..schemas import WorkflowDefinitionResponse

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowDefinitionResponse])
async def list_workflows(
    services: ServicesDependency,
) -> list[WorkflowDefinitionResponse]:
    workflows = services.list_workflows.execute()
    return [WorkflowDefinitionResponse.from_view(workflow) for workflow in workflows]
