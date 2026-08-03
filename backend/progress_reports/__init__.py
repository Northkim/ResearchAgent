"""Teacher-aligned Progress Report upload, history, and projection boundary."""

from .contracts import (
    ChainState,
    NormalizedProgressRecord,
    OutputArtifactReference,
    PinReference,
    ProgressReportUploadEnvelope,
    ProgressReportV2,
    ProgressStatus,
    ProgressUploadReceipt,
    ProjectProgressProjection,
    UploadedProgressReport,
    ValidationStatus,
)
from .normalization import ProgressReportNormalizer
from .service import ProgressReportService

__all__ = [
    "ChainState",
    "NormalizedProgressRecord",
    "OutputArtifactReference",
    "PinReference",
    "ProgressReportNormalizer",
    "ProgressReportService",
    "ProgressReportUploadEnvelope",
    "ProgressReportV2",
    "ProgressStatus",
    "ProgressUploadReceipt",
    "ProjectProgressProjection",
    "UploadedProgressReport",
    "ValidationStatus",
]
