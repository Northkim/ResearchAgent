"""Typed outcomes evaluated by the Workflow Engine."""

from enum import Enum


class ApprovalOutcome(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
