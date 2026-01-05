"""Vector Store - Semantic search over long-term memory.

Uses pgvector for similarity search over embedded content.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger()


@dataclass
class Document:
    """A document in the vector store."""
    id: UUID
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SearchResult:
    """Result from vector search."""
    document: Document
    score: float  # Similarity score (0-1)
    rank: int


class VectorStore:
    """PostgreSQL + pgvector based vector store.

    Features:
    - Semantic similarity search
    - Metadata filtering
    - Hybrid search (keyword + semantic)
    - Automatic embedding generation
    """

    def __init__(
        self,
        database_url: str | None = None,
        embedding_dimension: int = 1536,  # OpenAI ada-002
    ):
        if database_url is None:
            import os
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL environment variable is required")
        self._database_url = database_url
        self._embedding_dimension = embedding_dimension
        self._documents: dict[UUID, Document] = {}  # In-memory fallback

    async def add(
        self,
        content: str,
        embedding: list[float],
        metadata: Optional[dict] = None,
        source: Optional[str] = None,
    ) -> UUID:
        """Add a document to the vector store."""
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            source=source,
        )

        # TODO: Persist to PostgreSQL with pgvector
        # For now, use in-memory storage
        self._documents[doc_id] = doc

        logger.debug(
            "vector_store_add",
            doc_id=str(doc_id),
            content_length=len(content),
        )

        return doc_id

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        min_score: float = 0.7,
        metadata_filter: Optional[dict] = None,
    ) -> list[SearchResult]:
        """Search for similar documents.

        Args:
            query_embedding: Query vector
            limit: Max results to return
            min_score: Minimum similarity score
            metadata_filter: Filter by metadata fields

        Returns:
            List of search results ordered by similarity
        """
        results = []

        for doc in self._documents.values():
            # Apply metadata filter
            if metadata_filter:
                if not all(
                    doc.metadata.get(k) == v
                    for k, v in metadata_filter.items()
                ):
                    continue

            # Calculate cosine similarity
            score = self._cosine_similarity(query_embedding, doc.embedding)

            if score >= min_score:
                results.append(SearchResult(
                    document=doc,
                    score=score,
                    rank=0,  # Will be set after sorting
                ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        # Set ranks and limit
        for i, result in enumerate(results[:limit]):
            result.rank = i + 1

        return results[:limit]

    async def delete(self, doc_id: UUID) -> bool:
        """Delete a document."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            logger.debug("vector_store_delete", doc_id=str(doc_id))
            return True
        return False

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(x * x for x in b) ** 0.5

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)
