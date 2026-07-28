from __future__ import annotations

import pytest

from backend.api.composition import ApplicationContainer
from backend.research.adapters import FakePaperSearchProvider, OpenAlexPaperSearchProvider


def _database_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "REAGENT_DATABASE_URL",
        "postgresql+psycopg://reagent:placeholder@localhost/reagent_composition_test",
    )


def test_composition_defaults_to_network_free_fake_provider(monkeypatch) -> None:
    _database_environment(monkeypatch)
    monkeypatch.delenv("REAGENT_PAPER_SEARCH_PROVIDER", raising=False)
    container = ApplicationContainer.from_environment()
    try:
        assert isinstance(container.paper_search_provider, FakePaperSearchProvider)
        assert container.provider_execution_policy.budget.live_provider_enabled is False
    finally:
        container.close()


def test_openalex_requires_two_explicit_opt_in_values(monkeypatch) -> None:
    _database_environment(monkeypatch)
    monkeypatch.setenv("REAGENT_PAPER_SEARCH_PROVIDER", "openalex")
    monkeypatch.delenv("REAGENT_OPENALEX_LIVE_ENABLED", raising=False)
    with pytest.raises(ValueError, match="LIVE_ENABLED"):
        ApplicationContainer.from_environment()


def test_openalex_live_mode_requires_key_for_free_credit_preflight(monkeypatch) -> None:
    _database_environment(monkeypatch)
    monkeypatch.setenv("REAGENT_PAPER_SEARCH_PROVIDER", "openalex")
    monkeypatch.setenv("REAGENT_OPENALEX_LIVE_ENABLED", "true")
    monkeypatch.delenv("REAGENT_OPENALEX_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API_KEY"):
        ApplicationContainer.from_environment()


def test_openalex_configuration_is_injected_and_key_repr_is_redacted(monkeypatch) -> None:
    _database_environment(monkeypatch)
    monkeypatch.setenv("REAGENT_PAPER_SEARCH_PROVIDER", "openalex")
    monkeypatch.setenv("REAGENT_OPENALEX_LIVE_ENABLED", "true")
    monkeypatch.setenv("REAGENT_OPENALEX_API_KEY", "not-a-real-secret")
    container = ApplicationContainer.from_environment()
    try:
        provider = container.paper_search_provider
        assert isinstance(provider, OpenAlexPaperSearchProvider)
        assert provider.configuration.api_key == "not-a-real-secret"
        assert "not-a-real-secret" not in repr(provider.configuration)
        assert container.provider_execution_policy.budget.live_provider_enabled is True
        assert container.provider_execution_policy.budget.max_cost_minor_units == 0
    finally:
        container.close()
