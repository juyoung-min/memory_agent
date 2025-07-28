"""
PostgreSQL pgvector Storage Backend
Real vector database implementation for memory storage
"""

import asyncio
try:
    import asyncpg
except ImportError:
    raise ImportError("asyncpg is required for PgVectorStorage. Install with: pip install asyncpg")

try:
    import numpy as np
except ImportError:
    # numpy is optional, we can work without it
    np = None
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging

try:
    from ..memory_agent.memory_types import Memory, MemoryType
except ImportError:
    # Fallback for direct script execution
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from memory_agent.memory_types import Memory, MemoryType

class PgVectorStorage:
    """
    PostgreSQL with pgvector extension for memory storage
    Provides real vector database capabilities with embedding storage
    """
    
    def __init__(self, connection_string: str = None, embedding_dimension: int = 1536):
        """
        Initialize pgvector storage
        
        Args:
            connection_string: PostgreSQL connection string
            embedding_dimension: Vector embedding dimension (default 1536 for OpenAI)
        """
        self.connection_string = connection_string or self._get_default_connection_string()
        self.embedding_dimension = embedding_dimension
        self.pool = None
        self.logger = logging.getLogger(__name__)
    
    def _get_default_connection_string(self) -> str:
        """Get default connection string from environment or use local default"""
        import os
        
        # Try environment variables first
        if os.getenv('DATABASE_URL'):
            return os.getenv('DATABASE_URL')
        
        # Try supabase format
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if supabase_url and supabase_key:
            # Extract database details from supabase URL
            # Format: https://xxxxx.supabase.co
            db_host = supabase_url.replace('https://', '').replace('http://', '')
            db_name = 'postgres'
            db_user = 'postgres'
            db_password = os.getenv('SUPABASE_DB_PASSWORD', supabase_key)
            
            return f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"
        
        # Default local PostgreSQL
        return "postgresql://postgres:password@localhost:5432/memory_agent"
    
    async def initialize(self):
        """Initialize connection pool and create tables"""
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=30
            )
            
            # Create tables and extensions
            await self._create_tables()
            
            self.logger.info("PgVector storage initialized successfully")
            print("✅ PostgreSQL pgvector storage initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize pgvector storage: {e}")
            print(f"❌ PostgreSQL initialization failed: {e}")
            raise
    
    async def _create_tables(self):
        """Create necessary tables and enable pgvector extension"""
        
        async with self.pool.acquire() as connection:
            # Enable pgvector extension
            await connection.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create memories table with vector column
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS memories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(255) NOT NULL,
                session_id VARCHAR(255) NOT NULL,
                type VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                importance REAL DEFAULT 5.0,
                embedding vector({self.embedding_dimension}),
                metadata JSONB DEFAULT '{{}}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            
            await connection.execute(create_table_sql)
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id);",
                "CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);",
                "CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);",
                "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_memories_user_session ON memories(user_id, session_id);",
                # Vector similarity index (IVFFlat for large datasets)
                f"CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
            ]
            
            for index_sql in indexes:
                try:
                    await connection.execute(index_sql)
                except Exception as e:
                    # Some indexes might already exist or fail, that's ok
                    self.logger.warning(f"Index creation warning: {e}")
    
    async def store_memory(self, memory: Memory) -> bool:
        """
        Store memory with vector embedding in PostgreSQL
        """
        try:
            # Generate embedding for the content
            embedding = await self._generate_embedding(memory.content)
            
            async with self.pool.acquire() as connection:
                insert_sql = """
                INSERT INTO memories (user_id, session_id, type, content, importance, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id;
                """
                
                # Convert metadata to JSON
                metadata_json = json.dumps(memory.metadata) if memory.metadata else '{}'
                
                result = await connection.fetchval(
                    insert_sql,
                    memory.user_id,
                    memory.session_id,
                    memory.type.value,
                    memory.content,
                    memory.importance,
                    embedding,
                    metadata_json
                )
                
                # Update memory with database-generated ID
                memory.id = str(result)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to store memory: {e}")
            return False
    
    async def search_memories(self, user_id: str, session_id: str = None, 
                            query: str = "", memory_types: List[MemoryType] = None,
                            limit: int = 10, similarity_threshold: float = 0.7) -> List[Memory]:
        """
        Search memories using vector similarity and traditional filters
        """
        try:
            async with self.pool.acquire() as connection:
                
                # Base SQL query
                base_sql = """
                SELECT id, user_id, session_id, type, content, importance, metadata, created_at
                FROM memories
                WHERE user_id = $1
                """
                
                params = [user_id]
                param_count = 1
                
                # Add session filter
                if session_id:
                    param_count += 1
                    base_sql += f" AND session_id = ${param_count}"
                    params.append(session_id)
                
                # Add type filter
                if memory_types:
                    param_count += 1
                    type_values = [mt.value for mt in memory_types]
                    base_sql += f" AND type = ANY(${param_count})"
                    params.append(type_values)
                
                # Add vector similarity search if query provided
                if query.strip():
                    query_embedding = await self._generate_embedding(query)
                    param_count += 1
                    base_sql += f" AND (1 - (embedding <=> ${param_count})) >= {similarity_threshold}"
                    params.append(query_embedding)
                    
                    # Order by similarity
                    base_sql += f" ORDER BY embedding <=> ${param_count}"
                else:
                    # Order by importance and recency if no query
                    base_sql += " ORDER BY importance DESC, created_at DESC"
                
                # Add limit
                param_count += 1
                base_sql += f" LIMIT ${param_count}"
                params.append(limit)
                
                rows = await connection.fetch(base_sql, *params)
                
                memories = []
                for row in rows:
                    memory = Memory(
                        user_id=row['user_id'],
                        session_id=row['session_id'],
                        type=MemoryType(row['type']),
                        content=row['content'],
                        importance=row['importance']
                    )
                    memory.id = str(row['id'])
                    memory.timestamp = row['created_at']
                    memory.metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    memories.append(memory)
                
                return memories
                
        except Exception as e:
            self.logger.error(f"Failed to search memories: {e}")
            return []
    
    async def get_user_memories(self, user_id: str, session_id: str = None, 
                               limit: int = 100) -> List[Memory]:
        """Get all memories for a user, optionally filtered by session"""
        return await self.search_memories(user_id, session_id, "", None, limit, 0.0)
    
    async def get_memory_stats(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            async with self.pool.acquire() as connection:
                
                # Base query conditions
                where_clause = "WHERE user_id = $1"
                params = [user_id]
                
                if session_id:
                    where_clause += " AND session_id = $2"
                    params.append(session_id)
                
                # Get total count and average importance
                stats_sql = f"""
                SELECT 
                    COUNT(*) as total_memories,
                    AVG(importance) as avg_importance,
                    MIN(importance) as min_importance,
                    MAX(importance) as max_importance
                FROM memories {where_clause}
                """
                
                stats_row = await connection.fetchrow(stats_sql, *params)
                
                # Get type distribution
                type_sql = f"""
                SELECT type, COUNT(*) as count
                FROM memories {where_clause}
                GROUP BY type
                """
                
                type_rows = await connection.fetch(type_sql, *params)
                type_distribution = {row['type']: row['count'] for row in type_rows}
                
                # Get session distribution (if not filtering by session)
                session_distribution = {}
                if not session_id:
                    session_sql = """
                    SELECT session_id, COUNT(*) as count
                    FROM memories WHERE user_id = $1
                    GROUP BY session_id
                    """
                    session_rows = await connection.fetch(session_sql, user_id)
                    session_distribution = {row['session_id']: row['count'] for row in session_rows}
                
                return {
                    "total_memories": stats_row['total_memories'] or 0,
                    "average_importance": float(stats_row['avg_importance'] or 0),
                    "importance_range": {
                        "min": float(stats_row['min_importance'] or 0),
                        "max": float(stats_row['max_importance'] or 0)
                    },
                    "type_distribution": type_distribution,
                    "session_distribution": session_distribution,
                    "user_id": user_id,
                    "session_id": session_id
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}
    
    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing memory"""
        try:
            async with self.pool.acquire() as connection:
                
                # Build update query dynamically
                set_clauses = []
                params = []
                param_count = 0
                
                for key, value in updates.items():
                    if key in ['content', 'importance', 'metadata']:
                        param_count += 1
                        set_clauses.append(f"{key} = ${param_count}")
                        
                        if key == 'metadata':
                            params.append(json.dumps(value))
                        else:
                            params.append(value)
                
                if not set_clauses:
                    return False
                
                # Add updated_at timestamp
                param_count += 1
                set_clauses.append(f"updated_at = ${param_count}")
                params.append(datetime.now())
                
                # Add memory_id for WHERE clause
                param_count += 1
                params.append(memory_id)
                
                update_sql = f"""
                UPDATE memories 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
                """
                
                # If content is updated, also update embedding
                if 'content' in updates:
                    new_embedding = await self._generate_embedding(updates['content'])
                    param_count += 1
                    update_sql = update_sql.replace(
                        f"WHERE id = ${param_count-1}",
                        f", embedding = ${param_count} WHERE id = ${param_count-1}"
                    )
                    params.insert(-1, new_embedding)  # Insert before memory_id
                
                result = await connection.execute(update_sql, *params)
                
                return result == "UPDATE 1"
                
        except Exception as e:
            self.logger.error(f"Failed to update memory: {e}")
            return False
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID"""
        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(
                    "DELETE FROM memories WHERE id = $1",
                    memory_id
                )
                
                return result == "DELETE 1"
                
        except Exception as e:
            self.logger.error(f"Failed to delete memory: {e}")
            return False
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text
        This is a placeholder - you should implement actual embedding generation
        using OpenAI API, sentence-transformers, or your preferred method
        """
        # Placeholder: Simple hash-based embedding for demo
        # In production, use actual embeddings like:
        # - OpenAI embeddings API
        # - sentence-transformers
        # - Custom embedding model
        
        import hashlib
        
        # Create deterministic "embedding" from text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to float values between -1 and 1
        embedding = []
        for i in range(0, len(text_hash), 2):
            hex_val = text_hash[i:i+2]
            float_val = (int(hex_val, 16) - 127.5) / 127.5  # Normalize to [-1, 1]
            embedding.append(float_val)
        
        # Pad or truncate to desired dimension
        while len(embedding) < self.embedding_dimension:
            embedding.extend(embedding[:min(len(embedding), self.embedding_dimension - len(embedding))])
        
        return embedding[:self.embedding_dimension]
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about the storage backend"""
        return {
            "backend_type": "PostgreSQL_pgvector",
            "embedding_dimension": self.embedding_dimension,
            "connection_string": self.connection_string.replace(
                self.connection_string.split('@')[0].split('://')[-1], 
                "***"  # Hide credentials
            ) if '@' in self.connection_string else self.connection_string,
            "supports_vector_search": True,
            "supports_session_id": True,
            "supports_search": True,
            "supports_filtering": True,
            "supports_similarity_search": True
        }
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            print("✅ PostgreSQL connection pool closed")