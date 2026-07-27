"""Detached immutable persistence representation of a provider operation."""

from __future__ import annotations

from dataclasses import dataclass

from backend.research.contracts import ProviderOperation


@dataclass(frozen=True, slots=True)
class ProviderOperationRecord:
    operation: ProviderOperation
    persistence_version: int

    def __post_init__(self) -> None:
        if self.persistence_version <= 0:
            raise ValueError("ProviderOperationRecord.persistence_version must be positive")

