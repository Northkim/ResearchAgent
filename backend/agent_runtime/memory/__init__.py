"""Compatibility exports for the persistence-backed memory contract."""

from backend.persistence.models import MemoryRevision
from backend.persistence.ports import MemoryRepository

__all__ = ["MemoryRepository", "MemoryRevision"]
