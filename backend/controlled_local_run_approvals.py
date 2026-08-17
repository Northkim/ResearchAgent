"""Exact Cloud authorization for one controlled-local Experiment attempt.

This module deliberately contains no execution dispatcher.  Cloud records an
Owner decision; the Local Workspace validates and consumes it before using the
existing bounded runner.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

from backend.application.errors import (
    ApplicationCodedConflictError,
    ApplicationCodedNotFoundError,
    ApplicationCodedValidationError,
)
from backend.persistence.ports import DuplicateEntityError, StaleStateError
from backend.workflow_packages.security import require_sha256
from backend.workflow_packages.serialization import canonical_hash, canonical_json

APPROVAL_SCHEMA = "reagent.controlled-local-run-approval/v0.1"
SUMMARY_SCHEMA = "reagent.controlled-local-run-approval-summary/v0.1"
CONSUMPTION_SCHEMA = "reagent.controlled-local-run-approval-consumption/v0.1"
GENERIC_EXPERIMENT_ID = "reproduction-experiment-local-experimental"
GENERIC_EXPERIMENT_VERSION = "0.6.0"

_PROJECT_ID = re.compile(r"^project-[0-9a-f]{32}$")
_WORKFLOW_INSTANCE_ID = re.compile(r"^wfi-[0-9a-f]{32}$")
_REQUEST_ID = re.compile(r"^clra-[0-9a-f]{32}$")
_ATTEMPT_ID = re.compile(r"^attempt-[0-9a-f]{32}$")
_ABSOLUTE_PATH = re.compile(
    r"(?:^|[\s=:])(?:/(?:Users|Volumes|home|private|tmp|var|etc)/|[A-Za-z]:\\)"
)
_FORBIDDEN = re.compile(
    r"```|<[A-Za-z/!][^>]*>|-----BEGIN .*PRIVATE KEY-----|"
    r"\bTraceback \(most recent call last\)|(?:^|\s)(?:def |class |import |from \S+ import )|"
    r"\b(?:print|eval|exec|subprocess)\s*\(|\[(?:DEBUG|INFO|ERROR|CRITICAL)\]|"
    r"(?:https?://)[^\s/@]+:[^\s/@]+@|\bBearer\s+\S+|"
    r"\b(?:password|secret|token|api[_-]?key)\s*[:=]",
    re.IGNORECASE,
)


class ControlledLocalApprovalStatus(str, Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONSUMED = "CONSUMED"
    SUPERSEDED = "SUPERSEDED"


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value: Any, label: str, maximum: int = 1_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be bounded non-empty text")
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError(f"{label} contains multiline or binary content")
    if _ABSOLUTE_PATH.search(value) or _FORBIDDEN.search(value):
        raise ValueError(f"{label} contains code, logs, credentials, or local paths")
    return value


def _texts(values: Any, label: str, maximum: int = 20) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or len(values) > maximum:
        raise ValueError(f"{label} must be a bounded list")
    return tuple(_text(value, label) for value in values)


@dataclass(frozen=True, slots=True)
class ControlledLocalRunSummary:
    what_will_run: str
    research_objective: str
    preparation_method: str
    research_resources: tuple[str, ...]
    execution_environment: str
    network_policy: str
    compute_limits: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    evaluation_approach: str
    important_assumptions: tuple[str, ...]
    important_limitations: tuple[str, ...]
    schema: str = SUMMARY_SCHEMA
    summary_checksum: str = ""

    def __post_init__(self) -> None:
        if self.schema != SUMMARY_SCHEMA:
            raise ValueError("Run Approval summary schema is invalid")
        for name in (
            "what_will_run", "research_objective", "preparation_method",
            "execution_environment", "evaluation_approach",
        ):
            _text(getattr(self, name), name)
        for name in (
            "research_resources", "compute_limits", "expected_outputs",
            "important_assumptions", "important_limitations",
        ):
            object.__setattr__(self, name, _texts(getattr(self, name), name))
        if self.network_policy not in {"DISABLED", "BOUNDED_DECLARED"}:
            raise ValueError("Run Approval network policy is invalid")
        payload = self.payload()
        expected = canonical_hash(payload)
        if self.summary_checksum and self.summary_checksum != expected:
            raise ValueError("Run Approval summary checksum mismatch")
        object.__setattr__(self, "summary_checksum", expected)
        if len(canonical_json(self.to_dict()).encode("utf-8")) > 16_384:
            raise ValueError("Run Approval summary exceeds its byte bound")

    def payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "what_will_run": self.what_will_run,
            "research_objective": self.research_objective,
            "preparation_method": self.preparation_method,
            "research_resources": list(self.research_resources),
            "execution_environment": self.execution_environment,
            "network_policy": self.network_policy,
            "compute_limits": list(self.compute_limits),
            "expected_outputs": list(self.expected_outputs),
            "evaluation_approach": self.evaluation_approach,
            "important_assumptions": list(self.important_assumptions),
            "important_limitations": list(self.important_limitations),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "summary_checksum": self.summary_checksum}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ControlledLocalRunSummary":
        fields = {
            "schema", "what_will_run", "research_objective", "preparation_method",
            "research_resources", "execution_environment", "network_policy",
            "compute_limits", "expected_outputs", "evaluation_approach",
            "important_assumptions", "important_limitations", "summary_checksum",
        }
        if not isinstance(value, Mapping) or set(value) != fields:
            raise ValueError("Run Approval summary fields mismatch")
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class ControlledLocalRunApproval:
    request_id: str
    project_id: str
    workflow_instance_id: str
    research_objective_checksum: str
    execution_plan_checksum: str
    validated_package_checksum: str
    runtime_compatibility_checksum: str | None
    capability_checksum: str | None
    summary: ControlledLocalRunSummary
    created_at: datetime
    request_checksum: str
    status: ControlledLocalApprovalStatus = ControlledLocalApprovalStatus.REQUESTED
    owner_actor: str | None = None
    decision_reason: str | None = None
    decision_idempotency_key: str | None = None
    decided_at: datetime | None = None
    approval_checksum: str | None = None
    consumed_attempt_id: str | None = None
    consumed_at: datetime | None = None
    consumption_checksum: str | None = None
    schema: str = APPROVAL_SCHEMA

    @classmethod
    def create(
        cls, *, project_id: str, workflow_instance_id: str,
        research_objective_checksum: str, execution_plan_checksum: str,
        validated_package_checksum: str,
        runtime_compatibility_checksum: str | None,
        capability_checksum: str | None, summary: ControlledLocalRunSummary,
        created_at: datetime,
    ) -> "ControlledLocalRunApproval":
        payload = cls.request_payload(
            project_id=project_id, workflow_instance_id=workflow_instance_id,
            research_objective_checksum=research_objective_checksum,
            execution_plan_checksum=execution_plan_checksum,
            validated_package_checksum=validated_package_checksum,
            runtime_compatibility_checksum=runtime_compatibility_checksum,
            capability_checksum=capability_checksum, summary=summary,
            created_at=created_at,
        )
        checksum = canonical_hash(payload)
        return cls(
            request_id="clra-" + checksum.removeprefix("sha256:")[:32],
            request_checksum=checksum, **{
                key: value for key, value in payload.items()
                if key not in {"schema", "summary", "created_at"}
            }, summary=summary, created_at=created_at,
        )

    @staticmethod
    def request_payload(**values: Any) -> dict[str, Any]:
        return {
            "schema": APPROVAL_SCHEMA,
            "project_id": values["project_id"],
            "workflow_instance_id": values["workflow_instance_id"],
            "research_objective_checksum": values["research_objective_checksum"],
            "execution_plan_checksum": values["execution_plan_checksum"],
            "validated_package_checksum": values["validated_package_checksum"],
            "runtime_compatibility_checksum": values["runtime_compatibility_checksum"],
            "capability_checksum": values["capability_checksum"],
            "summary": values["summary"].to_dict(),
            "created_at": _utc_text(values["created_at"]),
        }

    def __post_init__(self) -> None:
        if self.schema != APPROVAL_SCHEMA or not _REQUEST_ID.fullmatch(self.request_id):
            raise ValueError("Run Approval request identity is invalid")
        if not _PROJECT_ID.fullmatch(self.project_id) or not _WORKFLOW_INSTANCE_ID.fullmatch(self.workflow_instance_id):
            raise ValueError("Run Approval Project or Workflow Instance identity is invalid")
        for value in (
            self.research_objective_checksum, self.execution_plan_checksum,
            self.validated_package_checksum,
        ):
            require_sha256(value, "Run Approval lineage checksum")
        for value in (self.runtime_compatibility_checksum, self.capability_checksum):
            if value is not None:
                require_sha256(value, "Run Approval optional lineage checksum")
        expected = canonical_hash(self.request_payload(
            project_id=self.project_id, workflow_instance_id=self.workflow_instance_id,
            research_objective_checksum=self.research_objective_checksum,
            execution_plan_checksum=self.execution_plan_checksum,
            validated_package_checksum=self.validated_package_checksum,
            runtime_compatibility_checksum=self.runtime_compatibility_checksum,
            capability_checksum=self.capability_checksum, summary=self.summary,
            created_at=self.created_at,
        ))
        if self.request_checksum != expected or self.request_id != "clra-" + expected.removeprefix("sha256:")[:32]:
            raise ValueError("Run Approval request checksum mismatch")
        self._validate_state()

    def _validate_state(self) -> None:
        decision_fields = (
            self.owner_actor, self.decision_idempotency_key, self.decided_at,
            self.approval_checksum,
        )
        consumption_fields = (
            self.consumed_attempt_id, self.consumed_at, self.consumption_checksum,
        )
        if self.status is ControlledLocalApprovalStatus.REQUESTED:
            if any(value is not None for value in (*decision_fields, *consumption_fields, self.decision_reason)):
                raise ValueError("Requested approval contains decision state")
        elif self.status is ControlledLocalApprovalStatus.APPROVED:
            if any(value is None for value in decision_fields) or any(value is not None for value in consumption_fields):
                raise ValueError("Approved request state is incomplete")
        elif self.status is ControlledLocalApprovalStatus.REJECTED:
            if any(value is None for value in decision_fields) or any(value is not None for value in consumption_fields):
                raise ValueError("Rejected request state is incomplete")
        elif self.status is ControlledLocalApprovalStatus.CONSUMED:
            if any(value is None for value in (*decision_fields, *consumption_fields)):
                raise ValueError("Consumed request state is incomplete")
        elif self.status is ControlledLocalApprovalStatus.SUPERSEDED:
            if any(value is not None for value in consumption_fields):
                raise ValueError("Superseded request cannot be consumed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "request_id": self.request_id,
            "project_id": self.project_id,
            "workflow_instance_id": self.workflow_instance_id,
            "research_objective_checksum": self.research_objective_checksum,
            "execution_plan_checksum": self.execution_plan_checksum,
            "validated_package_checksum": self.validated_package_checksum,
            "runtime_compatibility_checksum": self.runtime_compatibility_checksum,
            "capability_checksum": self.capability_checksum,
            "summary": self.summary.to_dict(), "created_at": _utc_text(self.created_at),
            "request_checksum": self.request_checksum, "status": self.status.value,
            "owner_actor": self.owner_actor, "decision_reason": self.decision_reason,
            "decision_idempotency_key": self.decision_idempotency_key,
            "decided_at": None if self.decided_at is None else _utc_text(self.decided_at),
            "approval_checksum": self.approval_checksum,
            "consumed_attempt_id": self.consumed_attempt_id,
            "consumed_at": None if self.consumed_at is None else _utc_text(self.consumed_at),
            "consumption_checksum": self.consumption_checksum,
        }

    def request_dict(self) -> dict[str, Any]:
        """Return only the immutable Local-to-Cloud request contract."""

        return {
            **self.request_payload(
                project_id=self.project_id,
                workflow_instance_id=self.workflow_instance_id,
                research_objective_checksum=self.research_objective_checksum,
                execution_plan_checksum=self.execution_plan_checksum,
                validated_package_checksum=self.validated_package_checksum,
                runtime_compatibility_checksum=self.runtime_compatibility_checksum,
                capability_checksum=self.capability_checksum,
                summary=self.summary,
                created_at=self.created_at,
            ),
            "request_id": self.request_id,
            "request_checksum": self.request_checksum,
        }


class ControlledLocalRunApprovalRepository(Protocol):
    def get(self, request_id: str, *, for_update: bool = False) -> ControlledLocalRunApproval | None: ...
    def get_current(self, project_id: str, workflow_instance_id: str, *, for_update: bool = False) -> ControlledLocalRunApproval | None: ...
    def add(self, request: ControlledLocalRunApproval) -> None: ...
    def save(self, request: ControlledLocalRunApproval) -> None: ...


class ControlledLocalRunApprovalService:
    """Project-scoped state transitions with no execution side effect."""

    def __init__(
        self, *, repository: ControlledLocalRunApprovalRepository,
        instance_resolver: Callable[[str, str], Any],
        commit_callback: Callable[[], None],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.instance_resolver = instance_resolver
        self.commit = commit_callback
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def report(self, request: ControlledLocalRunApproval) -> ControlledLocalRunApproval:
        self._scope(request.project_id, request.workflow_instance_id)
        existing = self.repository.get(request.request_id, for_update=True)
        if existing is not None:
            if existing.request_checksum != request.request_checksum:
                self._conflict("APPROVAL_REQUEST_IDENTITY_CONFLICT", "Run Approval request identity conflicts")
            return existing
        current = self.repository.get_current(
            request.project_id, request.workflow_instance_id, for_update=True
        )
        if current is not None and current.status in {
            ControlledLocalApprovalStatus.REQUESTED,
            ControlledLocalApprovalStatus.APPROVED,
        }:
            self.repository.save(replace(current, status=ControlledLocalApprovalStatus.SUPERSEDED))
        self.repository.add(request)
        self._commit("APPROVAL_REQUEST_CONFLICT")
        return request

    def observe(self, project_id: str, workflow_instance_id: str) -> ControlledLocalRunApproval | None:
        self._scope(project_id, workflow_instance_id)
        return self.repository.get_current(project_id, workflow_instance_id)

    def approve(
        self, project_id: str, workflow_instance_id: str, request_id: str, *,
        execution_plan_checksum: str, request_checksum: str,
        idempotency_key: str, owner_actor: str = "CONTROLLED_LOCAL_OWNER",
    ) -> ControlledLocalRunApproval:
        request = self._request(project_id, workflow_instance_id, request_id, lock=True)
        self._exact(request, execution_plan_checksum, request_checksum)
        if request.status is ControlledLocalApprovalStatus.APPROVED:
            if request.decision_idempotency_key == idempotency_key:
                return request
            self._conflict("ALREADY_APPROVED", "Run Approval was already approved")
        if request.status is ControlledLocalApprovalStatus.SUPERSEDED:
            self._conflict("APPROVAL_SUPERSEDED", "Run Approval was superseded by a newer request")
        if request.status is ControlledLocalApprovalStatus.REJECTED:
            self._conflict("APPROVAL_REJECTED", "Run Approval was already rejected")
        if request.status is ControlledLocalApprovalStatus.CONSUMED:
            self._conflict("ALREADY_CONSUMED", "Run Approval was already consumed")
        if request.status is not ControlledLocalApprovalStatus.REQUESTED:
            self._conflict("APPROVAL_NOT_REQUESTED", "Run Approval is no longer awaiting a decision")
        decided_at = self.clock()
        decision_payload = {
            "request_id": request.request_id,
            "execution_plan_checksum": request.execution_plan_checksum,
            "request_checksum": request.request_checksum,
            "decision": "APPROVED", "owner_actor": owner_actor,
            "idempotency_key": idempotency_key,
            "decided_at": _utc_text(decided_at),
        }
        approved = replace(
            request, status=ControlledLocalApprovalStatus.APPROVED,
            owner_actor=_text(owner_actor, "owner_actor", 120),
            decision_idempotency_key=_text(idempotency_key, "idempotency_key", 100),
            decided_at=decided_at, approval_checksum=canonical_hash(decision_payload),
        )
        self.repository.save(approved)
        self._commit("APPROVAL_DECISION_CONFLICT")
        return approved

    def reject(
        self, project_id: str, workflow_instance_id: str, request_id: str, *,
        execution_plan_checksum: str, request_checksum: str,
        idempotency_key: str, reason: str | None = None,
        owner_actor: str = "CONTROLLED_LOCAL_OWNER",
    ) -> ControlledLocalRunApproval:
        request = self._request(project_id, workflow_instance_id, request_id, lock=True)
        self._exact(request, execution_plan_checksum, request_checksum)
        if request.status is ControlledLocalApprovalStatus.REJECTED:
            if request.decision_idempotency_key == idempotency_key:
                return request
            self._conflict("ALREADY_REJECTED", "Run Approval was already rejected")
        if request.status is ControlledLocalApprovalStatus.SUPERSEDED:
            self._conflict("APPROVAL_SUPERSEDED", "Run Approval was superseded by a newer request")
        if request.status is ControlledLocalApprovalStatus.APPROVED:
            self._conflict("ALREADY_APPROVED", "Run Approval was already approved")
        if request.status is ControlledLocalApprovalStatus.CONSUMED:
            self._conflict("ALREADY_CONSUMED", "Run Approval was already consumed")
        if request.status is not ControlledLocalApprovalStatus.REQUESTED:
            self._conflict("APPROVAL_NOT_REQUESTED", "Run Approval is no longer awaiting a decision")
        decided_at = self.clock()
        rejected = replace(
            request, status=ControlledLocalApprovalStatus.REJECTED,
            owner_actor=_text(owner_actor, "owner_actor", 120),
            decision_reason=None if reason is None else _text(reason, "reason", 500),
            decision_idempotency_key=_text(idempotency_key, "idempotency_key", 100),
            decided_at=decided_at,
            approval_checksum=canonical_hash({
                "request_id": request.request_id,
                "execution_plan_checksum": request.execution_plan_checksum,
                "request_checksum": request.request_checksum,
                "decision": "REJECTED", "owner_actor": owner_actor,
                "idempotency_key": idempotency_key, "reason": reason,
                "decided_at": _utc_text(decided_at),
            }),
        )
        self.repository.save(rejected)
        self._commit("APPROVAL_DECISION_CONFLICT")
        return rejected

    def consume(
        self, project_id: str, workflow_instance_id: str, request_id: str, *,
        execution_plan_checksum: str, attempt_id: str,
    ) -> ControlledLocalRunApproval:
        request = self._request(project_id, workflow_instance_id, request_id, lock=True)
        require_sha256(execution_plan_checksum, "execution_plan_checksum")
        if request.execution_plan_checksum != execution_plan_checksum:
            self._conflict("APPROVAL_INVALIDATED", "Current execution plan differs from the approved plan")
        if not _ATTEMPT_ID.fullmatch(attempt_id):
            raise ApplicationCodedValidationError("Local execution attempt identity is invalid", code="INVALID_ATTEMPT_ID")
        if request.status is ControlledLocalApprovalStatus.CONSUMED:
            if request.consumed_attempt_id == attempt_id:
                return request
            self._conflict("ALREADY_CONSUMED", "Run Approval was consumed by another attempt")
        if request.status is ControlledLocalApprovalStatus.REJECTED:
            self._conflict("APPROVAL_REJECTED", "Rejected Run Approval cannot be consumed")
        if request.status is ControlledLocalApprovalStatus.SUPERSEDED:
            self._conflict("APPROVAL_SUPERSEDED", "Superseded Run Approval cannot be consumed")
        if request.status is not ControlledLocalApprovalStatus.APPROVED or request.approval_checksum is None:
            self._conflict("APPROVAL_NOT_APPROVED", "Run Approval is not approved")
        consumed_at = self.clock()
        consumption_checksum = canonical_hash({
            "schema": CONSUMPTION_SCHEMA, "request_id": request.request_id,
            "approval_checksum": request.approval_checksum,
            "execution_plan_checksum": request.execution_plan_checksum,
            "attempt_id": attempt_id, "consumed_at": _utc_text(consumed_at),
        })
        consumed = replace(
            request, status=ControlledLocalApprovalStatus.CONSUMED,
            consumed_attempt_id=attempt_id, consumed_at=consumed_at,
            consumption_checksum=consumption_checksum,
        )
        self.repository.save(consumed)
        self._commit("APPROVAL_CONSUMPTION_CONFLICT")
        return consumed

    def _scope(self, project_id: str, workflow_instance_id: str) -> Any:
        instance = self.instance_resolver(project_id, workflow_instance_id)
        if (
            instance.workflow_definition_id != GENERIC_EXPERIMENT_ID
            or instance.workflow_version != GENERIC_EXPERIMENT_VERSION
        ):
            raise ApplicationCodedValidationError(
                "Controlled-local Run Approval is available only for exact Experiment 0.6",
                code="RUN_APPROVAL_WORKFLOW_UNSUPPORTED",
            )
        return instance

    def _request(self, project_id: str, workflow_instance_id: str, request_id: str, *, lock: bool) -> ControlledLocalRunApproval:
        self._scope(project_id, workflow_instance_id)
        request = self.repository.get(request_id, for_update=lock)
        if request is None or request.project_id != project_id or request.workflow_instance_id != workflow_instance_id:
            raise ApplicationCodedNotFoundError("Run Approval request was not found in this scope", code="RUN_APPROVAL_NOT_FOUND")
        return request

    @staticmethod
    def _exact(request: ControlledLocalRunApproval, plan: str, checksum: str) -> None:
        if request.execution_plan_checksum != plan or request.request_checksum != checksum:
            raise ApplicationCodedConflictError(
                "Run Approval identity changed", code="APPROVAL_IDENTITY_MISMATCH"
            )

    def _commit(self, code: str) -> None:
        try:
            self.commit()
        except (DuplicateEntityError, StaleStateError) as error:
            raise ApplicationCodedConflictError(str(error), code=code) from error

    @staticmethod
    def _conflict(code: str, message: str) -> None:
        raise ApplicationCodedConflictError(message, code=code)


def consumption_receipt(value: ControlledLocalRunApproval) -> dict[str, Any]:
    if value.status is not ControlledLocalApprovalStatus.CONSUMED:
        raise ValueError("Run Approval has not been consumed")
    return {
        "schema": CONSUMPTION_SCHEMA,
        "request_id": value.request_id,
        "approval_checksum": value.approval_checksum,
        "execution_plan_checksum": value.execution_plan_checksum,
        "attempt_id": value.consumed_attempt_id,
        "consumed_at": _utc_text(value.consumed_at),
        "consumption_checksum": value.consumption_checksum,
    }
