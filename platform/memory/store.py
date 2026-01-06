"""Memory Store - Redis-backed short-term memory.

Provides fast access to conversation context and session state.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import structlog

logger = structlog.get_logger()


@dataclass
class MemoryEntry:
    """A memory entry."""
    id: str
    session_id: str
    content: str
    role: str  # user, assistant, system, tool
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class MemoryStore:
    """Redis-backed memory store for conversation context.

    Features:
    - Session-scoped memory
    - TTL-based expiration
    - Memory summarization
    - Cross-session retrieval
    """

    def __init__(self, redis_url: str | None = None):
        if redis_url is None:
            import os
            redis_url = os.environ.get("REDIS_URL")
            if not redis_url:
                raise ValueError("REDIS_URL environment variable is required")
        self._redis_url = redis_url
        self._client = None  # Lazy initialization
        self._local_cache: dict[str, list[MemoryEntry]] = {}

    async def _get_client(self):
        """Get Redis client (lazy initialization)."""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(self._redis_url, decode_responses=True)
            except ImportError:
                logger.warning("Redis not available, using local cache")
        return self._client

    async def add(self, entry: MemoryEntry) -> None:
        """Add a memory entry."""
        logger.debug(
            "memory_add",
            session_id=entry.session_id,
            role=entry.role,
        )

        # Add to local cache
        if entry.session_id not in self._local_cache:
            self._local_cache[entry.session_id] = []
        self._local_cache[entry.session_id].append(entry)

        # Persist to Redis if available
        client = await self._get_client()
        if client:
            import json
            key = f"memory:{entry.session_id}:{entry.id}"
            value = json.dumps({
                "id": entry.id,
                "session_id": entry.session_id,
                "content": entry.content,
                "role": entry.role,
                "metadata": entry.metadata,
                "created_at": entry.created_at.isoformat(),
            })
            await client.set(key, value)

            # Add to session list
            await client.rpush(f"memory:session:{entry.session_id}", entry.id)

    async def get_session(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        """Get memory entries for a session."""
        # Try local cache first
        if session_id in self._local_cache:
            entries = self._local_cache[session_id]
            return entries[-limit:] if len(entries) > limit else entries

        # Try Redis
        client = await self._get_client()
        if client:
            import json
            entry_ids = await client.lrange(
                f"memory:session:{session_id}", -limit, -1
            )
            entries = []
            for entry_id in entry_ids:
                # With decode_responses=True, entry_id is already a string
                data = await client.get(f"memory:{session_id}:{entry_id}")
                if data:
                    try:
                        parsed = json.loads(data)
                        created_at = datetime.fromisoformat(parsed["created_at"])
                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        logger.warning("memory_entry_parse_error", entry_id=entry_id, error=str(e))
                        continue
                    entries.append(MemoryEntry(
                        id=parsed["id"],
                        session_id=parsed["session_id"],
                        content=parsed["content"],
                        role=parsed["role"],
                        metadata=parsed.get("metadata", {}),
                        created_at=created_at,
                    ))
            return entries

        return []

    async def clear_session(self, session_id: str) -> None:
        """Clear all memory for a session."""
        logger.info("memory_clear_session", session_id=session_id)

        # Clear local cache
        if session_id in self._local_cache:
            del self._local_cache[session_id]

        # Clear Redis
        client = await self._get_client()
        if client:
            entry_ids = await client.lrange(f"memory:session:{session_id}", 0, -1)
            for entry_id in entry_ids:
                # With decode_responses=True, entry_id is already a string
                await client.delete(f"memory:{session_id}:{entry_id}")
            await client.delete(f"memory:session:{session_id}")

    async def summarize_session(self, session_id: str) -> Optional[str]:
        """Generate a summary of the session memory.

        Used for long-running conversations to compress context.
        """
        entries = await self.get_session(session_id)
        if not entries:
            return None

        # TODO: Use LLM to generate summary
        # For now, return concatenated content
        content = "\n".join(
            f"{e.role}: {e.content[:100]}..." for e in entries
        )
        return f"Session summary ({len(entries)} messages):\n{content}"
