"""Typed memory categories and retrieval contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID


class MemoryCategory(StrEnum):
    """Business facts and preferences retained for future AI assistance."""

    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    PREFERRED_LANGUAGE = "preferred_language"
    PAYMENT_TERMS = "payment_terms"
    INVOICE_STYLE = "invoice_style"
    RECURRING_PURCHASE = "recurring_purchase"
    BUSINESS_PREFERENCE = "business_preference"


@dataclass(frozen=True)
class CreateMemory:
    """Data required to persist one business-scoped memory."""

    category: MemoryCategory
    content: str
    attributes: dict[str, Any] | None = None
    source: str = "manual"


@dataclass(frozen=True)
class UpdateMemory:
    """Optional mutations for an existing memory."""

    content: str | None = None
    attributes: dict[str, Any] | None = None
    source: str | None = None


@dataclass(frozen=True)
class MemoryRecord:
    """Application-facing representation of a stored memory."""

    id: UUID
    business_id: UUID
    category: MemoryCategory
    content: str
    attributes: dict[str, Any] | None
    source: str | None


@dataclass(frozen=True)
class MemoryQuery:
    """Criteria for deterministic or future semantic memory retrieval."""

    business_id: UUID
    query: str
    categories: frozenset[MemoryCategory] = field(default_factory=frozenset)
    limit: int = 10


class SemanticMemoryRetriever(Protocol):
    """Port that a future vector or hybrid memory backend can implement."""

    def search(self, query: MemoryQuery) -> list[MemoryRecord]:
        """Return the most relevant memories for a business-scoped query."""
