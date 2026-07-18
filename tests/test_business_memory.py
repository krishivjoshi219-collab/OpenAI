"""Tests for durable business memory and its future semantic retrieval boundary."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.memory import (
    BusinessMemoryService,
    CreateMemory,
    KeywordMemoryRetriever,
    MemoryCategory,
    MemoryQuery,
    UpdateMemory,
)
from app.memory.repository import BusinessMemoryRepository
from app.models import Business


def test_memory_crud_is_business_scoped() -> None:
    """A memory can be created, updated, listed, and deleted through the service."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        business = Business(name="Acme", slug="acme")
        session.add(business)
        session.flush()
        service = BusinessMemoryService(session)
        memory = service.create(
            business.id,
            CreateMemory(
                category=MemoryCategory.PAYMENT_TERMS,
                content="Net 30 for wholesale customers.",
            ),
        )
        updated = service.update(
            business.id,
            memory.id,
            UpdateMemory(content="Net 30 for approved wholesale customers."),
        )

        assert updated.content == "Net 30 for approved wholesale customers."
        assert service.list(business.id, categories=frozenset({MemoryCategory.PAYMENT_TERMS}))

        service.delete(business.id, memory.id)
        assert service.get(business.id, memory.id) is None


def test_keyword_retriever_implements_semantic_memory_port() -> None:
    """The deterministic retriever can later be replaced by vector-backed search."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        business = Business(name="Acme", slug="acme")
        session.add(business)
        session.flush()
        service = BusinessMemoryService(session)
        service.remember_preferred_language(business.id, "Use English in customer invoices.")

        retriever = KeywordMemoryRetriever(BusinessMemoryRepository(session))
        records = retriever.search(MemoryQuery(business_id=business.id, query="English"))

        assert len(records) == 1
        assert records[0].category is MemoryCategory.PREFERRED_LANGUAGE
