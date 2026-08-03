"""Fail-closed composition isolated from the Hosted runtime container."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy import Engine

from backend.database.engine import create_postgres_engine, create_session_factory

from .fake_adapter import DeterministicFakePaperSearchAdapter
from .service import CloudAPIProxyService
from .sql import SQLProxyUnitOfWork

FEATURE_FLAG = "REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED"


def feature_enabled(value: str | None = None) -> bool:
    candidate = os.environ.get(FEATURE_FLAG) if value is None else value
    return candidate == "1"


@dataclass(slots=True)
class ProxyApplicationContainer:
    service: CloudAPIProxyService
    engine: Engine | None = None

    @classmethod
    def from_environment(cls) -> ProxyApplicationContainer:
        database_url = os.environ.get("REAGENT_DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "Experimental fake Proxy requires explicit PostgreSQL persistence"
            )
        engine = create_postgres_engine(database_url)
        session_factory = create_session_factory(engine)
        adapter = DeterministicFakePaperSearchAdapter()
        service = CloudAPIProxyService(
            unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
            adapter=adapter,
        )
        service.reconcile_interrupted()
        return cls(service=service, engine=engine)

    def close(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
