"""Generic repository implementation for SQLAlchemy entities."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    """Encapsulate basic persistence operations without owning transactions."""

    def __init__(self, session: Session, model_type: type[ModelT]) -> None:
        self._session = session
        self._model_type = model_type

    def add(self, entity: ModelT) -> ModelT:
        """Stage an entity for insertion or update and return it."""

        self._session.add(entity)
        return entity

    def get(self, entity_id: UUID) -> ModelT | None:
        """Find an entity by primary key."""

        return self._session.get(self._model_type, entity_id)

    def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[ModelT]:
        """Return a bounded page of entities ordered by creation time."""

        if offset < 0:
            raise ValueError("offset must be zero or greater")
        if not 1 <= limit <= 1_000:
            raise ValueError("limit must be between 1 and 1000")
        created_at = getattr(self._model_type, "created_at")
        statement = select(self._model_type).order_by(created_at).offset(offset).limit(limit)
        return self._session.scalars(statement).all()

    def delete(self, entity: ModelT) -> None:
        """Stage an entity for deletion."""

        self._session.delete(entity)

    def flush(self) -> None:
        """Synchronize staged work without committing the transaction."""

        self._session.flush()
