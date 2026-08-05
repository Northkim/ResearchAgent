"""Persistence port for local product projects."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .contracts import LocalProject


class LocalProjectRepository(ABC):
    @abstractmethod
    def add(self, project: LocalProject) -> None: ...

    @abstractmethod
    def save(self, project: LocalProject) -> None: ...

    @abstractmethod
    def get(self, project_id: str) -> LocalProject | None: ...

    @abstractmethod
    def list_all(self) -> tuple[LocalProject, ...]: ...
