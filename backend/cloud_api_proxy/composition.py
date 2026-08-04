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
OPENALEX_FEATURE_FLAG = "REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED"


def feature_enabled(value: str | None = None) -> bool:
    if value is not None:
        return value == "1"
    return fake_feature_enabled() or openalex_feature_enabled()


def fake_feature_enabled(value: str | None = None) -> bool:
    candidate = os.environ.get(FEATURE_FLAG) if value is None else value
    return candidate == "1"


def openalex_feature_enabled(value: str | None = None) -> bool:
    candidate = os.environ.get(OPENALEX_FEATURE_FLAG) if value is None else value
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
                "Experimental Proxy requires explicit PostgreSQL persistence"
            )
        engine = create_postgres_engine(database_url)
        try:
            session_factory = create_session_factory(engine)
            adapters = {}
            if fake_feature_enabled():
                adapter = DeterministicFakePaperSearchAdapter()
                adapters[adapter.adapter_id] = adapter
            if openalex_feature_enabled():
                from .openalex_adapter import (
                    EnvironmentOpenAlexCredentialSource,
                    HTTPXOpenAlexTransport,
                    OpenAlexPaperSearchAdapter,
                )

                credential_source = EnvironmentOpenAlexCredentialSource()
                credential_source.get()
                adapter = OpenAlexPaperSearchAdapter(
                    credential_source=credential_source,
                    transport=HTTPXOpenAlexTransport(),
                )
                adapters[adapter.adapter_id] = adapter
            if not adapters:
                raise RuntimeError("Experimental Proxy requires an explicit adapter feature flag")
            service = CloudAPIProxyService(
                unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
                adapters=adapters,
            )
            service.reconcile_interrupted()
            return cls(service=service, engine=engine)
        except BaseException:
            engine.dispose()
            raise

    def close(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
