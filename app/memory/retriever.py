"""Deterministic retrieval implementation and future semantic-memory boundary."""

from app.memory.contracts import MemoryQuery, MemoryRecord, SemanticMemoryRetriever
from app.memory.repository import BusinessMemoryRepository
from app.memory.service import memory_to_record


class KeywordMemoryRetriever(SemanticMemoryRetriever):
    """Use business-scoped keyword matching until a semantic backend is configured."""

    def __init__(self, repository: BusinessMemoryRepository) -> None:
        self._repository = repository

    def search(self, query: MemoryQuery) -> list[MemoryRecord]:
        """Return matching memories through the current deterministic strategy."""

        if not query.query.strip():
            return []
        return [
            memory_to_record(memory)
            for memory in self._repository.keyword_search(
                query.business_id,
                query.query,
                categories=query.categories,
                limit=query.limit,
            )
        ]
