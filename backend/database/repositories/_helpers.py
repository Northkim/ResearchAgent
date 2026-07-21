"""Small helpers shared only by SQLAlchemy adapters."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


def pending_instances(session: Session, model_type: type[T]) -> Iterable[T]:
    return (
        instance
        for instance in session.new
        if isinstance(instance, model_type)
    )


def pending_by_id(
    session: Session,
    model_type: type[T],
    entity_id: str,
) -> T | None:
    return next(
        (
            instance
            for instance in pending_instances(session, model_type)
            if getattr(instance, "id", None) == entity_id
        ),
        None,
    )


def pending_by_composite_key(
    session: Session,
    model_type: type[T],
    key: tuple[object, ...],
    fields: tuple[str, ...],
) -> T | None:
    return next(
        (
            instance
            for instance in pending_instances(session, model_type)
            if tuple(getattr(instance, field) for field in fields) == key
        ),
        None,
    )
