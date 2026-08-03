"""FastAPI dependency adapters for request-scoped resources."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from backend.agent_runtime import AgentRuntime
from backend.application.execution import ExecutionDispatcher
from backend.persistence.ports import UnitOfWork

from .composition import (
    ApplicationContainer,
    ApplicationServices,
    ProgressApplicationServices,
)


def get_container(request: Request) -> ApplicationContainer:
    return request.app.state.container


def get_unit_of_work(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> Iterator[UnitOfWork]:
    unit_of_work = container.unit_of_work_factory()
    try:
        yield unit_of_work
    except Exception:
        unit_of_work.rollback()
        raise
    finally:
        close = getattr(unit_of_work, "close", None)
        if callable(close):
            close()


def get_application_services(
    container: Annotated[ApplicationContainer, Depends(get_container)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> ApplicationServices:
    return container.build_services(unit_of_work)


def get_progress_services(
    container: Annotated[ApplicationContainer, Depends(get_container)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> ProgressApplicationServices:
    return container.build_progress_services(unit_of_work)


def get_runtime(
    services: Annotated[ApplicationServices, Depends(get_application_services)],
) -> AgentRuntime:
    return services.runtime


def get_dispatcher(
    services: Annotated[ApplicationServices, Depends(get_application_services)],
) -> ExecutionDispatcher:
    return services.dispatcher


ServicesDependency = Annotated[
    ApplicationServices,
    Depends(get_application_services),
]
RuntimeDependency = Annotated[AgentRuntime, Depends(get_runtime)]
DispatcherDependency = Annotated[ExecutionDispatcher, Depends(get_dispatcher)]
UnitOfWorkDependency = Annotated[UnitOfWork, Depends(get_unit_of_work)]
ProgressServicesDependency = Annotated[
    ProgressApplicationServices,
    Depends(get_progress_services),
]
