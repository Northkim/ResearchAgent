"""Append-only durable ProviderOperation repository for isolated evaluations."""

from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.persistence.models import ProviderOperationRecord
from backend.persistence.ports import (
    DuplicateEntityError,
    ProviderOperationRepository,
    StaleStateError,
)
from backend.research.contracts import (
    ProviderCategory,
    ProviderFailureCategory,
    ProviderOperation,
    ProviderOperationKind,
    ProviderOperationStatus,
    ProviderReservation,
    ProviderUsage,
    SettlementState,
    canonical_hash,
)
from backend.research.contracts._serialization import canonical_json

_JOURNAL_SCHEMA = "openalex-evaluation-provider-operation-journal/v1"


class EvaluationOperationJournalError(RuntimeError):
    pass


class JournaledProviderOperationUnit:
    """Small commit boundary for the evaluation-only provider ledger.

    The production SQL repository requires a real WorkflowRun foreign key.
    Evaluation is deliberately outside Agent Runtime, so this adapter implements
    the unchanged ProviderOperationRepository port as a private append-only
    journal under the ignored evaluation root.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.provider_operations = JournaledProviderOperationRepository(self.path)

    def commit(self) -> None:
        self.provider_operations.commit()


class JournaledProviderOperationRepository(ProviderOperationRepository):
    def __init__(self, path: Path) -> None:
        self.path = path
        self._records: dict[str, ProviderOperationRecord] = {}
        self._staged: dict[str, ProviderOperationRecord] = {}
        self._sequence = 0
        self._head_checksum: str | None = None
        if self.path.exists():
            self._reload(self.path.read_bytes())

    def save(
        self,
        operation: ProviderOperation,
        *,
        expected_version: int | None,
    ) -> int:
        current = self._current_record(operation.id)
        if expected_version is None:
            if current is not None:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} already exists at persistence "
                    f"version {current.persistence_version}"
                )
            owner = self.get_by_idempotency_key(
                operation.project_id,
                operation.idempotency_key,
            )
            if owner is not None and owner.id != operation.id:
                raise DuplicateEntityError(
                    "Provider operation idempotency key is already owned by "
                    f"ProviderOperation {owner.id}"
                )
            next_version = 1
        else:
            if current is None:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} does not exist"
                )
            if current.persistence_version != expected_version:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} expected persistence version "
                    f"{expected_version}; found {current.persistence_version}"
                )
            if operation.row_version != current.operation.row_version + 1:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} domain row version must advance "
                    f"from {current.operation.row_version} to "
                    f"{current.operation.row_version + 1}"
                )
            _assert_immutable_identity(current.operation, operation)
            next_version = expected_version + 1
        self._staged[operation.id] = ProviderOperationRecord(
            operation=operation,
            persistence_version=next_version,
        )
        return next_version

    def get(self, operation_id: str) -> ProviderOperation | None:
        record = self._current_record(operation_id)
        return record.operation if record is not None else None

    def get_version(self, operation_id: str) -> int | None:
        record = self._current_record(operation_id)
        return record.persistence_version if record is not None else None

    def get_by_idempotency_key(
        self,
        project_id: str,
        idempotency_key: str,
    ) -> ProviderOperation | None:
        matches = [
            record.operation
            for record in self._current_records().values()
            if record.operation.project_id == project_id
            and record.operation.idempotency_key == idempotency_key
        ]
        return min(matches, key=lambda item: item.id) if matches else None

    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ProviderOperation, ...]:
        operations = [
            record.operation
            for record in self._current_records().values()
            if record.operation.project_id == project_id
            and record.operation.workflow_run_id == workflow_run_id
        ]
        return tuple(sorted(operations, key=lambda item: (item.created_at, item.id)))

    def list_unsettled(
        self,
        *,
        project_id: str | None = None,
    ) -> tuple[ProviderOperation, ...]:
        operations = [
            record.operation
            for record in self._current_records().values()
            if record.operation.settlement_state is SettlementState.UNSETTLED
            and (project_id is None or record.operation.project_id == project_id)
        ]
        return tuple(sorted(operations, key=lambda item: (item.updated_at, item.id)))

    def commit(self) -> None:
        if not self._staged:
            return
        descriptor = os.open(
            self.path,
            os.O_RDWR | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        with os.fdopen(descriptor, "r+b", buffering=0) as journal:
            os.fchmod(journal.fileno(), 0o600)
            fcntl.flock(journal.fileno(), fcntl.LOCK_EX)
            journal.seek(0)
            persisted = journal.read()
            latest_records, sequence, head = _parse_journal(persisted)
            if sequence != self._sequence or head != self._head_checksum:
                raise StaleStateError(
                    "Evaluation ProviderOperation journal changed concurrently"
                )
            if latest_records != self._records:
                raise StaleStateError(
                    "Evaluation ProviderOperation journal state changed concurrently"
                )
            payload = {
                "schema_version": _JOURNAL_SCHEMA,
                "sequence": self._sequence + 1,
                "previous_checksum": self._head_checksum,
                "records": [
                    {
                        "operation": record.operation.to_dict(),
                        "persistence_version": record.persistence_version,
                    }
                    for _, record in sorted(self._staged.items())
                ],
            }
            checksum = canonical_hash(payload)
            line = canonical_json({**payload, "checksum": checksum}).encode("utf-8")
            journal.write(line + b"\n")
            os.fsync(journal.fileno())
            fcntl.flock(journal.fileno(), fcntl.LOCK_UN)
        self._records.update(self._staged)
        self._staged.clear()
        self._sequence += 1
        self._head_checksum = checksum

    def _reload(self, content: bytes) -> None:
        records, sequence, head = _parse_journal(content)
        self._records = records
        self._sequence = sequence
        self._head_checksum = head

    def _current_record(self, operation_id: str) -> ProviderOperationRecord | None:
        return self._staged.get(operation_id) or self._records.get(operation_id)

    def _current_records(self) -> dict[str, ProviderOperationRecord]:
        return {**self._records, **self._staged}


def _parse_journal(
    content: bytes,
) -> tuple[dict[str, ProviderOperationRecord], int, str | None]:
    if not content:
        return {}, 0, None
    if not content.endswith(b"\n"):
        raise EvaluationOperationJournalError(
            "ProviderOperation journal has a partial trailing record"
        )
    records: dict[str, ProviderOperationRecord] = {}
    head: str | None = None
    sequence = 0
    for raw_line in content.splitlines():
        try:
            value = json.loads(raw_line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise EvaluationOperationJournalError(
                "ProviderOperation journal contains malformed JSON"
            ) from None
        if not isinstance(value, Mapping):
            raise EvaluationOperationJournalError(
                "ProviderOperation journal record must be an object"
            )
        checksum = value.get("checksum")
        payload = {key: item for key, item in value.items() if key != "checksum"}
        if (
            value.get("schema_version") != _JOURNAL_SCHEMA
            or value.get("sequence") != sequence + 1
            or value.get("previous_checksum") != head
            or not isinstance(checksum, str)
            or checksum != canonical_hash(payload)
        ):
            raise EvaluationOperationJournalError(
                "ProviderOperation journal chain validation failed"
            )
        raw_records = value.get("records")
        if not isinstance(raw_records, list) or not raw_records:
            raise EvaluationOperationJournalError(
                "ProviderOperation journal transaction has no records"
            )
        for raw_record in raw_records:
            if not isinstance(raw_record, Mapping):
                raise EvaluationOperationJournalError(
                    "ProviderOperation journal record is invalid"
                )
            operation_value = raw_record.get("operation")
            if not isinstance(operation_value, Mapping):
                raise EvaluationOperationJournalError(
                    "ProviderOperation journal operation is invalid"
                )
            operation = _operation_from_dict(operation_value)
            persistence_version = int(raw_record["persistence_version"])
            current = records.get(operation.id)
            if current is None:
                if persistence_version != 1 or operation.row_version != 0:
                    raise EvaluationOperationJournalError(
                        "ProviderOperation journal insert version is invalid"
                    )
                owner = next(
                    (
                        item.operation
                        for item in records.values()
                        if item.operation.project_id == operation.project_id
                        and item.operation.idempotency_key
                        == operation.idempotency_key
                    ),
                    None,
                )
                if owner is not None:
                    raise EvaluationOperationJournalError(
                        "ProviderOperation journal has duplicate idempotency identity"
                    )
            else:
                if (
                    persistence_version != current.persistence_version + 1
                    or operation.row_version != current.operation.row_version + 1
                ):
                    raise EvaluationOperationJournalError(
                        "ProviderOperation journal update version is invalid"
                    )
                _assert_immutable_identity(current.operation, operation)
            records[operation.id] = ProviderOperationRecord(
                operation=operation,
                persistence_version=persistence_version,
            )
        sequence += 1
        head = checksum
    return records, sequence, head


def _operation_from_dict(value: Mapping[str, Any]) -> ProviderOperation:
    reservation_value = value["reservation"]
    if not isinstance(reservation_value, Mapping):
        raise EvaluationOperationJournalError("Invalid ProviderOperation reservation")
    usage_value = value.get("actual_usage")
    usage = None
    if usage_value is not None:
        if not isinstance(usage_value, Mapping):
            raise EvaluationOperationJournalError("Invalid ProviderOperation usage")
        usage = ProviderUsage(
            provider=str(usage_value["provider"]),
            model_or_endpoint=str(usage_value["model_or_endpoint"]),
            operation_kind=ProviderOperationKind(str(usage_value["operation_kind"])),
            request_count=int(usage_value["request_count"]),
            input_tokens=_optional_int(usage_value.get("input_tokens")),
            output_tokens=_optional_int(usage_value.get("output_tokens")),
            estimated_cost_minor_units=_optional_int(
                usage_value.get("estimated_cost_minor_units")
            ),
            cost_currency=_optional_string(usage_value.get("cost_currency")),
            latency_ms=int(usage_value["latency_ms"]),
            retry_count=int(usage_value.get("retry_count", 0)),
            failure_category=(
                None
                if usage_value.get("failure_category") is None
                else ProviderFailureCategory(str(usage_value["failure_category"]))
            ),
            provider_request_ids=tuple(
                str(item) for item in usage_value.get("provider_request_ids", ())
            ),
            schema_version=str(usage_value["schema_version"]),
        )
    return ProviderOperation(
        id=str(value["id"]),
        project_id=str(value["project_id"]),
        workflow_run_id=str(value["workflow_run_id"]),
        logical_step_id=str(value["logical_step_id"]),
        step_run_id=_optional_string(value.get("step_run_id")),
        provider_category=ProviderCategory(str(value["provider_category"])),
        operation_kind=ProviderOperationKind(str(value["operation_kind"])),
        provider_identity=str(value["provider_identity"]),
        adapter_version=str(value["adapter_version"]),
        model_or_endpoint=str(value["model_or_endpoint"]),
        idempotency_key=str(value["idempotency_key"]),
        request_fingerprint=str(value["request_fingerprint"]),
        reservation=ProviderReservation(
            request_count=int(reservation_value["request_count"]),
            input_tokens=int(reservation_value["input_tokens"]),
            output_tokens=int(reservation_value["output_tokens"]),
            cost_minor_units=int(reservation_value["cost_minor_units"]),
            cost_currency=str(reservation_value["cost_currency"]),
        ),
        is_live_provider=bool(value.get("is_live_provider", False)),
        status=ProviderOperationStatus(str(value["status"])),
        settlement_state=SettlementState(str(value["settlement_state"])),
        actual_usage=usage,
        failure_category=(
            None
            if value.get("failure_category") is None
            else ProviderFailureCategory(str(value["failure_category"]))
        ),
        retry_count=int(value.get("retry_count", 0)),
        diagnostic_metadata=dict(value.get("diagnostic_metadata", {})),
        created_at=_timestamp(value["created_at"]),
        updated_at=_timestamp(value["updated_at"]),
        started_at=_optional_timestamp(value.get("started_at")),
        finished_at=_optional_timestamp(value.get("finished_at")),
        row_version=int(value.get("row_version", 0)),
        schema_version=str(value["schema_version"]),
    )


def _assert_immutable_identity(
    current: ProviderOperation,
    operation: ProviderOperation,
) -> None:
    fields = (
        "project_id",
        "workflow_run_id",
        "logical_step_id",
        "step_run_id",
        "provider_category",
        "operation_kind",
        "provider_identity",
        "adapter_version",
        "model_or_endpoint",
        "idempotency_key",
        "request_fingerprint",
        "reservation",
        "is_live_provider",
        "created_at",
    )
    if any(getattr(current, name) != getattr(operation, name) for name in fields):
        raise DuplicateEntityError(
            "ProviderOperation immutable request identity cannot change"
        )


def _timestamp(value: Any) -> datetime:
    return datetime.fromisoformat(str(value))


def _optional_timestamp(value: Any) -> datetime | None:
    return None if value is None else _timestamp(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_string(value: Any) -> str | None:
    return None if value is None else str(value)
