"""CRUD application service for durable, business-scoped memory."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Business, BusinessMemory
from app.memory.contracts import CreateMemory, MemoryCategory, MemoryRecord, UpdateMemory
from app.memory.repository import BusinessMemoryRepository


class BusinessMemoryService:
    """Create, read, update, and delete memories without exposing ORM details."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = BusinessMemoryRepository(session)

    def create(self, business_id: UUID, data: CreateMemory) -> MemoryRecord:
        """Store a typed memory after validating its business scope and content."""

        self._require_business(business_id)
        memory = BusinessMemory(
            business_id=business_id,
            category=data.category.value,
            content=_require_content(data.content),
            attributes=data.attributes,
            source=data.source,
        )
        self._repository.add(memory)
        self._session.flush()
        return memory_to_record(memory)

    def get(self, business_id: UUID, memory_id: UUID) -> MemoryRecord | None:
        """Get one memory only if it belongs to the requested business."""

        memory = self._repository.get(business_id, memory_id)
        return memory_to_record(memory) if memory is not None else None

    def list(
        self,
        business_id: UUID,
        *,
        categories: frozenset[MemoryCategory] = frozenset(),
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemoryRecord]:
        """List memories with validated pagination and optional category filtering."""

        _validate_page(limit, offset)
        return [
            memory_to_record(memory)
            for memory in self._repository.list(
                business_id, categories=categories, limit=limit, offset=offset
            )
        ]

    def update(self, business_id: UUID, memory_id: UUID, data: UpdateMemory) -> MemoryRecord:
        """Apply requested changes to a business-scoped memory."""

        memory = self._require_memory(business_id, memory_id)
        if data.content is not None:
            memory.content = _require_content(data.content)
        if data.attributes is not None:
            memory.attributes = data.attributes
        if data.source is not None:
            memory.source = data.source
        self._session.flush()
        return memory_to_record(memory)

    def delete(self, business_id: UUID, memory_id: UUID) -> None:
        """Delete one business-scoped memory."""

        self._repository.delete(self._require_memory(business_id, memory_id))
        self._session.flush()

    def remember_customer(
        self, business_id: UUID, content: str, attributes: dict[str, Any] | None = None
    ) -> MemoryRecord:
        """Store a customer-specific fact or preference."""

        return self._remember(business_id, MemoryCategory.CUSTOMER, content, attributes)

    def remember_supplier(
        self, business_id: UUID, content: str, attributes: dict[str, Any] | None = None
    ) -> MemoryRecord:
        """Store a supplier-specific fact or preference."""

        return self._remember(business_id, MemoryCategory.SUPPLIER, content, attributes)

    def remember_preferred_language(self, business_id: UUID, language: str) -> MemoryRecord:
        """Store the business's preferred communication language."""

        return self._remember(business_id, MemoryCategory.PREFERRED_LANGUAGE, language, None)

    def remember_payment_terms(self, business_id: UUID, terms: str) -> MemoryRecord:
        """Store the business's payment-term convention."""

        return self._remember(business_id, MemoryCategory.PAYMENT_TERMS, terms, None)

    def remember_invoice_style(self, business_id: UUID, style: str) -> MemoryRecord:
        """Store invoice presentation or numbering preferences."""

        return self._remember(business_id, MemoryCategory.INVOICE_STYLE, style, None)

    def remember_recurring_purchase(
        self, business_id: UUID, content: str, attributes: dict[str, Any] | None = None
    ) -> MemoryRecord:
        """Store a recurring purchase detail."""

        return self._remember(business_id, MemoryCategory.RECURRING_PURCHASE, content, attributes)

    def remember_preference(self, business_id: UUID, preference: str) -> MemoryRecord:
        """Store any other business-level operational preference."""

        return self._remember(business_id, MemoryCategory.BUSINESS_PREFERENCE, preference, None)

    def _remember(
        self,
        business_id: UUID,
        category: MemoryCategory,
        content: str,
        attributes: dict[str, Any] | None,
    ) -> MemoryRecord:
        return self.create(
            business_id,
            CreateMemory(category=category, content=content, attributes=attributes),
        )

    def _require_business(self, business_id: UUID) -> None:
        if self._session.get(Business, business_id) is None:
            raise ValueError("Business not found.")

    def _require_memory(self, business_id: UUID, memory_id: UUID) -> BusinessMemory:
        memory = self._repository.get(business_id, memory_id)
        if memory is None:
            raise ValueError("Business memory not found.")
        return memory


def memory_to_record(memory: BusinessMemory) -> MemoryRecord:
    """Translate an ORM entity into the stable application-memory contract."""

    return MemoryRecord(
        id=memory.id,
        business_id=memory.business_id,
        category=MemoryCategory(memory.category),
        content=memory.content,
        attributes=memory.attributes,
        source=memory.source,
    )


def _require_content(content: str) -> str:
    """Reject empty facts before they enter durable business memory."""

    normalized = content.strip()
    if not normalized:
        raise ValueError("Business memory content cannot be empty.")
    return normalized


def _validate_page(limit: int, offset: int) -> None:
    """Protect list queries from invalid or unbounded pagination."""

    if not 1 <= limit <= 1_000:
        raise ValueError("limit must be between 1 and 1000")
    if offset < 0:
        raise ValueError("offset must be zero or greater")
