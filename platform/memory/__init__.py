"""Memory Module - Persistent State and Context Management.

Implements multi-tier memory for AI agents:
- Short-term: Conversation context (Redis)
- Long-term: Knowledge and facts (PostgreSQL + pgvector)
- Episodic: Past interaction summaries
"""

__version__ = "0.1.0"

from memory.store import MemoryStore, MemoryEntry
from memory.vector import VectorStore

__all__ = ["MemoryStore", "MemoryEntry", "VectorStore"]
