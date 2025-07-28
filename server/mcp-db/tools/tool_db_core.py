"""
Pure database operations for DB-MCP
No embedding generation - only stores pre-computed vectors
"""

import json
import logging
import asyncpg
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from mcp_instance import mcp
from src.database.connection import get_db_connection

logger = logging.getLogger(__name__)

@mcp.tool(description="Store a vector with metadata")
async def db_store_vector(
    table: str = 'memories',
    content: str = None,
    vector: List[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None
) -> str:
    """
    Store a pre-computed vector in the database.
    
    Parameters:
    - table: Table name (default: memories)
    - content: Text content
    - vector: Pre-computed vector (list of floats)
    - metadata: Additional metadata (JSON)
    - id: Optional ID (auto-generated if not provided)
    """
    
    if metadata is None:
        metadata = {}
    record_id = id or str(uuid.uuid4())
    
    # Validate required parameters
    if not content or not vector:
        return json.dumps({
            "success": False,
            "error": "content and vector are required",
            "error_type": "ValidationError"
        })
    
    # Validate vector is a list of numbers
    if not isinstance(vector, list) or not all(isinstance(x, (int, float)) for x in vector):
        return json.dumps({
            "success": False,
            "error": "vector must be a list of numbers",
            "error_type": "ValidationError"
        })
    
    try:
        async with get_db_connection() as conn:
            # Convert vector to PostgreSQL format
            vector_str = f"[{','.join(map(str, vector))}]"
            
            # Add timestamp to metadata
            metadata['stored_at'] = datetime.utcnow().isoformat()
            
            # Insert into table
            await conn.execute(f"""
                INSERT INTO {table} (id, content, embedding, metadata)
                VALUES ($1, $2, $3::vector, $4)
                ON CONFLICT (id) DO UPDATE
                SET content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """, record_id, content, vector_str, json.dumps(metadata))
            
            logger.info(f"Stored vector with ID: {record_id}")
            
            return json.dumps({
                "success": True,
                "id": record_id,
                "table": table
            })
            
    except asyncpg.PostgresError as e:
        logger.error(f"Database error: {e}")
        return json.dumps({
            "success": False,
            "error": f"Database error: {str(e)}",
            "error_type": "DatabaseError"
        })
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__
        })

@mcp.tool(description="Batch store multiple vectors")
async def db_batch_store_vectors(
    table: str = 'memories',
    items: List[Dict[str, Any]] = None
) -> str:
    """
    Store multiple vectors in a single operation.
    
    Parameters:
    - table: Table name
    - items: List of items with {id, content, vector, metadata}
    """
    
    if items is None:
        items = []
    
    if not items:
        return json.dumps({
            "success": False,
            "error": "items list is required",
            "error_type": "ValidationError"
        })
    
    try:
        async with get_db_connection() as conn:
            # Prepare batch data
            values = []
            for item in items:
                record_id = item.get('id', str(uuid.uuid4()))
                content = item.get('content')
                vector = item.get('vector')
                metadata = item.get('metadata', {})
                
                if not content or not vector:
                    continue
                
                # Add timestamp
                metadata['stored_at'] = datetime.utcnow().isoformat()
                
                # Convert vector to string
                vector_str = f"[{','.join(map(str, vector))}]"
                
                values.append((record_id, content, vector_str, json.dumps(metadata)))
            
            # Batch insert
            if values:
                await conn.executemany(f"""
                    INSERT INTO {table} (id, content, embedding, metadata)
                    VALUES ($1, $2, $3::vector, $4)
                    ON CONFLICT (id) DO UPDATE
                    SET content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                """, values)
            
            return json.dumps({
                "success": True,
                "stored": len(values),
                "total": len(items),
                "table": table
            })
            
    except Exception as e:
        logger.error(f"Batch store error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Search vectors by similarity")
async def db_search_vectors(
    table: str = 'memories',
    query_vector: List[float] = None,
    limit: int = 10,
    similarity_threshold: float = 0.0,
    filters: Optional[Dict[str, Any]] = None
) -> str:
    """
    Search for similar vectors using pre-computed query vector.
    
    Parameters:
    - table: Table name
    - query_vector: Pre-computed query vector
    - limit: Maximum results (default: 10)
    - similarity_threshold: Minimum similarity (0-1)
    - filters: Metadata filters (JSON)
    """
    
    if filters is None:
        filters = {}
    
    if not query_vector:
        return json.dumps({
            "success": False,
            "error": "query_vector is required",
            "error_type": "ValidationError"
        })
    
    try:
        async with get_db_connection() as conn:
            # Convert query vector to string
            query_vector_str = f"[{','.join(map(str, query_vector))}]"
            
            # Build filter conditions
            filter_conditions = []
            filter_values = [query_vector_str, limit]
            param_count = 2
            
            if similarity_threshold > 0:
                filter_conditions.append(f"(1 - (embedding <=> $1)) >= ${param_count + 1}")
                filter_values.append(similarity_threshold)
                param_count += 1
            
            # Add metadata filters
            for key, value in filters.items():
                param_count += 1
                filter_conditions.append(f"metadata->>'{key}' = ${param_count}")
                filter_values.append(str(value))
            
            where_clause = "WHERE " + " AND ".join(filter_conditions) if filter_conditions else ""
            
            # Execute search query
            query = f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> $1) as similarity
                FROM {table}
                {where_clause}
                ORDER BY embedding <=> $1
                LIMIT $2
            """
            
            rows = await conn.fetch(query, *filter_values)
            
            # Format results
            results = []
            for row in rows:
                results.append({
                    "id": row['id'],
                    "content": row['content'],
                    "metadata": json.loads(row['metadata']) if row['metadata'] else {},
                    "similarity": float(row['similarity'])
                })
            
            return json.dumps({
                "success": True,
                "results": results,
                "count": len(results),
                "table": table
            })
            
    except Exception as e:
        logger.error(f"Search error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Delete vectors by IDs")
async def db_delete_vectors(
    table: str = 'memories',
    ids: List[str] = None
) -> str:
    """Delete vectors from the database by their IDs"""
    
    if ids is None:
        ids = []
    
    if not ids:
        return json.dumps({
            "success": False,
            "error": "ids list is required",
            "error_type": "ValidationError"
        })
    
    try:
        async with get_db_connection() as conn:
            # Delete records
            result = await conn.execute(f"""
                DELETE FROM {table}
                WHERE id = ANY($1)
            """, ids)
            
            # Extract number of deleted rows
            deleted_count = int(result.split()[-1])
            
            return json.dumps({
                "success": True,
                "deleted": deleted_count,
                "requested": len(ids),
                "table": table
            })
            
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Update vector metadata")
async def db_update_metadata(
    table: str = 'memories',
    id: str = None,
    metadata: Optional[Dict[str, Any]] = None,
    merge: bool = True
) -> str:
    """Update metadata for a vector record"""
    
    record_id = id
    if metadata is None:
        metadata = {}
    
    if not record_id:
        return json.dumps({
            "success": False,
            "error": "id is required",
            "error_type": "ValidationError"
        })
    
    try:
        async with get_db_connection() as conn:
            if merge:
                # Fetch existing metadata
                existing = await conn.fetchval(f"""
                    SELECT metadata FROM {table} WHERE id = $1
                """, record_id)
                
                if existing:
                    existing_metadata = json.loads(existing) if existing else {}
                    existing_metadata.update(metadata)
                    metadata = existing_metadata
            
            # Update metadata
            metadata['updated_at'] = datetime.utcnow().isoformat()
            
            result = await conn.execute(f"""
                UPDATE {table}
                SET metadata = $2, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            """, record_id, json.dumps(metadata))
            
            # Check if record was updated
            updated = int(result.split()[-1]) > 0
            
            return json.dumps({
                "success": updated,
                "id": record_id,
                "message": "Metadata updated" if updated else "Record not found",
                "table": table
            })
            
    except Exception as e:
        logger.error(f"Update error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Create a vector table")
async def db_create_vector_table(
    table_name: str = None,
    dimension: int = 1536,
    additional_columns: Optional[Dict[str, str]] = None
) -> str:
    """Create a new table with vector support"""
    
    if additional_columns is None:
        additional_columns = {}
    
    if not table_name:
        return json.dumps({
            "success": False,
            "error": "table_name is required",
            "error_type": "ValidationError"
        })
    
    try:
        async with get_db_connection() as conn:
            # Build additional columns SQL
            extra_columns = ""
            for col_name, col_type in additional_columns.items():
                extra_columns += f",\n    {col_name} {col_type}"
            
            # Create table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({dimension}),
                    metadata JSONB DEFAULT '{{}}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    {extra_columns}
                )
            """)
            
            # Create indexes
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_embedding 
                ON {table_name} USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_metadata 
                ON {table_name} USING gin (metadata)
            """)
            
            return json.dumps({
                "success": True,
                "table": table_name,
                "dimension": dimension,
                "message": f"Table {table_name} created successfully"
            })
            
    except Exception as e:
        logger.error(f"Create table error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Get table information")
async def db_describe_table(
    table_name: str = None
) -> str:
    """Get information about a table including schema and statistics"""
    
    if not table_name:
        return json.dumps({
            "success": False,
            "error": "table_name is required",
            "error_type": "ValidationError"
        })
    
    try:
        async with get_db_connection() as conn:
            # Get table columns
            columns = await conn.fetch("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table_name)
            
            if not columns:
                return json.dumps({
                    "success": False,
                    "error": f"Table {table_name} not found",
                    "error_type": "NotFoundError"
                })
            
            # Get row count
            row_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            
            # Get indexes
            indexes = await conn.fetch("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = $1
            """, table_name)
            
            # Format response
            column_info = [
                {
                    "name": col['column_name'],
                    "type": col['data_type'],
                    "nullable": col['is_nullable'] == 'YES',
                    "default": col['column_default']
                }
                for col in columns
            ]
            
            index_info = [
                {
                    "name": idx['indexname'],
                    "definition": idx['indexdef']
                }
                for idx in indexes
            ]
            
            return json.dumps({
                "success": True,
                "table": table_name,
                "columns": column_info,
                "indexes": index_info,
                "row_count": row_count
            })
            
    except Exception as e:
        logger.error(f"Describe table error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })