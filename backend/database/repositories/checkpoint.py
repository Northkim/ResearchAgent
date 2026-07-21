"""SQLAlchemy append-only CheckpointRepository adapter."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.orm import CheckpointORM, CheckpointRecordORM
from backend.domain.models import Checkpoint
from backend.persistence.models import CheckpointBoundary, CheckpointRecord
from backend.persistence.ports import (
    CheckpointRepository,
    DuplicateEntityError,
)

from ._helpers import pending_by_id, pending_instances


class SQLAlchemyCheckpointRepository(CheckpointRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(
        self,
        checkpoint: Checkpoint,
        *,
        boundary: CheckpointBoundary,
        step_id: str | None = None,
        attempt: int | None = None,
    ) -> CheckpointRecord:
        checkpoint.verify_integrity()
        row = pending_by_id(self.session, CheckpointORM, checkpoint.id)
        if row is None:
            row = self.session.get(CheckpointORM, checkpoint.id)
        if row is not None:
            if self._to_domain(row) != checkpoint:
                raise DuplicateEntityError(
                    f"Checkpoint ID {checkpoint.id} has conflicting immutable content"
                )
        else:
            row = CheckpointORM(
                id=checkpoint.id,
                workflow_run_id=checkpoint.workflow_run_id,
                agent_session_id=checkpoint.agent_session_id,
                sequence=checkpoint.sequence,
                state_json=checkpoint.state_json,
                state_hash=checkpoint.state_hash,
                created_at=checkpoint.created_at,
                parent_id=checkpoint.parent_id,
            )
            self.session.add(row)

        records = self.list_records(checkpoint.workflow_run_id)
        for existing in records:
            if (
                existing.boundary == boundary
                and existing.checkpoint.id == checkpoint.id
                and existing.step_id == step_id
                and existing.attempt == attempt
            ):
                return existing

        record = CheckpointRecord(
            record_sequence=len(records) + 1,
            boundary=boundary,
            checkpoint=checkpoint,
            step_id=step_id,
            attempt=attempt,
        )
        self.session.add(
            CheckpointRecordORM(
                workflow_run_id=checkpoint.workflow_run_id,
                record_sequence=record.record_sequence,
                checkpoint_id=checkpoint.id,
                boundary=boundary.value,
                step_id=step_id,
                attempt=attempt,
            )
        )
        return record

    def get_latest(self, workflow_run_id: str) -> Checkpoint | None:
        checkpoints = self.list(workflow_run_id)
        return checkpoints[-1] if checkpoints else None

    def list(self, workflow_run_id: str) -> tuple[Checkpoint, ...]:
        unique: dict[str, Checkpoint] = {}
        for record in self.list_records(workflow_run_id):
            unique.setdefault(record.checkpoint.id, record.checkpoint)
        return tuple(
            sorted(unique.values(), key=lambda checkpoint: (checkpoint.sequence, checkpoint.id))
        )

    def list_records(self, workflow_run_id: str) -> tuple[CheckpointRecord, ...]:
        rows = list(
            self.session.scalars(
                select(CheckpointRecordORM)
                .where(CheckpointRecordORM.workflow_run_id == workflow_run_id)
                .order_by(CheckpointRecordORM.record_sequence)
            )
        )
        rows.extend(
            row
            for row in pending_instances(self.session, CheckpointRecordORM)
            if row.workflow_run_id == workflow_run_id and row not in rows
        )
        rows.sort(key=lambda row: row.record_sequence)
        return tuple(self._to_record(row) for row in rows)

    def _to_record(self, row: CheckpointRecordORM) -> CheckpointRecord:
        checkpoint_row = pending_by_id(
            self.session,
            CheckpointORM,
            row.checkpoint_id,
        )
        if checkpoint_row is None:
            checkpoint_row = self.session.get(CheckpointORM, row.checkpoint_id)
        if checkpoint_row is None:
            raise DuplicateEntityError(
                f"Checkpoint record references missing checkpoint {row.checkpoint_id}"
            )
        return CheckpointRecord(
            record_sequence=row.record_sequence,
            boundary=CheckpointBoundary(row.boundary),
            checkpoint=self._to_domain(checkpoint_row),
            step_id=row.step_id,
            attempt=row.attempt,
        )

    @staticmethod
    def _to_domain(row: CheckpointORM) -> Checkpoint:
        return Checkpoint(
            id=row.id,
            workflow_run_id=row.workflow_run_id,
            agent_session_id=row.agent_session_id,
            sequence=row.sequence,
            state_json=row.state_json,
            state_hash=row.state_hash,
            created_at=row.created_at,
            parent_id=row.parent_id,
        )
