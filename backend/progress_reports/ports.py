"""Persistence port for append-only uploaded Progress Report history."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .contracts import ProjectProgressProjection, UploadedProgressReport


class ProgressReportRepository(ABC):
    @abstractmethod
    def lock_report_identity(self, report_id: str) -> None: ...

    @abstractmethod
    def append(self, report: UploadedProgressReport) -> None: ...

    @abstractmethod
    def get_receipt(self, receipt_id: str) -> UploadedProgressReport | None: ...

    @abstractmethod
    def find_exact(
        self,
        *,
        project_id: str,
        workflow_instance_id: str,
        package_id: str,
        package_checksum: str,
        report_id: str,
        report_checksum: str,
        original_report_checksum: str,
    ) -> UploadedProgressReport | None: ...

    @abstractmethod
    def list_for_project(
        self,
        project_id: str,
        *,
        package_id: str | None = None,
        workflow_instance_id: str | None = None,
    ) -> tuple[UploadedProgressReport, ...]: ...

    @abstractmethod
    def list_by_report_id(self, report_id: str) -> tuple[UploadedProgressReport, ...]: ...

    @abstractmethod
    def list_by_original_checksum(
        self,
        original_report_checksum: str,
    ) -> tuple[UploadedProgressReport, ...]: ...

    @abstractmethod
    def save_projection(self, projection: ProjectProgressProjection) -> None: ...

    @abstractmethod
    def get_projection(
        self,
        *,
        project_id: str,
        package_id: str,
        workflow_id: str,
        workflow_version: str,
    ) -> ProjectProgressProjection | None: ...
