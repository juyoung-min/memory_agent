"""Storage Backends for Memory Agent"""

from .memory_storage import MemoryStorage

# Optional import for pgvector storage (requires asyncpg)
try:
    from .pgvector_storage import PgVectorStorage
    __all__ = ['MemoryStorage', 'PgVectorStorage']
except ImportError:
    # pgvector storage requires additional dependencies
    PgVectorStorage = None
    __all__ = ['MemoryStorage']