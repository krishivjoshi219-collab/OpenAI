"""Persistence adapter for business memories."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.memory.contracts import MemoryCategory
from app.models import BusinessMemory


class BusinessMemoryRepository:
    """Keep business-memory queries out of application services."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, memory: BusinessMemory) -> BusinessMemory:
        """Stage a memory for persistence."""

        self._session.add(memory)
        return memory

    def get(self, business_id: UUID, memory_id: UUID) -> BusinessMemory | None:
        """Find one memory while enforcing its owning business boundary."""

        return self._session.scalar(
            select(BusinessMemory).where(
                BusinessMemory.business_id == business_id,
                BusinessMemory.id == memory_id,
            )
        )

    def list(
        self,
        business_id: UUID,
        *,
        categories: frozenset[MemoryCategory] = frozenset(),
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[BusinessMemory]:
        """List recent business memories, optionally narrowed by category."""

        statement = self._base_statement(business_id, categories)
        return self._session.scalars(
            statement.order_by(BusinessMemory.updated_at.desc()).offset(offset).limit(limit)
        ).all()

    def keyword_search(
        self,
        business_id: UUID,
        query: str,
        *,
        categories: frozenset[MemoryCategory] = frozenset(),
        limit: int = 10,
    ) -> Sequence[BusinessMemory]:
        """Perform deterministic text retrieval until semantic search is installed."""

        statement = self._base_statement(business_id, categories).where(
            BusinessMemory.content.ilike(f"%{query.strip()}%")
        )
        return self._session.scalars(
            statement.order_by(BusinessMemory.updated_at.desc()).limit(limit)
        ).all()

    def delete(self, memory: BusinessMemory) -> None:
        """Stage a business memory for deletion."""

        self._session.delete(memory)

    @staticmethod
    def _base_statement(
        business_id: UUID, categories: frozenset[MemoryCategory]
    ) -> Select[tuple[BusinessMemory]]:
        statement = select(BusinessMemory).where(BusinessMemory.business_id == business_id)
        if categories:
            statement = statement.where(
                BusinessMemory.category.in_([item.value for item in categories])
            )
        return statement
