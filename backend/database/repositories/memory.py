"""SQLAlchemy append-only working-memory repository."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.orm import MemoryRevisionORM
from backend.persistence.models import MemoryRevision
from backend.persistence.models._immutability import freeze_json, thaw_json
from backend.persistence.ports import MemoryRepository

from ._helpers import pending_instances


class SQLAlchemyMemoryRepository(MemoryRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def initialize_context(
        self,
        *,
        project_id: str,
        workflow_run_id: str,
        context: Mapping[str, Any],
        producer: str,
        source_references: tuple[str, ...] = (),
    ) -> MemoryRevision:
        existing = self.history(project_id, workflow_run_id)
        if existing:
            return existing[-1]
        return self.update_context(
            project_id=project_id,
            workflow_run_id=workflow_run_id,
            updates=context,
            producer=producer,
            source_references=source_references,
        )

    def read_context(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> Mapping[str, Any]:
        revisions = self.history(project_id, workflow_run_id)
        return revisions[-1].context if revisions else freeze_json({}, path="context")

    def update_context(
        self,
        *,
        project_id: str,
        workflow_run_id: str,
        updates: Mapping[str, Any],
        producer: str,
        source_references: tuple[str, ...] = (),
    ) -> MemoryRevision:
        history = self.history(project_id, workflow_run_id)
        merged = thaw_json(history[-1].context) if history else {}
        merged.update(thaw_json(freeze_json(updates, path="updates")))
        revision = MemoryRevision(
            project_id=project_id,
            workflow_run_id=workflow_run_id,
            revision=len(history) + 1,
            context=merged,
            producer=producer,
            source_references=source_references,
        )
        self.session.add(
            MemoryRevisionORM(
                project_id=project_id,
                workflow_run_id=workflow_run_id,
                revision=revision.revision,
                context_json=thaw_json(revision.context),
                producer=producer,
                source_references_json=list(source_references),
            )
        )
        return revision

    def history(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[MemoryRevision, ...]:
        rows = list(
            self.session.scalars(
                select(MemoryRevisionORM)
                .where(
                    MemoryRevisionORM.project_id == project_id,
                    MemoryRevisionORM.workflow_run_id == workflow_run_id,
                )
                .order_by(MemoryRevisionORM.revision)
            )
        )
        rows.extend(
            row
            for row in pending_instances(self.session, MemoryRevisionORM)
            if row.project_id == project_id
            and row.workflow_run_id == workflow_run_id
            and row not in rows
        )
        rows.sort(key=lambda row: row.revision)
        return tuple(
            MemoryRevision(
                project_id=row.project_id,
                workflow_run_id=row.workflow_run_id,
                revision=row.revision,
                context=row.context_json,
                producer=row.producer,
                source_references=tuple(row.source_references_json),
            )
            for row in rows
        )
