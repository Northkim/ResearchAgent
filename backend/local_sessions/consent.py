"""Ephemeral owner consent for one real local Literature Search session."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

REAL_PROVIDER_DISCLOSURE_VERSION = "reagent.openalex-owner-disclosure/v0.1"
REAL_PROVIDER_CONFIRMATION = "continue-real-search"
REAL_PROVIDER_CONSENT_LIFETIME = timedelta(minutes=2)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RealProviderConsentRegistry:
    """Hold short-lived, exact-scope grants in memory and consume them once."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = _utc_now,
        lifetime: timedelta = REAL_PROVIDER_CONSENT_LIFETIME,
    ) -> None:
        if lifetime <= timedelta(0):
            raise ValueError("Real Provider consent lifetime must be positive")
        self._clock = clock
        self._lifetime = lifetime
        self._grants: dict[tuple[str, ...], datetime] = {}
        self._lock = threading.Lock()

    @staticmethod
    def scope(
        *,
        project_id: str,
        package_id: str,
        package_checksum: str,
        workflow_id: str,
        workflow_version: str,
        workflow_checksum: str,
    ) -> tuple[str, ...]:
        return (
            project_id,
            package_id,
            package_checksum,
            workflow_id,
            workflow_version,
            workflow_checksum,
        )

    def grant(
        self,
        *,
        disclosure_version: str,
        confirmation: str,
        **identity: str,
    ) -> datetime:
        if disclosure_version != REAL_PROVIDER_DISCLOSURE_VERSION:
            raise ValueError("Real Provider disclosure version is unsupported")
        if confirmation != REAL_PROVIDER_CONFIRMATION:
            raise ValueError("Real Provider consent was not explicitly confirmed")
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Real Provider consent clock must be timezone-aware")
        expires_at = now + self._lifetime
        scope = self.scope(**identity)
        with self._lock:
            self._prune(now)
            self._grants[scope] = expires_at
        return expires_at

    def consume(self, **identity: str) -> bool:
        now = self._clock()
        scope = self.scope(**identity)
        with self._lock:
            self._prune(now)
            expires_at = self._grants.pop(scope, None)
        return expires_at is not None and expires_at > now

    def _prune(self, now: datetime) -> None:
        expired = [scope for scope, expiry in self._grants.items() if expiry <= now]
        for scope in expired:
            del self._grants[scope]
